"""Deterministic API-return regressions, explicitly not real kernel failures."""
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from observador.cleanup import CleanupStatus
from isolated_suspended_spawn import SuspendedProbe
from isolated_cleanup_diagnostic import CleanupDiagnostic,PHASES


class SuspendedCleanupInjectionTest(unittest.TestCase):
    def probe(self,waits,*,error=5,terminate=False,job_ok=True,attached=True,close=True):
        probe=SuspendedProbe.__new__(SuspendedProbe);probe.status=CleanupStatus();probe.diagnostic=CleanupDiagnostic()
        probe.assigned=attached;probe.job_attached=attached;probe.diagnostic_origin='injected';calls=[];replies=iter(waits)
        def wait(handle,milliseconds):calls.append(('wait',milliseconds));return next(replies,258)
        def stop(*args):calls.append(('terminate',));return terminate
        def close_handle(handle):calls.append(('close',handle));return close
        def close_job():
            if not job_ok:raise OSError('SYNTHETIC_SECRET')
        probe.job=SimpleNamespace(close=close_job,processes_confirmed=job_ok,cleanup_confirmed=job_ok,close_state='closed')
        probe.process=SimpleNamespace(handle=11,close_state='open');probe.thread=SimpleNamespace(handle=12,close_state='open')
        probe.api=SimpleNamespace(WaitForSingleObject=wait,TerminateProcess=stop,CloseHandle=close_handle)
        return probe,calls

    def test_confirmed_job_exit_is_waited_before_any_fallback(self):
        p,calls=self.probe([0]);p.close()
        self.assertEqual(calls,[('wait',2000),('close',12),('close',11)])
        self.assertTrue(p.status.confirmed);self.assertTrue(p.diagnostic.process_exit_confirmed)

    def test_access_denied_is_recovered_only_with_exit_and_job_proof(self):
        for error,signaled,job_ok,confirmed in ((5,True,True,True),(5,False,True,False),
                                             (6,True,True,False),(87,True,True,False),(5,True,False,False)):
            with self.subTest(error=error,signaled=signaled,job_ok=job_ok):
                p,calls=self.probe([258,0 if signaled else 258],job_ok=job_ok)
                with patch('isolated_cleanup_diagnostic.ctypes.get_last_error',return_value=error,create=True):
                    if confirmed:p.close()
                    else:
                        with self.assertRaisesRegex(OSError,'^isolated_cleanup_unconfirmed$'):p.close()
                self.assertEqual(p.status.confirmed,confirmed)
                self.assertEqual(p.diagnostic.exit_race_confirmed,confirmed)
                self.assertEqual([x for x in calls if x[0]=='close'],[('close',12),('close',11)])
                self.assertEqual(p.diagnostic.phases['process_fallback'],'failed')
                self.assertNotIn('SYNTHETIC_SECRET',json.dumps(p.diagnostic.snapshot(p)))

    def test_wait_failure_and_close_failure_are_not_forgiven(self):
        for waits,closed in (([0xffffffff],True),([0],False)):
            p,calls=self.probe(waits,close=closed)
            with patch('isolated_cleanup_diagnostic.ctypes.get_last_error',return_value=6,create=True):
                with self.assertRaisesRegex(OSError,'^isolated_cleanup_unconfirmed$'):p.close()
            self.assertFalse(p.status.confirmed);self.assertFalse(p.diagnostic.exit_race_confirmed)
            self.assertEqual(len([x for x in calls if x[0]=='close']),2)
            before=list(calls)
            with self.assertRaises(OSError):p.close()
            self.assertEqual(calls,before)

    def test_wait_budget_does_not_grow_after_initial_timeout(self):
        p,calls=self.probe([258,258],terminate=True)
        with patch('isolated_suspended_spawn.time.monotonic',side_effect=[10,12.1]):
            with self.assertRaises(OSError):p.close()
        self.assertEqual([x for x in calls if x[0]=='wait'],[('wait',2000),('wait',0),('wait',0)])
        self.assertFalse(p.status.confirmed)

    def test_diagnostic_contains_only_closed_categories_and_no_resource_values(self):
        p,_=self.probe([0]);p.close();value=p.diagnostic.snapshot(p)
        self.assertEqual(set(value['phases']),set(PHASES))
        self.assertEqual(value['handles'],{'thread':'closed','process':'closed'})
        self.assertNotIn('11',json.dumps(value));self.assertNotIn('12',json.dumps(value))
        with self.assertRaises(ValueError):p.diagnostic.note('SYNTHETIC_SECRET','failed')
