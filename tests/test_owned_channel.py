"""Portable wire tests and real Windows owned-child tests; no simulator substitution."""
from copy import deepcopy
import json
from pathlib import Path
import secrets
import struct
import sys
import time
import unittest
from uuid import uuid4

from observador import owned_channel_protocol as wire
from observador.owned_channel import OwnedSyntheticChannel


def context():
    def peer(pid):return dict(pid=pid,start_ticks=638000000000000000,session_slot=1,image_sha256='1'*64)
    return dict(parent=peer(100),child=peer(101),fixture_sha256='2'*64,ttl_ms=30000,handle_count=4)


class WireTest(unittest.TestCase):
    def setUp(self):
        self.key=secrets.token_bytes(32)
        self.args=dict(kind='hello',epoch=str(uuid4()),session=str(uuid4()),generation=1,sequence=0,
                       nonce=secrets.token_hex(32),binding=context())
        self.raw=wire.seal(self.key,'parent',**self.args,payload={'action':'pair'})

    def test_wire_canonical_direction_binding_and_mac(self):
        self.assertEqual(wire.verify(self.raw,self.key,'parent',**self.args),{'action':'pair'})
        with self.assertRaises(wire.ChannelError):wire.verify(self.raw,self.key,'child',**self.args)
        for field in ('generation','sequence','nonce','epoch','session','binding'):
            args=deepcopy(self.args)
            if field in ('generation','sequence'):args[field]+=1
            elif field=='binding':args[field]['child']['start_ticks']+=1
            else:args[field]=str(uuid4())
            with self.subTest(field=field),self.assertRaises(wire.ChannelError):wire.verify(self.raw,self.key,'parent',**args)

    def test_duplicate_nan_unknown_noncanonical_truncated_and_oversize_rejected(self):
        bads=[b'',self.raw[:-1],b'{"version":1,'+self.raw[1:],self.raw.replace(b'"version":1',b'"version":NaN'),
              b' '+self.raw,b'x'*(wire.MAX_WIRE+1),b'\xff']
        frame=wire.decode(self.raw);frame['extra']='synthetic';bads.append(wire.canonical(frame))
        frame=wire.decode(self.raw);frame['mac']='0'*63;bads.append(wire.canonical(frame))
        for raw in bads:
            with self.subTest(length=len(raw)),self.assertRaises(wire.ChannelError):wire.decode(raw)
        for size in (0,wire.MAX_WIRE+1,2**32-1):
            with self.assertRaises(wire.ChannelError):wire.frame_size(struct.pack('>I',size))
        self.assertEqual(wire.frame_size(wire.length_header(wire.MAX_WIRE)),wire.MAX_WIRE)

    def test_default_off_and_no_nonwindows_fallback(self):
        channel=OwnedSyntheticChannel()
        self.assertEqual(channel.snapshot()['state'],'disabled');self.assertIsNone(channel.process)
        self.assertFalse(channel.snapshot()['adapter_enabled'])
        if sys.platform!='win32':
            with self.assertRaises(wire.ChannelError):channel.start()
        channel.close()

    def test_seeded_wire_invalid_domains_and_mutations_are_rejected(self):
        import random
        rng=random.Random(1701)
        for _ in range(100):
            frame=wire.decode(self.raw)
            field=rng.choice(('version','kind','nonce','generation','sequence','payload','binding','mac'))
            if field=='version':frame[field]=True
            elif field=='kind':frame[field]=['hello']
            elif field=='nonce':frame[field]='F'*64
            elif field=='generation':frame[field]=0
            elif field=='sequence':frame[field]=-1
            elif field=='payload':frame[field]['extra']='synthetic'
            elif field=='binding':frame[field]['parent']['session_slot']+=1
            else:frame[field]='0'*63
            with self.subTest(field=field),self.assertRaises(wire.ChannelError):wire.decode(wire.canonical(frame))
        with self.assertRaises(wire.ChannelError):wire.decode(b'['*1000+b']'*1000)


@unittest.skipUnless(sys.platform=='win32','Requires real Windows kernel process/handle execution')
class WindowsChannelTest(unittest.TestCase):
    def channel(self,**kwargs):
        channel=OwnedSyntheticChannel(**kwargs);self.addCleanup(channel.close);return channel

    def test_real_owned_peer_key_pipe_minimal_handles_and_pause(self):
        channel=self.channel();channel.start()
        self.assertTrue(channel.snapshot()['owned_peer_authenticated'])
        self.assertEqual(channel.snapshot()['inherited_handle_count'],4)
        self.assertTrue(channel.snapshot()['bootstrap_closed'])
        self.assertTrue(all(channel.snapshot()['proof_flags'].values()))
        self.assertEqual(channel.sample()['ordinal'],1)
        old_generation=channel._generation;old_nonce=channel._nonce
        result=channel.pause();self.assertEqual(result['state'],'paused')
        self.assertEqual(result['scope'],'owned_ipc_fixture_transport_not_inbox_or_uia_ack')
        channel.resume();self.assertGreater(channel._generation,old_generation)
        self.assertNotEqual(channel._nonce,old_nonce);self.assertEqual(channel.sample()['ordinal'],2)
        channel.stop();channel.close()
        snapshot=channel.snapshot();self.assertFalse(snapshot['process_running']);self.assertFalse(snapshot['worker_alive'])
        self.assertTrue(snapshot['shutdown_confirmed'])
        print('OWNED_WINDOWS_CHANNEL_VERIFIED',json.dumps(dict(real_child=True,key_delivered_by_private_pipe=True,
              explicit_handle_list=4,descendant_denied=True,pause_reproved=True,adapter_enabled=False,human_acceptance=False)))

    def test_real_adversarial_child_responses_fail_closed(self):
        for fault in ('wrong_key','wrong_identity','bad_mac','short_mac','duplicate','nan','oversize','truncated','flood','exit'):
            with self.subTest(fault=fault):
                channel=self.channel(fault=fault)
                with self.assertRaises(wire.ChannelError):channel.start()
                channel.close();self.assertFalse(channel.snapshot()['process_running'])
                self.assertFalse(channel.snapshot()['worker_alive']);self.assertIsNone(channel._key)

    def test_real_timeout_cancellation_and_natural_expiry(self):
        channel=self.channel(fault='stall');started=time.monotonic()
        with self.assertRaises(wire.ChannelError):channel.start()
        channel.close();self.assertLess(time.monotonic()-started,9)
        channel=self.channel(ttl_ms=3000);channel.start()
        until=time.monotonic()+5
        while channel.snapshot()['worker_alive'] and time.monotonic()<until:time.sleep(.02)
        channel.close();self.assertFalse(channel.snapshot()['process_running'])
        self.assertFalse(channel.snapshot()['worker_alive'])

    def test_real_decoy_and_unrelated_child_cannot_inherit_channel_handles(self):
        import subprocess
        from observador.owned_channel_win32 import Kernel
        kernel=Kernel();decoy=kernel.api.CreateEventW(None,True,False,None)
        self.assertTrue(bool(decoy));kernel.inherit(decoy,True)
        try:
            channel=self.channel(decoy_handles=(int(decoy),));channel.start()
            self.assertTrue(channel.snapshot()['proof_flags']['decoys_absent'])
            startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESTDHANDLES
            startup.hStdInput=startup.hStdOutput=startup.hStdError=0
            # Explicitly broad inheritance outside the launcher after its narrow window:
            # parent endpoints must all already be non-inheritable.
            probe=subprocess.run([sys.executable,'-I','-S','-B',str(Path(__import__('observador.owned_channel',fromlist=['x']).__file__).with_name('owned_channel_child.py')),
                                  '--probe',*(str(h) for h in channel._handles)],
                                 close_fds=False,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,timeout=5)
            self.assertEqual(probe.returncode,0)
            self.assertEqual(channel.sample()['ordinal'],1)
        finally:kernel.close(decoy)

    def test_real_foreign_child_rejected_and_never_killed_by_channel(self):
        import subprocess
        foreign=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time; time.sleep(30)'],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        self.addCleanup(lambda:foreign.poll() is None and foreign.kill())
        try:
            channel=self.channel();channel.start()
            with self.assertRaises(wire.ChannelError):channel._call('check_peer',foreign)
            channel.close();self.assertIsNone(foreign.poll())
        finally:
            if foreign.poll() is None:foreign.kill()
            foreign.wait(timeout=5)

    def test_real_replay_and_authenticated_wrong_context_fail_closed(self):
        for change in ('replay','generation','nonce','session','binding','reflection','duplicate','oversize','partial'):
            with self.subTest(change=change):
                channel=self.channel();channel.start()
                raw=channel._packet('command',dict(action='sample',ordinal=1),channel._sequence+1)
                if change=='replay':channel.sample()
                elif change in ('generation','nonce','session','binding'):
                    frame=wire.decode(raw)
                    if change=='generation':frame[change]+=1
                    elif change=='binding':frame['binding']['child']['start_ticks']+=1
                    else:frame[change]=str(uuid4()) if change=='session' else secrets.token_hex(32)
                    frame['mac']=wire.mac(channel._key,'parent',{k:v for k,v in frame.items() if k!='mac'})
                    raw=wire.canonical(frame)
                elif change=='reflection':
                    frame=wire.decode(raw);frame['mac']=wire.mac(channel._key,'child',{k:v for k,v in frame.items() if k!='mac'})
                    raw=wire.canonical(frame)
                elif change=='duplicate':raw=b'{"version":1,'+raw[1:]
                packet=(struct.pack('>I',wire.MAX_WIRE+1) if change=='oversize' else
                        wire.length_header(len(raw))+raw[:len(raw)//2] if change=='partial' else
                        wire.length_header(len(raw))+raw)
                with self.assertRaises(wire.ChannelError):channel._call('raw',packet)
                channel.close();self.assertFalse(channel.snapshot()['process_running']);self.assertFalse(channel.snapshot()['worker_alive'])

    def test_real_pause_rejects_old_frame_and_two_instances_do_not_share_keys(self):
        first=self.channel();second=self.channel();first.start();second.start()
        old=first._packet('command',dict(action='sample',ordinal=1),first._sequence+1)
        first.pause();self.assertEqual(second.sample()['ordinal'],1);first.resume()
        with self.assertRaises(wire.ChannelError):first._call('raw',wire.length_header(len(old))+old)
        first.close();self.assertEqual(second.sample()['ordinal'],2)
        # Restart creates new epoch/key; a frame from the dead owner is not accepted.
        restarted=self.channel();restarted.start()
        self.assertNotEqual(first._epoch,restarted._epoch)
        self.assertTrue(first._key is None) # Closed owner releases its key reference.
        with self.assertRaises(wire.ChannelError):restarted._call('raw',wire.length_header(len(old))+old)
        restarted.close();self.assertEqual(second.sample()['ordinal'],3)

    def test_real_creation_mismatch_is_rejected_without_claiming_os_pid_reuse(self):
        channel=self.channel();channel.start()
        channel._binding['child']['start_ticks']+=1 # Fault injection, not forced PID reuse.
        with self.assertRaises(wire.ChannelError):channel.sample()
        channel.close();self.assertFalse(channel.snapshot()['process_running'])

    def test_real_owner_kill_reaps_owned_descendant(self):
        import subprocess
        import ctypes
        from ctypes import wintypes
        from observador.owned_channel_win32 import Kernel
        owner=subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).parent/'fixtures/owned_channel_owner.py')],
                               stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        child_handle=None;kernel=Kernel()
        try:
            # Bound the harness too; its stdout contains only synthetic PID/creation.
            import threading
            output=[]
            reader=threading.Thread(target=lambda:output.append(owner.stdout.readline(4097)),daemon=True);reader.start();reader.join(10)
            self.assertFalse(reader.is_alive(),'owner_harness_no_ready')
            if not output or len(output[0])>4096:raise AssertionError('owner_harness_no_ready')
            try:info=json.loads(output[0])
            except ValueError:raise AssertionError('owner_harness_no_ready') from None
            kernel.api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
            kernel.api.OpenProcess.restype=wintypes.HANDLE
            child_handle=kernel.api.OpenProcess(0x1000|0x100000,False,info['pid'])
            self.assertTrue(bool(child_handle))
            self.assertEqual(kernel.identity(child_handle)['start_ticks'],info['start_ticks'])
            owner.kill();owner.wait(timeout=5)
            self.assertEqual(kernel.api.WaitForSingleObject(child_handle,5000),0)
            print('OWNED_PARENT_KILL_VERIFIED',json.dumps(dict(real_owner_kill=True,descendant_exited=True,human_acceptance=False)))
        finally:
            if owner.poll() is None:owner.kill()
            owner.wait(timeout=5)
            if owner.stdout:owner.stdout.close()
            if child_handle:kernel.close(child_handle)

    def test_real_two_channels_pause_and_inbox_expired_receipt_clock_injected(self):
        from datetime import datetime,timedelta,timezone
        import tempfile
        from observador.offline_bridge import OfflineBridge,BridgeError,make_batch
        from test_offline_bridge import source,events_for
        now=[datetime.now(timezone.utc)]
        first=self.channel();second=self.channel();first.start();second.start()
        with tempfile.TemporaryDirectory() as tmp:
            b=OfflineBridge(Path(tmp)/'inbox/db.sqlite3',clock=lambda:now[0])
            try:
                p=source('windows');p['instance']=first.session
                b.authorize(p);b.control('start')
                ordinal=first.sample()['ordinal']
                batch=make_batch(b.ticket(p['instance']),events_for(p,(ordinal,)))
                ack=b.ingest(batch);self.assertEqual(b.ingest(batch),ack)
                first.pause();b.control('pause');self.assertEqual(second.sample()['ordinal'],1)
                self.assertEqual(b.ingest(batch),ack)
                self.assertFalse(first.snapshot()['uia_pause_ack']);self.assertFalse(first.snapshot()['inbox_ack'])
                first.resume();self.assertEqual(first.sample()['ordinal'],2)
                now[0]+=timedelta(seconds=86401);b.purge() # Injected store clock, not elapsed real24h.
                with self.assertRaisesRegex(BridgeError,'receipt_expired_or_unknown'):b.ingest(batch)
                self.assertEqual(b.retention_snapshot()['counts']['batch_markers'],1)
                self.assertEqual(b.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                print('OWNED_CHANNEL_INBOX_TEST',json.dumps(dict(real_channels=2,clock_injected=True,real_24h_observed=False,
                      receipt_expired=True,markers_preserved=True,adapter_enabled=False,human_acceptance=False)))
            finally:b.close()

    def test_real_key_created_after_spawn_and_never_in_arguments_or_environment(self):
        import subprocess
        import base64
        from unittest.mock import patch
        actual=subprocess.Popen;calls=[];draws=[];random_bytes=secrets.token_bytes
        def spawn(args,**kwargs):
            calls.append((args,kwargs));return actual(args,**kwargs)
        channel=self.channel()
        def draw(size=None):
            draws.append(bool(calls and channel.process is not None))
            return random_bytes(size)
        with patch('observador.owned_channel.subprocess.Popen',new=spawn),patch('observador.owned_channel.secrets.token_bytes',new=draw):channel.start()
        self.assertTrue(bool(draws) and all(draws),'key_or_nonce_generated_before_spawn')
        self.assertEqual(len(calls),1)
        args,kwargs=calls[0]
        self.assertNotIn('env',kwargs)
        self.assertTrue(kwargs['close_fds'])
        self.assertEqual(len(kwargs['startupinfo'].lpAttributeList['handle_list']),4)
        self.assertEqual(kwargs['startupinfo'].hStdInput,0)
        self.assertEqual(len(channel._key),32)
        command=' '.join(args)
        # Boolean assertions avoid printing the runtime secret even on test failure.
        self.assertTrue(channel._key.hex() not in command,'ephemeral_key_in_command_line')
        self.assertTrue(base64.b64encode(channel._key).decode() not in command,'ephemeral_key_in_command_line')
        channel.close();self.assertIsNone(channel._key)

    def test_real_message_budget_saturates_and_cancellation_unblocks_one_pending_io(self):
        import threading
        channel=self.channel();channel.start()
        for ordinal in range(1,63):self.assertEqual(channel.sample()['ordinal'],ordinal)
        with self.assertRaises(wire.ChannelError):channel.sample()
        channel.close();self.assertEqual(channel.snapshot()['messages'],64)
        stalled=self.channel(fault='stall_sample',io_timeout=5);stalled.start();errors=[]
        def pending():
            try:stalled.sample()
            except wire.ChannelError:errors.append('closed')
        requester=threading.Thread(target=pending);requester.start()
        until=time.monotonic()+2
        while not stalled._operation.locked() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(stalled._operation.locked())
        with self.assertRaisesRegex(wire.ChannelError,'^owned_channel_busy$'):stalled.sample()
        started=time.monotonic();stalled.close();requester.join(3)
        self.assertLess(time.monotonic()-started,4)
        self.assertFalse(requester.is_alive());self.assertEqual(errors,['closed'])
        self.assertFalse(stalled.snapshot()['worker_alive']);self.assertFalse(stalled.snapshot()['process_running'])

    def test_real_wpf_fixture_does_not_receive_parent_channel_endpoints(self):
        import subprocess
        import ctypes
        from ctypes import wintypes
        from observador.owned_channel_win32 import Kernel
        channel=self.channel();channel.start();kernel=Kernel()
        target=Path(__file__).resolve().parents[1]/'tools/SyntheticWpfTaskApp/bin/Release/net8.0-windows/SyntheticWpfTaskApp.exe'
        fixture=subprocess.Popen([str(target)],close_fds=True,creationflags=subprocess.CREATE_NO_WINDOW)
        compare=ctypes.WinDLL('kernelbase',use_last_error=True).CompareObjectHandles
        compare.argtypes=[wintypes.HANDLE,wintypes.HANDLE];compare.restype=wintypes.BOOL
        try:
            self.assertIsNone(fixture.poll())
            # If a numeric handle was reused by WPF, compare the actual kernel object
            # instead of treating the coincident number as inherited capability.
            for handle in tuple(channel._handles):
                copied=wintypes.HANDLE()
                if kernel.api.DuplicateHandle(int(fixture._handle),handle,kernel.current(),ctypes.byref(copied),0,False,2):
                    try:self.assertFalse(compare(handle,copied))
                    finally:kernel.close(copied.value)
            self.assertEqual(channel.sample()['ordinal'],1)
            print('OWNED_WPF_ISOLATION_VERIFIED',json.dumps(dict(real_wpf_child=True,channel_endpoints_not_inherited=True,
                  bootstrap_already_closed=True,adapter_enabled=False,human_acceptance=False)))
        finally:
            if fixture.poll() is None:fixture.terminate()
            fixture.wait(timeout=5)
