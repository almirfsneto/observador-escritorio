"""Strict wire contract for the isolated owned-child IPC fixture, not the UIA agent."""
import hashlib
import hmac
import json
from pathlib import Path
import re
import struct
from uuid import UUID

MAX_WIRE=16384
MAX_MESSAGES=64
DIRECTION={'parent','child'}
FRAME_KEYS={'version','kind','epoch','session','generation','sequence','nonce','binding','payload','mac'}
IDENTITY_KEYS={'pid','start_ticks','session_slot','image_sha256'}
BINDING_KEYS={'parent','child','fixture_sha256','ttl_ms','handle_count'}
KINDS={'hello','proof','command','ack'}
ACTIONS={'start','sample','pause','resume','stop'}


class ChannelError(ValueError):
    pass


def reject():
    raise ChannelError('owned_channel_rejected')


def integer(value,minimum=0,maximum=2**63-1):
    if type(value) is not int or not minimum<=value<=maximum:reject()
    return value


def hex_digest(value):
    if type(value) is not str or re.fullmatch('[a-f0-9]{64}',value) is None:reject()


def identity(value):
    if type(value) is not dict or set(value)!=IDENTITY_KEYS:reject()
    integer(value['pid'],1,2**32-1);integer(value['start_ticks'],1)
    integer(value['session_slot'],0,2**32-1);hex_digest(value['image_sha256'])


def binding(value):
    if type(value) is not dict or set(value)!=BINDING_KEYS:reject()
    identity(value['parent']);identity(value['child']);hex_digest(value['fixture_sha256'])
    integer(value['ttl_ms'],1000,900000)
    if value['handle_count']!=4 or type(value['handle_count']) is not int:reject()
    if value['parent']['pid']==value['child']['pid'] or value['parent']['session_slot']!=value['child']['session_slot']:reject()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def payload(kind,value):
    if type(value) is not dict:reject()
    if kind=='hello':
        if value!={'action':'pair'}:reject()
    elif kind=='proof':
        if set(value)!={'action','bootstrap_closed','handles_private','descendant_denied'}:reject()
        if value['action']!='paired' or any(value[k] is not True for k in value if k!='action'):reject()
    elif kind=='command':
        if set(value)!={'action','ordinal'} or value['action'] not in ACTIONS:reject()
        integer(value['ordinal'],0,10000)
        if (value['action']=='sample')!=(value['ordinal']>0):reject()
    else:
        if set(value)!={'action','ordinal','state','scope'} or value['action'] not in ACTIONS:reject()
        integer(value['ordinal'],0,10000)
        if (value['action']=='sample')!=(value['ordinal']>0):reject()
        if value['state'] not in ('active','paused','closed') or value['scope']!='owned_ipc_fixture_transport_not_inbox_or_uia_ack':reject()


def validate(frame):
    if type(frame) is not dict or set(frame)!=FRAME_KEYS:reject()
    if type(frame['version']) is not int or frame['version']!=1 or frame['kind'] not in KINDS:reject()
    for key in ('epoch','session'):
        if type(frame[key]) is not str or str(UUID(frame[key]))!=frame[key]:reject()
    integer(frame['generation'],1);integer(frame['sequence'],0,MAX_MESSAGES)
    hex_digest(frame['nonce']);hex_digest(frame['mac']);binding(frame['binding'])
    payload(frame['kind'],frame['payload'])


def decode(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:reject()
            result[key]=value
        return result
    try:
        if type(raw) is not bytes or not 0<len(raw)<=MAX_WIRE:reject()
        frame=json.loads(raw.decode('ascii'),object_pairs_hook=pairs,
                         parse_float=lambda _:reject(),parse_constant=lambda _:reject())
        validate(frame)
        if canonical(frame)!=raw:reject()
        return frame
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):reject()


def length_header(size):
    integer(size,1,MAX_WIRE)
    return struct.pack('>I',size)


def frame_size(header):
    if type(header) is not bytes or len(header)!=4:reject()
    return integer(struct.unpack('>I',header)[0],1,MAX_WIRE)


def mac(key,direction,body):
    if type(key) is not bytes or len(key)!=32 or direction not in DIRECTION:reject()
    return hmac.new(key,b'observador-owned-ipc-v1\0'+direction.encode()+b'\0'+canonical(body),hashlib.sha256).hexdigest()


def seal(key,direction,*,kind,epoch,session,generation,sequence,nonce,binding,payload):
    body=dict(version=1,kind=kind,epoch=epoch,session=session,generation=generation,
              sequence=sequence,nonce=nonce,binding=binding,payload=payload)
    frame=dict(body,mac=mac(key,direction,body));validate(frame)
    raw=canonical(frame);length_header(len(raw))
    return raw


def verify(raw,key,direction,*,kind,epoch,session,generation,sequence,nonce,binding):
    frame=decode(raw)
    expected=dict(kind=kind,epoch=epoch,session=session,generation=generation,sequence=sequence,nonce=nonce,binding=binding)
    if any(frame[k]!=v for k,v in expected.items()):reject()
    body={k:v for k,v in frame.items() if k!='mac'}
    if not hmac.compare_digest(frame['mac'],mac(key,direction,body)):reject()
    return frame['payload']


def fixture_digest():
    """Source pin, not code attestation against a same-token filesystem attacker."""
    digest=hashlib.sha256()
    for name in ('owned_channel.py','owned_channel_child.py','owned_channel_protocol.py','owned_channel_win32.py'):
        path=Path(__file__).with_name(name)
        data=path.read_bytes()
        if len(data)>512*1024:reject()
        digest.update(name.encode('ascii')+b'\0'+data)
    return digest.hexdigest()
