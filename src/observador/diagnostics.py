"""Closed aggregate diagnostics. Never contains identifiers, events or paths."""
from copy import deepcopy
import json
from pathlib import Path
import time

from .acceptance_report import obj,enum,nullable,_validate,ReportError,safe_output_directory

COUNT = {'type':'integer','minimum':0,'maximum':2**63-1}
DURATION = {'type':'number','minimum':0,'maximum':1e12}
FLOW = ('received','accepted','rejected','coalesced','overflow','drained','discarded')
LEDGER = ('received','enqueued','ingress_rejected','buffered','inflight','written','duplicates','write_rejected','uncertain')
ERRORS = ('none','busy','full','io','projection','post_commit','rollback_failed','commit_unknown')
GAPS = ('component_snapshots_not_atomic','native_sample_unavailable','native_sample_stale','native_queue_unavailable',
        'writer_unavailable','volatile_counters_reset_on_restart','budget_not_os_quota','sampling_not_continuous',
        'native_and_python_phases_differ','purge_includes_preexisting_rows','commit_outcome_uncertain',
        'human_acceptance_pending','row_balance_not_proven','writer_shutdown_incomplete')
BUDGET = obj(dict(limit_bytes=COUNT,reserve_bytes=COUNT,observed_bytes=nullable(COUNT),
                  peak_observed_bytes=nullable(COUNT),observations=COUNT,physical_quota={'const':False}))
SCHEMA = {'$schema':'https://json-schema.org/draft/2020-12/schema',**obj({
    'schema_version':{'const':1},'kind':{'const':'synthetic_lab_diagnostics'},'pilot_authorized':{'const':False},
    'sample_sequence':COUNT,'scope':{'const':'component_lifetimes_not_global'},
    'agent':obj(dict(state=enum(('disabled','starting','active','pausing','paused','stopped','expired')),
                     uptime_ms=DURATION)),
    'native':nullable(obj(dict(sample_age_ms=DURATION,dropped=COUNT,
        callbacks=obj({key:COUNT for key in ('focus','invoke','toggle','excluded','errors')}),
        queues=nullable(obj(dict(output_depth=COUNT,output_capacity={'const':512},focus_depth=COUNT,focus_capacity={'const':256})))))),
    'python':nullable(obj(dict(enabled={'type':'boolean'},stopped={'type':'boolean'},ready={'type':'boolean'},
        pending_ack={'type':'boolean'},expired={'type':'boolean'},flow=obj({key:COUNT for key in FLOW}),
        buffered=COUNT,capacity=COUNT,invalid_messages=COUNT,sequence_gaps=COUNT))),
    'writer':nullable(obj(dict(health=enum(('starting','ready','quota_full','storage_unavailable','shutdown_timeout')),
        shutdown={'type':'boolean'},worker_alive={'type':'boolean'},capacity_batches=COUNT,
        row_balance=enum(('balanced','unreconciled','unavailable')),
        ledger=obj({key:COUNT for key in LEDGER}),last_batch_ms=nullable(DURATION),
        storage=nullable(obj(dict(rows_at_open=COUNT,rows_current=nullable(COUNT),purged=COUNT,
                                  last_error=enum(ERRORS),budget=BUDGET)))))),
    'gaps':{'type':'array','maxItems':len(GAPS),'uniqueItems':True,'items':enum(GAPS)},
})}


class DiagnosticError(ValueError):
    pass


def validate_diagnostics(document):
    try:
        _validate(document,SCHEMA)
        if document['sample_sequence']<1:raise ValueError()
        p,w,n=document['python'],document['writer'],document['native']
        state=document['agent']['state']
        if p:
            f=p['flow']
            if (f['received']!=f['accepted']+f['rejected']+f['coalesced']+f['overflow']
                    or f['accepted']!=f['drained']+f['discarded']+p['buffered']
                    or not 1<=p['capacity']<=4096 or p['buffered']>p['capacity']):raise ValueError()
            expected=('expired' if p['expired'] else 'stopped' if p['stopped'] else
                      'starting' if p['enabled'] and p['pending_ack'] else 'active' if p['enabled'] else
                      'pausing' if p['pending_ack'] else 'paused')
            if (state!=expected or (p['stopped'] and (p['enabled'] or p['buffered']))
                    or (p['expired'] and not p['stopped']) or (state=='active' and not p['ready'])):raise ValueError()
        elif state!='disabled':raise ValueError()
        if n and n['queues']:
            if n['queues']['output_depth']>512 or n['queues']['focus_depth']>256:raise ValueError()
        if w:
            l=w['ledger']
            if (l['received']!=l['enqueued']+l['ingress_rejected']
                    or l['enqueued']!=sum(l[key] for key in ('buffered','inflight','written','duplicates','write_rejected','uncertain'))
                    or not 1<=w['capacity_batches']<=64 or l['buffered']>100*w['capacity_batches']
                    or l['inflight']>100 or (not w['worker_alive'] and (l['buffered'] or l['inflight']))
                    or (w['health']=='ready' and not w['worker_alive'] and not w['shutdown'])):raise ValueError()
            if w['storage']:
                b=w['storage']['budget']
                if (b['observations']==0)!=(b['observed_bytes'] is None):raise ValueError()
                if b['observed_bytes'] is not None and (b['peak_observed_bytes'] is None or b['observed_bytes']>b['peak_observed_bytes']):raise ValueError()
                if b['reserve_bytes']>b['limit_bytes']:raise ValueError()
                balance=('unavailable' if w['storage']['rows_current'] is None else 'balanced'
                         if w['storage']['rows_at_open']+l['written']-w['storage']['purged']==w['storage']['rows_current']
                         and not l['uncertain'] else 'unreconciled')
            else:balance='unavailable'
            if w['row_balance']!=balance or (l['uncertain'] and w['health']=='ready'):raise ValueError()
        required={'component_snapshots_not_atomic','volatile_counters_reset_on_restart','budget_not_os_quota',
                  'sampling_not_continuous','native_and_python_phases_differ','purge_includes_preexisting_rows','human_acceptance_pending'}
        if n is None:required.add('native_sample_unavailable')
        elif n['queues'] is None:required.add('native_queue_unavailable')
        if n and n['sample_age_ms']>2000:required.add('native_sample_stale')
        if w is None or w['storage'] is None:required.add('writer_unavailable')
        if w and w['ledger']['uncertain']:required.add('commit_outcome_uncertain')
        if w and w['row_balance']!='balanced':required.add('row_balance_not_proven')
        if w and w['health']=='shutdown_timeout':required.add('writer_shutdown_incomplete')
        if not required<=set(document['gaps']):raise ValueError()
        return document
    except (ReportError,ValueError,TypeError,KeyError,OverflowError):
        raise DiagnosticError('diagnostic_document_rejected') from None


class DiagnosticRecorder:
    def __init__(self, *, monotonic=time.monotonic):
        self.clock=monotonic
        self.started=monotonic()
        self.sequence=0

    def sample(self, *, stream=None,writer=None):
        self.sequence+=1
        p=stream.diagnostics_snapshot() if stream else None
        native=None
        if p:
            native=(dict(sample_age_ms=p['native_age_ms'],callbacks=p['native_callbacks'],
                         dropped=p['native_dropped'],queues=p['native_queues']) if p['native_age_ms'] is not None else None)
            for key in ('native_age_ms','native_callbacks','native_dropped','native_queues'):p.pop(key)
        state=('disabled' if p is None else 'expired' if p['expired'] else 'stopped' if p['stopped'] else
               'starting' if p['enabled'] and p['pending_ack'] else 'active' if p['enabled'] else
               'pausing' if p['pending_ack'] else 'paused')
        w=writer.diagnostics_snapshot() if writer else None
        gaps=['component_snapshots_not_atomic','volatile_counters_reset_on_restart','budget_not_os_quota',
              'sampling_not_continuous','native_and_python_phases_differ','purge_includes_preexisting_rows','human_acceptance_pending']
        if native is None:gaps.append('native_sample_unavailable')
        elif native['queues'] is None:gaps.append('native_queue_unavailable')
        if native and native['sample_age_ms']>2000:gaps.append('native_sample_stale')
        if w is None or w['storage'] is None:gaps.append('writer_unavailable')
        if w and w['ledger']['uncertain']:gaps.append('commit_outcome_uncertain')
        if w and w['row_balance']!='balanced':gaps.append('row_balance_not_proven')
        if w and w['health']=='shutdown_timeout':gaps.append('writer_shutdown_incomplete')
        return validate_diagnostics(dict(schema_version=1,kind='synthetic_lab_diagnostics',pilot_authorized=False,
            sample_sequence=self.sequence,scope='component_lifetimes_not_global',
            agent=dict(state=state,uptime_ms=max(0,(self.clock()-self.started)*1000)),native=native,python=p,writer=w,gaps=gaps))


class DiagnosticHistory:
    """Replay/rollback checks within ONE collector lifetime, not authentication."""
    def __init__(self):self.previous=None

    def accept(self, document):
        validate_diagnostics(document)
        previous=self.previous
        if previous:
            if document['sample_sequence']<=previous['sample_sequence'] or document['agent']['uptime_ms']<previous['agent']['uptime_ms']:
                raise DiagnosticError('diagnostic_replay_rejected')
            for component,key in (('python','flow'),('writer','ledger')):
                before,after=previous[component],document[component]
                if before is not None and after is None:raise DiagnosticError('diagnostic_component_reset_rejected')
                if before and after:
                    monotonic_keys=FLOW if component=='python' else ('received','enqueued','ingress_rejected','written','duplicates','write_rejected','uncertain')
                    if any(after[key][name]<before[key][name] for name in monotonic_keys):
                        raise DiagnosticError('diagnostic_counter_rollback_rejected')
                    if component=='python' and before['stopped'] and not after['stopped']:
                        raise DiagnosticError('diagnostic_lifecycle_rollback_rejected')
                    if component=='writer' and before['shutdown'] and not after['shutdown']:
                        raise DiagnosticError('diagnostic_lifecycle_rollback_rejected')
        self.previous=deepcopy(document)
        return deepcopy(document)


def write_diagnostics(document,repository,destination):
    validate_diagnostics(document)
    path=Path(destination).absolute()
    safe_output_directory(repository,path.parent).mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(document,stream,ensure_ascii=False,allow_nan=False,indent=2)
        stream.write('\n')
    return path


def read_diagnostics(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise DiagnosticError('diagnostic_duplicate_key_rejected')
            result[key]=value
        return result
    try:
        with Path(path).open('rb') as stream:payload=stream.read(65537)
        if len(payload)>65536:raise DiagnosticError('diagnostic_document_too_large')
        document=json.loads(payload,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return validate_diagnostics(document)
    except (ValueError,UnicodeError,RecursionError):
        raise DiagnosticError('diagnostic_document_rejected') from None


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Diagnóstico agregado desativado; sem iniciar coleta.')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    write_diagnostics(DiagnosticRecorder().sample(),Path(__file__).resolve().parents[2],args.out)
    print('{"saved":true,"capture_real":false,"pilot_authorized":false}')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError):raise SystemExit('Diagnóstico não salvo; confira destino novo fora de Git.') from None
