"""Closed report schema: identifiers, paths, UI contents and free notes cannot pass."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from uuid import uuid4

STATUSES = ('PASSOU', 'FALHOU', 'NAO_EXECUTADO')
OBSERVATIONS = ('NAO_AVALIADO', 'SEM_ANOMALIA', 'LENTIDAO_PERCEBIDA', 'TRAVAMENTO',
                'CONTADOR_INESPERADO', 'SENHA_NAO_EXCLUIDA', 'RETOMADA_FALHOU',
                'PROCESSO_PERMANECEU', 'DEPENDENCIA_AUSENTE', 'OUTRO_REQUER_REVISAO')
MANUAL_STEPS = {
    'interface': 'Interface visível e responsiva',
    'inicio_fim': 'Início explícito e fim visível',
    'acoes_rapidas': 'Alternar os dois botões fictícios rapidamente',
    'segunda_instancia': 'Segunda instância não aumenta o contador',
    'pausa_retomada': 'Pausar, interagir, retomar sem replay de pendências',
    'senha': 'Campo de senha fictícia excluído',
    'limpeza_filhos': 'Fechar fixture/controlador encerra os filhos próprios',
    'latencia': 'Percepção humana de latência',
    'expiracao': 'Esperar o fim automático de 15 minutos',
    'persistencia': 'Gravação local opcional e contadores',
}
ROLES = ('controller', 'fixture', 'provider', 'fixture_secondary')
COUNTERS = ('events_accepted', 'invoke', 'focus', 'toggle', 'native_dropped',
            'python_dropped', 'sequence_gaps', 'invalid_messages', 'queue_written',
            'queue_discarded', 'queue_purged')
GAPS = ('manual_review_required', 'windows10_trial_required', 'windows11_trial_required',
        'sampling_not_continuous', 'os_peak_covers_process_lifetime', 'metrics_unavailable',
        'commit_unavailable', 'source_modified', 'preparation_incomplete',
        'automatic_tests_not_passed', 'unsupported_os', 'network_absence_not_instrumented',
        'pilot_not_authorized')


def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def enum(values):
    return {'type': 'string', 'enum': list(values)}


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


NUMBER = {'type': 'number', 'minimum': 0, 'maximum': 1e12}
INTEGER = {'type': 'integer', 'minimum': 0, 'maximum': 2**63 - 1}
VERSION = {'type': 'string', 'pattern': r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,5}$'}
HASH = {'type': 'string', 'pattern': r'^[a-f0-9]{64}$'}
PROCESS_METRIC = obj({
    'availability': enum(('not_sampled', 'sampled', 'unavailable')),
    'samples': INTEGER, 'cpu_single_core_sample_peak_percent': nullable(NUMBER),
    'ram_working_set_sample_peak_bytes': nullable(INTEGER),
    'ram_working_set_process_lifetime_peak_bytes': nullable(INTEGER),
})
SESSION = obj({
    'capture_started': {'type': 'boolean'}, 'persistence_enabled': {'type': 'boolean'},
    'termination': enum(('not_started', 'operator_stop', 'window_close', 'fixture_exit',
                         'expired', 'backend_error')),
    'children_stopped': nullable({'type': 'boolean'}),
    'counters': obj({key: INTEGER for key in COUNTERS}),
    'metrics': obj({
        'sample_interval_ms': {'const': 500},
        'fixture_launch_call_ms': nullable(NUMBER),
        'start_to_active_ack_ms': nullable(NUMBER),
        'pause_ack_samples': INTEGER, 'pause_ack_peak_ms': nullable(NUMBER),
        'pause_unconfirmed': INTEGER,
        'processes': obj({role: PROCESS_METRIC for role in ROLES}),
    }),
})
REPORT_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    **obj({
        'schema_version': {'const': 1}, 'kind': {'const': 'synthetic_lab_acceptance'},
        'report_id': {'type': 'string', 'pattern': r'^[a-f0-9]{32}$'},
        'created_utc': {'type': 'string', 'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'},
        'origin': enum(('operator_guided', 'automated_test')),
        'pilot_authorized': {'const': False},
        'human_gate': {'const': 'PENDENTE_REVISAO_HUMANA'},
        'environment': obj({
            'os_family': enum(('windows10', 'windows11', 'windows_server', 'unsupported')),
            'os_edition': enum(('Home', 'HomeSingleLanguage', 'Pro', 'Enterprise',
                                'EnterpriseLTSC', 'Education', 'Server', 'unknown')),
            'os_build': nullable(INTEGER), 'python': VERSION,
            'tk': nullable({'type': 'string', 'pattern': r'^[0-9]{1,3}\.[0-9]{1,3}(?:\.[0-9]{1,5})?$'}),
            'dotnet_sdk': nullable(VERSION),
        }),
        'source': obj({'commit': nullable({'type': 'string', 'pattern': r'^[a-f0-9]{40}$'}),
                       'modified': nullable({'type': 'boolean'})}),
        'artifacts': obj({role: obj({key: nullable(HASH) for key in
                          ('exe_sha256', 'assembly_sha256', 'deps_sha256', 'runtimeconfig_sha256')})
                          for role in ('fixture', 'provider')}),
        'checks': obj({key: enum(STATUSES) for key in
                      ('python', 'tk', 'dotnet_sdk', 'offline_build', 'artifact_hashes')}),
        'automated_tests': obj({'status': enum(STATUSES), 'discovered': nullable(INTEGER),
                              'skipped': nullable(INTEGER), 'failures': nullable(INTEGER),
                              'errors': nullable(INTEGER)}),
        'manual_checks': obj({key: obj({'status': enum(STATUSES), 'observation': enum(OBSERVATIONS)})
                              for key in MANUAL_STEPS}),
        'sessions': {'type': 'array', 'maxItems': 6, 'items': SESSION},
        'gaps': {'type': 'array', 'maxItems': len(GAPS), 'uniqueItems': True, 'items': enum(GAPS)},
    }),
}


class ReportError(ValueError):
    """Static messages only: never echo a rejected value."""


def _validate(value, schema):
    if 'anyOf' in schema:
        for choice in schema['anyOf']:
            try:
                _validate(value, choice)
                return
            except ReportError:
                pass
        raise ReportError('report_value_rejected')
    if 'const' in schema:
        if type(value) is not type(schema['const']) or value != schema['const']:
            raise ReportError('report_constant_rejected')
        return
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'boolean': bool,
             'integer': int, 'null': type(None)}
    if kind == 'number':
        if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
            raise ReportError('report_number_rejected')
    elif type(value) is not types[kind]:
        raise ReportError('report_type_rejected')
    if kind == 'object':
        if set(value) != set(schema['properties']):
            raise ReportError('report_fields_rejected')
        for key, child in schema['properties'].items():
            _validate(value[key], child)
    elif kind == 'array':
        if len(value) > schema['maxItems']:
            raise ReportError('report_size_rejected')
        for item in value:
            _validate(item, schema['items'])
        if schema.get('uniqueItems') and len(value) != len(set(value)):
            raise ReportError('report_duplicates_rejected')
    elif kind == 'string':
        if ('enum' in schema and value not in schema['enum']) or ('pattern' in schema and not re.fullmatch(schema['pattern'], value)):
            raise ReportError('report_text_rejected')
    elif kind in ('number', 'integer'):
        if value < schema['minimum'] or value > schema['maximum']:
            raise ReportError('report_range_rejected')


def validate_report(report):
    _validate(report, REPORT_SCHEMA)
    try:
        datetime.strptime(report['created_utc'], '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise ReportError('report_date_rejected') from None
    for key in ('tk', 'dotnet_sdk'):
        if report['checks'][key] == 'PASSOU' and report['environment'][key] is None:
            raise ReportError('unproven_dependency_rejected')
    if report['checks']['artifact_hashes'] == 'PASSOU' and any(
            value is None for artifact in report['artifacts'].values() for value in artifact.values()):
        raise ReportError('unproven_hashes_rejected')
    for check in report['manual_checks'].values():
        if check['status'] == 'NAO_EXECUTADO' and check['observation'] != 'NAO_AVALIADO':
            raise ReportError('unexecuted_observation_rejected')
    auto = report['automated_tests']
    if auto['status'] == 'PASSOU' and (not auto['discovered'] or auto['failures'] != 0 or auto['errors'] != 0):
        raise ReportError('unproven_tests_rejected')
    if auto['discovered'] is not None and auto['skipped'] is not None and auto['skipped']>auto['discovered']:
        raise ReportError('inconsistent_tests_rejected')
    if auto['status']=='PASSOU' and (auto['skipped'] is None or auto['skipped']>=auto['discovered']):
        raise ReportError('unexecuted_tests_rejected')
    for session in report['sessions']:
        if not session['capture_started'] and session['counters']['events_accepted']:
            raise ReportError('unstarted_capture_rejected')
        for metric in session['metrics']['processes'].values():
            if metric['availability'] == 'sampled' and (not metric['samples'] or metric['ram_working_set_sample_peak_bytes'] is None):
                raise ReportError('unproven_measurement_rejected')
    return report


def empty_session():
    return {'capture_started': False, 'persistence_enabled': False,
            'termination': 'not_started', 'children_stopped': None,
            'counters': dict.fromkeys(COUNTERS, 0),
            'metrics': {'sample_interval_ms': 500, 'fixture_launch_call_ms': None,
                        'start_to_active_ack_ms': None, 'pause_ack_samples': 0,
                        'pause_ack_peak_ms': None, 'pause_unconfirmed': 0,
                        'processes': {role: {'availability': 'not_sampled', 'samples': 0,
                          'cpu_single_core_sample_peak_percent': None,
                          'ram_working_set_sample_peak_bytes': None,
                          'ram_working_set_process_lifetime_peak_bytes': None} for role in ROLES}}}


def new_report(origin='operator_guided'):
    import sys
    report = {'schema_version': 1, 'kind': 'synthetic_lab_acceptance',
              'report_id': uuid4().hex, 'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
              'origin': origin, 'pilot_authorized': False, 'human_gate': 'PENDENTE_REVISAO_HUMANA',
              'environment': {'os_family': 'unsupported', 'os_edition': 'unknown', 'os_build': None,
                              'python': '.'.join(map(str, sys.version_info[:3])), 'tk': None, 'dotnet_sdk': None},
              'source': {'commit': None, 'modified': None},
              'artifacts': {role: dict.fromkeys(('exe_sha256', 'assembly_sha256', 'deps_sha256', 'runtimeconfig_sha256'))
                            for role in ('fixture', 'provider')},
              'checks': dict.fromkeys(('python', 'tk', 'dotnet_sdk', 'offline_build', 'artifact_hashes'), 'NAO_EXECUTADO'),
              'automated_tests': {'status': 'NAO_EXECUTADO', 'discovered': None, 'skipped': None, 'failures': None, 'errors': None},
              'manual_checks': {key: {'status': 'NAO_EXECUTADO', 'observation': 'NAO_AVALIADO'} for key in MANUAL_STEPS},
              'sessions': [], 'gaps': []}
    return report


def operator_trial_recorded(report):
    """A declared trial on THIS OS, never approval or cross-version evidence.

    Environment alone, CI and checked boxes without started sessions are insufficient.
    Failed/incomplete manual results still block acceptance through their own fields.
    """
    return (report['origin']=='operator_guided'
            and report['environment']['os_family'] in ('windows10','windows11')
            and any(s['capture_started'] for s in report['sessions'])
            and any(c['status']!='NAO_EXECUTADO' for c in report['manual_checks'].values()))


def finalize_report(report):
    result = deepcopy(report)
    validate_report(result)
    gaps = ['manual_review_required',
            'sampling_not_continuous', 'os_peak_covers_process_lifetime',
            'network_absence_not_instrumented', 'pilot_not_authorized']
    for os in ('windows10','windows11'):
        if result['environment']['os_family']!=os or not operator_trial_recorded(result):
            gaps.append(os+'_trial_required')
    if not result['source']['commit']:
        gaps.append('commit_unavailable')
    if result['source']['modified']:
        gaps.append('source_modified')
    if any(status != 'PASSOU' for status in result['checks'].values()):
        gaps.append('preparation_incomplete')
    if result['automated_tests']['status'] != 'PASSOU':
        gaps.append('automatic_tests_not_passed')
    if result['environment']['os_family'] not in ('windows10', 'windows11'):
        gaps.append('unsupported_os')
    if any(m['availability'] == 'unavailable' for s in result['sessions'] for m in s['metrics']['processes'].values()):
        gaps.append('metrics_unavailable')
    result['gaps'] = gaps
    return validate_report(result)


def safe_output_directory(repository, destination):
    root, output = Path(repository).resolve(), Path(destination).resolve()
    if output == root or root in output.parents:
        raise ReportError('output_inside_repository')
    for parent in (output, *output.parents):
        if (parent / '.git').exists():
            raise ReportError('output_inside_version_control')
    return output


def write_report(report, repository, destination):
    report = finalize_report(report)
    output = safe_output_directory(repository, destination)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = output / ('aceite-' + report['report_id'] + '.json')
    # Exclusive create: never overwrite a prior operator record or follow a file symlink.
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
    return path
