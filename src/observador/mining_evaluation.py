"""Small labelled synthetic benchmark; pair metrics are not real-world accuracy."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from itertools import combinations
from uuid import uuid5,NAMESPACE_URL

from .task_discovery import discover_tasks
from .events import Event

SPECS=(('filing',('download','rename','move','register')),
       ('filing',('download','rename','move','review','register')),
       ('filing',('download','rename','rename','move','register')),
       ('review_routing',('download','review','move','register')),
       ('interrupted',('download','rename','register')))


def labelled_corpus():
    events=[];labels=[];signatures=[]
    for index,(label,operations) in enumerate(spec for spec in SPECS for _ in range(2)):
        labels.append(label)
        signatures.append(tuple(('browser','browser_action',action,'control') for action in operations))
        for sequence,action in enumerate(operations,1):
            events.append(Event(1,str(uuid5(NAMESPACE_URL,f'labelled-event-{index}-{sequence}')),
                (datetime(2026,11,3,12,tzinfo=timezone.utc)+timedelta(minutes=index,seconds=sequence*.2)).isoformat(),
                'laboratorio-sintetico',str(uuid5(NAMESPACE_URL,f'labelled-session-{index}')),'synthetic-web',
                'browser_action',action,f'control-{index:016x}',metadata={'category':'synthetic','control_role':'control','source_sequence':sequence}))
    return events,labels,signatures


def evaluate_synthetic_mining():
    events,labels,signatures=labelled_corpus()
    result=discover_tasks(events)
    assignments={}
    for index,signature in enumerate(signatures):
        matches=[]
        for family in result['candidates']:
            for variant in family['variants']:
                fp=tuple((s['app_category'],s['event_type'],s['action'],s['role']) for s in variant)
                if fp==signature:matches.append(family['candidate_id'])
        # Ambiguous or absent full-trace coverage is not a correct predicted match.
        assignments[index]=matches[0] if len(set(matches))==1 else None
    tp=fp=fn=tn=0
    for left,right in combinations(range(len(labels)),2):
        truth=labels[left]==labels[right]
        predicted=assignments[left] is not None and assignments[left]==assignments[right]
        if truth and predicted:tp+=1
        elif not truth and predicted:fp+=1
        elif truth:fn+=1
        else:tn+=1
    return dict(schema_version=1,kind='synthetic_mining_evaluation',corpus='labelled_negative_v1',
        traces=len(labels),events=len(events),pairs=tp+fp+fn+tn,true_positive=tp,false_positive=fp,false_negative=fn,true_negative=tn,
        precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
        metric_scope='full_trace_pair_family_assignment',real_world_accuracy_claim=False,
        gaps=['small_handcrafted_corpus','labels_are_synthetic','no_causal_or_productivity_inference','human_review_required'])
