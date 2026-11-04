"""Bounded, synthetic-only task candidates. Temporal recurrence is not causality."""
from collections import defaultdict
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from .events import Event

APPS = {'synthetic-web':'browser','synthetic-files':'files','synthetic-app':'desktop',
        'Chrome':'browser','Explorer':'files','SistemaDemo':'desktop'}
ACTIONS = frozenset(('open','click','save','review','download','rename','move','register','invoke','toggle',
                     'open_menu','select_menu','select_tab','submit','navigate','transition'))


@dataclass(frozen=True)
class Occurrence:
    segment: int
    start: int
    end: int
    duration: float


def _stamp(event):
    return datetime.fromisoformat(event.timestamp_utc.replace('Z','+00:00')).timestamp()


def _steps(fingerprint):
    return [dict(app_category=app,event_type=kind,action=action,role=role) for app,kind,action,role in fingerprint]


def _disjoint(occurrences):
    # Interval scheduling maximizes independent occurrences within this family.
    # Different candidate families are alternatives, not additive execution totals.
    selected=[]
    for segment in sorted({o.segment for o in occurrences}):
        end=-1
        for occurrence in sorted(set(o for o in occurrences if o.segment==segment),key=lambda o:(o.end,-(o.end-o.start),o.start)):
            if occurrence.start>=end:
                selected.append(occurrence)
                end=occurrence.end
    return selected


def _distance_one(left,right):
    if left==right:return 0
    if abs(len(left)-len(right))>1:return 2
    if len(left)==len(right):return sum(a!=b for a,b in zip(left,right))
    if len(left)>len(right):left,right=right,left
    for index in range(len(right)):
        if right[:index]+right[index+1:]==left:return 1
    return 2


def discover_tasks(events, *, min_count=2, max_steps=8, max_gap_seconds=30,
                   assumed_automation_seconds=None, top=20):
    if (type(min_count) is not int or min_count<2 or type(max_steps) is not int or not 2<=max_steps<=8
            or type(top) is not int or not 1<=top<=20 or type(max_gap_seconds) not in (int,float)
            or not math.isfinite(max_gap_seconds) or not 0<max_gap_seconds<=300):
        raise ValueError('discovery_limits_rejected')
    if assumed_automation_seconds is not None and (type(assumed_automation_seconds) not in (int,float)
            or not math.isfinite(assumed_automation_seconds) or not 0<=assumed_automation_seconds<=3600):
        raise ValueError('discovery_scenario_rejected')
    groups=defaultdict(list)
    seen={}
    duplicate=skipped=count=0
    for index,event in enumerate(events):
        count+=1
        if count>10000:raise ValueError('discovery_input_limit')
        try:
            event.validate()
        except (ValueError,TypeError,AttributeError,OverflowError):
            raise ValueError('discovery_event_rejected') from None
        if event.duration_ms>60000:raise ValueError('discovery_duration_rejected')
        if event.event_id in seen:
            if seen[event.event_id] != event:raise ValueError('discovery_conflicting_identity')
            duplicate+=1
            continue
        seen[event.event_id]=event
        if (event.metadata.get('category') not in ('synthetic','laboratory','demo') or event.app not in APPS
                or event.device_id not in ('laboratorio-sintetico','demo-device-01')):
            raise ValueError('discovery_synthetic_source_required')
        if event.event_type not in ('ui_action','file_action','browser_action') or event.action not in ACTIONS:
            skipped+=1
            continue
        role=event.metadata.get('control_role','control')
        signature=(APPS[event.app],event.event_type,event.action,role)
        groups[(event.device_id,event.session_id)].append((event,index,signature))
    segments=[]
    for group in groups.values():
        group.sort(key=lambda item:(_stamp(item[0]),item[0].metadata.get('source_sequence',0),item[1]))
        current=[]
        for item in group:
            if current and (_stamp(item[0])-_stamp(current[-1][0])>max_gap_seconds or len(current)>=64):
                segments.append(current);current=[]
            current.append(item)
        if current:segments.append(current)
    candidates=defaultdict(list)
    for number,segment in enumerate(segments):
        for start in range(len(segment)):
            for length in range(2,min(max_steps,len(segment)-start)+1):
                part=segment[start:start+length]
                fp=tuple(item[2] for item in part)
                duration=max(0,_stamp(part[-1][0])-_stamp(part[0][0]))+part[-1][0].duration_ms/1000
                candidates[fp].append(Occurrence(number,start,start+length,duration))
                if len(candidates)>50000:raise ValueError('discovery_candidate_limit')
    exact={fp:_disjoint(occurrences) for fp,occurrences in candidates.items()}
    ordered=sorted(exact,key=lambda fp:(-len(exact[fp])*len(fp),-len(fp),fp))
    limited=len(ordered)>200
    ordered=ordered[:200]
    # Suppress closed subpatterns only when ALL their occurrences are covered by
    # one longer recurrent exact pattern. Do not hide partial/uncovered routines.
    closed=[]
    coverage={}
    for fp in ordered:
        indexed=defaultdict(list)
        for occurrence in exact[fp]:indexed[occurrence.segment].append((occurrence.start,occurrence.end))
        coverage[fp]={key:sorted(intervals) for key,intervals in indexed.items()}
    def covered(occurrence,parent):
        intervals=coverage[parent].get(occurrence.segment,[])
        index=bisect_right(intervals,(occurrence.start,float('inf')))-1
        return index>=0 and intervals[index][1]>=occurrence.end
    for fp in ordered:
        redundant=False
        for parent in ordered:
            if len(parent)<=len(fp) or len(exact[parent])<min_count:continue
            if not any(parent[i:i+len(fp)]==fp for i in range(len(parent)-len(fp)+1)):continue
            if all(covered(o,parent) for o in exact[fp]):
                redundant=True;break
        if not redundant:closed.append(fp)
    families=[]
    consumed=set()
    for canonical in closed:
        if canonical in consumed:continue
        variants=[canonical]
        for other in closed:
            if (other in consumed or other==canonical or canonical[0]!=other[0] or canonical[-1]!=other[-1]):continue
            if _distance_one(canonical,other)<=1 and 1-1/max(len(canonical),len(other))>=.7:variants.append(other)
        occurrences=_disjoint([o for variant in variants for o in exact[variant]])
        if len(occurrences)<min_count:continue
        consumed.update(variants)
        durations=[o.duration for o in occurrences]
        distinct_segments=len({o.segment for o in occurrences})
        source_sessions=len({(segments[o.segment][0][0].device_id,segments[o.segment][0][0].session_id) for o in occurrences})
        coarse=any(step[2] in ('invoke','click','toggle') for variant in variants for step in variant)
        confidence='low' if coarse or source_sessions<2 else 'moderate' if source_sessions<3 or len(occurrences)<4 else 'high'
        repeated=returns=0
        for occurrence in occurrences:
            signatures=[item[2] for item in segments[occurrence.segment][occurrence.start:occurrence.end]]
            repeated+=sum(a==b for a,b in zip(signatures,signatures[1:]))
            returns+=sum(signatures[i]==signatures[i+2] and signatures[i]!=signatures[i+1] for i in range(len(signatures)-2))
        gaps=['human_review_required','temporal_not_causal','duration_not_work_time','boundaries_are_heuristic']
        if coarse:gaps.append('coarse_control_semantics')
        scenario=None if assumed_automation_seconds is None else {
            'assumed_automation_seconds':assumed_automation_seconds,
            'potential_seconds':round(sum(max(0,d-assumed_automation_seconds) for d in durations),3),
            'scenario_only':True,'feasibility_validated':False}
        families.append(dict(candidate_id=hashlib.sha256(repr(canonical).encode()).hexdigest()[:16],steps=_steps(canonical),
            variants=[_steps(fp) for fp in sorted(variants)],occurrences=len(occurrences),sessions=source_sessions,segments=distinct_segments,
            median_observed_span_seconds=round(median(durations),3),total_observed_span_seconds=round(sum(durations),3),
            confidence_heuristic=confidence,rework_signals={'adjacent_repetitions':repeated,'returns':returns,'interpretation':'requires_review'},
            saving_scenario=scenario,gaps=gaps))
    families.sort(key=lambda family:(-family['occurrences']*len(family['steps']),-family['total_observed_span_seconds'],family['candidate_id']))
    return dict(schema_version=1,kind='synthetic_task_candidates',capture_real=False,pilot_authorized=False,
                input_events=count,eligible_events=sum(map(len,segments)),duplicates_removed=duplicate,skipped_events=skipped,
                sessions=len(groups),segments=len(segments),candidates=families[:top],
                gaps=['human_review_required','candidate_families_are_not_additive']+(['candidate_review_limited'] if limited else []))


def synthetic_office_corpus(repetitions=8):
    """Fictional document workflow; no filenames, clients or case information."""
    from datetime import timedelta,timezone
    from uuid import uuid5,NAMESPACE_URL
    if type(repetitions) is not int or not 1<=repetitions<=100:raise ValueError('corpus_limit')
    events=[]
    start=datetime(2026,11,3,12,tzinfo=timezone.utc)
    for session in range(repetitions):
        operations=['download','rename','move','register']
        if session%4==1:operations.insert(3,'review')
        if session%4==2:operations.insert(2,'rename')
        for index,operation in enumerate(operations):
            app='synthetic-web' if operation in ('download','register','review') else 'synthetic-files'
            events.append(Event(1,str(uuid5(NAMESPACE_URL,f'synthetic-office-{session}-{index}')),
                (start+timedelta(minutes=session,seconds=index*.4)).isoformat(),'laboratorio-sintetico',
                str(uuid5(NAMESPACE_URL,f'synthetic-office-session-{session}')),app,
                'browser_action' if app=='synthetic-web' else 'file_action',operation,
                f'control-{session:016x}',duration_ms=50,
                metadata={'category':'synthetic','control_role':'control','source_sequence':index+1}))
    return events


def main():
    import argparse
    from .acceptance_report import safe_output_directory
    parser=argparse.ArgumentParser(description='Descoberta somente em corpus fictício; sem captura.')
    parser.add_argument('--out',required=True)
    parser.add_argument('--scenario-automation-seconds',type=float)
    args=parser.parse_args()
    report=discover_tasks(synthetic_office_corpus(),assumed_automation_seconds=args.scenario_automation_seconds)
    path=Path(args.out).absolute()
    safe_output_directory(Path(__file__).resolve().parents[2],path.parent).mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({'candidates':len(report['candidates']),'capture_real':False,'pilot_authorized':False}))


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError):
        raise SystemExit('Relatório não criado: confirme parâmetros e destino novo fora de Git. Nenhum detalhe bruto foi salvo.') from None
