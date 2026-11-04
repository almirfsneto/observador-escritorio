"""Executable protocol MODEL, not an IPC transport or source authenticator.

All peer identities and key delivery are simulated trusted inputs. There is NO
kernel peer verification, listener, filesystem token, native host or collector
integration. Never use this class to authorize OfflineBridge or real data.
"""
from copy import deepcopy
import hashlib
import hmac
import re
import secrets
import time
from uuid import uuid4

from .offline_bridge import BridgeError,canonical,number,uuid,validate_batch,validate_source,MAX_BYTES

IDENTITY_KEYS={'provider_pid','provider_created_ticks','fixture_pid','fixture_created_ticks','session_slot',
               'provider_alias','fixture_alias'}
ENVELOPE_KEYS={'schema_version','kind','simulation_only','epoch','challenge','generation','sequence','identity','source','batch','mac'}


def validate_model_identity(identity):
    if type(identity) is not dict or set(identity)!=IDENTITY_KEYS:raise BridgeError('model_identity_rejected')
    for name in ('provider_pid','fixture_pid'):number(identity[name],1,2**32-1)
    for name in ('provider_created_ticks','fixture_created_ticks'):number(identity[name],1,2**63-1)
    number(identity['session_slot'],0,2**32-1)
    if (identity['provider_pid']==identity['fixture_pid'] or identity['provider_alias']!='owned_windows_observer'
            or identity['fixture_alias']!='owned_synthetic_wpf'):
        raise BridgeError('model_identity_rejected')
    return identity


class SyntheticAuthModel:
    """One synthetic peer, one challenge, <=64 frames, 5s challenge/900s session.

    The signer is deliberately named for_test: key provision/peer identity are
    assumptions in this model, NOT a verified property of a Windows process.
    No method ingests into the inbox or acknowledges producer pause.
    """
    def __init__(self,*,monotonic=time.monotonic):
        self.monotonic=monotonic;self.last_clock=monotonic()
        self.state='disabled';self.generation=0;self.next_sequence=1
        self.epoch=str(uuid4());self.challenge=None;self._key=None
        self.identity=None;self.source=None;self.deadline=None;self.challenge_deadline=None

    def _reject(self):
        self.state='closed';self._key=None;self.challenge=None
        raise BridgeError('synthetic_auth_model_rejected')

    def _alive(self):
        now=self.monotonic()
        if now<self.last_clock or self.deadline is None or now>=self.deadline:self._reject()
        self.last_clock=now
        return now

    def arm_for_test(self,identity,source):
        """Models explicit consent + trusted kernel inspection + private key delivery.

        These preconditions are NOT implemented here. Cannot rearm a closed owner.
        """
        if self.state!='disabled':self._reject()
        try:
            validate_model_identity(identity);validate_source(source)
            if source['kind']!='windows':raise BridgeError('model_windows_only')
        except (ValueError,TypeError,KeyError):self._reject()
        self.identity=deepcopy(identity);self.source=deepcopy(source)
        self._key=secrets.token_bytes(32);self.deadline=self.monotonic()+900
        self.last_clock=self.monotonic();self._challenge()
        return self.challenge_document()

    def _challenge(self):
        self.generation+=1;self.challenge=secrets.token_hex(32)
        self.challenge_deadline=self.monotonic()+5;self.state='pairing'

    def challenge_document(self):
        now=self._alive()
        if self.state!='pairing' or now>=self.challenge_deadline:self._reject()
        return dict(schema_version=1,kind='synthetic_auth_model_challenge',simulation_only=True,
                    epoch=self.epoch,challenge=self.challenge,generation=self.generation,
                    identity=deepcopy(self.identity),source=deepcopy(self.source))

    def _mac(self,body):
        # Domain separation: no bridge ACK/signature shares this model-only purpose.
        return hmac.new(self._key,b'observador-synthetic-auth-model-v1\0'+canonical(body).encode(),hashlib.sha256).hexdigest()

    def sign_for_test(self,batch=None):
        """Synthetic trusted-peer oracle; NEVER expose as a signing endpoint."""
        if self._key is None:self._reject()
        body=dict(schema_version=1,kind='synthetic_auth_model_proof' if batch is None else 'synthetic_auth_model_frame',
                  simulation_only=True,epoch=self.epoch,challenge=self.challenge,generation=self.generation,
                  sequence=0 if batch is None else self.next_sequence,identity=deepcopy(self.identity),
                  source=deepcopy(self.source),batch=deepcopy(batch))
        return dict(body,mac=self._mac(body))

    def verify(self,envelope):
        """Return model acceptance only. No durable ACK, source auth or IPC claimed."""
        try:
            now=self._alive()
            if type(envelope) is not dict or set(envelope)!=ENVELOPE_KEYS:raise ValueError()
            if len(canonical(envelope).encode())>MAX_BYTES+4096:raise ValueError()
            body={k:v for k,v in envelope.items() if k!='mac'}
            if (type(body['schema_version']) is not int or body['schema_version']!=1 or body['simulation_only'] is not True
                    or not isinstance(envelope['mac'],str) or not re.fullmatch('[a-f0-9]{64}',envelope['mac'])
                    or not hmac.compare_digest(envelope['mac'],self._mac(body))):raise ValueError()
            uuid(body['epoch']);number(body['generation']);number(body['sequence'],0,64)
            validate_model_identity(body['identity']);validate_source(body['source'])
            if (body['epoch']!=self.epoch or body['challenge']!=self.challenge or body['generation']!=self.generation
                    or body['identity']!=self.identity or body['source']!=self.source):raise ValueError()
            if self.state=='pairing':
                if now>=self.challenge_deadline or body['kind']!='synthetic_auth_model_proof' or body['batch'] is not None or body['sequence']!=0:raise ValueError()
                self.state='active'
            elif self.state=='active':
                if body['kind']!='synthetic_auth_model_frame' or body['sequence']!=self.next_sequence:raise ValueError()
                validate_batch(body['batch'])
                if body['batch']['source']!=self.source:raise ValueError()
                self.next_sequence+=1
            else:raise ValueError()
            return dict(schema_version=1,kind='synthetic_auth_model_result',simulation_only=True,
                        scope='model_transport_only_no_inbox_or_producer_ack',state=self.state,
                        generation=self.generation,next_sequence=self.next_sequence)
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError):self._reject()

    def pause(self):
        self._alive()
        if self.state!='active':self._reject()
        self.generation+=1;self.state='paused'
        return dict(simulation_only=True,state='paused',producer_pause_confirmed=False)

    def resume_for_test(self):
        self._alive()
        if self.state!='paused':self._reject()
        self._challenge();return self.challenge_document()

    def close(self):
        self.state='closed';self._key=None;self.challenge=None
