"""Real interpreter lifetime, deliberately delayed synthetic cleanup; no desktop."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT='''
import sys,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
from observador.lab_controller import LaboratoryWindow
window=LaboratoryWindow.__new__(LaboratoryWindow)
window.finished=False;window.session=None;window.cleanup=None
window.tk=SimpleNamespace(DISABLED='disabled')
button=SimpleNamespace(config=lambda **kw:None)
window.launch_btn=window.start_btn=window.pause_btn=window.stop_btn=window.persist_box=button
window.status_var=SimpleNamespace(set=lambda value:None)
def cleanup():
    time.sleep(.2)
    Path(sys.argv[2]).write_bytes(b'cleaned')
window._cleanup=cleanup
window.stop()
window.cleanup.join(timeout=.01)
# Main returns while cleanup is pending, modeling an exhausted bounded join.
'''


class CleanupLifetimeTest(unittest.TestCase):
    def test_interpreter_waits_for_owned_cleanup_after_bounded_join_expires(self):
        source=Path(__file__).resolve().parents[1]/'src'
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'synthetic.cleanup'
            result=subprocess.run([sys.executable,'-I','-S','-c',SCRIPT,str(source),str(marker)],
                                  capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,'synthetic cleanup subprocess failed')
            self.assertTrue(marker.exists(),'interpreter abandoned the cleanup worker')
            self.assertEqual(marker.read_bytes(),b'cleaned')
