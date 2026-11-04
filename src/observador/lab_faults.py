"""Deterministic faults for the synthetic queue only; no files, CLI or privileges."""
import sqlite3

STAGES = frozenset(('before_transaction','after_insert','before_commit','after_commit',
                    'before_rollback','after_rollback','purge_before_commit','purge_after_commit'))


class LabFaultPlan:
    def __init__(self, plan):
        if (type(plan) is not dict or set(plan)-STAGES or sum(map(len,plan.values()))>16
                or any(type(values) is not list or any(value not in ('busy','full','io') for value in values)
                       for values in plan.values())):
            raise ValueError('synthetic_fault_plan_rejected')
        self.plan = {key:list(values) for key,values in plan.items()}

    def hit(self, stage):
        values = self.plan.get(stage,[])
        if values:
            code = {'busy':sqlite3.SQLITE_BUSY,'full':sqlite3.SQLITE_FULL,'io':sqlite3.SQLITE_IOERR}[values.pop(0)]
            error = sqlite3.OperationalError('synthetic_storage_fault')
            error.sqlite_errorcode = code
            raise error
