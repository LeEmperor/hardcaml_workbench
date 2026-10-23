#!/usr/bin/env python3
"""Private native HTTP/PTY sidebar, live schemes and planned-run acceptance.

Uses matching prebuilt binaries, actual ANSI cells and a private synthetic provider.
No EDA, live state, implicit builds or shared provider source edits.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('sidebar_refinement', HERE / 'test-frontend-refinement.py')
refinement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refinement)
composition = refinement.composition
field, sexp, require, wait = composition.field, composition.sexp, composition.require, composition.wait
pane_rect, pane_body = refinement.pane_rect, refinement.pane_body


def acceptance(t, check, http, runs, presets):
    def registry(): return http.rpc(domain='workspace')
    def mutate(op): return http.mutate(registry(), op)
    def calls():
        return [json.loads(line)['argv'] for line in
                (t.base / 'project/provider-calls.jsonl').read_text().splitlines()]
    def producers(): return [a for a in calls() if a[:2] == ['flow', 'run'] or a[:1] == ['finalize']]
    initial_calls, initial_producers = calls(), producers()
    original = registry()
    overview = next(w for w in field(original, 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(overview, 'id')
    def tile(kind):
        return next(x for x in field(registry(), 'tiles') if field(x, 'workspace') == wid and field(x, 'kind') == kind)
    def zoom(kind):
        mutate('(Set_zoom (workspace %s) (tile (%s)))' % (sexp(wid), sexp(field(tile(kind), 'id'))))
        t.capture('sidebar-focused-' + kind, [kind.replace('-', ' ') if kind == 'stage-checklist' else kind], ['Session'])
    def select(run):
        ws = registry()
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(overview, 'context'))
        http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                    (sexp(wid), sexp(field(context, 'id')), field(context, 'selection_revision'), sexp(run)))
    def preview(): return field(http.rpc(wait=False), 'preview')
    def right_rects(screen):
        return [pane_rect(screen, title) for title in
                ('synthesis', 'timing', 'placement', 'routing', 'checks', 'finalization')]

    screen = t.capture('sidebar-overview-120x40', ['planned-run', 'empty:', 'Reported cells (agg.): 128',
        'not reported unknown', 'Analysis: not yet observed; no authoritative STA evidence',
        'Check drc: pass', 'Acceptance (agg.): not_evaluated'], ['Aggregate Setup slack: 0.42 ns'])
    # This fixture intentionally has successful terminal slack but no authoritative
    # supplementary STA observation. Check actual Timing-pane cells, not just text
    # somewhere else on the screen: WB069 must not borrow finalization's metrics.
    left, top, right, bottom = pane_rect(screen, 'timing')
    timing_body = '\n'.join(line[left + 1:right - 1]
                            for line in screen.lines()[top + 1:bottom - 1])
    check('not reported unknown' in timing_body and 'no authoritative STA evidence' in timing_body
          and '0.42' not in timing_body and 'completed' not in timing_body,
          'Timing pane explicitly reports absent authoritative STA and never borrows terminal slack/completion')
    refinement.sidebar_geometry(screen, check)
    stages = [composition.status_text(line) for line in pane_body(screen, 'stage checklist')]
    # The stable initial cursor can remain on Timing if it was first observed
    # before physical stages hydrated. WB001 clips only a selected long label at
    # this width. Require each canonical row exactly once, accepting that precise
    # bounded selected-label fallback rather than assuming a hydration order.
    names = ['Synthesis', 'Floorplan', 'Placement', 'CTS', 'Routing', 'Signoff']
    def rendered_stage(line, name):
        return name + ': completed' in line or (
            len(name) > 7 and '> ' in line and name[:6] + '…: completed' in line)
    check(all(sum(rendered_stage(line, name) for line in stages) == 1 for name in names),
           'All six explicit stages are visible as vertical checklist rows at120x40')
    check(sum('Timing: not reported' in line and 'unknown' in line for line in stages) == 1,
          'Supplementary Timing row remains unknown independently of six completed physical stages')
    check(not any('(agg.)' in line for line in stages), 'Compact checklist prioritizes stages over aggregate preamble')
    before = registry()
    t.command('Run selector: More visible rows (+1)')
    t.capture('sidebar-selector-five', ['runs 5/6'])
    t.command('Run selector: More visible rows (+1)')
    grown = t.capture('sidebar-selector-six', ['runs 6/6'])
    check(pane_rect(grown, 'runs')[3] > pane_rect(screen, 'runs')[3], 'Run capacity grows actual sidebar selector height')
    check(right_rects(grown) == right_rects(screen), 'Selector expansion leaves all six main-panel rectangles unchanged')
    refinement.sidebar_geometry(grown, check)
    check(registry() == before and calls() == initial_calls, 'Selector capacity is local presentation with no registry/provider changes')
    t.command('Reset presentation overrides (inherit)')
    t.capture('sidebar-selector-reset', ['runs 4/6'])
    t.resize(180, 55)
    refinement.sidebar_geometry(t.capture('sidebar-overview-180x55', ['planned-run', 'Reported cells (agg.)']), check)
    t.resize(80, 24)
    t.capture('sidebar-overview-80x24', ['Compact: focused tile only'])
    t.resize(120, 40)

    # A real pin is part of the invariant, not just an unpinned empty registry.
    pinned = tile('synthesis')
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(field(pinned, 'id')), sexp(runs[0])))
    scheme_samples = {}
    def schemes(workspace, titles):
        # Opening Timing starts a finite selected/neighbor detail demand. Pane
        # titles can render before those explicit reads finish. Settle that demand
        # BEFORE freezing the no-I/O appearance baseline, rather than attributing
        # navigation's late detail reads to a subsequent color-scheme command.
        previous, stable_since = None, None
        deadline = time.monotonic() + 20
        while True:
            t.drain()
            current = calls()
            pending = any(field(op, 'state') in ('pending', 'executing')
                          for op in field(http.rpc(wait=False), 'operations'))
            if current == previous and not pending:
                stable_since = stable_since or time.monotonic()
                if time.monotonic() - stable_since >= .6: break
            else:
                stable_since = None
            previous = current
            require(time.monotonic() < deadline, 'Finite inspection demand did not settle before appearance baseline')
        baseline = registry()
        provider_before = calls()
        geometry = None
        selections = None
        for scheme in ('Carbon', 'Slate', 'Crimson', 'Neon'):
            t.command('Color scheme: ' + scheme)
            t.open_palette('Color scheme: ' + scheme)
            # Pin synchronization may invalidate a captured command target; a
            # reopened palette now captures the settled registry revision.
            if 'Color scheme: ' + scheme + ' [active]' not in t.drain().text():
                t.key(b'\r')
                t.open_palette('Color scheme: ' + scheme)
            t.capture('sidebar-' + workspace + '-' + scheme.lower() + '-active', ['Color scheme: ' + scheme + ' [active]'])
            t.key(b'\x1b')
            shot = t.capture('sidebar-' + workspace + '-' + scheme.lower(), titles)
            rects = [pane_rect(shot, title) for title in titles]
            if geometry is None:
                geometry = rects
                selections = [line for line in shot.lines() if '> ' in line]
            check(rects == geometry, workspace + ': ' + scheme + ' preserves actual pane geometry')
            check([line for line in shot.lines() if '> ' in line] == selections,
                  workspace + ': ' + scheme + ' preserves visible selections')
            check(registry() == baseline and calls() == provider_before,
                  workspace + ': ' + scheme + ' preserves registry, pins, selection and provider calls')
            # Sample actual painted roles: blank cell backgrounds plus framed border
            # foregrounds (the latter are the scheme's selected/border accents).
            backgrounds = sorted({attrs[1] for row in shot.cells for char, attrs in row if attrs[1] != 'default'})
            accents = [shot.cells[top][left][1][0] for left, top, _, _ in rects]
            check(backgrounds and all(a != 'default' for a in accents), 'Explicit ANSI background/accent paint: ' + workspace + '/' + scheme)
            scheme_samples[workspace + '/' + scheme] = dict(backgrounds=backgrounds, accents=accents)
        check(len({tuple(scheme_samples[workspace + '/' + s]['backgrounds']) for s in ('Carbon', 'Slate', 'Crimson', 'Neon')}) == 4,
              workspace + ': all four schemes have distinct actual background attributes')
        check(len({tuple(scheme_samples[workspace + '/' + s]['accents']) for s in ('Carbon', 'Slate', 'Crimson', 'Neon')}) == 4,
              workspace + ': all four schemes have distinct actual accent attributes')
        return t.capture('sidebar-' + workspace + '-neon-retained', titles)

    schemes('overview', ['session', 'runs', 'stage checklist', 'synthesis', 'timing', 'placement', 'routing', 'checks', 'finalization', 'planned-run'])
    t.command('Inspect timing paths ' + field(runs[0], 'id'))
    timing_neon = t.capture('sidebar-timing-inherits-neon', ['timing · paths', 'timing · selected path', 'timing · provenance'])
    check(sorted({a[1] for row in timing_neon.cells for _, a in row if a[1] != 'default'}) == scheme_samples['overview/Neon']['backgrounds'],
          'Switching Overview to Timing preserves the live Neon scheme')
    schemes('timing', ['session', 'runs', 'timing · paths', 'timing · selected path', 'timing · provenance'])
    t.command('Switch to Overview')
    restored = t.capture('sidebar-overview-inherits-neon', ['planned-run', 'PIN asic/'])
    check(sorted({a[1] for row in restored.cells for _, a in row if a[1] != 'default'}) == scheme_samples['overview/Neon']['backgrounds'],
          'Switching Timing to Overview retains scheme and real pinned run')
    (t.base / 'scheme-samples.json').write_text(json.dumps(scheme_samples, indent=2))
    check(producers() == initial_producers, 'Geometry, browsing, pinning and all scheme changes launch no producers')

    # Install private provider controls after seeding. Production sources stay intact.
    wrapper = t.base / 'project/synthetic-flow'
    original_wrapper = wrapper.read_text()
    control = t.base / 'plan-control'
    wrapper.write_text('#!' + sys.executable + '\n' +
        'import json, os, sys, time\nfrom pathlib import Path\n' +
        'control = Path(' + repr(str(control)) + ')\n' +
        'if sys.argv[1:3] == ["flow", "plan"] and control.exists():\n' +
        '    control.with_suffix(".started").write_text("started")\n' +
        '    deadline = time.monotonic() + 25\n' +
        '    while not control.with_suffix(".release").exists():\n' +
        '        if time.monotonic() > deadline: raise SystemExit("private plan gate deadline")\n' +
        '        time.sleep(.05)\n' +
        '    if control.read_text().strip() == "fail":\n' +
        '        with (control.parent / "project/provider-calls.jsonl").open("a") as out:\n' +
        '            out.write(json.dumps(dict(argv=sys.argv[1:], injected=True)) + "\\n")\n' +
        '        raise SystemExit("INJECTED private synthetic Plan failure")\n' + original_wrapper.split('\n', 1)[1])
    zoom('stage-checklist')
    t.capture('sidebar-stage-focus', ['Synthesis: completed', 'Placement: completed'])
    t.key(b'k' * 10)  # Establish Synthesis explicitly, independent of startup hydration.
    t.key(b'j'); t.key(b'j'); t.key(b'r')
    ready_preview = wait(lambda: preview(), 'placement stage exact plan')[0]
    check(dict(field(ready_preview, 'selection')) == dict(flow='synthetic', profile='success', endpoint='placement', assignments=[]),
          'Stage r publishes the exact typed flow/profile/endpoint/assignments')
    t.command('Unzoom workspace')
    ready = t.capture('sidebar-plan-ready', ['ready:', 'flow: synthetic / profile: success', 'endpoint: placement', 'assignments: (none)'])
    ready_color = ready.attrs_for('ready:')[0][0][0]
    zoom('planned-run'); t.key(b'\r')
    identity = field(ready_preview, 'plan_identity')
    t.capture('sidebar-plan-exact-identity', ['exact plan identity: ' + identity, 'exact plan metadata (JSON)'])
    t.key(b'j' * 200)
    t.capture('sidebar-plan-metadata-scroll', ['Plan reuse readiness is separate from launch/producer lifecycle'])
    t.key(b'\x1b'); t.command('Unzoom workspace')
    select(runs[1])
    t.capture('sidebar-plan-historical-selection-independent', ['ready:', 'endpoint: placement'])
    check(preview() == [ready_preview], 'Selecting a historical run does not retarget the project plan')
    select(runs[0])

    # New exact endpoint, delayed failure: the prior successful preview must never
    # be painted or launchable as ready for the new local intent. The real backend
    # currently clears it when a new Plan starts; retained-preview detail is checked
    # too if a backend retains it explicitly.
    control.write_text('fail')
    zoom('stage-checklist'); t.key(b'k' * 20); t.key(b'j' * 3)
    t.capture('sidebar-stage-cts-request', ['> ✓ CTS: completed'])
    t.key(b'r')
    wait(lambda: control.with_suffix('.started').exists(), 'private delayed planner entered')
    t.command('Unzoom workspace')
    pending = t.capture('sidebar-plan-pending-old-preview', ['pending:', 'endpoint: cts'])
    check(not pane_body(pending, 'planned-run')[0].startswith('ready:'), 'Pending new plan never paints the retained successful preview ready')
    control.with_suffix('.release').write_text('release')
    failed = t.capture('sidebar-plan-failed-old-preview', ['failed:'])
    retained = preview()
    check(retained in ([], [ready_preview]), 'Failed request publishes no replacement ready preview (daemon may clear the prior preview)')
    check(failed.attrs_for('failed:')[0][0][0] != ready_color, 'Failed new plan uses failure paint, not previous ready/success paint')
    zoom('planned-run'); t.key(b'\r')
    t.capture('sidebar-plan-failed-retained-detail',
              ['failed:', 'INJECTED', 'local requested selection', 'endpoint: cts'] +
              (['Retained/unconfirmed shared preview', 'not ready for current intent', identity] if retained else []))
    t.key(b'\x1b'); t.command('Unzoom workspace')
    check(producers() == initial_producers, 'Planning, pending/failure inspection and historical selection invoke no flow run/finalize')
    t.open_palette('Launch')
    t.capture('sidebar-failed-launch-unavailable',
              ['Launch', 'Current plan is pending, failed, stale or unconfirmed'] if retained else ['Launch', 'No preview:'])
    t.key(b'\x1b')

    # Explicit retry then explicit Launch is the sole allocation in this harness.
    control.unlink()
    zoom('stage-checklist'); t.key(b'r')
    retry = wait(lambda: [p for p in preview() if field(field(p, 'selection'), 'endpoint') == 'cts'], 'retry ready CTS')[0]
    t.command('Unzoom workspace')
    t.capture('sidebar-retry-ready', ['ready:', 'endpoint: cts'])
    before_runs = field(http.rpc(wait=False), 'runs')
    t.command('Launch synthetic / success → cts')
    allocated = wait(lambda: [r for r in field(http.rpc(wait=False), 'runs') if field(r, 'run') not in [field(x, 'run') for x in before_runs]], 'explicit Launch distinct allocation')[0]
    run = field(allocated, 'run')
    check(run not in runs and field(field(allocated, 'reference'), 'attempt') != field(retry, 'plan_identity'),
          'Explicit Launch allocates a distinct execution, separate from historical runs and plan identity')
    check(len(producers()) == len(initial_producers) + 1 and producers()[-1][:2] == ['flow', 'run'], 'Exactly one producer starts, solely from explicit Launch')
    active_run = wait(lambda: [op for op in field(http.rpc(wait=False), 'operations')
                              if field(op, 'kind') == 'run' and field(op, 'state') in ('queued', 'running', 'executing', 'waiting')],
                      'allocated producer operation key')[0]
    http.rpc('(Cancel %s)' % sexp(field(active_run, 'key')), wait=False)
    wait(lambda: [op for op in field(http.rpc(wait=False), 'operations')
                  if field(op, 'key') == field(active_run, 'key') and field(op, 'state') == 'failed'],
         'owned synthetic producer cancellation')
    t.capture('sidebar-final-plan-and-launch', ['planned-run', 'ready:'], ['no job allocated', 'no queued job'])
    launch = next(l for l in field(http.rpc(wait=False), 'launches')
                  if field(l, 'run_id') == [field(run, 'id')])
    check(field(launch, 'preview') == retry and field(launch, 'key') == field(active_run, 'key').removeprefix('run:'),
          'Retained ready plan has its exact submitted preview/key/allocation ledger identity after cancellation')
    (t.base / 'provider-calls-final.json').write_text(json.dumps(calls(), indent=2))
    return 'Overview'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'): p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--evidence', type=Path)
    p.add_argument('--timeout', type=int, default=600)
    args = p.parse_args()
    for name in ('daemon', 'client', 'preset_export'): setattr(args, name, getattr(args, name).resolve(strict=True))
    args.evidence = args.evidence or Path('/tmp/opencode') / ('overview-sidebar-' + secrets.token_hex(6))
    require(args.evidence.resolve().is_relative_to('/tmp/opencode'), 'Evidence must be private /tmp/opencode state')
    args.palette_only = False
    args.harness = 'Overview sidebar/schemes/planned-run'
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Sidebar acceptance budget exhausted')))
    signal.alarm(args.timeout)
    try: composition.run(args, acceptance=acceptance)
    finally: signal.alarm(0)


if __name__ == '__main__': main()
