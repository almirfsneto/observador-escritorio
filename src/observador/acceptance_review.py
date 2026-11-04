"""Closed local diagnostic companion to acceptance v1; never grants acceptance.

Does not import an operator file, start capture or infer why native events dropped.
The v1 contract remains unchanged; these are review findings, not human sign-off.
"""
from copy import deepcopy
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path

from .acceptance_report import (INTEGER,ReportError,_validate,obj,enum,nullable,
    finalize_report,operator_trial_recorded,safe_output_directory)
from .acceptance_test_runner import CATEGORIES,read_summary,MARKER

PHASES=('active','starting','pausing','paused','stopped','unknown')
HEALTH_SCHEMA=obj(dict(samples=INTEGER,reported_drop_highwater=nullable(INTEGER),
    drop_increases_seen=obj({p:INTEGER for p in PHASES}),
    callback_errors_highwater=nullable(INTEGER),output_depth_peak=nullable(INTEGER),
    focus_depth_peak=nullable(INTEGER),last_sample_age_ms=nullable(INTEGER),
    final_health_confirmed={'const':False}))
ISSUES=('operator_trial_not_recorded','manual_checks_incomplete','manual_checks_failed',
    'native_drop_requires_review','native_drop_cause_unknown','native_health_sampling_not_final',
    'test_counts_unknown','test_failures_or_no_executed_success','skips_require_review',
    'skip_details_unavailable','commit_unavailable','source_state_unknown','source_modified',
    'cleanup_unconfirmed','expiry_not_observed','cross_os_trial_required','independent_review_pending',
    'preparation_incomplete','pilot_not_authorized')
TOTAL={**INTEGER,'maximum':6*INTEGER['maximum']}
REVIEW_SCHEMA={'$schema':'https://json-schema.org/draft/2020-12/schema',**obj(dict(
    schema_version={'const':1},kind={'const':'synthetic_acceptance_review'},
    report_sha256={'type':'string','pattern':'^[a-f0-9]{64}$'},
    pilot_authorized={'const':False},review_status={'const':'PENDENTE_REVISAO_HUMANA'},
    os_family=enum(('windows10','windows11','windows_server','unsupported')),
    declared_operator_trial={'type':'boolean'},
    source=obj(dict(commit_available={'type':'boolean'},state=enum(('clean','modified','unknown')))),
    tests=obj(dict(status=enum(('PASSOU','FALHOU','NAO_EXECUTADO')),discovered=nullable(INTEGER),
                   executed=nullable(INTEGER),skipped=nullable(INTEGER),
                   skip_categories=obj({k:INTEGER for k in CATEGORIES}),
                   category_provenance=enum(('structured_runner','unavailable')))),
    sessions=obj({k:TOTAL for k in ('count','started','expired','cleanup_confirmed','cleanup_unconfirmed',
                                   'persistence_enabled','persistence_with_writes')}),
    human_checks=obj({k:INTEGER for k in ('passed','failed','not_executed')}),
    native=obj(dict(reported_dropped=TOTAL,sessions_with_drops=INTEGER,
                    attribution={'const':'unknown_from_aggregate'},
                    loss_rate={'const':None},
                    health_samples={'type':'array','maxItems':6,'items':HEALTH_SCHEMA})),
    issues={'type':'array','maxItems':len(ISSUES),'uniqueItems':True,'items':enum(ISSUES)},
))}


def empty_health():
    return dict(samples=0,reported_drop_highwater=None,drop_increases_seen=dict.fromkeys(PHASES,0),
                callback_errors_highwater=None,output_depth_peak=None,focus_depth_peak=None,
                last_sample_age_ms=None,final_health_confirmed=False)


class NativeHealthObservation:
    """Only cached numeric health samples. Python phase observed != native cause."""
    def __init__(self):self.data=empty_health();self._marker=None

    def observe(self,stream):
        with getattr(stream,'lock',nullcontext()):
            marker=getattr(stream,'last_health_received',None)
            if marker is None:return
            age=max(0,int((stream.monotonic()-marker)*1000))
            self.data['last_sample_age_ms']=min(age,INTEGER['maximum'])
            if marker==self._marker:return
            self._marker=marker;self.data['samples']+=1
            drop=stream.native_dropped
            if type(drop) is int and 0<=drop<=INTEGER['maximum']:
                delta=max(0,drop-(self.data['reported_drop_highwater'] or 0))
                phase='stopped' if stream.stopped else stream.health if stream.health in PHASES else 'unknown'
                self.data['drop_increases_seen'][phase]+=delta
                self.data['reported_drop_highwater']=max(drop,self.data['reported_drop_highwater'] or 0)
            callbacks=getattr(stream,'native_callbacks',{})
            queues=getattr(stream,'native_queues',None) or {}
            for target,value in (('callback_errors_highwater',callbacks.get('errors')),
                                 ('output_depth_peak',queues.get('output_depth')),
                                 ('focus_depth_peak',queues.get('focus_depth'))):
                if type(value) is int and 0<=value<=INTEGER['maximum']:
                    self.data[target]=max(self.data[target] or 0,value)

    def snapshot(self):return deepcopy(self.data)


def build_review(report,*,test_summary=None,native_health=None):
    report=finalize_report(report)
    auto=report['automated_tests'];sessions=report['sessions'];issues=[]
    known=auto['discovered'] is not None and auto['skipped'] is not None
    executed=auto['discovered']-auto['skipped'] if known else None
    categories=dict.fromkeys(CATEGORIES,0);provenance='unavailable'
    if test_summary is not None:
        # Revalidate closed packet/counts; no free text/test identifiers pass through.
        packet=read_summary(MARKER+json.dumps(test_summary),auto)
        if packet is None:raise ReportError('test_diagnostics_rejected')
        categories=packet['skip_categories'];provenance='structured_runner'
    else:categories['unclassified']=auto['skipped'] or 0
    checks=[x['status'] for x in report['manual_checks'].values()]
    started=[s for s in sessions if s['capture_started']]
    dropped=sum(s['counters']['native_dropped'] for s in sessions)
    trial=operator_trial_recorded(report)
    if any(s!='PASSOU' for s in report['checks'].values()):issues.append('preparation_incomplete')
    if not trial:issues.append('operator_trial_not_recorded')
    if 'NAO_EXECUTADO' in checks:issues.append('manual_checks_incomplete')
    if 'FALHOU' in checks:issues.append('manual_checks_failed')
    if dropped:issues.extend(('native_drop_requires_review','native_drop_cause_unknown'))
    issues.append('native_health_sampling_not_final')
    if not known:issues.append('test_counts_unknown')
    if auto['status']!='PASSOU' or not executed:issues.append('test_failures_or_no_executed_success')
    if auto['skipped']:
        issues.append('skips_require_review')
        if provenance=='unavailable' or categories['unclassified']:issues.append('skip_details_unavailable')
    if not report['source']['commit']:issues.append('commit_unavailable')
    if report['source']['modified'] is None:issues.append('source_state_unknown')
    if report['source']['modified']:issues.append('source_modified')
    if any(s['children_stopped'] is not True for s in started):issues.append('cleanup_unconfirmed')
    if not any(s['termination']=='expired' for s in started):issues.append('expiry_not_observed')
    issues.extend(('cross_os_trial_required','independent_review_pending','pilot_not_authorized'))
    health=[empty_health() for _ in sessions] if native_health is None else deepcopy(native_health)
    if type(health) is not list or len(health)!=len(sessions):raise ReportError('health_diagnostics_rejected')
    value=dict(schema_version=1,kind='synthetic_acceptance_review',
        report_sha256=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest(),
        pilot_authorized=False,review_status='PENDENTE_REVISAO_HUMANA',
        os_family=report['environment']['os_family'],declared_operator_trial=bool(trial),
        source=dict(commit_available=report['source']['commit'] is not None,
                    state='unknown' if report['source']['modified'] is None else 'modified' if report['source']['modified'] else 'clean'),
        tests=dict(status=auto['status'],discovered=auto['discovered'],executed=executed,skipped=auto['skipped'],
                   skip_categories=categories,category_provenance=provenance),
        sessions=dict(count=len(sessions),started=len(started),expired=sum(s['termination']=='expired' for s in started),
                      cleanup_confirmed=sum(s['children_stopped'] is True for s in started),
                      cleanup_unconfirmed=sum(s['children_stopped'] is not True for s in started),
                      persistence_enabled=sum(s['persistence_enabled'] for s in started),
                      persistence_with_writes=sum(s['persistence_enabled'] and s['counters']['queue_written']>0 for s in started)),
        human_checks=dict(passed=checks.count('PASSOU'),failed=checks.count('FALHOU'),not_executed=checks.count('NAO_EXECUTADO')),
        native=dict(reported_dropped=dropped,sessions_with_drops=sum(s['counters']['native_dropped']>0 for s in sessions),
                    attribution='unknown_from_aggregate',loss_rate=None,health_samples=health),issues=issues)
    _validate(value,REVIEW_SCHEMA)
    return value


def write_review(report,repository,destination,**details):
    value=build_review(report,**details)
    directory=safe_output_directory(repository,destination);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/('diagnostico-'+report['report_id']+'.json')
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,allow_nan=False,indent=2);stream.write('\n')
    return path
