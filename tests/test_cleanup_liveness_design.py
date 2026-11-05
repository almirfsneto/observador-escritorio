"""Issue #30: isolated liveness contract and process-boundary negatives.

This is deliberately NOT a production watchdog. No real collection or UIA.
"""
from dataclasses import dataclass
import os
import subprocess
import sys
import tempfile
import unittest


@dataclass(frozen=True)
class Evidence:
    """Independent closed observations; booleans must be actual bool, not truthy."""
    worker_exited: bool = False
    owner_exited: bool = False
    deadline_elapsed: bool = False
    cancel_requested: bool = False
    cancel_acknowledged: bool = False
    children_exited: bool = False
    job_zero: bool = False
    handles_closed: bool = False
    cleanup_error: bool = False
    ui_state: str = 'unknown'


def classify(e):
    """Test-only classification: neither timeout nor cancel is proof of exit."""
    if (type(e) is not Evidence
            or any(type(getattr(e, name)) is not bool
                   for name in Evidence.__dataclass_fields__ if name != 'ui_state')
            or type(e.ui_state) is not str
            or e.ui_state not in ('responsive', 'unavailable', 'unknown')
            or (e.cancel_acknowledged and not e.cancel_requested)):
        raise ValueError('liveness_evidence_rejected')
    # Distinguish completed, overdue and still-active workers. UI is orthogonal.
    if e.deadline_elapsed:
        worker = 'deadline_expired'  # Historical deadline violation remains visible after late exit.
    elif e.worker_exited:
        worker = 'exited'
    elif e.cancel_requested:
        worker = 'cancel_pending'
    else:
        worker = 'running'
    if (e.worker_exited and e.children_exited and e.job_zero and e.handles_closed
            and not e.cleanup_error):
        cleanup = 'confirmed'
    elif (e.cleanup_error or e.deadline_elapsed or e.owner_exited
          or (e.cancel_requested and not e.cancel_acknowledged)):
        cleanup = 'unconfirmed'
    else:
        cleanup = 'pending'
    return {
        'kind': 'synthetic_liveness_contract',
        'worker_state': worker,
        'worker_exit_confirmed': e.worker_exited,
        'deadline_expired': e.deadline_elapsed,
        'cleanup_state': cleanup,
        'ui_state': e.ui_state,
        'owner_exited': e.owner_exited,
        'cancel_state': 'acknowledged' if e.cancel_acknowledged else
                        'requested' if e.cancel_requested else 'not_requested',
        'children_exit_confirmed': e.children_exited,
    }


class LivenessContractTest(unittest.TestCase):
    def test_timeout_does_not_imply_worker_exited_or_cleanup(self):
        d = classify(Evidence(deadline_elapsed=True, cancel_requested=True))
        self.assertEqual((d['worker_state'], d['cleanup_state']),
                         ('deadline_expired', 'unconfirmed'))

    def test_cancel_failure_or_ack_does_not_prove_exit(self):
        for acknowledged in (False, True):
            with self.subTest(acknowledged=acknowledged):
                d = classify(Evidence(cancel_requested=True,
                                      cancel_acknowledged=acknowledged))
                self.assertEqual(d['worker_state'], 'cancel_pending')
                self.assertNotEqual(d['cleanup_state'], 'confirmed')

    def test_worker_exit_does_not_prove_children_or_handles_closed(self):
        for e in (Evidence(worker_exited=True),
                  Evidence(worker_exited=True, children_exited=True),
                  Evidence(worker_exited=True, children_exited=True, job_zero=True)):
            self.assertNotEqual(classify(e)['cleanup_state'], 'confirmed')

    def test_owner_crash_without_child_proof_fails_closed(self):
        d = classify(Evidence(owner_exited=True, deadline_elapsed=True))
        self.assertEqual(d['cleanup_state'], 'unconfirmed')
        self.assertFalse(d['children_exit_confirmed'])

    def test_ui_timeout_is_independent_of_cleanup(self):
        proof = dict(worker_exited=True, children_exited=True,
                     job_zero=True, handles_closed=True)
        for state in ('responsive', 'unavailable', 'unknown'):
            d = classify(Evidence(**proof, ui_state=state))
            self.assertEqual(d['cleanup_state'], 'confirmed')
            self.assertEqual(d['ui_state'], state)

    def test_late_exit_preserves_expired_deadline_independently_of_cleanup(self):
        # Eventual resource confirmation does not erase a deadline violation.
        complete = Evidence(worker_exited=True, deadline_elapsed=True,
                            children_exited=True, job_zero=True, handles_closed=True)
        d = classify(complete)
        self.assertEqual(d['worker_state'], 'deadline_expired')
        self.assertTrue(d['worker_exit_confirmed'])
        self.assertTrue(d['deadline_expired'])
        self.assertEqual(d['cleanup_state'], 'confirmed')  # Different evidence dimension.
        incomplete = classify(Evidence(worker_exited=True, deadline_elapsed=True))
        self.assertEqual(incomplete['worker_state'], 'deadline_expired')
        self.assertTrue(incomplete['worker_exit_confirmed'])
        self.assertEqual(incomplete['cleanup_state'], 'unconfirmed')

    def test_cancel_ack_without_request_is_invalid_evidence(self):
        with self.assertRaisesRegex(ValueError, '^liveness_evidence_rejected
        d = classify(Evidence(worker_exited=True, children_exited=True,
                              job_zero=True, handles_closed=True, cleanup_error=True))
        self.assertEqual(d['worker_state'], 'exited')
        self.assertEqual(d['cleanup_state'], 'unconfirmed')

    def test_confirmed_requires_all_independent_proofs(self):
        d = classify(Evidence(worker_exited=True, children_exited=True,
                              job_zero=True, handles_closed=True))
        self.assertEqual(d['worker_state'], 'exited')
        self.assertEqual(d['cleanup_state'], 'confirmed')

    def test_invalid_untrusted_evidence_is_rejected(self):
        for bad in (object(), Evidence(worker_exited=1),
                    Evidence(deadline_elapsed='yes'), Evidence(ui_state='yes'),
                    Evidence(ui_state=1)):
            with self.subTest(type=type(bad).__name__):
                with self.assertRaisesRegex(ValueError, '^liveness_evidence_rejected$'):
                    classify(bad)

    def test_real_isolated_subprocess_with_non_daemon_blocked_lock(self):
        # REAL process, but the blocked operation and cancellation are synthetic.
        # A non-daemon worker remains alive after a bounded join; do NOT kill a
        # thread inside the caller or leave an infinite hang in the CI.
        script = (
            'import threading,sys\n'
            'lock=threading.Lock()\n'
            'lock.acquire()\n'
            'def blocked():\n'
            '    lock.acquire()\n'
            'worker=threading.Thread(target=blocked,daemon=False)\n'
            'worker.start()\n'
            'worker.join(timeout=.05)\n'
            'print("BLOCKED_AFTER_JOIN" if worker.is_alive() else "UNEXPECTED_EXIT",flush=True)\n'
            'sys.stdin.readline()\n'
            'print("CANCEL_NOT_IMPLEMENTED",flush=True)\n'
            'worker.join()\n'
        )
        env = {}
        if sys.platform == 'win32':
            env = {'SystemRoot': os.environ['SystemRoot'],
                   'TEMP': tempfile.gettempdir(), 'TMP': tempfile.gettempdir()}
        p = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', script],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env)
        try:
            # A cancellation-looking input cannot release the unrelated lock.
            with self.assertRaises(subprocess.TimeoutExpired):
                p.communicate(input=b'cancel\n', timeout=1.5)
            self.assertIsNone(p.poll())
        finally:
            if p.poll() is None:
                p.kill()  # Only our own isolated synthetic process.
            out, _ = p.communicate(timeout=5)
            self.assertIsNotNone(p.returncode)
        self.assertIn(b'BLOCKED_AFTER_JOIN', out)
        self.assertIn(b'CANCEL_NOT_IMPLEMENTED', out)
        self.assertNotIn(b'UNEXPECTED_EXIT', out)


if __name__ == '__main__':
    unittest.main()
):
            classify(Evidence(cancel_acknowledged=True))

    def test_sticky_cleanup_error_blocks_confirmation_even_after_exit(self):
        d = classify(Evidence(worker_exited=True, children_exited=True,
                              job_zero=True, handles_closed=True, cleanup_error=True))
        self.assertEqual(d['worker_state'], 'exited')
        self.assertEqual(d['cleanup_state'], 'unconfirmed')

    def test_confirmed_requires_all_independent_proofs(self):
        d = classify(Evidence(worker_exited=True, children_exited=True,
                              job_zero=True, handles_closed=True))
        self.assertEqual(d['worker_state'], 'exited')
        self.assertEqual(d['cleanup_state'], 'confirmed')

    def test_invalid_untrusted_evidence_is_rejected(self):
        for bad in (object(), Evidence(worker_exited=1),
                    Evidence(deadline_elapsed='yes'), Evidence(ui_state='yes'),
                    Evidence(ui_state=1)):
            with self.subTest(type=type(bad).__name__):
                with self.assertRaisesRegex(ValueError, '^liveness_evidence_rejected$'):
                    classify(bad)

    def test_real_isolated_subprocess_with_non_daemon_blocked_lock(self):
        # REAL process, but the blocked operation and cancellation are synthetic.
        # A non-daemon worker remains alive after a bounded join; do NOT kill a
        # thread inside the caller or leave an infinite hang in the CI.
        script = (
            'import threading,sys\n'
            'lock=threading.Lock()\n'
            'lock.acquire()\n'
            'def blocked():\n'
            '    lock.acquire()\n'
            'worker=threading.Thread(target=blocked,daemon=False)\n'
            'worker.start()\n'
            'worker.join(timeout=.05)\n'
            'print("BLOCKED_AFTER_JOIN" if worker.is_alive() else "UNEXPECTED_EXIT",flush=True)\n'
            'sys.stdin.readline()\n'
            'print("CANCEL_NOT_IMPLEMENTED",flush=True)\n'
            'worker.join()\n'
        )
        env = {}
        if sys.platform == 'win32':
            env = {'SystemRoot': os.environ['SystemRoot'],
                   'TEMP': tempfile.gettempdir(), 'TMP': tempfile.gettempdir()}
        p = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', script],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env)
        try:
            # A cancellation-looking input cannot release the unrelated lock.
            with self.assertRaises(subprocess.TimeoutExpired):
                p.communicate(input=b'cancel\n', timeout=1.5)
            self.assertIsNone(p.poll())
        finally:
            if p.poll() is None:
                p.kill()  # Only our own isolated synthetic process.
            out, _ = p.communicate(timeout=5)
            self.assertIsNotNone(p.returncode)
        self.assertIn(b'BLOCKED_AFTER_JOIN', out)
        self.assertIn(b'CANCEL_NOT_IMPLEMENTED', out)
        self.assertNotIn(b'UNEXPECTED_EXIT', out)


if __name__ == '__main__':
    unittest.main()
