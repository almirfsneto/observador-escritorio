"""Closed diagnostics for the isolated study only; no handles/paths/exception text."""
import ctypes

PHASES=('job_terminate','job_zero','job_handle_close','process_wait','process_fallback',
        'thread_handle_close','process_handle_close')
STATES=('not_attempted','passed','timeout','failed')
ERRORS=('none','access_denied','invalid_handle','other','unavailable')


class CleanupDiagnostic:
    def __init__(self):
        self.phases=dict.fromkeys(PHASES,'not_attempted');self.first_failure=None
        self.native_errors=dict.fromkeys(PHASES,'none');self.after_failure_wait='not_attempted'
        self.process_exit_confirmed=False;self.exit_race_confirmed=False

    def note(self,phase,state,*,native=False):
        if phase not in PHASES or state not in STATES:raise ValueError('diagnostic_rejected')
        self.phases[phase]=state
        if state=='failed':
            if self.first_failure is None:self.first_failure=phase
            if native:
                getter=getattr(ctypes,'get_last_error',None)
                code=getter() if getter else None
                self.native_errors[phase]=({5:'access_denied',6:'invalid_handle'}.get(code,'other')
                                           if code is not None else 'unavailable')

    def boolean_call(self,phase,action):
        try:result=action()
        except Exception:
            self.note(phase,'failed');raise
        self.note(phase,'passed' if result else 'failed',native=not result)
        return result

    def wait(self,action):
        try:result=action()
        except Exception:
            self.note('process_wait','failed');raise
        self.note('process_wait','passed' if result==0 else 'timeout' if result==258 else 'failed',native=result not in (0,258))
        return result

    def snapshot(self,probe):
        origin=getattr(probe,'diagnostic_origin','unknown')
        if origin not in ('win32','injected','win32_with_injected_wait','unknown'):raise ValueError('diagnostic_rejected')
        return dict(kind='isolated_cleanup_diagnostic',origin=origin,phases=dict(self.phases),
                    first_failure=self.first_failure,native_errors=dict(self.native_errors),
                    after_failure_wait=self.after_failure_wait,process_exit_confirmed=self.process_exit_confirmed,
                    exit_race_confirmed=self.exit_race_confirmed,
                    resources=probe.status.snapshot(),assigned=probe.assigned,
                    job=dict(processes_confirmed=probe.job.processes_confirmed,
                             cleanup_confirmed=probe.job.cleanup_confirmed,close_state=probe.job.close_state),
                    handles=dict(thread=probe.thread.close_state,process=probe.process.close_state))
