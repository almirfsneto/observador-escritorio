from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest

from observador.diagnostics import (SCHEMA,DiagnosticRecorder,DiagnosticHistory,DiagnosticError,
                                    validate_diagnostics,write_diagnostics,read_diagnostics)
from observador.stream import LabStream
from observador.lab_queue import AsyncLabQueue
from test_storage_hardening import event


class DiagnosticsTest(unittest.TestCase):
    def stream(self,capacity=2):
        now=datetime.now(timezone.utc)
        stream=LabStream(now+timedelta(minutes=1),capacity=capacity)
        stream.receive(json.dumps(dict(kind='ready',pid=123,start_ticks=456)))
        stream.command(True)
        stream.receive(json.dumps(dict(kind='ack',generation=stream.generation,active=True)))
        return stream

    def receive(self,stream,sequence,action='invoke',**changes):
        record=dict(kind='event',generation=stream.generation,sequence=sequence,
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),action=action,role=50000,control_id='a'*16)
        record.update(changes)
        stream.receive(json.dumps(record))

    def test_closed_schema_is_published_and_disabled_by_default(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(json.loads((root/'docs/DIAGNOSTICS_SCHEMA.json').read_text()),SCHEMA)
        report=DiagnosticRecorder().sample()
        self.assertEqual(report['agent']['state'],'disabled')
        self.assertIsNone(report['native'])
        self.assertFalse(report['pilot_authorized'])

    def test_stream_reconciles_overflow_pause_coalescing_replay_and_expiry(self):
        stream=self.stream()
        self.receive(stream,1,'focus')
        self.receive(stream,2,'focus')
        self.receive(stream,3)
        self.receive(stream,4)
        self.assertEqual(stream.flow,dict(received=4,accepted=2,rejected=0,coalesced=1,overflow=1,drained=0,discarded=0))
        stream.command(False)
        self.receive(stream,5,generation=1)
        self.assertEqual(stream.flow['discarded'],2)
        stream.command(True)
        stream.receive(json.dumps(dict(kind='ack',generation=stream.generation,active=True)))
        self.receive(stream,6)
        self.assertEqual(len(stream.drain()),1)
        self.receive(stream,6)  # Replay is protocol failure, not a second accepted event.
        report=DiagnosticRecorder().sample(stream=stream)
        self.assertEqual(report['agent']['state'],'stopped')
        self.assertEqual(stream.flow['rejected'],2)
        stream=self.stream()
        self.receive(stream,1)
        stream.deadline=stream.monotonic()-1
        report=DiagnosticRecorder().sample(stream=stream)
        self.assertEqual(report['agent']['state'],'expired')
        self.assertEqual(report['python']['flow']['discarded'],1)

    def test_native_gauges_are_sampled_and_never_mixed_with_python_totals(self):
        stream=self.stream()
        stream.receive(json.dumps(dict(kind='health',generation=1,dropped=9,
            callbacks=dict(focus=20,invoke=30,toggle=0,excluded=4,errors=1),
            queues=dict(output_depth=3,output_capacity=512,focus_depth=2,focus_capacity=256))))
        report=DiagnosticRecorder().sample(stream=stream)
        self.assertEqual(report['native']['dropped'],9)
        self.assertEqual(report['python']['flow']['received'],0)
        self.assertNotIn('pid',json.dumps(report))
        stream.last_health_received-=3
        self.assertIn('native_sample_stale',DiagnosticRecorder().sample(stream=stream)['gaps'])

    def test_rejects_text_extra_fields_bad_numbers_and_contradictions_without_echo(self):
        base=DiagnosticRecorder().sample(stream=self.stream())
        variants=[]
        for key in ('hostname','path','session_id','window_title','payload','username','ip'):
            bad=deepcopy(base);bad[key]='SECRET C:\\Clients\\Alice 10.0.0.1';variants.append(bad)
        for value in (float('nan'),float('inf'),True,-1,10**100):
            bad=deepcopy(base);bad['agent']['uptime_ms']=value;variants.append(bad)
        bad=deepcopy(base);bad['python']['flow']['received']=1;variants.append(bad)
        bad=deepcopy(base);bad['agent']['state']='disabled';variants.append(bad)
        bad=deepcopy(base);bad['python']['stopped']=True;variants.append(bad)
        bad=deepcopy(base);bad['gaps']=[];variants.append(bad)
        for bad in variants:
            with self.assertRaisesRegex(DiagnosticError,'^diagnostic_document_rejected$'):
                validate_diagnostics(bad)

    def test_writer_duplicate_flush_shutdown_and_export_are_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink=AsyncLabQueue(Path(tmp)/'queue/db.sqlite3')
            item=event()
            sink.submit([item,item])
            sink.close()
            sink.submit([event()])
            report=DiagnosticRecorder().sample(writer=sink)
            self.assertEqual(report['writer']['ledger'],dict(received=3,enqueued=2,ingress_rejected=1,
                buffered=0,inflight=0,written=1,duplicates=1,write_rejected=0,uncertain=0))
            self.assertEqual(report['writer']['row_balance'],'balanced')
            path=write_diagnostics(report,Path(tmp)/'repo',Path(tmp)/'export/health.json')
            self.assertEqual(json.loads(path.read_text()),report)
            self.assertEqual(read_diagnostics(path),report)
            with self.assertRaises(FileExistsError):write_diagnostics(report,Path(tmp)/'repo',path)
            bad=deepcopy(report);bad['writer']['ledger']['written']=2
            with self.assertRaises(DiagnosticError):validate_diagnostics(bad)
            bad=deepcopy(report);bad['writer']['storage']['rows_current']=99
            with self.assertRaises(DiagnosticError):validate_diagnostics(bad)

    def test_reader_rejects_duplicate_keys_nan_and_oversized_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'invalid.json'
            for payload in ('{"kind":0,"kind":1}', '{"a":NaN}', ' '*65537):
                path.write_text(payload)
                with self.assertRaises(DiagnosticError):read_diagnostics(path)

    def test_history_rejects_replayed_samples_counter_rollback_and_lifecycle_reset(self):
        stream=self.stream()
        recorder=DiagnosticRecorder()
        history=DiagnosticHistory()
        first=history.accept(recorder.sample(stream=stream))
        with self.assertRaises(DiagnosticError):history.accept(first)
        self.receive(stream,1)
        history.accept(recorder.sample(stream=stream))
        bad=deepcopy(first);bad['sample_sequence']=3;bad['agent']['uptime_ms']=1000
        with self.assertRaises(DiagnosticError):history.accept(bad)
        stream.stop()
        history.accept(recorder.sample(stream=stream))
        with self.assertRaises(DiagnosticError):history.accept(recorder.sample())
