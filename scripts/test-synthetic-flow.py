#!/usr/bin/env python3
"""Bounded synthetic CLI/real HTTP/optional PTY acceptance; stdlib, no builds/EDA.

Default uses existing built daemon/client. --smoke runs provider-only checks.
All evidence is retained in a new directory; owned processes are always stopped.
"""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('synthetic_demo', REPO / 'scripts/synthetic-flow-demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
from http_client import Client, field, parse, sexp
import provider

# Reuse the existing ANSI screen reconstruction oracle rather than matching stale
# PTY diff bytes (Enter/Esc must change the CURRENT screen).
screen_spec = importlib.util.spec_from_file_location('fs0_screen', REPO / 'scripts/test-fs0.py')
fs0_screen = importlib.util.module_from_spec(screen_spec)
screen_spec.loader.exec_module(fs0_screen)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def wait_for(predicate, label, seconds=15):
    deadline = time.monotonic() + seconds
    while True:
        result = predicate()
        if result:
            return result
        require(time.monotonic() < deadline, 'Timeout: ' + label)
        time.sleep(.05)


def smoke(base):
    require(parse(r'"SYNTHETIC \226\128\148 \194\181m"') == 'SYNTHETIC — µm', 'Sexplib escaped UTF-8 bytes')
    require(parse(r'"\\226"') == r'\226', 'Literal Sexplib backslash preserved')
    root = base / 'project'
    wrapper = root / 'synthetic-flow'
    def call(*argv, ok=True):
        result = subprocess.run([str(wrapper), *argv], cwd=root, capture_output=True, timeout=5)
        require((result.returncode == 0) == ok, repr(argv) + ': ' + result.stderr.decode())
        return json.loads(result.stdout) if ok else None
    require(call('--version', '--json')['cli_contract']['version'] == 4, 'CLI4 metadata')
    call('flow', 'list', '--json')
    call('flow', 'describe', '--flow', 'synthetic', '--json')
    selected = provider.selection(endpoint='placement')
    preview = call('flow', 'plan', '--flow', 'synthetic', '--profile', 'success', '--endpoint', 'placement', '--json')
    require(preview['stage_plan']['stages'][2]['action'] == selected, 'Exact advertised action selection')
    require([s['name'] for s in preview['stage_plan']['stages']] ==
            ['Synthesis', 'Floorplan', 'Placement', 'CTS', 'Routing', 'Signoff'],
            'Production-like producer checklist labels')
    require(all('SYNTHETIC' in s['reason'] for s in preview['stage_plan']['stages']),
            'Synthetic provenance retained separately from labels')
    for reference in provider.load(base / 'manifest.json')['runs']:
        attempt = Path(reference['attempt'])
        before = {str(p): p.read_bytes() for p in attempt.rglob('*') if p.is_file()}
        observation = call('observation', 'inspect', str(attempt), '--json')
        updates = call('observation', 'read-updates', str(attempt), '--stream-id', reference['stream_id'], '--after', '0', '--json')
        require(updates['cursor'] == observation['cursor'] and len(updates['events']) == observation['cursor'], 'Update cursors/events')
        report = call('report', str(attempt / 'execution.json'), '--json')
        require(report['execution'] == provider.load(attempt / 'execution.json'), 'Report exact execution bytes')
        operation = call('finalization-inspect', reference['finalization'], '--json')
        require(operation['execution']['sha256'] == provider.digest(attempt / 'execution.json'), 'Execution SHA-256')
        require(operation['results']['sha256'] == provider.digest(operation['results']['path']), 'Results SHA-256')
        for domain in ('timing', 'clocks', 'physical', 'routing'):
            index = call('inspect', str(attempt / 'execution.json'), '--domain', domain, '--stage', 'routing', '--json')
            require(index['execution_sha256'] == operation['execution']['sha256'], 'Inspection execution hash')
            require(index['source_digest'] == provider.digest(attempt / ('inspection-' + domain + '-routing.json')), 'Inspection evidence hash')
            rows = index['rows']
            require(len(rows) == (12 if domain == 'timing' else 5), 'Rich inspection row count: ' + domain)
            ids = [r['id'] for r in rows]
            require(len(ids) == len(set(ids)), 'Duplicate inspection row identities')
            evidence = provider.load(attempt / ('inspection-' + domain + '-routing.json'))
            require(set(ids) == set(evidence['details']), 'Every stable row has exact keyed detail')
            available = reference['stream_id'] == 'synthetic-reference'
            require(all(r['status'] == ('available' if available else 'unavailable') and
                        (r['value'] is not None) == available for r in rows), 'Uncompleted stages retain unavailable values')
            if domain == 'timing':
                require({r['corner'] for r in rows} == {'synthetic_typical', 'synthetic_slow'} and
                        {r['group'] for r in rows} == {'clk', 'io'}, 'Two timing corners and two groups')
                require({dict(r['fields'])['evidence_kind'] for r in rows} == {'setup', 'hold'}, 'Setup and hold paths')
                require(rows[0]['id'] == 'synthetic-timing-routing' and
                        rows[0]['name'] == 'SYNTHETIC setup path clk:reg0 -> reg7', 'Original first path identity/name preserved')
            elif domain == 'clocks':
                require({dict(r['fields'])['evidence_kind'] for r in rows} ==
                        {'declared_constraint', 'synthetic_measurement'}, 'Declared clocks distinguished from synthetic measurements')
            detail_args = ('inspect', str(attempt / 'execution.json'), '--domain', domain, '--stage', 'routing',
                           '--row-id', index['rows'][0]['id'], '--expected-digest')
            require('SYNTHETIC' in call(*detail_args, index['source_digest'], '--json')['detail'], 'Synthetic detail')
            call(*detail_args, '0' * 64, '--json', ok=False)
            last = call('inspect', str(attempt / 'execution.json'), '--domain', domain, '--stage', 'routing',
                        '--row-id', ids[-1], '--expected-digest', index['source_digest'], '--json')
            require(last['detail'] == evidence['details'][ids[-1]], 'Last row detail matches retained evidence')
        completed_paths = provider.load(attempt / 'inspection-timing-cts.json')['rows']
        values = [r['value'] for r in completed_paths]
        require(all(v is not None for v in values), 'Completed CTS retains timing paths')
        if reference['stream_id'] == 'synthetic-failed':
            require(min(values) < 0 < max(values), 'Failed candidate has meaningful signed timing values')
        normalized = provider.load(operation['results']['path'])
        for key, unit in [('final_standard_cell_area', 'um^2'), ('final_utilization', 'fraction')]:
            require(normalized['metrics'][key]['value'] > 0 and normalized['metrics'][key]['unit'] == unit and
                    normalized['metrics'][key]['unavailable_reason'] is None, 'Populated physical metric: ' + key)
        require(before == {str(p): p.read_bytes() for p in attempt.rglob('*') if p.is_file()}, 'Read-only evidence changed')
    # Exercise actual adapter-compatible streaming launcher, deterministic step and SIGTERM.
    def launch(endpoint='placement'):
        run_preview = preview if endpoint == 'placement' else call('flow', 'plan', '--flow', 'synthetic',
            '--profile', 'success', '--endpoint', endpoint, '--json')
        process = subprocess.Popen([str(wrapper), 'flow', 'run', '--flow', 'synthetic', '--profile', 'success',
            '--endpoint', endpoint, '--expected-plan-identity', run_preview['plan_identity'],
            '--results-root', str(base / 'results'), '--json'], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        require(select.select([process.stdout], [], [], 5)[0], 'No early allocation')
        allocation = json.loads(process.stdout.readline())
        return process, Path(allocation['attempt'])
    process, attempt = launch()
    try:
        require(provider.load(attempt / 'observation.json')['stage_plan']['stages'][0]['status'] == 'running', 'Explicit running stage')
        for _ in range(3):
            call('advance', str(attempt))
        stdout, stderr = process.communicate(timeout=5)
        require(process.returncode == 0, stderr)
        require(provider.load(attempt / 'observation.json')['state']['outcome']['status'] == 'completed', 'Prefix completed')
        require([s['status'] for s in provider.load(attempt / 'observation.json')['stage_plan']['stages']] ==
                ['completed'] * 3 + ['not_requested'] * 3, 'Prefix is new run, not resume')
        require(len(stdout.splitlines()) == 2, 'Terminal envelope + valid execution record')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    process, cancelled = launch()
    try:
        require(cancelled != attempt, 'Distinct allocation identity')
        process.terminate()
        process.communicate(timeout=5)
        state = provider.load(cancelled / 'observation.json')
        require(state['state']['outcome']['status'] == 'cancelled' and not state['writer_active'], 'SIGTERM publishes cancelled')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    settings = provider.load(root / 'synthetic-settings.json')
    provider.save(root / 'synthetic-settings.json', dict(manual=False, delay_seconds=.02, max_run_seconds=2))
    started = time.monotonic()
    process = None
    try:
        process, timed = launch('signoff')
        stdout, stderr = process.communicate(timeout=2)
        elapsed = time.monotonic() - started
        require(process.returncode == 0, 'Automatic playback failed: ' + stderr)
        state = provider.load(timed / 'observation.json')
        require(state['state']['outcome']['status'] == 'completed' and not state['writer_active'] and
                [s['status'] for s in state['stage_plan']['stages']] == ['completed'] * 6,
                'Nonmanual six-stage playback must complete without advance commands')
        require(elapsed < 1.5, 'Short automatic playback exceeded 1.5 second budget')
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        provider.save(root / 'synthetic-settings.json', settings)
    provider.save(base / 'smoke-verified.json', dict(status='passed', synthetic=True,
        automatic_run=str(timed), automatic_seconds=elapsed, timing_rows=12, other_domain_rows=5))


def pty_check(base, client_path, http):
    # A different existing preview makes an ignored `r` fail even though the
    # preceding HTTP test also planned placement.
    http.rpc('(Plan ((flow synthetic) (profile success) (endpoint signoff) (assignments ())))')
    ws = http.rpc(domain='workspace')
    workspace = field(field(ws, 'workspaces')[0], 'id')
    context_id = field(field(ws, 'workspaces')[0], 'context')
    original_zoom = field(field(ws, 'workspaces')[0], 'zoomed_tile')
    checklist = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == workspace and field(t, 'kind') == 'stage-checklist')
    context_before = next(c for c in field(ws, 'contexts') if field(c, 'id') == context_id)
    before_runs = field(http.rpc(), 'runs')
    before_ids = {field(field(r, 'run'), 'id') for r in before_runs}
    def supervised_jobs():
        snapshot = http.raw('/api/v1/snapshot', [['instance_id', http.instance]])
        return {field(job, 'id') for job in field(snapshot, 'jobs')}
    jobs_before = supervised_jobs()
    def calls():
        return [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]
    def launches():
        return [a for a in calls() if a[:2] == ['flow', 'run']]
    def producers():
        return [a for a in calls() if a[:2] == ['flow', 'run'] or a[:1] == ['finalize']]
    def planners():
        return [a for a in calls() if a[:2] == ['flow', 'plan']]
    launches_before = launches()
    producers_before = producers()
    planners_before = planners()
    result_dirs_before = set((base / 'results').iterdir())
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
    process = subprocess.Popen(demo.switch_command([client_path.resolve(), '--connect', http.url,
        '--project-root', base / 'project', '--environment', 'opam:' + demo.switch_name()]),
        stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
        env=dict(os.environ, TERM='xterm-256color', XDG_STATE_HOME=str(base / 'client-state')))
    os.close(slave)
    transcript = bytearray()
    def drain(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if select.select([master], [], [], .05)[0]:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                transcript.extend(data)
    def keys(value):
        os.write(master, value)
        drain(.25)
    def screen(label, expected, absent=()):
        deadline = time.monotonic() + 10
        while True:
            drain(.1)
            text = fs0_screen.terminal_screen(bytes(transcript))
            # Skins may uppercase headings. Match presentation case-insensitively;
            # exact stage IDs/selections/statuses are independently fenced by HTTP.
            # Checklist keywords share a padded column (WB-001).
            visible = re.sub(r'(?<=\S:) {2,}(?=\S)', ' ', text).casefold()
            if all(s.casefold() in visible for s in expected) and all(s.casefold() not in visible for s in absent):
                (base / ('pty-' + label + '.txt')).write_text(text)
                (base / ('pty-' + label + '.ansi')).write_bytes(transcript)
                return text
            require(process.poll() is None, 'PTY client exited before ' + label)
            require(time.monotonic() < deadline, label + ': current screen mismatch:\n' + text)
    def palette(label):
        for key in (b' ', b'c', b'c'):
            keys(key)
        keys(label.encode())
        drain(.3)
        keys(b'\x1b[A' * 100)
        keys(b'\r')
    def no_launch(label, allow_planning=False):
        require(supervised_jobs() == jobs_before, label + ' created an unsolicited supervisor job')
        require(producers() == producers_before, label + ' dispatched a producer command')
        if not allow_planning:
            require(planners() == planners_before, label + ' dispatched an unsolicited planning command')
        require(set((base / 'results').iterdir()) == result_dirs_before, label + ' allocated an attempt')
        require({field(field(r, 'run'), 'id') for r in field(http.rpc(wait=False), 'runs')} == before_ids,
                label + ' registered a new run')
        semantic = lambda snapshot: [entry for entry in snapshot if entry[0] != 'revision']
        require(semantic(http.rpc(domain='workspace')) == semantic(ws), label + ' changed authoritative workspace state')
    try:
        drain(2)
        overview_screen = screen('full-overview', ['Overview', 'Timing', 'Session', 'Runs',
            'Stage checklist', 'Synthesis', 'Reported cells (agg.): 128',
              'timing', 'no authoritative STA evidence', 'placement', 'routing', 'checks', 'Check drc: pass'])
        require('[1 Overview]'.casefold() in overview_screen.casefold(), 'Overview workspace tab is not active')
        palette('Switch to Timing')
        timing_screen = screen('full-timing', ['Overview', 'Timing', 'Session', 'Runs',
              'Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', '12 paths'])
        require('[4 Timing]'.casefold() in timing_screen.casefold(), 'Timing workspace switch did not apply')
        palette('Inspect timing paths asic/synthetic-reference')
        screen('path-workspace', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', '12 paths'])
        current = http.rpc(domain='workspace')
        require(field(next(c for c in field(current, 'contexts') if field(c, 'id') == context_id), 'selected_run') ==
                field(context_before, 'selected_run'), 'Timing inspection changed Main selection')
        require(field(current, 'tiles') == field(ws, 'tiles') and
                field(current, 'workspaces') == field(ws, 'workspaces'),
                'Ordinary inspection must reuse the existing built-in workspace and tile IDs')
        ws = current
        palette('Zoom focused tile')
        ascending = screen('path-index', ['Timing · Paths', '12 paths',
            'SYNTHETIC setup path clk:reg0 -> reg7', '0.420 ns', 'available'])
        require(ascending.index('hold path clk:reg16 -> reg23') < ascending.index('setup path clk:reg5 -> reg12'),
                'Timing table is not numerically ascending')
        keys(b's')
        descending = screen('path-sorted', ['12 paths', 'value ↓',
            'hold path clk:reg16 -> reg23', 'setup path clk:reg5 -> reg12'])
        require(descending.index('setup path clk:reg5 -> reg12') < descending.index('hold path clk:reg16 -> reg23'),
                'Timing sort did not reverse actual row order')
        keys(b'/')
        keys(b'clk:reg0 -> reg7')
        keys(b'\r')
        screen('path-filtered', ['Timing · Paths', '1 paths', 'Filter: clk:reg0 -> reg7',
             'SYNTHETIC setup path clk:reg0 -> reg7', '0.420 ns'], ['hold path clk:reg16 -> reg23'])
        keys(b'\r')
        palette('Unzoom workspace')
        screen('path-detail', ['Timing · Paths', 'Timing · Selected path', 'Path: SYNTHETIC setup path clk:reg0 -> reg7', 'Slack: 0.420 ns', 'signoff: completed', 'No tool report or binary layout is claimed.'])
        reference_run = field(context_before, 'selected_run')[0]
        details = field(http.rpc(wait=False), 'inspection_details')
        detail = next(d for d in details if field(d, 'run') == reference_run and
                      field(d, 'domain') == 'timing' and field(d, 'stage') == 'signoff' and
                      field(d, 'row_id') == 'synthetic-timing-signoff')
        reference = next(field(r, 'reference') for r in before_runs if field(r, 'run') == reference_run)
        expected_detail = provider.load(Path(field(reference, 'attempt')) / 'inspection-timing-signoff.json')['details']['synthetic-timing-signoff']
        require(field(detail, 'text') == expected_detail and field(detail, 'error') == [],
                'Timing inspector detail differs from exact retained synthetic evidence')
        # Detail is a cooperating pane, so Esc no longer dismisses a full-screen
        # inspector. The filtered path table remains present alongside exact detail.
        screen('path-index-retained', ['Timing · Paths', '1 paths', 'Timing · Provenance'])
        palette('Switch to Overview')
        screen('full-overview-restored', ['Stage checklist', 'Reported cells (agg.): 128', 'no authoritative STA evidence'])
        no_launch('Unzoomed Overview/Timing browsing and timing path inspection')
        # Only after the physical demo proof, zoom the actual checklist for the
        # existing deterministic interaction/launch scenario.
        ws = http.mutate(http.rpc(domain='workspace'), '(Set_zoom (workspace %s) (tile (%s)))' % (workspace, field(checklist, 'id')))
        screen('elaboration-first', ['Stage checklist', '> ? Elaboration: unavailable'])
        keys(b'j')
        screen('initial', ['Stage checklist', '> ✓ Synthesis: completed'],
               ['Session', 'Reported cells (agg.)'])
        # Compact preset hides hints by default. Explicitly enable them for the
        # existing plan-preview/launch guidance assertions in this zoomed scenario.
        palette('Toggle focused tile hints')
        keys(b'\r')
        screen('synthesis-detail', ['Stage ID: synthesis', 'Action: r prepares NEW run through endpoint'])
        keys(b'\x1b')
        screen('synthesis-overview', ['> ✓ Synthesis: completed', 'Placement'], ['Stage ID: synthesis'])
        keys(b'j')
        keys(b'\r')
        screen('j-floorplan', ['Stage ID: floorplan'], ['Stage ID: synthesis'])
        keys(b'\x1b')
        keys(b'k')
        keys(b'\r')
        screen('k-synthesis', ['Stage ID: synthesis'], ['Stage ID: floorplan'])
        keys(b'\x1b')
        for appearance in ('C - Minimal', 'A - Instrument'):
            palette('Appearance: ' + appearance)
            for key in (b' ', b'c', b'c'):
                keys(key)
            keys(('Appearance: ' + appearance).encode())
            screen('appearance-' + appearance[0] + '-active', [appearance + ' [active]'])
            keys(b'\x1b')
            screen('appearance-' + appearance[0], ['Stage checklist', '> ✓ Synthesis: completed'])
        no_launch('Enter/Esc, j/k browsing and restyling')
        # Placement follows synthesis and floorplan, below the preparation row.
        keys(b'j')
        keys(b'j')
        keys(b'\r')
        screen('placement-detail', ['Stage ID: placement', 'endpoint placement'], ['Stage ID: synthesis'])
        keys(b'\x1b')
        keys(b'r')
        drain(1)
        planned = http.rpc()
        require(field(planned, 'preview'), 'Checklist r did not prepare preview')
        preview = field(planned, 'preview')[0]
        selected = field(preview, 'selection')
        require(dict(selected) == dict(flow='synthetic', profile='success', endpoint='placement', assignments=[]),
                'Checklist r did not plan the selected exact stage action')
        screen('placement-preview', ['Matching plan: placement', 'Space c c: Launch'])
        require(len(planners()) == len(planners_before) + 1, 'Explicit checklist r must plan exactly once')
        no_launch('Checklist planning', allow_planning=True)
        # Take identities and launch records immediately before the launch keys,
        # including every earlier HTTP/seeded/cancelled run, not an allowlist.
        require({field(field(r, 'run'), 'id') for r in field(http.rpc(), 'runs')} == before_ids,
                'Run identities changed before launch')
        palette('Launch and view planned run in captured context')
        def new_allocation():
            runs = field(http.rpc(wait=False), 'runs')
            new = [r for r in runs if field(field(r, 'run'), 'id') not in before_ids]
            require(len(new) <= 1, 'PTY launch allocated multiple new runs')
            return new
        allocated = wait_for(new_allocation, 'distinct PTY launch allocation')[0]
        run = field(allocated, 'run')
        require(field(allocated, 'selection') == [selected], 'New PTY run has the wrong exact selection')
        reference = field(allocated, 'reference')
        require(field(reference, 'stream_id') == field(run, 'id'), 'Allocation stream/run mismatch')
        new_launches = launches()[len(launches_before):]
        require(len(new_launches) == 1, 'Expected exactly one provider flow run from PTY Launch')
        argv = new_launches[0]
        for flag, value in [('--flow', 'synthetic'), ('--profile', 'success'), ('--endpoint', 'placement'),
                            ('--expected-plan-identity', field(preview, 'plan_identity'))]:
            require(argv[argv.index(flag) + 1] == value, 'PTY launch argv mismatch: ' + flag)
        def target_selected():
            current = http.rpc(domain='workspace')
            arrangement = next(w for w in field(current, 'workspaces') if field(w, 'id') == workspace)
            require(field(arrangement, 'context') == context_id, 'Launch-and-view changed context identity')
            context = next(c for c in field(current, 'contexts') if field(c, 'id') == context_id)
            return current if field(context, 'selected_run') == [run] else None
        after = wait_for(target_selected, 'Launch-and-view target context selection')
        context_after = next(c for c in field(after, 'contexts') if field(c, 'id') == context_id)
        require(field(context_before, 'selected_run') != [run] and
                int(field(context_after, 'selection_revision')) == int(field(context_before, 'selection_revision')) + 1,
                'Launch-and-view did not advance captured context selection exactly once')
        require([c for c in field(after, 'contexts') if field(c, 'id') != context_id] ==
                [c for c in field(ws, 'contexts') if field(c, 'id') != context_id], 'Launch changed unrelated contexts')
        attempt = Path(field(reference, 'attempt'))
        def observe(expected, cursor):
            http.rpc('(Observe %s)' % sexp(run), wait=False)
            def matches():
                current = next(r for r in field(http.rpc(wait=False), 'runs') if field(r, 'run') == run)
                return current if (int(field(current, 'cursor')) == cursor and
                    [field(s, 'status') for s in field(current, 'stages')] == expected) else None
            return wait_for(matches, 'PTY run observed stages: ' + repr(expected))
        transitions = [observe(['Running', 'Pending', 'Pending'] + ['Not_requested'] * 3, 0)]
        screen('new-run-synthesis-running', ['Stage checklist', 'Synthesis', 'running'])
        expected_steps = [['Completed', 'Running', 'Pending'], ['Completed', 'Completed', 'Running'], ['Completed'] * 3]
        for cursor, expected in enumerate(expected_steps, 1):
            subprocess.run([str(base / 'project/synthetic-flow'), 'advance', str(attempt)],
                           cwd=base / 'project', check=True, stdout=subprocess.PIPE, timeout=5)
            transitions.append(observe(expected + ['Not_requested'] * 3, cursor))
            if cursor < 3:
                screen('new-run-stage-' + str(cursor), [('Floorplan' if cursor == 1 else 'Placement'), 'running'])
        require(field(transitions[-1], 'status') == 'completed', 'PTY placement prefix did not complete')
        http.rpc()
        require(len(launches()) == len(launches_before) + 1, 'Extra provider launches during observation')
        require(len(field(http.rpc(), 'runs')) == len(before_runs) + 1, 'PTY run count did not increase exactly once')
        provider.save(base / 'pty-verified.json', dict(status='passed', before_ids=sorted(before_ids),
            new_run=run, selection=selected, provider_launch=new_launches[0], context_before=context_before,
            context_after=context_after, transitions=transitions, launches_before=len(launches_before),
            launches_after=len(launches())))
        keys(b'q')
        process.wait(timeout=5)
        require(process.returncode == 0, 'PTY client exit')
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        os.close(master)
        (base / 'pty.ansi').write_bytes(transcript)
        # Retain a normally openable full Overview/reference after either success
        # or failure, rather than leaving the sandbox zoomed onto the test run.
        current = http.rpc(domain='workspace')
        current = http.mutate(current, '(Set_zoom (workspace %s) (tile %s))' % (workspace, sexp(original_zoom)))
        context = next(c for c in field(current, 'contexts') if field(c, 'id') == context_id)
        if field(context, 'selected_run') != field(context_before, 'selected_run'):
            current = http.mutate(current, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run %s))' %
                (workspace, context_id, field(context, 'selection_revision'), sexp(field(context_before, 'selected_run'))))
        provider.save(base / 'pty-restored-workspace.json', current)


def integration(base, args):
    discovery = base / 'discovery'
    discovery.mkdir()
    log = (base / 'daemon.log').open('wb')
    daemon = subprocess.Popen(demo.switch_command([args.daemon.resolve(), '--port', '0', '--discovery-dir', discovery,
        '--state-dir', base / 'state']), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    http = None
    try:
        metadata = discovery / 'daemon.sexp'
        wait_for(lambda: metadata.exists() or daemon.poll() is not None, 'daemon discovery')
        require(daemon.poll() is None, 'Daemon exited; see daemon.log')
        url = field(parse(metadata.read_text()), 'endpoint')
        http, runs = demo.seed(base, url, args.preset_export)
        # Explicit seed now schedules FS2 through the normal supervisor. Account
        # for those exact jobs; unrelated Dune/build/discovery jobs remain errors.
        jobs = field(http.raw('/api/v1/snapshot', [['instance_id', http.instance]]), 'jobs')
        require(len(jobs) == 3 and all(field(field(j, 'kind'), 'namespace') == 'simulation' for j in jobs) and
                sorted(field(field(j, 'kind'), 'name') for j in jobs) == ['discover', 'run', 'run'] and
                all(field(j, 'state') == 'Complete' for j in jobs),
                'Fresh seed must create only one FS2 discovery and two completed synthetic process jobs')
        simulation = http.rpc(domain='simulation', wait=False)
        require(len(field(simulation, 'attempts')) == 2 and
                {field(a, 'outcome') for a in field(simulation, 'attempts')} == {'Passed', 'Failed'},
                'Fresh seed FS2 pass/failure attempts')
        presets = demo.workspace_presets(args.preset_export)
        layout = http.rpc(domain='workspace')
        for arrangement in field(layout, 'workspaces'):
            identity = field(arrangement, 'preset')
            if not identity or identity[0] not in presets:
                continue
            expected = [field(t, 'kind') for t in field(presets[identity[0]], 'tiles')]
            visible = [t for t in field(layout, 'tiles') if field(t, 'workspace') == field(arrangement, 'id')
                       and field(t, 'hidden') == 'false']
            require(sorted(field(t, 'kind') for t in visible) == sorted(expected),
                    'Fresh synthetic workspace must match the shared OCaml preset: ' + identity[0])
        snapshot = http.rpc()
        require({field(r, 'status') for r in field(snapshot, 'runs')} == {'completed', 'failed'}, 'Reference and failed outcomes')
        for run in field(snapshot, 'runs'):
            stages = field(run, 'stages')
            require(len(stages) == 6, 'Missing explicit stage observations; build backend stage-plan changes')
            statuses = [field(s, 'status') for s in stages]
            require(statuses == (['Completed'] * 6 if field(run, 'status') == 'completed' else
                                 ['Completed'] * 4 + ['Failed', 'Skipped']), 'Incorrect stage statuses')
        for summary in field(snapshot, 'summaries'):
            require(field(summary, 'cell_count') and field(summary, 'terminal'), 'Synthesis + aggregate finalization import')
            metrics = {field(m, 'key'): m for m in field(field(summary, 'terminal')[0], 'metrics')}
            for key, unit in [('final_standard_cell_area', 'um^2'), ('final_utilization', 'fraction')]:
                require(field(metrics[key], 'availability') == 'available' and field(metrics[key], 'value') and
                        field(metrics[key], 'unit_') == [unit], 'Daemon physical metric projection: ' + key)
        require(len(field(snapshot, 'inspections')) == 8, 'Expected four FS1 indexes per reference run')
        for index in field(snapshot, 'inspections'):
            row = field(index, 'rows')[0]
            http.rpc('(Inspect_detail (run %s) (domain %s) (stage %s) (source_digest %s) (row_id %s))' %
                (sexp(field(index, 'run')), sexp(field(index, 'domain')), sexp(field(index, 'stage')),
                 sexp(field(index, 'source_digest')), sexp(field(row, 'id'))))
        require(field(snapshot, 'artifacts'), 'Artifact catalog empty')
        for artifact in field(snapshot, 'artifacts'):
            http.rpc('(Read_artifact (run %s) (artifact_id %s) (offset 0) (limit 512))' %
                     (sexp(field(artifact, 'run')), sexp(field(artifact, 'id'))))
        selection = '(Plan ((flow synthetic) (profile success) (endpoint placement) (assignments ())))'
        preview = field(http.rpc(selection), 'preview')[0]
        request = '(Run (key synthetic-http-prefix) (preview %s))' % sexp(preview)
        http.rpc(request, wait=False)
        allocated = wait_for(lambda: [r for r in field(http.rpc(wait=False), 'runs')
            if field(r, 'selection') and field(field(r, 'selection')[0], 'endpoint') == 'placement'], 'HTTP allocation')[0]
        attempt = Path(field(field(allocated, 'reference'), 'attempt'))
        run = field(allocated, 'run')
        require(provider.load(attempt / 'observation.json')['writer_active'], 'Manual run not active')
        for _ in range(3):
            subprocess.run([str(base / 'project/synthetic-flow'), 'advance', str(attempt)],
                           cwd=base / 'project', check=True, stdout=subprocess.PIPE, timeout=5)
        http.rpc()
        snapshot = http.rpc('(Observe %s)' % sexp(run))
        observed = next(r for r in field(snapshot, 'runs') if field(r, 'run') == run)
        require(field(observed, 'status') == 'completed', 'HTTP prefix did not complete')
        require([field(s, 'status') for s in field(observed, 'stages')] ==
                ['Completed'] * 3 + ['Not_requested'] * 3, 'HTTP prefix stages')
        duplicate = http.rpc(request)
        require(len(field(duplicate, 'runs')) == 3, 'Idempotency duplicate allocated a run')
        # Keep the PTY run manual so every requested stage transition is observable.
        if args.pty:
            pty_check(base, args.client, http)
            http.rpc()
        # Explicit daemon cancellation is last: cancelled tasks may retain failed operation diagnostics.
        provider.save(base / 'project/synthetic-settings.json', dict(manual=True, delay_seconds=.05, max_run_seconds=120))
        preview = field(http.rpc(selection), 'preview')[0]
        before_cancel_ids = {field(field(r, 'run'), 'id') for r in field(http.rpc(), 'runs')}
        http.rpc('(Run (key synthetic-http-cancel) (preview %s))' % sexp(preview), wait=False)
        cancelling = wait_for(lambda: [r for r in field(http.rpc(wait=False), 'runs')
            if field(field(r, 'run'), 'id') not in before_cancel_ids], 'distinct cancel allocation')[0]
        cancelled_run = field(cancelling, 'run')
        def producer_calls():
            return [entry['argv'] for entry in
                    (json.loads(line) for line in (base / 'project/provider-calls.jsonl').read_text().splitlines())
                    if entry['argv'][:2] == ['flow', 'run'] or entry['argv'][:1] == ['finalize']]
        producers_before_cancel = producer_calls()
        http.rpc('(Cancel "run:synthetic-http-cancel")', wait=False)
        attempt = Path(field(field(cancelling, 'reference'), 'attempt'))
        wait_for(lambda: provider.load(attempt / 'observation.json')['state']['outcome'], 'cancelled outcome')
        require(provider.load(attempt / 'observation.json')['state']['outcome']['status'] == 'cancelled', 'Cancel did not publish cancelled')
        # Cancel is nonblocking and stops the automatic reader as well as the
        # launcher. Wait for both lifecycle tasks to release their keys before
        # explicitly reacquiring a read-only observer. Failed cancellation task
        # diagnostics are retained, so use non-waiting Get rather than the
        # convenience client's global "all operations succeeded" assertion.
        lifecycle_keys = {'run:synthetic-http-cancel', 'observe:' + field(cancelled_run, 'id')}
        def lifecycle_finalized():
            current = http.rpc(wait=False)
            operations = [o for o in field(current, 'operations') if field(o, 'key') in lifecycle_keys]
            return current if (any(field(o, 'key') == 'run:synthetic-http-cancel' for o in operations) and
                all(field(o, 'state') not in ('pending', 'executing') for o in operations)) else None
        stopped = wait_for(lifecycle_finalized, 'cancel launcher/observer lifecycle finalized', seconds=25)
        http.rpc('(Observe %s)' % sexp(cancelled_run), wait=False)
        def cancellation_reconciled():
            current = http.rpc(wait=False)
            observed = next(r for r in field(current, 'runs') if field(r, 'run') == cancelled_run)
            observers = [o for o in field(current, 'operations')
                         if field(o, 'key') == 'observe:' + field(cancelled_run, 'id')]
            return current if (field(observed, 'status') == 'cancelled' and field(observed, 'error') == [] and
                [field(s, 'status') for s in field(observed, 'stages')] ==
                ['Cancelled'] * 3 + ['Not_requested'] * 3 and observers and
                all(field(o, 'state') == 'completed' for o in observers)) else None
        reconciled = wait_for(cancellation_reconciled, 'explicit Observe reconciles cancelled daemon stages')
        require(producer_calls() == producers_before_cancel, 'Cancellation reconciliation dispatched another producer')
        require({field(field(r, 'run'), 'id') for r in field(reconciled, 'runs')} ==
                before_cancel_ids | {field(cancelled_run, 'id')}, 'Cancellation reconciliation allocated another run')
        provider.save(base / 'cancellation-verified.json', dict(status='passed', run=cancelled_run,
            lifecycle_finalized=stopped, reconciled=reconciled, producer_calls=producers_before_cancel,
            reconciliation='Explicit read-only Observe after launcher and automatic reader finalized'))
        provider.save(base / 'integration-verified.json', dict(status='passed', synthetic=True, url=url, pty=args.pty))
    finally:
        if http:
            provider.save(base / 'test-http.json', http.history)
        try:
            os.killpg(daemon.pid, signal.SIGTERM)
            daemon.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            if daemon.poll() is None:
                os.killpg(daemon.pid, signal.SIGKILL)
                daemon.wait(timeout=5)
        log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true', help='provider-only bounded checks, no daemon/client')
    parser.add_argument('--pty', action='store_true', help='also exercise real checklist j/k/r and launch palette')
    parser.add_argument('--evidence', type=Path, help='NEW directory, default /tmp/opencode/synthetic-flow-*')
    parser.add_argument('--daemon', type=Path, default=REPO / '_build/default/daemon/main.exe')
    parser.add_argument('--client', type=Path, default=REPO / '_build/default/terminal/main.exe')
    parser.add_argument('--preset-export', type=Path, help='built OCaml preset exporter; also verify export with --smoke')
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Synthetic acceptance wall-clock budget exhausted')))
    signal.alarm(args.timeout)
    base = demo.prepare(args.evidence, manual=True, delay=.05)
    print('SYNTHETIC test evidence: ' + str(base), flush=True)
    smoke(base)
    if args.preset_export:
        presets = demo.workspace_presets(args.preset_export)
        require(set(presets) == {'overview', 'timing', 'testing', 'waveforms'}, 'Shared stable exported preset identities')
        for definition in presets.values():
            tiles = field(definition, 'tiles')
            require(len({field(t, 'kind') for t in tiles}) == len(tiles), 'Unique default tile kinds')
            navigation = next(t for t in tiles if field(t, 'kind') == 'workspace-tabs')
            require(field(field(navigation, 'presentation'), 'title') == ['false'], 'Quiet navigation default')
        # Exercise the real consumer independently of daemon availability. Names
        # deliberately disagree with preset IDs; custom workspaces stay custom.
        class Recorder:
            def __init__(self):
                self.mutations = []
            def mutate(self, snapshot, mutation):
                self.mutations.append(parse(mutation))
                return snapshot
        recorder = Recorder()
        snapshot = [['workspaces', [
            [['id', 'renamed'], ['name', 'Timing'], ['preset', ['overview']]],
            [['id', 'custom'], ['name', 'Overview'], ['preset', []]]]]]
        demo.apply_workspace_presets(recorder, snapshot, presets)
        require(len(recorder.mutations) == 1, 'Explicit custom workspace must not infer by name')
        mutation = recorder.mutations[0]
        require(mutation[0] == 'Apply_preset' and field(mutation[1:], 'preset') == 'overview',
                'Renamed workspace must apply stable preset identity')
        require(field(mutation[1:], 'tiles') == [[field(t, 'kind'), field(t, 'geometry')]
                for t in field(presets['overview'], 'tiles')], 'Seed specs must be exact OCaml export')
        provider.save(base / 'preset-export-verified.json', dict(status='passed', ids=sorted(presets)))
    if not args.smoke:
        integration(base, args)
    print('SYNTHETIC ' + ('provider smoke' if args.smoke else 'HTTP' + (' + PTY' if args.pty else '')) + ': passed')


if __name__ == '__main__':
    main()
