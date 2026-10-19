#!/usr/bin/env python3
"""Native indicator acceptance using matching prebuilt binaries and private state.

No builds or EDA. Evidence must be a NEW directory below /tmp/opencode. Exercises
real public Plan/Launch/Observe and FS2 requests, bounded synthetic providers, and
actual reconstructed ANSI cells (including screenshots), never daemon state files.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sys
import time
import traceback
from types import SimpleNamespace
import unicodedata

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sidebar = load('indicators_sidebar', 'test-overview-sidebar.py')
workflow = load('indicators_workflow', 'test-checklist-launch-workflow.py')
testing = load('indicators_testing', 'test-synthetic-testing.py')
c = sidebar.composition
demo, field, sexp, require, wait = c.demo, c.field, c.sexp, c.require, c.wait


class Terminal(c.Terminal):
    def open_palette(self, query=''):
        try:
            super().open_palette(query)
        except AssertionError:
            # A resize is diagnostic only: it must never turn a missing native
            # input redraw into a passing acceptance assertion.
            screen = self.resize(self.width + 1, self.height)
            self.save('palette-missing-redraw-after-resize', screen)
            raise


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def framed(screen):
    """Adapt ASCII frame cells for the shared rounded-frame geometry oracle.

    Only horizontal frame endpoints change; coordinates, title content, and all
    body/indicator cells remain the actual native capture.
    """
    lines = []
    for line in screen.lines():
        chars = list(line)
        for match in re.finditer(r'\+([^+\n]*-{2,})\+', line):
            top = bool(match.group(1).strip(' -'))
            chars[match.start()] = '╭' if top else '╰'
            chars[match.end() - 1] = '╮' if top else '╯'
        lines.append(''.join(chars))
    return SimpleNamespace(width=screen.width, height=screen.height, lines=lambda: lines)


def row(screen, label):
    lines = screen.lines()
    if label.startswith(('Synthesis:', 'Routing:', 'Signoff:')):
        left, top, right, bottom = sidebar.pane_rect(framed(screen), 'stage checklist')
        lines = [line[left:right] for line in lines[top + 1:bottom - 1]]
    lines = [c.status_text(line) for line in lines]
    matches = [line for line in lines if label.casefold() in line.casefold()]
    require(len(matches) == 1, 'Exactly one visible lifecycle row for ' + label + ': ' + repr(matches))
    return matches[0]


def prefix(screen, label):
    line = row(screen, label)
    # Ignore frame and keyboard cursor. Only the indicator area before the full
    # semantic label is inspected; unrelated clocks/log/progress cannot pass this.
    return line[1:line.casefold().index(label.casefold())].strip().removeprefix('>').strip()


def samples(t, label, marker, check, moving, alive=None):
    observed = []
    for index in range(10):
        if alive is not None:
            check(alive(), label + ': provider/request is genuinely active during sample ' + str(index))
        screen = t.drain((.137, .223, .181)[index % 3])
        t.save(label + '-%02d' % index, screen)
        observed.append(prefix(screen, marker))
    check((len(set(observed)) > 1) if moving else (len(set(observed)) == 1),
          label + (': native lifecycle frames advance' if moving else ': lifecycle indicator is settled'))
    save(t.base / (label + '-frames.json'), dict(marker=marker, prefixes=observed, moving=moving))
    return observed


def check_icon(value, mode, check, label):
    if mode == 'Off':
        check(value == '', label + ': Off leaves no indicator or padding glyph')
    else:
        check(len(value) == 1 and all(not unicodedata.combining(ch) and
              unicodedata.east_asian_width(ch) not in ('W', 'F') for ch in value),
              label + ': compact single-cell-width indicator characters')
        check(value.isascii() if mode == 'ASCII' else not value.isascii(),
              label + ': ' + mode + ' fallback vocabulary')


def calls(base):
    result = {}
    for name in ('provider-calls.jsonl', 'simulation-calls.jsonl'):
        path = base / 'project' / name
        result[name] = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return result


def intent_calls(base):
    """Domain polling may read observations; presentation must not discover/work."""
    all_calls = calls(base)
    return dict(asic=[x for x in all_calls['provider-calls.jsonl']
                      if x['argv'][:1] in (['flow'], ['finalize'])],
                simulation=all_calls['simulation-calls.jsonl'])


def semantic(http):
    asic = http.rpc(wait=False)
    sim = http.rpc(domain='simulation', wait=False)
    return dict(runs=[field(r, 'run') for r in field(asic, 'runs')],
                launches=field(asic, 'launches'), preview=field(asic, 'preview'),
                attempts=[field(a, 'id') for a in field(sim, 'attempts')],
                workspace=http.rpc(domain='workspace'))


def icons(t, http, mode, check):
    before, commands = semantic(http), intent_calls(t.base)
    title = 'Appearance: Icons ' + mode
    for _ in range(3):
        t.command(title)
        t.open_palette(title)
        if title + ' [active]' in t.drain().text():
            break
        # Public zoom/selection mutations may reach the client between palette
        # capture and dispatch. Reopen against the settled revision, as sidebar
        # acceptance does; the final active-state assertion remains mandatory.
        t.key(b'\x1b')
    else:
        t.open_palette(title)
    t.capture('icons-' + mode.lower() + '-active-' + str(len(t.keys)), ['Appearance: Icons ' + mode + ' [active]'])
    t.key(b'\x1b')
    check(semantic(http) == before, 'Icons ' + mode + ' retains exact runs/attempts/preview/launches/registry')
    check(intent_calls(t.base) == commands, 'Icons ' + mode + ' launches/discovers/plans no extra work')


def install_gate(wrapper, control):
    original = wrapper.read_text()
    wrapper.write_text('#!' + sys.executable + '\n' +
        'import sys,time\nfrom pathlib import Path\n' +
        'c=Path(' + repr(str(control)) + ')\n' +
        'if sys.argv[1:3]==["flow","plan"] and c.exists():\n' +
        ' c.with_suffix(".entered").write_text("entered")\n' +
        ' deadline=time.monotonic()+90\n' +
        ' while not c.with_suffix(".release").exists():\n' +
        '  if time.monotonic()>deadline: raise SystemExit("private indicator gate timeout")\n' +
        '  time.sleep(.05)\n' +
        ' if c.read_text()=="fail": raise SystemExit("INJECTED indicator Plan failure")\n' +
        original.split('\n', 1)[1])


def acceptance(t, http, runs, check):
    baseline = intent_calls(t.base)
    titles = ('session', 'runs', 'stage checklist', 'synthesis', 'timing',
              'placement', 'routing', 'checks', 'finalization', 'planned-run')
    geometry = None
    for mode in ('Unicode', 'ASCII', 'Off'):
        icons(t, http, mode, check)
        shot = t.capture('overview-' + mode.lower() + '-120x40', ['Synthesis: completed', 'Acceptance (agg.): not_evaluated'])
        sidebar.refinement.sidebar_geometry(framed(shot), check)
        rects = [sidebar.pane_rect(framed(shot), title) for title in titles]
        check(all(0 <= l < r <= 120 and 0 <= top < bottom <= 40 for l, top, r, bottom in rects),
              mode + ': all actual pane bounds fit 120x40')
        if geometry is None: geometry = rects
        check(rects == geometry, mode + ': icons preserve dense geometry')
        check_icon(prefix(shot, 'Synthesis: completed'), mode, check, 'Completed stage')
        workflow.zoom(http, 'stage-checklist')
        shot = t.capture('stages-' + mode.lower(), ['Synthesis: completed', 'Floorplan: completed',
            'Placement: completed', 'CTS: completed', 'Routing: completed', 'Signoff: completed'])
        samples(t, 'completed-' + mode.lower(), 'Synthesis: completed', check, False)
        t.command('Unzoom workspace')
    check(intent_calls(t.base) == baseline, 'All initial mode/geometry/status checks cause no discovery or work')
    workflow.zoom(http, 'run-selector')
    t.capture('historical-exact-identities', [field(run, 'id') for run in runs] + ['completed', 'failed'])
    workflow.setup_workspace(http, runs[1], demo.workspace_presets(t.args.preset_export))
    workflow.zoom(http, 'stage-checklist')
    for mode in ('Unicode', 'ASCII', 'Off'):
        icons(t, http, mode, check)
        t.capture('failed-and-skipped-' + mode.lower(), ['Routing: failed', 'Signoff: skipped'])
        samples(t, 'failed-stage-' + mode.lower(), 'Routing: failed', check, False)
        samples(t, 'skipped-stage-' + mode.lower(), 'Signoff: skipped', check, False)
    workflow.setup_workspace(http, runs[0], demo.workspace_presets(t.args.preset_export))
    t.command('Unzoom workspace')

    # Native local Plan intent is observable while a genuine provider request is
    # blocked. The private gate has a hard deadline and only changes copied files.
    gate = t.base / 'plan-control'
    install_gate(t.base / 'project/synthetic-flow', gate)
    for index, (mode, endpoint) in enumerate(zip(('Unicode', 'ASCII', 'Off'),
                                               ('synthesis', 'floorplan', 'placement'))):
        gate.with_suffix('.entered').unlink(missing_ok=True)
        gate.with_suffix('.release').unlink(missing_ok=True)
        gate.write_text('success')
        icons(t, http, mode, check)
        workflow.zoom(http, 'stage-checklist')
        t.capture('plan-stage-selection-' + mode.lower(), ['Synthesis: completed'])
        t.key(b'k' * 20)
        if index: t.key(b'j' * index)
        t.key(b'r')
        wait(lambda: gate.with_suffix('.entered').exists(), 'private Plan provider entered')
        # Direct public zoom mutation avoids spending the bounded Plan request's
        # 30-second backend budget on palette navigation between active samples.
        workflow.zoom(http, 'planned-run')
        t.capture('plan-pending-' + mode.lower(), ['pending:', 'endpoint: ' + endpoint])
        plan_calls = intent_calls(t.base)
        observed = samples(t, 'plan-active-' + mode.lower(), 'pending:', check, mode != 'Off',
            lambda: not gate.with_suffix('.release').exists() and not field(http.rpc(wait=False), 'preview'))
        for value in observed: check_icon(value, mode, check, 'Active Plan')
        check(intent_calls(t.base) == plan_calls, mode + ': pending frames issue no additional Plan/discovery/producer')
        gate.with_suffix('.release').write_text('release')
        preview = wait(lambda: next(iter(field(http.rpc(wait=False), 'preview')), None), 'exact ready preview')
        check(dict(field(preview, 'selection')) == dict(flow='synthetic', profile='success', endpoint=endpoint, assignments=[]),
              mode + ': Plan keeps exact keyboard-captured selection')
        t.capture('plan-ready-' + mode.lower(), ['ready:', 'endpoint: ' + endpoint])
        samples(t, 'plan-ready-settled-' + mode.lower(), 'ready:', check, False)
    identity = field(preview, 'plan_identity')
    icons(t, http, 'Unicode', check)
    t.capture('plan-ready', ['ready:', 'endpoint: placement'])
    t.key(b'\r')
    t.capture('plan-exact-identity', ['exact plan identity: ' + identity, 'exact plan metadata (JSON)'])
    t.key(b'\x1b'); t.command('Unzoom workspace')

    # Explicit Launch is the only ASIC producer; manual synthetic playback gives
    # stable stage content so a changing row can only be native animation.
    before = semantic(http)
    t.command('Launch synthetic / success → placement')
    allocated = wait(lambda: next((r for r in field(http.rpc(wait=False), 'runs')
        if field(r, 'run') not in before['runs']), None), 'explicit synthetic allocation')
    run = field(allocated, 'run')
    attempt = Path(field(field(allocated, 'reference'), 'attempt'))
    check(attempt.resolve().is_relative_to(t.base / 'results'), 'Producer attempt belongs to private evidence')
    wait(lambda: (attempt / 'observation.json').exists() and
         demo.provider.load(attempt / 'observation.json')['writer_active'], 'synthetic writer active')
    workflow.setup_workspace(http, run, demo.workspace_presets(t.args.preset_export))
    workflow.zoom(http, 'stage-checklist')
    t.capture('run-stage-active', ['Synthesis: running', 'not requested'])
    active_calls = intent_calls(t.base)
    for mode in ('Unicode', 'ASCII', 'Off'):
        icons(t, http, mode, check)
        t.capture('run-active-' + mode.lower(), ['Synthesis: running', 'not requested'])
        observed = samples(t, 'run-active-' + mode.lower(), 'Synthesis: running', check, mode != 'Off',
            lambda: demo.provider.load(attempt / 'observation.json')['writer_active'])
        for value in observed: check_icon(value, mode, check, 'Running stage')
    check(intent_calls(t.base) == active_calls, 'Active animation and icon switches create no additional producer or discovery')
    while demo.provider.load(attempt / 'observation.json')['writer_active']:
        demo.provider.advance(attempt)
    http.rpc('(Observe %s)' % sexp(run), wait=False)
    wait(lambda: any(field(r, 'run') == run and field(r, 'status') == 'completed'
                    for r in field(http.rpc(wait=False), 'runs')), 'completed synthetic observation')
    for mode in ('Unicode', 'ASCII', 'Off'):
        icons(t, http, mode, check)
        shot = t.capture('run-terminal-' + mode.lower(), ['Synthesis: completed', 'not requested'])
        check_icon(prefix(shot, 'Synthesis: completed'), mode, check, 'Terminal stage')
        samples(t, 'run-terminal-' + mode.lower(), 'Synthesis: completed', check, False)
    launch = next(l for l in field(http.rpc(wait=False), 'launches') if field(l, 'run_id') == [field(run, 'id')])
    check(field(launch, 'preview') == preview, 'Animation preserves exact submitted preview/plan identity in launch ledger')
    workflow.zoom(http, 'run-selector')
    t.capture('full-run-identities', [field(run, 'id'), 'completed'])
    t.command('Unzoom workspace')

    # A failed Plan must also settle and cannot revive the prior ready identity.
    gate.with_suffix('.entered').unlink(); gate.with_suffix('.release').unlink()
    gate.write_text('fail')
    workflow.setup_workspace(http, runs[0], demo.workspace_presets(t.args.preset_export))
    workflow.zoom(http, 'stage-checklist')
    t.capture('failed-plan-selection', ['Synthesis: completed'])
    t.key(b'k' * 20); t.key(b'j'); t.key(b'r')
    wait(lambda: gate.with_suffix('.entered').exists(), 'failing Plan entered')
    t.command('Unzoom workspace'); workflow.zoom(http, 'planned-run')
    t.capture('failed-plan-pending', ['pending:', 'endpoint: floorplan'])
    gate.with_suffix('.release').write_text('release')
    t.capture('failed-plan-terminal', ['failed:'])
    samples(t, 'failed-plan-settled', 'failed:', check, False)
    t.command('Unzoom workspace')

    # Seeded FS2 evidence is public, exact and semantically distinct from exit 0.
    t.command('Switch to Testing')
    t.capture('cooperative-testing-default', ['SIMULATION CATALOG', 'ATTEMPTS', 'ARTIFACTS'])
    testing.ensure_legacy_simulation(http)
    t.command('Switch to Legacy simulation')
    for _ in range(12):
        t.open_palette('Simulation: Reopen')
        available = 'No matching commands' not in t.drain().text()
        t.key(b'\x1b')
        if available: break
        t.key(b'\t')
    require(available, 'Testing simulation commands available through native focus')
    receipts = demo.provider.load(t.base / 'simulation-seed.json')['submissions']
    for outcome, key in (('Passed', 'synthetic-fs2-v1-pass'), ('Failed', 'synthetic-fs2-v1-failure')):
        aid = receipts[key]['attempt_id']
        detail = testing.details(http, aid)
        check(field(detail, 'outcome') == outcome and field(detail, 'exit_code') == ['0'],
              outcome + ': real structured semantic outcome distinct from process exit')
        # The exact opaque ID exceeds the palette's 88-cell title budget. Query
        # all of it, require a unique native match, then assert its full identity
        # in the zoomed result rather than expecting an unclipped palette label.
        t.open_palette('Simulation: Reopen ' + aid + ' synthetic-checks')
        t.capture('simulation-exact-command-' + outcome.lower(),
                  ['Simulation: Reopen ' + aid[:35], '1/1'], ['No matching commands'])
        t.key(b'\x1b[A' * 100); t.key(b'\r')
        t.command('Zoom focused tile')
        t.capture('simulation-' + outcome.lower(), [aid, outcome, 'SYNTHETIC'])
        t.command('Unzoom workspace')
    t.command('Switch to Overview')
    for width, height in ((120, 40), (180, 55)):
        t.resize(width, height)
        sidebar.refinement.sidebar_geometry(framed(t.capture('final-%dx%d' % (width, height), ['planned-run'])), check)
    final_calls = calls(t.base)
    check(sum(x['argv'][:2] == ['flow', 'run'] for x in final_calls['provider-calls.jsonl']) == 1
          and not any(x['argv'][:1] == ['finalize'] for x in final_calls['provider-calls.jsonl']),
          'Exactly one ASIC producer, solely explicit Launch; no finalize or EDA')
    check(sum(x['operation'] == 'run' for x in final_calls['simulation-calls.jsonl']) == 2
          and sum(x['operation'] == 'discover' for x in final_calls['simulation-calls.jsonl']) == 1,
          'Testing browsing and indicator changes retain exactly the two seeded FS2 attempts and one seed discovery')
    save(t.base / 'exact-preview.json', preview)
    save(t.base / 'exact-launch.json', launch)
    save(t.base / 'provider-calls-final.json', calls(t.base))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--evidence', type=Path, help='NEW private directory under /tmp/opencode')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'):
        path = getattr(args, name).resolve(strict=True)
        require(path.is_file() and os.access(path, os.X_OK), 'Prebuilt executable required: ' + str(path))
        setattr(args, name, path)
    args.evidence = (args.evidence or Path('/tmp/opencode') / ('terminal-indicators-' + secrets.token_hex(6))).resolve()
    require(args.evidence.is_relative_to('/tmp/opencode') and args.evidence != Path('/tmp/opencode'), 'Private evidence directory required')
    require(args.evidence.parent.is_dir() and not args.evidence.exists(), 'Evidence must be NEW with existing parent')
    require(args.timeout > 0, 'Positive timeout required')
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Indicator acceptance budget exhausted')))
    signal.alarm(args.timeout)
    base = demo.prepare(args.evidence, manual=True, delay=.05)
    for name in ('home', 'config', 'client-state'): (base / name).mkdir()
    result = dict(status='failed', checks=[], evidence=str(base),
        binaries={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.daemon, args.client, args.preset_export)})
    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)
    daemon, terminal = workflow.consistency.PrivateDaemon(args, base), None
    print('Indicator evidence: ' + str(base), flush=True)
    try:
        daemon.start()
        http, runs = demo.seed(base, daemon.url, args.preset_export)
        daemon.histories.append(http.history)
        terminal = Terminal(base, args, daemon.url)
        terminal.args = args
        terminal.capture('startup', ['stage checklist', 'Synthesis: completed'])
        acceptance(terminal, http, runs, check)
        retained, commands = semantic(http), intent_calls(base)
        # The restart helper writes keys.json for its own session. Preserve the
        # complete interaction log before that fresh client's empty log replaces it.
        save(base / 'interaction-keys.json', terminal.keys)
        terminal.close(); terminal = None
        terminal = Terminal(base, args, daemon.url)
        shot = terminal.capture('persisted-icons-off', ['Synthesis: completed'])
        check_icon(prefix(shot, 'Synthesis: completed'), 'Off', check, 'Fresh native client persists icon choice')
        check(semantic(http) == retained and intent_calls(base) == commands,
              'Client restart and persisted icons preserve registry/identities and launch/discover nothing')
        result['status'] = 'passed'
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        try:
            if terminal is not None: terminal.close()
        finally:
            try: daemon.stop()
            finally:
                signal.alarm(0)
                save(base / 'result.json', result)
    print('PASS native terminal indicators: ' + str(base), flush=True)


if __name__ == '__main__': main()
