"""Isolated IPC-only fixture. No observer/UIA, capture, socket, disk output or agent import."""
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import threading
import time


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def main():
    kernel=None;handles=[];key=None;stage=71
    try:
        if sys.platform!='win32':return 79
        wire=load('owned_channel_protocol');win=load('owned_channel_win32');kernel=win.Kernel()
        if len(sys.argv)>=2 and sys.argv[1]=='--probe':
            return 0 if all(kernel.flags(int(value)) is None for value in sys.argv[2:]) else 91
        if len(sys.argv)!=8 or sys.argv[1]!='--owned-ipc-fixture':return 79
        stage=72
        read,write,bootstrap,parent=(int(v) for v in sys.argv[2:6]);handles=[read,write,bootstrap,parent]
        if len(set(handles))!=4:return 79
        fault=sys.argv[6];decoys=[] if sys.argv[7]=='none' else [int(v) for v in sys.argv[7].split(',')]
        if len(decoys)>8:return 79
        private=True
        for handle in handles:
            if kernel.flags(handle) is None:return 79
            kernel.inherit(handle,False);private=private and kernel.flags(handle)==0
        absent=all(kernel.flags(handle) is None for handle in decoys)
        started=time.monotonic();deadline=[started+5]
        def guard():
            if not kernel.alive(parent) or time.monotonic()>=deadline[0]:raise OSError('owned_fixture_expired')
        until=started+5
        stage=73
        key=kernel.read(bootstrap,32,until,guard);kernel.expect_eof(bootstrap,until,guard)
        kernel.close(bootstrap);handles.remove(bootstrap)
        # At this point even a child using unrestricted handle inheritance gets none
        # of the channel handles. The key pipe is already closed before this probe.
        stage=74
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESTDHANDLES
        startup.hStdInput=startup.hStdOutput=startup.hStdError=0
        probe=subprocess.run([sys.executable,'-I','-S','-B',str(Path(__file__).absolute()),'--probe',
                              *(str(h) for h in (read,write,parent))],close_fds=False,startupinfo=startup,
                             creationflags=subprocess.CREATE_NO_WINDOW,timeout=3)
        descendant_denied=probe.returncode==0
        def watchdog():
            while kernel.alive(parent) and time.monotonic()<deadline[0]:time.sleep(.02)
            os._exit(80)
        threading.Thread(target=watchdog,daemon=True).start()
        if fault=='wrong_key':key=bytes([key[0]^1])+key[1:]
        stage=75
        actual_parent=kernel.identity(parent);actual_child=kernel.identity(kernel.current())
        def receive():
            first=kernel.read(read,1,deadline[0],guard)
            stop=min(deadline[0],time.monotonic()+5)
            size=wire.frame_size(first+kernel.read(read,3,stop,guard))
            return kernel.read(read,size,stop,guard)
        def send(raw):
            packet=wire.length_header(len(raw))+raw
            kernel.write(write,packet,min(deadline[0],time.monotonic()+5),guard)
        stage=76
        raw=receive();frame=wire.decode(raw);context=frame['binding']
        if (context['parent']!=actual_parent or context['child']!=actual_child or
                context['fixture_sha256']!=wire.fixture_digest()):return 79
        epoch,session,nonce=frame['epoch'],frame['session'],frame['nonce'];generation=1;sequence=0
        stage=77
        wire.verify(raw,key,'parent',kind='hello',epoch=epoch,session=session,generation=generation,
                    sequence=0,nonce=nonce,binding=context)
        deadline[0]=started+context['ttl_ms']/1000
        evidence=dict(action='paired',bootstrap_closed=True,handles_private=private,
                      decoys_absent=absent,descendant_denied=descendant_denied)
        def proof():
            return wire.seal(key,'child',kind='proof',epoch=epoch,session=session,generation=generation,
                             sequence=0,nonce=nonce,binding=context,payload=evidence)
        if fault=='stall':time.sleep(30);return 79
        if fault=='exit':return 79
        stage=78
        reply=proof()
        if fault=='wrong_identity':
            bad=wire.decode(reply);bad['binding']['child']['start_ticks']+=1
            bad['mac']=wire.mac(key,'child',{k:v for k,v in bad.items() if k!='mac'});reply=wire.canonical(bad)
        elif fault in ('bad_mac','short_mac'):
            bad=wire.decode(reply);bad['mac']='0'*(63 if fault=='short_mac' else 64);reply=wire.canonical(bad)
        elif fault=='duplicate':reply=b'{"version":1,'+reply[1:]
        elif fault=='nan':reply=reply.replace(b'"bootstrap_closed":true',b'"bootstrap_closed":NaN')
        elif fault=='oversize':
            kernel.write(write,(wire.MAX_WIRE+1).to_bytes(4,'big'),until,guard);return 79
        elif fault=='truncated':
            kernel.write(write,wire.length_header(len(reply))+reply[:len(reply)//2],until,guard);return 79
        elif fault=='flood':
            kernel.write(write,b'x'*(wire.MAX_WIRE*8),until,guard);return 79
        send(reply)
        stage=79
        state='paired_start';ordinal=0;total=1
        while True:
            raw=receive();frame=wire.decode(raw);total+=1
            if total>wire.MAX_MESSAGES:return 79
            if frame['kind']=='hello':
                if state!='needs_pair' or frame['nonce']==nonce:return 79
                generation+=1;nonce=frame['nonce'];sequence=0
                wire.verify(raw,key,'parent',kind='hello',epoch=epoch,session=session,generation=generation,
                            sequence=0,nonce=nonce,binding=context)
                send(proof());state='paired_resume';continue
            sequence+=1
            command=wire.verify(raw,key,'parent',kind='command',epoch=epoch,session=session,
                                generation=generation,sequence=sequence,nonce=nonce,binding=context)
            action=command['action']
            if fault=='stall_sample' and action=='sample':time.sleep(30);return 79
            if action=='start' and state=='paired_start':state='active'
            elif action=='resume' and state=='paired_resume':state='active'
            elif action=='sample' and state=='active' and command['ordinal']==ordinal+1:ordinal+=1
            elif action=='pause' and state=='active':state='needs_pair'
            elif action=='stop':state='closed'
            else:return 79
            result=dict(action=action,ordinal=command['ordinal'],state='paused' if state=='needs_pair' else state,
                        scope='owned_ipc_fixture_transport_not_inbox_or_uia_ack')
            send(wire.seal(key,'child',kind='ack',epoch=epoch,session=session,generation=generation,
                           sequence=sequence,nonce=nonce,binding=context,payload=result))
            if state=='closed':
                kernel.expect_eof(read,deadline[0],guard);return 0
    except BaseException:
        return stage # Never print an exception, key, frame or identity to stdio.
    finally:
        key=None
        if kernel:
            for handle in handles:kernel.close(handle)


if __name__=='__main__':
    raise SystemExit(main())
