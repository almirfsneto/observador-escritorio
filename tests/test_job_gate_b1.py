"""One finite B1 matrix, two controlled death cases, and bounded negatives."""
import ctypes
from ctypes import wintypes as W
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from job_gate_b1_fixture import observe, members, stop_owned
from isolated_suspended_spawn import minimal_environment
from isolated_process_supervision import disarm_job
from observador.acceptance_metrics import OwnedJob
from observador.cleanup import CleanupStatus
from observador.owned_channel_win32 import Kernel
from observador.win32_handles import close_handle_once
from test_job_at_creation_windows import duplicate_process


def read_line(process):
    values=queue.Queue(maxsize=1)
    thread=threading.Thread(target=lambda:values.put(process.stdout.readline(4096)),daemon=True)
    thread.start()
    value=values.get(timeout=10)
    thread.join(timeout=2)
    if thread.is_alive():raise OSError('b1_control_unconfirmed')
    return value


def finish_popen(process,kernel):
    if process.poll() is None:
        try:
            process.stdin.write('stop\n');process.stdin.flush();process.wait(timeout=5)
        except (OSError,subprocess.TimeoutExpired):
            process.kill();process.wait(timeout=5)
    process.stdin.close();process.stdout.close()
    owner=SimpleNamespace(handle=process._handle.Detach(),close_state='open')
    close_handle_once(owner,kernel.api)


class GateB1ContractTest(unittest.TestCase):
    def test_error_truncation_duplicate_and_race_are_not_stable_proof(self):
        def api_for(ids,active=1,other=None,incomplete=False,failed=False):
            calls=[]
            def query(handle,kind,buffer,size,returned):
                if failed:return False
                if kind==3:
                    value=buffer._obj;seq=ids if not calls or other is None else other;calls.append(1)
                    value.assigned=len(seq)+int(incomplete);value.listed=len(seq)
                    for i,n in enumerate(seq):value.ids[i]=n
                else:W.DWORD.from_buffer(buffer,40).value=active
                return True
            return SimpleNamespace(QueryInformationJobObject=query,GetProcessId=lambda h:11)
        for api in (api_for([11],incomplete=True),api_for([11,11]),api_for([],failed=True)):
            with self.assertRaises(OSError):members(api,1)
        for api in (api_for([11],other=[11,22]),api_for([11],active=2)):
            worker=SimpleNamespace(job=SimpleNamespace(close_state='open',handle=1,api=api),api=api)
            self.assertFalse(observe(worker,'ready',[1])['stable'])
        worker=SimpleNamespace(job=SimpleNamespace(close_state='closed'))
        self.assertIsNone(observe(worker,'after_close',[])['active'])



@unittest.skipUnless(sys.platform=='win32','Requires real Windows kernel process/handle execution')
class GateB1WindowsTest(unittest.TestCase):
    def launch(self,args,tmp):
        return subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).with_name('job_gate_b1_fixture.py')),*args],
                                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                text=True,close_fds=True,env=minimal_environment(tmp),
                                creationflags=subprocess.CREATE_NO_WINDOW)

    def test_real_finite_matrix_eight_cells(self):
        for ancestor in (False,True):
            for descendant in (False,True):
                for no_window in (False,True):
                    with self.subTest(ancestor=ancestor,descendant=descendant,no_window=no_window),tempfile.TemporaryDirectory() as tmp:
                        kernel=Kernel();outer=None
                        p=self.launch(['row','desc' if descendant else 'single','no_window' if no_window else 'console',tmp],tmp)
                        try:
                            self.assertEqual(read_line(p).strip(),'ready')
                            if ancestor:
                                outer=OwnedJob();outer.assign(p);disarm_job(outer)
                            output,_=p.communicate('go\n',timeout=30)
                            self.assertEqual(p.returncode,0,'b1_row_failed')
                            result=json.loads(output)
                            self.assertEqual([s['phase'] for s in result['phases']],
                                             ['before_create','after_create','before_resume','after_resume','ready','before_close','after_close'])
                            self.assertTrue(result['job_zero'] and result['resources_closed'] and result['own_processes_exited'])
                            self.assertEqual(result['bulk_termination_calls'],0)
                            self.assertTrue(result['job_disarmed_before_close'])
                            self.assertFalse(result['phases'][-1]['consultable'])
                            result['controlled_ancestor']=ancestor
                            if outer:
                                outer._confirm_empty();self.assertTrue(outer.processes_confirmed)
                            result['outer_zero_confirmed']=bool(outer and outer.processes_confirmed)
                            print('B1_MATRIX '+json.dumps(result,sort_keys=True),flush=True)
                        finally:
                            cleanup=CleanupStatus()
                            cleanup.attempt('provider',lambda:finish_popen(p,kernel))
                            if outer:
                                def finish_outer():
                                    outer._confirm_empty();close_handle_once(outer,outer.api)
                                cleanup.attempt('session',finish_outer)
                            cleanup.finish();self.assertTrue(cleanup.confirmed,'b1_matrix_cleanup_unconfirmed')

    def death_case(self,stage):
        with tempfile.TemporaryDirectory() as tmp:
            kernel=Kernel();root=self.launch(['relay',stage,str(Path(tmp)/'state')],tmp)
            owner=worker=None
            try:
                packet=json.loads(read_line(root)) # PRIVATE slots never printed/asserted as values.
                self.assertTrue(set(packet)=={'owner_slot','worker_slot','snapshot','disarmed'},'b1_control_rejected')
                owner=duplicate_process(kernel,int(root._handle),packet['owner_slot'])
                worker=duplicate_process(kernel,int(root._handle),packet['worker_slot'])
                self.assertIs(packet['disarmed'],stage=='disarmed')
                snapshot=packet['snapshot'];self.assertTrue(snapshot['stable'])
                if stage=='armed':self.assertEqual(snapshot['unknown'],0)
                # Both roots die abruptly. Observer owns only PROCESS handles, no target Job.
                root.kill();root.wait(timeout=5)
                from isolated_job_creation import extended_api
                api=extended_api();self.assertTrue(api.TerminateProcess(owner.handle,1))
                self.assertEqual(api.WaitForSingleObject(owner.handle,2000),0)
                if stage=='armed':
                    self.assertEqual(api.WaitForSingleObject(worker.handle,5000),0)
                    survived=False
                else:
                    self.assertEqual(api.WaitForSingleObject(worker.handle,200),258)
                    survived=True # Actual counterexample; NOT automatic containment.
                print('B1_DOUBLE_DEATH '+json.dumps(dict(origin='win32',stage=stage,worker_survived=survived,
                    unknown=snapshot['unknown'],observer_target_job_handles=0,automatic_containment=not survived)),flush=True)
            finally:
                cleanup=CleanupStatus()
                # Emergency stop is outside the observation and is NEVER counted as autonomous containment.
                for item in (worker,owner):
                    if item:
                        def recover(o=item):
                            from isolated_job_creation import extended_api
                            api=extended_api()
                            try:stop_owned(o,api)
                            finally:close_handle_once(o,api)
                        cleanup.attempt('provider',recover)
                cleanup.attempt('provider',lambda:finish_popen(root,kernel))
                cleanup.finish();self.assertTrue(cleanup.confirmed,'b1_observer_cleanup_unconfirmed')
            print('B1_OBSERVER_RECOVERY verified_known_handles_only no_orphan',flush=True)

    def test_real_double_death_armed_suspended_known_worker(self):self.death_case('armed')
    def test_real_double_death_disarmed_worker_survives_until_observer_cleanup(self):self.death_case('disarmed')
