#!/usr/bin/env python3
"""Synthetic-only native checklist regression: fresh intents, exact source handoff.

No default real-demo inventory or real providers. Named legacy cases now test
the same catalog/default/rejection invariants using a private synthetic catalog.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


# Keep these transport/helper exports used by test-terminal-indicators.py.
consistency = load('checklist_consistency', HERE / 'test-launch-stage-consistency.py')
shared = load('checklist_fresh', HERE / 'fixtures/fresh_frontend.py')
c, real = consistency.composition, consistency.real
field, sexp, require, wait, save = shared.field, shared.sexp, shared.api.require, shared.wait, shared.api.save


def setup_workspace(http, run, presets):
    ws = c.demo.ensure_workspaces(http, http.rpc(domain='workspace'), presets)
    ws = c.demo.apply_workspace_presets(http, ws, presets)
    overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
    context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
    http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision'), sexp(run)))


def zoom(http, kind):
    ws = http.rpc(domain='workspace')
    overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
    tile = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == field(overview, 'id') and field(t, 'kind') == kind)
    http.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' % (sexp(field(overview, 'id')), sexp(field(tile, 'id'))))


def preference(base, selection, inherited=False):
    environment = 'Inherit_daemon' if inherited else '(Opam_switch ' + c.demo.switch_name() + ')'
    key = '(' + str(base / 'project') + ' ' + environment + ')' if inherited else '(' + str(base / 'project') + environment + ')'
    directory = base / 'client-state/hardcaml-workbench/terminal'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('launch-' + hashlib.sha256(key.encode()).hexdigest() + '.sexp')
    path.write_text(sexp([['schema_version', '1'], ['project_key', key], ['selection', selection]]))
    save(base / 'remembered-selection.json', dict(project_key=key, path=str(path), selection=selection))


def selected(f):
    f.terminal.drain(.05)
    ws = f.http.rpc(domain='workspace')
    overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
    context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
    return field(context, 'selected_run')


def clear_context(f):
    ws = f.http.rpc(domain='workspace')
    overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
    context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
    f.http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run ()))' %
                  (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision')))


def position(f, index):
    zoom(f.http, 'stage-checklist')
    f.terminal.capture('focused-' + str(index), ['stage checklist', 'Overview | run'])
    f.terminal.key(b'k' * 15)
    f.terminal.key(b'j' * index)


def withdraw(f, endpoint):
    path = f.base / 'results/synthetic-reference/observation.json'
    payload = json.loads(path.read_text())
    for stage in payload['stage_plan']['stages']:
        if stage['id'] == endpoint:
            stage.pop('action', None)
    path.write_text(json.dumps(payload))
    run = next(r for r in field(f.snapshot(), 'runs') if field(field(r, 'reference'), 'stream_id') == 'synthetic-reference')
    f.http.rpc('(Observe %s)' % sexp(field(run, 'run')), wait=False)
    wait(lambda: not field(next(s for r in field(f.snapshot(), 'runs') if field(r, 'run') == field(run, 'run')
                               for s in field(r, 'stages') if field(s, 'id') == endpoint), 'action'), 'withdraw action')


def catalog_config(mode):
    def configure(f):
        path = f.base / 'results/synthetic-reference/observation.json'
        payload = json.loads(path.read_text())
        for stage in payload['stage_plan']['stages']:
            stage.pop('action', None)
        path.write_text(json.dumps(payload))
        (f.root / 'catalog-mode').write_text(mode)
        if mode in ('remembered', 'stale-profile'):
            preference(f.base, [['flow', 'synthetic'], ['profile', 'obsolete-explicit' if mode == 'stale-profile' else 'failure'],
                                ['endpoint', 'synthesis'], ['assignments', ['X=remembered'] if mode == 'remembered' else []]], inherited=True)
    return configure


def catalog_case(args, mode, check):
    f = None
    try:
        f, _ = shared.setup(args, mode, check, configure=catalog_config(mode), cold=True)
        t = f.terminal
        cold = f.snapshot()
        check(not field(cold, 'flows') and not field(cold, 'preview') and not field(cold, 'fresh_intent'), mode + ': restarted catalog and input intent are cold')
        check(not field(field(cold, 'runs')[0], 'selection'), mode + ': registered history supplies no implicit launch selection')
        before = len(f.events('pinned-call'))
        t.open_palette('Launch planned run without view')
        t.capture('disabled-before-stage', ['Launch', 'No preview:'])
        t.key(b'\r'); t.key(b'\x1b')
        check(len(f.events('pinned-call')) == before and not field(f.snapshot(), 'workflows'), mode + ': passive palette and disabled Enter never discover or launch')
        position(f, 5)  # Elaboration, synthesis, floorplan, placement, CTS, routing.
        if mode == 'changed-context':
            f.mode('discovery', 'hold')
        t.key(b'r')
        if mode == 'changed-context':
            wait(lambda: f.events('discovery-held'), 'catalog discovery held')
            clear_context(f)
            t.capture('context-changed', ['Run: none selected'])
            (f.root / 'discovery-release').write_text('release')
            wait(lambda: field(f.snapshot(), 'flows'), 'late catalog reply')
            t.drain(1)
            t.open_palette('Launch planned run without view')
            t.capture('changed-context-launch-disabled', ['context changed'])
            t.key(b'\r'); t.key(b'\x1b')
            check(not field(f.snapshot(), 'fresh_intent') and not field(f.snapshot(), 'workflows'), 'Changed context fences discovery before input-intent staging or producer creation')
        elif mode in ('stale-profile', 'nonfresh', 'unsupported-endpoint'):
            wait(lambda: field(f.snapshot(), 'flows'), 'negative catalog discovery')
            t.drain(1)
            t.open_palette('Launch planned run without view')
            reason = 'Selected profile unavailable' if mode == 'stale-profile' else 'Unsupported fresh endpoint'
            t.capture('negative-launch-disabled', [reason])
            t.key(b'\r'); t.key(b'\x1b')
            check(not field(f.snapshot(), 'fresh_intent') and not field(f.snapshot(), 'workflows'), mode + ': invalid mapping cannot stage or submit a replacement')
        else:
            intent = wait(lambda: next(iter(field(f.snapshot(), 'fresh_intent')), None), 'routing input intent')
            selection = field(intent, 'selection')
            check(selection == [['flow', 'synthetic'], ['profile', 'failure' if mode == 'remembered' else 'success'],
                                ['endpoint', 'routing'], ['assignments', ['X=remembered'] if mode == 'remembered' else []]] and
                  not field(intent, 'expected_plan_identity'), mode + ': exact default/remembered input selection, no generated-plan pin')
            t.command('Unzoom workspace')
            zoom(f.http, 'planned-run')
            t.capture('ready-input-intent', ['ready:', 'endpoint: routing', 'Fresh launch:'])
            t.open_palette('Launch planned run without view')
            t.capture('ready-launch-not-pressed', ['Launch planned run without view'], ['No preview:', 'No matching commands'])
            t.key(b'\x1b')
            check(not field(f.snapshot(), 'workflows'), mode + ': explicit r only stages; enabled launch remains read-only until accepted')
        check(not f.events('emit-start') and not f.events('physical-admitted') and
              not any(e['argv'][:2] in (['flow', 'plan'], ['flow', 'run']) for e in f.events('pinned-call')),
              mode + ': catalog resolution never renders pinned plans, emits bundles or starts physical tools')
    finally:
        if f:
            shared.finish(f)


def quick_case(args, check, view=True, failure=False, changed=False, named=False):
    label = 'named-view' if named else 'quick-' + ('changed' if changed else 'failure' if failure else 'view' if view else 'no-view')
    f = None
    try:
        f, _ = shared.setup(args, label, check)
        t = f.terminal
        before = selected(f)
        if not view:
            t.command('Quick-launch behavior: keep current context')
            t.close()
            f.terminal = t = c.Terminal(f.base, f.client_args, f.url, 180, 55)
            t.capture('preference-client-restarted', ['stage checklist'])
            t.open_palette('Quick-launch behavior: keep current context')
            t.capture('preference-restarted', ['keep current context (selected)'])
            t.key(b'\x1b')
            check(True, 'No-view quick-launch preference survives a fresh native client')
        position(f, 3)
        if failure or changed:
            f.mode('emit', 'fail' if failure else 'hold')
        if named:
            t.open_palette('launch syn')
            t.capture('named-captured', ['> Launch synthesis and view'])
            withdraw(f, 'synthesis')
            t.drain(1)
            t.key(b'\r'); t.key(b'\x1b')
            check(not field(f.snapshot(), 'workflows') and not f.events('emit-start'), 'Stale named action rejects before source submission after capability withdrawal')
            # Re-observe the restored exact advertised action; no fabricated frontend state.
            path = f.base / 'results/synthetic-reference/observation.json'
            payload = json.loads(path.read_text())
            next(s for s in payload['stage_plan']['stages'] if s['id'] == 'synthesis')['action'] = dict(flow='synthetic', profile='success', endpoint='synthesis', assignments=[])
            path.write_text(json.dumps(payload))
            run = next(r for r in field(f.snapshot(), 'runs') if field(field(r, 'reference'), 'stream_id') == 'synthetic-reference')
            f.http.rpc('(Observe %s)' % sexp(field(run, 'run')), wait=False)
            wait(lambda: field(next(s for r in field(f.snapshot(), 'runs') if field(r, 'run') == field(run, 'run') for s in field(r, 'stages') if field(s, 'id') == 'synthesis'), 'action'), 'restored named action')
            t.drain(1)
            t.type_action('launch syn', 'Launch synthesis and view', 'named-selected-action')
        elif failure or changed:
            t.key(b'R')
        else:
            t.type_action('quick lau', 'Quick launch selected stage', 'selected-action')
        w = wait(lambda: next(iter(field(f.snapshot(), 'workflows')), None), 'one daemon-owned workflow')
        if changed:
            wait(lambda: f.events('emit-held'), 'source emission held')
            clear_context(f)
            t.capture('context-changed', ['Run: none selected'])
            (f.root / 'emit-release').write_text('release')
        w = f.done(field(w, 'key'), 'Failed' if failure else 'Completed')
        if failure:
            check(field(w, 'error') and not field(w, 'run') and not f.events('physical-admitted'), 'Preparation failure retains workflow diagnostic and blocks all downstream work')
            check(selected(f) == before, 'Preparation failure does not steal context')
        else:
            endpoint = 'synthesis' if named else 'placement'
            prepared = field(w, 'prepared')[0]
            admitted = f.events('physical-admitted')
            check(len(admitted) == 1 and admitted[0]['plan_identity'] == field(prepared, 'plan_identity') and
                  admitted[0]['stages'] == ['synthesis', 'floorplan', 'placement'][:1 if named else 3], label + ': one exact direct-provider physical prefix from its own emitted plan')
            expected = [] if changed else field(w, 'run') if view or named else before
            wait(lambda: selected(f) == expected, label + ' captured context policy')
            check(selected(f) == expected, label + ': completion respects captured follow/focus policy')
        check(len(field(f.snapshot(), 'workflows')) == 1 and len(f.events('emit-start')) == 1 and
              not any(e['argv'][:2] in (['flow', 'plan'], ['flow', 'run']) for e in f.events('pinned-call')),
              label + ': one source chain and zero pinned planning/flow-run bypasses')
        t.open_palette('Quick-launch behavior: ' + ('view launched run' if view else 'keep current context'))
        t.capture('preference-unchanged', [('view launched run' if view else 'keep current context') + ' (selected)'])
        t.key(b'\x1b')
    finally:
        if f:
            shared.finish(f)


def synthetic_case(args, check):
    """Manual r/launch, failed replacement and pending-response launch fences."""
    f = proxy = None
    try:
        f, _ = shared.setup(args, 'synthetic-manual', check)
        f.terminal.close()
        proxy = shared.StageReplyGate(f)
        proxy.release.set()
        f.terminal = t = c.Terminal(f.base, f.client_args, proxy.url, 180, 55)
        t.capture('manual-client', ['stage checklist'])
        position(f, 3)
        t.key(b'r')
        old = wait(lambda: next(iter(field(f.snapshot(), 'fresh_intent')), None), 'manual placement intent')
        check(field(field(old, 'selection'), 'endpoint') == 'placement' and not field(old, 'expected_plan_identity') and
              not field(f.snapshot(), 'workflows') and not f.events('emit-start'),
              'Manual r captures exact selected placement inputs with zero jobs/producers')
        # Failed replacement must invalidate the old still-unlaunched receipt.
        prep = f.root / 'hardcaml-workbench-preparation.sexp'
        original = prep.read_bytes()
        prep.unlink()
        t.key(b'j'); t.key(b'r')
        wait(lambda: not field(f.snapshot(), 'fresh_intent'), 'failed replacement clears old intent')
        t.drain(.5)
        t.open_palette('Launch planned run without view')
        screen = t.capture('failed-replacement-launch-disabled', ['Launch'])
        check('configured' in screen.text().lower() or 'staging failed' in screen.text().lower() or
              '[Fresh intent unavailable' in screen.text(),
              'Failed replacement gives a visible explicit unavailable/staging failure reason')
        t.key(b'\r'); t.key(b'\x1b')
        check(not field(f.snapshot(), 'workflows') and not f.events('emit-start'), 'Failed input replacement cannot launch an older ready intent')
        prep.write_bytes(original)
        # Hold the actual retry reply after backend staging, not a pinned render.
        proxy.entered.clear()
        proxy.release.clear()
        t.key(b'r')
        wait(proxy.entered.is_set, 'retry input intent response held')
        t.open_palette('Launch planned run without view')
        screen = t.capture('pending-replacement-launch-disabled', ['Launch'])
        check('Staging' in screen.text() or 'Preparing' in screen.text() or 'pending' in screen.text().lower(),
              'Pending replacement has an explicit staging/pending launch reason')
        t.key(b'\r'); t.key(b'\x1b')
        check(not field(f.snapshot(), 'workflows') and not f.events('emit-start'), 'Pending replacement cannot submit its older receipt or start producers')
        proxy.release.set()
        t.drain(.7)
        intent = field(f.snapshot(), 'fresh_intent')[0]
        check(intent != old and field(field(intent, 'selection'), 'endpoint') == 'cts', 'Retry captures a distinct exact CTS input intent')
        t.type_action('launch and vi', 'Launch and view planned run', 'manual-launch-selected')
        w = wait(lambda: next(iter(field(f.snapshot(), 'workflows')), None), 'manual workflow reservation')
        w = f.done(field(w, 'key'))
        f.exact(w, 'cts')
        wait(lambda: selected(f) == field(w, 'run'), 'manual view follows exact allocation')
        check(field(w, 'intent') == intent and len(field(f.snapshot(), 'workflows')) == 1 and
              len(f.events('emit-start')) == 1 and len(f.events('physical-admitted')) == 1,
              'Manual explicit launch binds the exact new input intent to one build/emit/direct-provider chain')
        check(not any(e['argv'][:2] in (['flow', 'plan'], ['flow', 'run']) for e in f.events('pinned-call')),
              'Manual pending/failure/retry path never renders or executes the pinned project')
    finally:
        if proxy:
            proxy.close()
        if f:
            shared.finish(f)


def selected_async_case(args, check, change):
    f = proxy = None
    try:
        f, _ = shared.setup(args, 'selected-async-' + change, check)
        if change == 'capability':
            withdraw(f, 'placement')
        f.terminal.close()
        proxy = shared.StageReplyGate(f)
        f.terminal = t = c.Terminal(f.base, f.client_args, proxy.url, 180, 55)
        position(f, 3)
        t.type_action('quick lau', 'Quick launch selected stage', 'captured-selected-action')
        wait(proxy.entered.is_set, 'real Stage_fresh reply held at client boundary')
        before = f.http.rpc(domain='workspace')
        if change == 'cursor':
            t.key(b'j')
            t.capture('local-cursor-changed', ['> ✓ CTS:'])
        elif change == 'action':
            withdraw(f, 'placement')
        else:
            (f.root / 'catalog-mode').write_text('withdraw-placement')
            f.http.rpc('Discover', wait=False)
            wait(lambda: all('placement' not in field(flow, 'fresh_stage_endpoints') for flow in field(f.snapshot(), 'flows')), 'fresh placement capability withdrawn')
        t.drain(1)
        check(f.http.rpc(domain='workspace') == before, change + ': async invalidation leaves registry/context unchanged')
        proxy.release.set()
        t.drain(1.5)
        t.capture('async-rejected')
        check(field(f.snapshot(), 'fresh_intent') and not field(f.snapshot(), 'workflows') and not f.events('emit-start') and not f.events('physical-admitted'),
              change + ': exact daemon input receipt exists but invalidated selected shortcut submits no source/physical producer')
        check(sum('(Stage_fresh' in r['request'] for r in proxy.requests) == 1 and
              not any('(Launch_fresh' in r['request'] for r in proxy.requests),
              change + ': one real native Stage response; no stale Launch RPC')
    finally:
        if proxy:
            proxy.close()
        if f:
            shared.finish(f)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=900)
    choices = ('historical-default', 'remembered', 'default-not-first', 'stale-profile', 'nonfresh', 'unsupported-endpoint', 'changed-context', 'synthetic', 'selected-async')
    parser.add_argument('--case', action='append', choices=choices)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.evidence = (args.evidence or Path('/tmp/opencode') / ('checklist-workflow-' + secrets.token_hex(6))).resolve()
    require(args.evidence.is_relative_to('/tmp/opencode'), 'Private evidence required')
    os.umask(0o077)
    args.evidence.mkdir(exist_ok=False)
    print('Evidence: ' + str(args.evidence), flush=True)
    result = dict(status='failed', checks=[], cases=args.case or 'complete synthetic matrix',
                  evidence=str(args.evidence), binaries=consistency.hashes([args.daemon, args.client, args.preset_export]))
    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Checklist budget exhausted')))
    signal.alarm(args.timeout)
    try:
        for mode in choices[:7]:
            if not args.case or mode in args.case:
                catalog_case(args, mode, check)
        if not args.case or 'synthetic' in args.case:
            synthetic_case(args, check)
            quick_case(args, check)
            quick_case(args, check, view=False)
            quick_case(args, check, view=False, named=True)
            quick_case(args, check, failure=True)
            quick_case(args, check, changed=True)
        if not args.case or 'selected-async' in args.case:
            for change in ('cursor', 'action', 'capability'):
                selected_async_case(args, check, change)
        result['status'] = 'passed'
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        signal.alarm(0)
        save(args.evidence / 'result.json', result)
    print('PASS synthetic checklist launch workflow: ' + str(len(result['checks'])) + ' assertions; ' + str(args.evidence))


if __name__ == '__main__':
    main()
