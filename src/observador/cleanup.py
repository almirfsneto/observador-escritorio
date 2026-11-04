"""Independent cleanup attempts and bounded diagnostics; never stores exceptions."""
import subprocess
import threading

RESOURCES=('session','sink','fixture','secondary','sampler','observation','provider',
           'stream','stop_command','reader','writer','stdin','stdout','controls','cleanup_worker')


class CleanupStatus:
    def __init__(self):
        self.errors=dict.fromkeys(RESOURCES,0);self.finished=False;self.lock=threading.Lock()

    def fail(self,resource):
        if resource not in RESOURCES:raise ValueError('cleanup_resource_rejected')
        with self.lock:self.errors[resource]=min(2**63-1,self.errors[resource]+1)

    def attempt(self,resource,action):
        try:action();return True
        except Exception:
            self.fail(resource);return False

    def check(self,resource,predicate):
        try:
            if predicate():return True
        except Exception:pass
        self.fail(resource);return False

    @property
    def confirmed(self):
        with self.lock:return self.finished and not any(self.errors.values())

    def finish(self):
        with self.lock:self.finished=True

    def snapshot(self):
        with self.lock:
            return dict(kind='owned_cleanup',status='pending' if not self.finished else
                        'cleanup_unconfirmed' if any(self.errors.values()) else 'confirmed',
                        errors=dict(self.errors))

    def stop_process(self,resource,process,*,force=False):
        if process is None:return
        try:running=process.poll() is None
        except Exception:self.fail(resource);running=True
        if running:
            if not self.attempt(resource,process.kill if force else process.terminate):
                self.attempt(resource,process.kill)
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.attempt(resource,process.kill)
            self.attempt(resource,lambda:process.wait(timeout=2))
        except Exception:
            self.fail(resource)
            self.attempt(resource,process.kill)
            self.attempt(resource,lambda:process.wait(timeout=2))
        self.check(resource,lambda:process.poll() is not None)
