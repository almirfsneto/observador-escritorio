"""Instrumentation and extra synthetic fixture for the visible acceptance laboratory."""
import subprocess
import threading
import time

from .acceptance_metrics import OwnedSampler
from .acceptance_report import empty_session
from .acceptance_review import NativeHealthObservation
from .lab_controller import LaboratoryWindow


def termination_for_stop(fixture, session):
    """Classify before the base controller changes every stream into stopped."""
    if fixture and fixture.poll() is not None:
        return 'fixture_exit'
    if session is None:
        return 'not_started'
    stream = session.stream
    if stream.clock() >= stream.expires_at or stream.monotonic() >= stream.deadline:
        return 'expired'
    return 'backend_error' if stream.stopped else 'operator_stop'


class SessionRecorder:
    def __init__(self, *, clock=time.monotonic):
        self.data = empty_session()
        self.native_health=NativeHealthObservation()
        self.clock = clock
        self.start_at = self.pause_at = self.pause_generation = None

    def request_start(self):
        self.start_at = self.clock()

    def request_pause(self, generation):
        if self.pause_at is not None:
            self.data['metrics']['pause_unconfirmed'] += 1
        self.pause_at, self.pause_generation = self.clock(), generation

    def observe(self, stream):
        if stream.health == 'active' and self.start_at is not None:
            self.data['capture_started'] = True
            self.data['metrics']['start_to_active_ack_ms'] = max(0, (self.clock() - self.start_at) * 1000)
            self.start_at = None
        if self.pause_at is not None:
            if stream.generation != self.pause_generation or stream.stopped:
                self.data['metrics']['pause_unconfirmed'] += 1
                self.pause_at = self.pause_generation = None
            elif stream.health == 'paused' and stream.pending_ack_at is None:
                value = max(0, (self.clock() - self.pause_at) * 1000)
                self.data['metrics']['pause_ack_samples'] += 1
                self.data['metrics']['pause_ack_peak_ms'] = max(self.data['metrics']['pause_ack_peak_ms'] or 0, value)
                self.pause_at = self.pause_generation = None
        counts = self.data['counters']
        counts.update(native_dropped=stream.native_dropped, python_dropped=stream.dropped,
                      sequence_gaps=stream.sequence_gaps, invalid_messages=stream.invalid)
        self.native_health.observe(stream)

    def events(self, events):
        if events:
            self.data['capture_started'] = True
        for event in events:
            self.data['counters']['events_accepted'] += 1
            self.data['counters'][event.action] += 1


class AcceptanceLaboratory(LaboratoryWindow):
    def __init__(self, tk, *, root, preparation, data_target, sampler_factory=OwnedSampler):
        from .acceptance_prepare import binaries
        self.preparation = preparation
        self.recorder = SessionRecorder()
        self.secondary = None
        self.sampling_closed = False
        self.sampling_lock = threading.RLock()
        self.sampler = sampler_factory(self.recorder.data)
        paths = binaries(preparation.root)
        super().__init__(tk, root=root, fixture_target=paths['fixture'], observer_target=paths['provider'], data_target=data_target)
        self.root.title('Observador | Aceite guiado — somente laboratório')
        self.secondary_btn = tk.Button(self.root, text='Abrir segunda instância fictícia (não observada)',
                                       command=self.launch_secondary)
        self.secondary_btn.pack(pady=4)
        self.root.geometry('800x580')
        self.sampler.register('controller', current_controller=True)

    def launch_fixture(self):
        if not self.preparation.verify_artifacts():
            self.status_var.set('Hashes mudaram ou preparação incompleta. Prepare novamente; coleta não iniciada.')
            return
        before = time.monotonic()
        super().launch_fixture()
        if self.fixture:
            self.recorder.data['metrics']['fixture_launch_call_ms'] = (time.monotonic() - before) * 1000
            self.sampler.register('fixture', self.fixture)

    def launch_secondary(self):
        if self.finished or self.secondary or not self.preparation.verify_artifacts():
            return
        try:
            self.secondary = subprocess.Popen([str(self.target)], cwd=str(self.target.parent))
            self.sampler.register('fixture_secondary', self.secondary)
            self.secondary_btn.config(state=self.tk.DISABLED)
            self.append('Segunda instância aberta. Apenas a primeira permanece autorizada; compare o contador.')
        except OSError:
            self.append('Segunda instância não pôde ser aberta. Registre NÃO EXECUTADO ou FALHOU.')

    def start(self):
        if not self.preparation.verify_artifacts():
            self.append('Hashes não conferem. Nenhuma coleta iniciada; prepare novamente.')
            return
        self.recorder.request_start()
        super().start()
        if self.session:
            self.recorder.data['persistence_enabled'] = self.persist.get()
            self.sampler.register('provider', self.session.process)

    def toggle_pause(self):
        pausing = self.session is not None and self.session.stream.enabled
        super().toggle_pause()
        if pausing and self.session:
            self.recorder.request_pause(self.session.stream.generation)

    def on_events(self, events):
        self.recorder.events(events)

    def tick(self):
        if self.closed:
            return
        if not self.finished:
            if self.session:
                stream = self.session.stream
                self.recorder.observe(stream)
            with self.sampling_lock:
                if not self.sampling_closed:
                    self.sampler.sample()
        if self.sink:
            self.recorder.data['counters'].update(queue_written=self.sink.written,
                queue_discarded=self.sink.discarded, queue_purged=self.sink.purged)
        super().tick()

    def stop(self):
        if self.finished:
            return
        if self.session:
            self.recorder.observe(self.session.stream)
        if self.recorder.data['termination'] == 'not_started':
            self.recorder.data['termination'] = termination_for_stop(self.fixture, self.session)
        if hasattr(self, 'secondary_btn'):
            self.secondary_btn.config(state=self.tk.DISABLED)
        super().stop()

    def close(self):
        if not self.finished:
            self.recorder.data['termination'] = 'window_close'
        super().close()

    def _cleanup(self):
        status=self.cleanup_status
        if status.finished:return
        self._cleanup_resources(status)
        status.stop_process('secondary',self.secondary)
        def close_sampler():
            with self.sampling_lock:
                try:self.sampler.close()
                finally:self.sampling_closed=True
        status.attempt('sampler',close_sampler)
        status.check('sampler',lambda:self.sampler.cleanup_confirmed)
        if self.session:status.attempt('observation',lambda:self.recorder.observe(self.session.stream))
        if self.sink:
            status.attempt('observation',lambda:self.recorder.data['counters'].update(
                queue_written=self.sink.written,queue_discarded=self.sink.discarded,queue_purged=self.sink.purged))
        status.finish()
        self.recorder.data['children_stopped']=status.confirmed
