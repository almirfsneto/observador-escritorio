"""Injected cleanup faults, explicitly distinct from actual Windows kernel tests."""
from concurrent.futures import Future
import unittest
from types import SimpleNamespace

from observador.owned_channel import OwnedSyntheticChannel
from observador.owned_channel_protocol import ChannelError


class CleanupStabilizationTest(unittest.TestCase):
    def test_cleanup_attempts_all_resources_and_completes_waiter_on_close_error(self):
        class Kernel:
            def __init__(self):self.attempts=[]
            def close(self,handle):
                self.attempts.append(handle)
                if handle in (11,13):raise OSError('synthetic_close_fault')
        class Job:
            def close(self):raise OSError('synthetic_job_fault')
        channel=OwnedSyntheticChannel();channel._kernel=Kernel();channel._handles={11,12};channel._cancel_handle=13
        channel._job=Job();channel._key=b'x'*32
        pending=Future();channel._queue.put_nowait(('sample',None,pending))
        channel._cleanup()
        self.assertEqual(set(channel._kernel.attempts),{11,12,13})
        self.assertIsNone(channel._key);self.assertIsNone(channel._cancel_handle)
        self.assertFalse(channel.snapshot()['shutdown_confirmed']);self.assertEqual(channel.snapshot()['cleanup_errors'],3)
        self.assertEqual(channel.snapshot()['last_error'],'cleanup_unconfirmed')
        with self.assertRaises(ChannelError):pending.result(timeout=.1)

    def test_cancel_error_still_joins_worker_and_never_claims_clean_shutdown(self):
        joined=[]
        def cancel(handle):raise OSError('synthetic_cancel_fault')
        channel=OwnedSyntheticChannel();channel._cancel_handle=11
        channel._kernel=SimpleNamespace(cancel_thread=cancel)
        channel._thread=SimpleNamespace(join=lambda **_:joined.append(True),is_alive=lambda:False)
        channel.close()
        self.assertEqual(joined,[True]);self.assertFalse(channel.snapshot()['shutdown_confirmed'])
        self.assertEqual(channel.snapshot()['cleanup_errors'],1);self.assertEqual(channel.snapshot()['state'],'failed')
