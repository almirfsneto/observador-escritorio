"""Closed skip categories for the LOCAL validator; no test IDs/reasons in reports."""
import json
import sys
import unittest

MARKER='OBS_ACCEPTANCE_TEST_SUMMARY_V1 '
CATEGORIES=('foreground_desktop_unavailable','windows_platform_required','browser_dedicated',
            'symlink_privilege_unavailable','unclassified')
FOREGROUND_REASONS={
    'Hosted foreground unavailable; manual Windows 10/11 trial still required',
    'Hosted foreground desktop unavailable; manual controller validation required',
    'Hosted runner has no usable foreground desktop; manual Windows validation required',
    'Hosted runner has no usable foreground desktop; manual validation required',
    'Foreground unavailable; no comparative desktop coverage proved',
}
PLATFORM_REASONS={
    'Windows acceptance integration requires Windows','Native lifecycle requires Windows',
    'Windows controller smoke requires Windows','Windows desktop automation requires Windows',
    'Native comparative coverage requires Windows desktop','Windows kernel owned-child probe required',
    'Windows native DACL/DPAPI requires Windows','Requires real Windows kernel process/handle execution',
}
MODULES=('test_acceptance_windows.','test_native_windows.','test_windows_controller.',
         'test_windows_desktop.','test_windows_coverage.','test_source_auth_model.',
         'test_storage_hardening.','test_owned_channel.','test_handle_lifetime.')


def summarize(result,platform=sys.platform):
    categories=dict.fromkeys(CATEGORIES,0)
    for test,reason in result.skipped:
        identity=test.id().removeprefix('tests.')
        if identity.startswith('test_browser_extension.') and reason=='Real browser test enabled in dedicated web CI job':
            category='browser_dedicated'
        elif identity.startswith(MODULES) and platform!='win32' and reason in PLATFORM_REASONS:
            category='windows_platform_required'
        elif identity.startswith(MODULES) and platform=='win32' and reason in FOREGROUND_REASONS:
            category='foreground_desktop_unavailable'
        elif identity.startswith('test_storage_hardening.') and reason=='Windows denied optional symlink creation privilege; no policy/privilege changed':
            category='symlink_privilege_unavailable'
        else:category='unclassified'
        categories[category]+=1
    return dict(schema_version=1,kind='synthetic_acceptance_test_summary',discovered=result.testsRun,
                executed=result.testsRun-len(result.skipped),skipped=len(result.skipped),
                failures=len(result.failures),errors=len(result.errors),skip_categories=categories)


def read_summary(output,automatic):
    """Bounded strict parse; missing legacy output never invents a skip reason."""
    def pairs(items):
        value={}
        for k,v in items:
            if k in value:raise ValueError()
            value[k]=v
        return value
    lines=[line[len(MARKER):] for line in output.splitlines() if line.startswith(MARKER)]
    try:
        if len(lines)!=1 or len(lines[0])>2048:return None
        value=json.loads(lines[0],object_pairs_hook=pairs)
        expected={'schema_version','kind','discovered','executed','skipped','failures','errors','skip_categories'}
        if type(value) is not dict or set(value)!=expected:return None
        if type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='synthetic_acceptance_test_summary':return None
        if type(value['skip_categories']) is not dict or set(value['skip_categories'])!=set(CATEGORIES):return None
        numbers=[value[k] for k in ('discovered','executed','skipped','failures','errors')]+list(value['skip_categories'].values())
        if any(type(n) is not int or not 0<=n<=2**63-1 for n in numbers):return None
        if value['executed']+value['skipped']!=value['discovered'] or sum(value['skip_categories'].values())!=value['skipped']:return None
        if any(value[k]!=automatic[k] for k in ('discovered','skipped','failures','errors')):return None
        return value
    except (ValueError,TypeError,KeyError,RecursionError):return None


def main():
    suite=unittest.defaultTestLoader.discover('tests')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(MARKER+json.dumps(summarize(result),sort_keys=True),flush=True)
    return int(not result.wasSuccessful() or result.testsRun==len(result.skipped))
