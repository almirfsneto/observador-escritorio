"""Negative model tests; these do NOT authenticate a Windows IPC peer."""
from copy import deepcopy
import json
import random
import time
import unittest
from uuid import uuid4

from observador.offline_bridge import BridgeError,make_batch
from observador.source_auth_simulator import SyntheticAuthModel
from test_offline_bridge import source,events_for


def identity():
    return dict(provider_pid=100,provider_created_ticks=638000000000000000,fixture_pid=101,
                fixture_created_ticks=638000000000000001,session_slot=1,
                provider_alias='owned_windows_observer',fixture_alias='owned_synthetic_wpf')


class AuthModelTest(unittest.TestCase):
    def setUp(self):self.now=0;self.p=source('windows')

    def paired(self):
        model=SyntheticAuthModel(monotonic=lambda:self.now)
        model.arm_for_test(identity(),self.p);model.verify(model.sign_for_test())
        return model

    def batch(self):
        ticket=dict(schema_version=1,kind='synthetic_bridge_ticket',bridge_epoch=str(uuid4()),generation=1,
                    source=self.p,next_batch_sequence=1,next_source_sequence=1,remaining_ms=900000)
        return make_batch(ticket,events_for(self.p))

    def test_default_off_explicit_pairing_and_scopes(self):
        m=SyntheticAuthModel(monotonic=lambda:self.now)
        self.assertEqual(m.state,'disabled')
        with self.assertRaises(BridgeError):m.challenge_document()
        m=self.paired();result=m.verify(m.sign_for_test(self.batch()))
        self.assertEqual(result['scope'],'model_transport_only_no_inbox_or_producer_ack')
        self.assertTrue(result['simulation_only']);self.assertFalse(m.pause()['producer_pause_confirmed'])

    def test_forged_origin_identity_session_epoch_generation_challenge_or_mac_closes(self):
        for field in ('identity','source','epoch','generation','challenge','mac','schema_version','sequence','simulation_only'):
            with self.subTest(field=field):
                m=self.paired();frame=m.sign_for_test(self.batch())
                if field=='identity':frame[field]['fixture_pid']+=1
                elif field=='source':frame[field]['instance']=str(uuid4())
                elif field in ('epoch','challenge'):frame[field]=str(uuid4())
                elif field=='mac':frame[field]='0'*64
                elif field=='simulation_only':frame[field]=False
                else:frame[field]+=1
                with self.assertRaises(BridgeError):m.verify(frame)
                self.assertEqual(m.state,'closed');self.assertIsNone(m._key)

    def test_trusted_signer_cannot_override_allowlist_or_expected_binding(self):
        for change in ('fixture_alias','session_slot','provider_created_ticks','fixture_pid'):
            m=self.paired();frame=m.sign_for_test(self.batch());frame['identity'][change]='other' if change=='fixture_alias' else 102
            body={k:v for k,v in frame.items() if k!='mac'};frame['mac']=m._mac(body)
            with self.subTest(change=change),self.assertRaises(BridgeError):m.verify(frame)
        m=SyntheticAuthModel();bad=identity();bad['fixture_alias']='professional_app'
        with self.assertRaises(BridgeError):m.arm_for_test(bad,self.p)
        with self.assertRaises(BridgeError):SyntheticAuthModel().arm_for_test(identity(),source('web'))

    def test_pause_resume_requires_fresh_proof_and_invalidates_pending_frames(self):
        m=self.paired();old=m.sign_for_test(self.batch());m.pause();m.resume_for_test()
        with self.assertRaises(BridgeError):m.verify(old)
        m=self.paired();old_challenge=m.challenge;m.pause();m.resume_for_test()
        self.assertNotEqual(old_challenge,m.challenge)
        m.verify(m.sign_for_test());self.assertEqual(m.verify(m.sign_for_test(self.batch()))['next_sequence'],2)
        m.pause()
        with self.assertRaises(BridgeError):m.verify(m.sign_for_test(self.batch()))

    def test_replay_restart_and_second_writer_cannot_reuse_proof(self):
        m=self.paired();frame=m.sign_for_test(self.batch());m.verify(frame)
        with self.assertRaises(BridgeError):m.verify(frame)
        m=self.paired();proof=m.sign_for_test(self.batch())
        other=self.paired()
        self.assertNotEqual(m.epoch,other.epoch)
        with self.assertRaises(BridgeError):other.verify(proof)
        m.close();self.assertIsNone(m._key)
        with self.assertRaises(BridgeError):m.verify(proof)

    def test_timeout_clock_regression_and_challenge_expiry(self):
        for elapsed in (5,6):
            self.now=0;m=SyntheticAuthModel(monotonic=lambda:self.now);m.arm_for_test(identity(),self.p)
            proof=m.sign_for_test();self.now=elapsed
            with self.assertRaises(BridgeError):m.verify(proof)
        self.now=0;m=self.paired();frame=m.sign_for_test(self.batch());self.now=900
        with self.assertRaises(BridgeError):m.verify(frame)
        self.now=10;m=self.paired();self.now=9
        with self.assertRaises(BridgeError):m.verify(m.sign_for_test(self.batch()))

    def test_limits_and_malformed_inputs_close_without_free_text_errors(self):
        for payload in (None,[],{}, {'content':'SYNTHETIC_SENTINEL'}):
            m=self.paired()
            with self.assertRaisesRegex(BridgeError,'^synthetic_auth_model_rejected$'):m.verify(payload)
        m=self.paired();frame=m.sign_for_test(self.batch());frame['extra']='x'*300000
        with self.assertRaises(BridgeError):m.verify(frame)
        m=self.paired()
        for _ in range(64):m.verify(m.sign_for_test(self.batch()))
        with self.assertRaises(BridgeError):m.verify(m.sign_for_test(self.batch()))

    def test_seeded_tamper_fuzz_does_not_yield_acceptance(self):
        rng=random.Random(1402)
        for _ in range(100):
            m=self.paired();frame=m.sign_for_test(self.batch())
            field=rng.choice(('epoch','challenge','generation','sequence','mac'))
            frame[field]=rng.randrange(100000) if field in ('generation','sequence') else str(uuid4())
            with self.assertRaises(BridgeError):m.verify(frame)
            self.assertEqual(m.state,'closed')

    def test_synthetic_benchmark_is_model_only(self):
        start=time.perf_counter();m=self.paired();batch=self.batch()
        for _ in range(64):m.verify(m.sign_for_test(batch))
        print('SYNTHETIC_AUTH_MODEL_BENCHMARK',json.dumps(dict(frames=64,elapsed_ms=round((time.perf_counter()-start)*1000,3),
              serialized_frame_bytes=len(json.dumps(m.sign_for_test(batch)).encode()),scope='in_memory_model_only',kernel_peer_verified=False,
              inbox_committed=False,human_acceptance=False)))

    @unittest.skipUnless(__import__('sys').platform=='win32','Windows kernel owned-child probe required')
    def test_windows_kernel_identity_of_owned_synthetic_fixture(self):
        import ctypes
        from ctypes import wintypes
        from pathlib import Path
        import subprocess
        from observador.native_session import creation_ticks
        from observador.windows_peer_probe import inspect_owned_child
        target=Path(__file__).resolve().parents[1]/'tools/SyntheticWpfTaskApp/bin/Release/net8.0-windows/SyntheticWpfTaskApp.exe'
        wrong=target.parents[4]/'WindowsObserver/bin/Release/net8.0-windows/WindowsObserver.exe'
        child=subprocess.Popen([str(target)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.ProcessIdToSessionId.argtypes=[wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
            kernel.ProcessIdToSessionId.restype=wintypes.BOOL
            slot=wintypes.DWORD();self.assertTrue(kernel.ProcessIdToSessionId(child.pid,ctypes.byref(slot)))
            ticks=creation_ticks(child)
            self.assertEqual(inspect_owned_child(child,target,ticks,slot.value)['pid'],child.pid)
            for path,created,session in ((wrong,ticks,slot.value),(target,ticks+1,slot.value),(target,ticks,slot.value+1)):
                with self.assertRaisesRegex(ValueError,'^owned_child_identity_rejected$'):
                    inspect_owned_child(child,path,created,session)
            print('SYNTHETIC_OWNED_CHILD_PROBE',json.dumps(dict(kernel_path_creation_session_verified=True,
                  transport_peer_verified=False,inbox_integrated=False,human_acceptance=False)))
        finally:
            child.terminate();child.wait(timeout=5)
        with self.assertRaises(ValueError):inspect_owned_child(child,target,ticks,slot.value)
