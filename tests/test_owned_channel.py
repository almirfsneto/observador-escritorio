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
