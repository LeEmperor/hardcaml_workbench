#!/usr/bin/env python3
"""Private real terminal-result HTTP/PTY acceptance; existing binaries, no EDA.

--physical-evidence ROOT consumes ROOT/workbench-inputs.json from the parent-run
run-fs1-physical.py. --failed-execution PHYSICAL_JSON instead adopts a failed
implementation's original allocation and checks retained checkpoint metrics.
No allocation is fabricated and no Run/finalize/build/Git command is requested.
All outputs and owned children are private; evidence survives under /tmp/opencode.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('metrics', Path(__file__).with_name('test-fs1-metrics.py'))
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
fs0, dashboard = metrics.fs0, metrics.dashboard
field, record, require = fs0.field, fs0.record, fs0.require


def load(path):
    return json.loads(Path(path).read_text())


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Session(fs0.Session):
    def start(self):
        # The shared helper starts a directly owned daemon; give it its own
        # process group as well, so interrupted report children are owned too.
        popen = subprocess.Popen

        def owned(*args, **kwargs):
            kwargs.setdefault('start_new_session', True)
            return popen(*args, **kwargs)

        subprocess.Popen = owned
        try:
            super().start()
        finally:
            subprocess.Popen = popen

    def stop(self):
        if self.process:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            super().stop()
        finally:
            if self.process:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def private_project(args, receipt, inputs):
    root = args.evidence / 'project'
    root.mkdir()
    (args.evidence / 'state').mkdir()
    (root / 'dune-project').write_text('(lang dune 3.17)\n(name fs1_terminal_results_acceptance)\n')
    config = metrics.parse((args.example_root / 'hardcaml-workbench-asic.sexp').read_text())
    allocation = receipt['allocation']
    provider = receipt.get('config', {}).get('provider', field(config, 'provider_executable'))
    execution = receipt['execution_file']
    attempt = inputs['operation_attempt'] if inputs else None
    guard = args.evidence / 'read-only-provider'
    # Observation inspect/read-updates are read-only public queries used internally
    # by Load_summary/Inspect_finalization. The guard rejects producer commands.
    guard.write_text('#!' + sys.executable + '\n' +
        'import json, pathlib, subprocess, sys, time\n' +
        'base = pathlib.Path(' + repr(str(args.evidence)) + ')\n' +
        'a = sys.argv[1:]\n' +
        'ok = a == ["--version", "--json"] or a == ["report", ' + repr(execution) + ', "--json"]\n' +
        'ok = ok or a == ["observation", "inspect", ' + repr(allocation['attempt']) + ', "--json"]\n' +
        'ok = ok or (len(a) == 8 and a[:3] == ["observation", "read-updates", ' + repr(allocation['attempt']) + '] and a[3:6] == ["--stream-id", ' + repr(allocation['stream_id']) + ', "--after"] and a[6].isdigit() and a[7:] == ["--json"])\n' +
        'ok = ok or a == ["finalization-inspect", ' + repr(attempt) + ', "--json"]\n' +
        'with (base / "provider-calls.jsonl").open("a") as f: f.write(json.dumps(dict(argv=a, allowed=ok, time=time.time())) + "\\n")\n' +
        'if not ok: sys.exit("FS1 read-only guard rejected command")\n' +
        'p = subprocess.run([' + repr(provider) + '] + a, capture_output=True)\n' +
        'name = "query-" + str(time.time_ns())\n' +
        '(base / (name + ".stdout")).write_bytes(p.stdout)\n' +
        '(base / (name + ".stderr")).write_bytes(p.stderr)\n' +
        '(base / (name + ".json")).write_text(json.dumps(dict(argv=a, returncode=p.returncode)))\n' +
        'if a[0] == "report": (base / "actual-stage-report.json").write_bytes(p.stdout)\n' +
        'if a[0] == "finalization-inspect": (base / "actual-operation.json").write_bytes(p.stdout)\n' +
        'sys.stdout.buffer.write(p.stdout)\nsys.stderr.buffer.write(p.stderr)\nsys.exit(p.returncode)\n')
    guard.chmod(0o700)
    # No project flow command is needed to adopt an existing allocation. Fail
    # closed even if a future UI regression tries to launch through the project.
    deny = args.evidence / 'no-project-execution'
    deny.write_text('#!' + sys.executable + '\nimport sys\nsys.exit("FS1 acceptance forbids project execution")\n')
    deny.chmod(0o700)
    config = metrics.put(config, 'provider_executable', str(guard))
    config = metrics.put(config, 'project_executable', str(deny))
    config = metrics.put(config, 'results_root', receipt['config']['results_root'])
    (root / 'hardcaml-workbench-asic.sexp').write_text(fs0.sexp(config) + '\n')
    return root, Path(provider)


METRIC_SPECS = {
    'setup_slack': ('metrics', 'Setup slack', 'ns', True, False),
    'hold_slack': ('metrics', 'Hold slack', 'ns', True, False),
    'mapped_area': ('metrics', 'Mapped cell area', 'um^2', False, False),
    'sequential_area': ('metrics', 'Sequential cell area', 'um^2', False, False),
    'mapped_cells': ('metrics', 'Mapped cells', 'cells', False, True),
    'final_standard_cell_area': ('metrics', 'Final standard-cell area', 'um^2', False, False),
    'final_utilization': ('metrics', 'Final utilization', 'fraction', False, False),
    'unmapped_instances': ('synthesis_checks', 'Unmapped instances', 'count', False, True),
    'synthesis_errors': ('synthesis_checks', 'Synthesis errors', 'count', False, True),
    'inferred_latches': ('synthesis_checks', 'Inferred latches', 'count', False, True),
}


def verify_declared_clock(check, metric, report, operation):
    """Independent oracle from exact historical bytes, never current config/results."""
    m = record(metric)
    reference = report['methodology'].get('reference')
    reference_fields = reference if isinstance(reference, dict) else {}
    path, expected_hash = reference_fields.get('snapshot_path'), reference_fields.get('snapshot_sha256')
    port = value = None
    if path is None and expected_hash is None:
        source = dict(reason='historical_snapshot_not_recorded', reference=reference)
    else:
        check(isinstance(path, str) and Path(path).is_absolute() and isinstance(expected_hash, str) and bool(expected_hash),
              'Declared clock has complete exact historical snapshot path/hash')
        check(sha256(path) == expected_hash, 'Declared clock raw methodology-plan SHA-256 verified independently')
        snapshot = load(path)
        check(snapshot.get('contract') == 'hardcaml-asic.methodology-plan' and snapshot.get('schema_version') == 1,
              'Clock snapshot is the historical methodology-plan contract')
        plan, bundle = snapshot['plan_identity'], snapshot['bundle_identity']
        check(bool(plan) and bool(bundle) and
              report['methodology']['plan_identity'] == reference_fields['plan_identity'] == plan and
              report['methodology']['bundle_identity'] == reference_fields['bundle_identity'] == bundle and
              reference_fields['attempt_id'] == report['execution']['attempt_id'] == operation['execution']['attempt_id'] and
              operation['evidence_context']['build_identity'] == bundle,
              'Hashed clock plan/bundle bound to exact reported execution and operation')
        configuration_bytes = snapshot.get('configuration_bytes')
        try:
            configuration = json.loads(configuration_bytes)
        except (TypeError, ValueError):
            configuration = {}
        if not isinstance(configuration, dict):
            configuration = {}
        raw_port, period = configuration.get('CLOCK_PORT'), configuration.get('CLOCK_PERIOD')
        if isinstance(raw_port, str) and raw_port.strip():
            port = raw_port
        if port is not None and isinstance(period, (int, float)) and not isinstance(period, bool) and math.isfinite(period) and period > 0:
            value = period
        source = dict(kind='declared_constraint', snapshot_path=path, snapshot_sha256=expected_hash,
                      plan_identity=plan, bundle_identity=bundle, reference=reference,
                      configuration_bytes=configuration_bytes,
                      fields=dict(CLOCK_PORT=raw_port, CLOCK_PERIOD=period),
                      resolved_settings=snapshot.get('resolved_settings'),
                      reason=None if value is not None else 'invalid_or_missing_declared_clock')
    check(m['key'] == 'declared_clock_period' and m['label'] == ('Declared clock ' + port + ' period' if port is not None else 'Declared clock period') and
          m['unit_'] == ['ns'], 'Exact declared-clock key, port label and ns unit')
    check((len(m['value']) == 1 and float(m['value'][0]) == value and m['availability'] == 'available') if value is not None else
          (m['value'] == [] and m['availability'] == 'unavailable'),
          'Declared period equals hashed CLOCK_PERIOD or remains explicitly unavailable')
    check(len(m['source']) == 1 and json.loads(m['source'][0]) == source,
          'Complete exact declared-clock provenance, raw configuration bytes and source SHA preserved')


def verify_terminal(check, summary, inputs, operation, normalized, report, expected_acceptance):
    terminal = field(summary, 'terminal')
    check(len(terminal) == 1, 'Explicit inspection imports one terminal result')
    terminal = terminal[0]
    result_ref = operation['results']
    check(field(terminal, 'results_file') == result_ref['path'] and
          field(terminal, 'results_digest') == sha256(result_ref['path']) == result_ref['sha256'],
          'Terminal results exact path and SHA-256 match retained normalized bytes')
    check(operation['execution']['path'] == inputs['execution_file'] and
          operation['execution']['sha256'] == sha256(inputs['execution_file']), 'Exact execution bytes match operation hash')
    check(field(terminal, 'attempt') == inputs['operation_attempt'], 'Original finalization attempt retained exactly')
    for name, expected in (
        ('operation_status', operation['status']),
        ('physical_completion', report['completion']['physical']),
        ('acceptance', operation['acceptance']),
        ('timing_goal', normalized.get('timing_goal') if normalized.get('timing_goal') in ('pass', 'fail', 'unknown') else 'unknown'),
    ):
        check(field(terminal, name) == expected, 'Independent reported terminal fact: ' + name)
    expected_postcheck = {'not_evaluated': 'not_evaluated', 'pass': 'completed', 'fail': 'failed'}[expected_acceptance]
    check(operation['acceptance'] == expected_acceptance and operation['external_postcheck'] == expected_postcheck,
          'Operation acceptance/external-postcheck match explicit expected verdict: ' + expected_acceptance)
    check(inputs['acceptance'] == operation['acceptance'] and inputs['external_postcheck'] == operation['external_postcheck'],
          'Workbench input manifest matches exact operation verdicts')
    check(operation['status'] in ('completed', 'failed', 'interrupted') and
          (operation['status'] == 'completed') == (operation['exit_code'] == 0),
          'Operation status and exit code remain independent reported terminal facts')
    if expected_acceptance != 'not_evaluated':
        check(operation['request'].get('accept') is True, 'Evaluated acceptance was explicitly requested in the exact receipt')
    if expected_acceptance == 'pass':
        check(operation['status'] == 'completed' and operation['exit_code'] == 0,
              'Acceptance pass is backed by completed operation and external postcheck')
    check(report['acceptance'] == 'not_evaluated' and field(summary, 'acceptance') == report['acceptance'] and field(summary, 'timing') == [],
          'Stage summary retains report acceptance not_evaluated, independently of terminal verdict; no legacy timing inferred')
    actual = {field(m, 'key'): record(m) for m in field(terminal, 'metrics')}
    expected_keys = {key for key, (group, *_rest) in METRIC_SPECS.items() if key in normalized.get(group, {})}
    expected_keys.add('declared_clock_period')
    check(set(actual) == expected_keys and len(actual) == len(field(terminal, 'metrics')),
          'Exact supplied normalized metrics plus one historical declared-clock metric')
    check(field(field(terminal, 'metrics')[-1], 'key') == 'declared_clock_period', 'Declared clock metric is always appended')
    verify_declared_clock(check, next(m for m in field(terminal, 'metrics') if field(m, 'key') == 'declared_clock_period'), report, operation)

    def provenance(source, group, key, supplied):
        check(len(source) == 1, 'Full source present: ' + group + '.' + key)
        source = json.loads(source[0])
        path = supplied.get('source')
        path = path if isinstance(path, str) and path else None
        resolved = (str(Path(inputs['operation_attempt']) / path) if not Path(path).is_absolute() else path) if path else None
        check(source == dict(attempt=inputs['operation_attempt'], operation=str(Path(inputs['operation_attempt']) / 'operation.json'),
                             results_path=result_ref['path'], results_sha256=result_ref['sha256'],
                             field=group + '.' + key, resolved_source=resolved, supplied=supplied),
              'Exact field/hash/full supplied provenance: ' + group + '.' + key)

    for key, m in actual.items():
        if key == 'declared_clock_period':
            continue  # Independently validated against the hashed plan above.
        group, label, unit, signed, integral = METRIC_SPECS[key]
        raw = normalized[group][key]
        value = raw.get('value')
        valid = (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                 and (signed or value >= 0) and (not integral or int(value) == value)
                 and raw.get('unit') == unit and 'unavailable_reason' in raw and raw['unavailable_reason'] is None)
        check(m['label'] == label and m['unit_'] == ([raw['unit']] if isinstance(raw.get('unit'), str) else []), 'Exact label/unit: ' + key)
        check(m['availability'] == ('available' if valid else 'unavailable') and
              (len(m['value']) == 1 and float(m['value'][0]) == value if valid else m['value'] == []),
              'Exact signed value or explicit unavailable: ' + key)
        provenance(m['source'], group, key, raw)
    check(any(k in actual and actual[k]['availability'] == 'available' for k in ('setup_slack', 'hold_slack')),
          'Real normalized evidence supplies available signed timing')
    checks = {field(c, 'name'): record(c) for c in field(terminal, 'checks')}
    check(set(checks) == {'drc', 'lvs', 'antenna'}, 'All three independently reported check statuses exposed')
    for key, c in checks.items():
        supplied = normalized.get('checks', {}).get(key)
        status = supplied.get('status') if isinstance(supplied, dict) else None
        check(c['status'] == (status if status in ('pass', 'fail', 'unknown') else 'unknown'), 'Exact check status, no zero-to-pass inference: ' + key)
        reason = supplied.get('reason') if isinstance(supplied, dict) else 'not_recorded'
        check(c['reason'] == ([reason] if isinstance(reason, str) else []), 'Exact check reason: ' + key)
        if supplied is not None:
            provenance(c['source'], 'checks', key, supplied)
        else:
            check(c['source'] == [], 'Missing check has no invented provenance')
    check(json.loads(field(terminal, 'evidence')) == dict(operation=operation, results=normalized),
          'Complete operation/results evidence preserved without elision')
    return terminal


def metric_text(metric):
    m = record(metric)
    value = ('%g' % float(m['value'][0]) + (' ' + m['unit_'][0] if m['unit_'] else ' (unit not reported)')) if m['value'] else 'unavailable'
    return '%s: %s [%s]' % (m['label'], value, m['availability'])


def compact_screen(text):
    return re.sub(r'\s+', '', text.replace('|', ''))


def fully_visible(value, pages):
    # Long historical configuration sources can span more than one viewport.
    # Every contiguous chunk must be visible in an actual overlapping screenshot.
    value = compact_screen(value)
    screens = [compact_screen(p) for p in pages]
    return all(any(value[i:i + 256] in page for page in screens) for i in range(0, len(value), 256))


def exercise(args):
    inputs = None
    if args.physical_evidence:
        input_file = args.physical_evidence / 'workbench-inputs.json'
        require(input_file.is_file(), 'Physical evidence is not ready: missing ' + str(input_file))
        inputs = load(input_file)
        if inputs.get('physical_receipt'):
            receipt_path = Path(inputs['physical_receipt'])
        else:
            # Acceptance-only specimens explicitly reference the original physical
            # evidence root; never substitute the newest execution/operation.
            receipt_path = Path(inputs['physical_evidence']) / 'physical.json'
    else:
        receipt_path = args.failed_execution
    receipt = load(receipt_path)
    allocation = receipt['allocation']
    require(Path(allocation['attempt']).is_absolute() and allocation['stream_id'], 'Missing original public allocation')
    require(Path(receipt['execution_file']).is_file(), 'Missing exact retained execution file')
    if inputs:
        require(inputs['allocation'] == allocation and inputs['execution_file'] == receipt['execution_file'], 'Inputs/physical allocation mismatch')
    else:
        require(receipt.get('outcome', {}).get('status') == 'failed' and not receipt.get('execution_completed'), 'Failed mode needs a real failed execution receipt')
    watched = [receipt_path.parent, Path(receipt['config']['results_root']),
               args.example_root / 'hardcaml-workbench-asic.sexp', Path(receipt['config']['provider'])]
    if inputs:
        watched += [args.physical_evidence, Path(inputs['operation']), Path(inputs['operation_attempt']), Path(inputs['results']['path'])]
    before = dashboard.inventory(watched)
    (args.evidence / 'files-before.json').write_text(json.dumps(before, indent=2))
    outcome = dict(status='failed', mode='terminal' if inputs else 'failed-execution',
                   expected_acceptance=args.expected_acceptance, checks=[])
    session = terminal = None

    def check(ok, message):
        outcome['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def calls():
        p = args.evidence / 'provider-calls.jsonl'
        return p.read_bytes() if p.exists() else b''

    def find_summary(snapshot):
        return next(s for s in field(snapshot, 'summaries') if field(s, 'run') == run)

    def mutate(text):
        return session.mutate(session.rpc('workspace'), text)

    def select(selected):
        ws = session.rpc('workspace')
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(demo, 'context'))
        return session.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run %s))' % (
            field(demo, 'id'), field(context, 'id'), field(context, 'selection_revision'),
            '()' if selected is None else '(' + fs0.sexp(selected) + ')'))

    def scroll_pages(label, limit=200):
        pages = [terminal.capture(label + '-000')]
        for i in range(1, limit + 1):
            # Overlapping pages retain full evidence coverage without reparsing
            # the growing ANSI transcript once for every single evidence line.
            terminal.key(b'j' * 20)
            page = terminal.capture(label + '-%03d' % i)
            if page == pages[-1]:
                terminal.key(b'j' * 100)
                bottom = terminal.capture(label + '-overscroll')
                terminal.key(b'k')
                reverse = terminal.capture(label + '-reverse')
                check(bottom != reverse, 'First reverse key moves immediately after bottom overscroll: ' + label)
                terminal.key(b'j')
                return pages
            pages.append(page)
        raise AssertionError(label + ': scroll did not reach end within budget')

    try:
        root, _provider = private_project(args, receipt, inputs)
        session = Session(args, args.evidence, root)
        metrics.guard_generic_builds(session)
        session.start()
        metrics.no_generic_jobs(session, 'initial daemon')
        check(field(session.rpc('asic'), 'runs') == [], 'Private daemon starts without canonical registered runs')
        reference = [['attempt', allocation['attempt']], ['stream_id', allocation['stream_id']]]
        snap = session.rpc('asic', '(Register %s)' % fs0.sexp(reference), wait=True)
        registered = field(snap, 'runs')
        check(len(registered) == 1 and field(registered[0], 'reference') == reference, 'Register adopts exact original allocation, not a new execution')
        run = field(registered[0], 'run')
        if inputs:
            operation = load(inputs['operation'])
            normalized = load(inputs['results']['path'])
            check(sha256(inputs['results']['path']) == inputs['results']['sha256'] == operation['results']['sha256'], 'Parent input normalized-results hash verified')
            snap = session.rpc('asic', '(Inspect_finalization (run %s) (attempt %s))' % (fs0.sexp(run), fs0.sexp(inputs['operation_attempt'])), wait=True)
        else:
            snap = session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True)
        summary = find_summary(snap)
        report = load(args.evidence / 'actual-stage-report.json')
        check(field(summary, 'execution_file') == receipt['execution_file'], 'Exact original execution file adopted')
        check(field(summary, 'freshness') == 'Validated', 'Initial read-only import validates actual evidence')
        check(field(summary, 'completion') == report['execution']['status'], 'Execution failure/completion remains the reported status')
        synthesis = metrics.synthesis_checkpoint(report)
        raw = {m['raw_key']: m for m in synthesis['metrics'] if m['raw_key'] in metrics.KNOWN}
        projected = {field(m, 'key'): m for m in field(summary, 'metrics')}
        check(set(projected) == set(raw), 'Synthesis metrics use explicit reference.boundary=synthesis in both physical modes')
        for key, m in projected.items():
            r = raw[key]
            check(json.loads(field(m, 'source')[0]) == r['source'] and
                  field(m, 'availability') == r['availability'] and
                  (float(field(m, 'value')[0]) == r['value'] if field(m, 'value') else r['availability'] != 'available'),
                  'Exact synthesis-boundary metric/value/source: ' + key)
        count = raw['design__instance__count']['value']
        check(int(field(summary, 'cell_count')[0]) == count == 673,
              'Real balanced specimen synthesis total is 673, never routing/signoff count 1042')
        if inputs:
            imported = verify_terminal(check, summary, inputs, operation, normalized, report, args.expected_acceptance)
        else:
            check(field(summary, 'completion') == 'failed' and field(summary, 'terminal') == [], 'Failed signoff remains failed with no finalization result')
            check(field(summary, 'acceptance') == 'not_evaluated' and field(summary, 'timing') == [], 'Failed implementation has no invented acceptance/timing')
            check(any(c['reference']['boundary'] == 'synthesis' for c in report['checkpoints']) and
                  not any(c['reference']['boundary'] == 'signoff' for c in report['checkpoints']), 'Earlier synthesis retained; no completed signoff checkpoint')
            check(bool(projected), 'Earlier accumulated synthesis resource/diagnostic metrics remain available')
        ws = session.rpc('workspace')
        ws = session.mutate(ws, '(Create_workspace (window %s) (name "FS1 Terminal Results Private") (context %s))' % (
            field(field(ws, 'windows')[0], 'id'), field(ws, 'main_context')))
        demo = field(ws, 'workspaces')[-1]
        kinds = ['timing', 'timing', 'placement', 'checks', 'cts', 'routing', 'finalization'] if inputs else ['synthesis', 'synthesis', 'finalization']
        tiles = []
        for kind in kinds:
            ws = mutate('(Create_tile (workspace %s) (kind %s) (geometry ((x 0) (y 0) (width 56) (height 14))))' % (field(demo, 'id'), kind))
            tiles.append(field(field(ws, 'tiles')[-1], 'id'))
        select(run)
        mutate('(Set_zoom (workspace %s) (tile (%s)))' % (field(demo, 'id'), tiles[0]))
        terminal = metrics.Terminal(session)
        terminal.palette('Switch to FS1 Terminal Results Private')
        if inputs:
            acceptance_line = 'Acceptance (reported): ' + operation['acceptance']
            timing_lines = [metric_text(m) for m in field(imported, 'metrics') if field(m, 'key') in ('setup_slack', 'hold_slack')]
            terminal.capture('01-timing', ['Terminal timing (aggregate)', 'Signed slack; units as reported', acceptance_line] + timing_lines)
            # Exercise the real command and argument form, not just the RPC path.
            terminal.palette('Inspect finalization for asic/' + field(run, 'id') + ' (enter exact attempt)')
            terminal.capture('02-exact-reference-form', ['INSPECT FINALIZATION', 'exact'])
            terminal.key('é界'.encode())
            terminal.capture('02-unicode-input', ['é界'])
            terminal.key(b'\x7f\x7f')
            terminal.key(b'\x1b[200~' + inputs['operation_attempt'].encode() + b'\x1b[201~')
            terminal.capture('02-exact-reference-input', ['INSPECT FINALIZATION'])
            def inspection_count():
                return sum(json.loads(line)['argv'][0] == 'finalization-inspect' for line in calls().splitlines())

            previous_inspections = inspection_count()
            terminal.key(b'\r')
            deadline = time.monotonic() + args.outer_timeout
            while inspection_count() == previous_inspections:
                require(time.monotonic() < deadline, 'PTY exact-reference form did not dispatch finalization inspection')
                terminal.drain(.2)
            check(inspection_count() == previous_inspections + 1, 'Actual palette form dispatched one exact-reference inspection')
            summary = find_summary(session.rpc('asic', wait=True))
            imported = verify_terminal(check, summary, inputs, operation, normalized, report, args.expected_acceptance)
            terminal.capture('03-imported-timing', ['Terminal timing (aggregate)', 'Validated', acceptance_line] + timing_lines)
            terminal.key(b'\r')
            pages = scroll_pages('04-enter-details')
            check(len(pages) > 1, 'Enter opens scrollable terminal detail/evidence')
            compact = lambda s: re.sub(r'\s+', '', s.replace('|', ''))
            screens = [compact(p) for p in pages]
            for value in (field(imported, 'attempt'), field(imported, 'results_file'), field(imported, 'results_digest'), receipt['execution_file']):
                check(any(compact(value) in p for p in screens), 'PTY detail exposes complete exact reference: ' + value)
            for m in field(imported, 'metrics'):
                check(fully_visible(field(m, 'source')[0], pages), 'PTY exposes every chunk of full metric provenance: ' + field(m, 'key'))
            full_evidence = compact(field(imported, 'evidence'))
            check(all(any(full_evidence[i:i + 256] in page for page in screens)
                      for i in range(0, len(full_evidence), 256)),
                  'Every character of full terminal evidence is reachable through overlapping PTY scroll pages')
            terminal.key(b'\x1b')
            terminal.capture('05-escape-overview', ['Terminal timing (aggregate)'], ['Finalization attempt (exact):'])
            terminal.key(b'e')
            terminal.capture('06-e-details', ['Finalization attempt (exact):'])
            terminal.key(b'\x1b')
        else:
            terminal.capture('01-failed-summary', ['Cell count:'])
            terminal.key(b'e')
            terminal.capture('01-failed-evidence', ['Completion (reported): failed', 'Acceptance (reported): not_evaluated'])
            terminal.key(b'\x1b')
            terminal.key(b'm')
            terminal.capture('02-failed-metrics', ['Synthesis metrics', 'Mapped cells:', 'Mapped cell area:', 'Lint warnings:'])
        warm = calls()
        # Tile-local detail state and pin resolution are independent of context.
        if inputs:
            terminal.key(b'e')
            terminal.capture('06-pinned-detail-state', ['Finalization attempt (exact):'])
        mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (tiles[0], fs0.sexp(run)))
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.capture('07-independent-follow-tile', ['Terminal timing (aggregate)' if inputs else 'Cell count:'],
                         ['Finalization attempt (exact):', 'Synthesis metrics |'])
        select(None)
        terminal.capture('08-follow-cleared', ['No run selected'], ['Setup slack:', 'Mapped cells:'])
        # Focus traversal is forward-only. Cycle through the remaining private
        # tiles to return to the first, pinned tile.
        terminal.palette('Unzoom workspace')
        for _ in range(len(kinds) - 1):
            terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.capture('09-independent-pin',
                         (['Terminal timing (aggregate)', 'Finalization attempt (exact):'] if inputs else ['Synthesis metrics']) + [field(run, 'id')])
        select(run)
        if inputs:
            # Visit each supported terminal tile using real focus/zoom commands.
            terminal.palette('Unzoom workspace')
            terminal.key(b'\t')
            for index, (kind, expected) in enumerate([
                ('placement', ['Terminal physical resources (aggregate)', 'not placement-stage evidence', 'no percent conversion']),
                ('checks', ['Terminal checks (reported statuses)', 'independent of acceptance and physical completion']),
                ('cts', ['Declared clocks (recorded configuration)', 'Recorded methodology configuration, not measured CTS',
                         'CTS tree / skew / clock coverage: unsupported / not reported']),
                ('routing', ['Routing-stage detail: unsupported / not reported']),
                ('finalization', ['Finalization (imported terminal result)', acceptance_line]),
            ]):
                terminal.key(b'\t')
                terminal.palette('Zoom focused tile')
                expected += [acceptance_line, 'Operation status (reported): ' + operation['status']]
                if kind == 'checks':
                    expected += [field(c, 'name') + ': ' + field(c, 'status') for c in field(imported, 'checks')]
                elif kind == 'placement':
                    expected += [metric_text(m) for m in field(imported, 'metrics') if field(m, 'key') in ('final_standard_cell_area', 'final_utilization')]
                elif kind == 'cts':
                    clock = next(m for m in field(imported, 'metrics') if field(m, 'key') == 'declared_clock_period')
                    check(field(clock, 'availability') == 'available', 'Real physical specimen has a recorded available declared clock')
                    expected += [metric_text(clock)]
                terminal.capture('10-%02d-%s' % (index, kind), expected)
                if kind == 'cts':
                    terminal.key(b'e')
                    clock_pages = [terminal.capture('10-cts-details-000', ['Finalization attempt (exact):'])]
                    clock_source = field(clock, 'source')[0]
                    for page_index in range(1, 201):
                        if fully_visible(clock_source, clock_pages) and any('Key: declared_clock_period' in p for p in clock_pages):
                            break
                        terminal.key(b'j' * 20)
                        clock_pages.append(terminal.capture('10-cts-details-%03d' % page_index))
                        if clock_pages[-1] == clock_pages[-2]:
                            break
                    check(fully_visible(clock_source, clock_pages) and any('Key: declared_clock_period' in p for p in clock_pages),
                          'CTS e/details scroll exposes full hashed historical clock configuration provenance')
                    terminal.key(b'\x1b')
                    terminal.capture('10-cts-escape', expected, ['Finalization attempt (exact):'])
                terminal.palette('Unzoom workspace')
        else:
            terminal.palette('Unzoom workspace')
            terminal.key(b'\t')
            terminal.key(b'\t')
            terminal.palette('Zoom focused tile')
            terminal.key(b'e')
            terminal.capture('10-no-finalization', ['No terminal result imported; inspect exact finalization reference'])
        check(calls() == warm, 'Inspection, scrolling, pinning and selection are provider-free once warm')
        snap = session.rpc('asic')
        check(len(field(snap, 'runs')) == 1 and field(field(snap, 'runs')[0], 'reference') == reference, 'No new allocation or changed public execution reference')
        check(find_summary(snap) == summary, 'PTY inspection preserves complete imported summary')
        final_ws = session.rpc('workspace')
        metrics.no_generic_jobs(session, 'before restart')
        terminal.close()
        terminal = None
        old_instance = session.metadata['instance_id']
        session.stop()
        session.start()
        check(session.metadata['instance_id'] != old_instance, 'Daemon restart creates a new instance')
        check(session.rpc('workspace') == final_ws, 'Private layout, selection and pin persist exactly')
        restored = find_summary(session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True))
        check(field(restored, 'freshness') == 'Cached_unverified', 'Restarted L2 is explicitly cached/unverified')
        check({k: v for k, v in restored if k != 'freshness'} == {k: v for k, v in summary if k != 'freshness'}, 'L2 preserves all terminal/synthesis fields except freshness')
        check(calls() == warm, 'Restart and L2 load make no provider queries')
        # Reopen an actual PTY after restart to verify displayed freshness too.
        terminal = metrics.Terminal(session)
        terminal.palette('Switch to FS1 Terminal Results Private')
        mutate('(Set_zoom (workspace %s) (tile (%s)))' % (field(demo, 'id'), tiles[0]))
        terminal.capture('11-restarted-cache', ['Cached_unverified', 'Terminal timing (aggregate)' if inputs else 'Cell count:'])
        check(calls() == warm, 'Restarted PTY remains provider-free')
        metrics.no_generic_jobs(session, 'after restarted PTY')
        check(True, 'No generic build/test/discovery jobs throughout private acceptance')
        logged = [json.loads(line) for line in calls().splitlines()]
        check(all(c['allowed'] for c in logged), 'Every provider command is an exact-reference read-only query')
        if not inputs:
            check(not any(c['argv'][0] == 'finalization-inspect' for c in logged), 'Failed-execution mode never imports finalization')
        outcome.update(status='passed', summary=record(summary), restored_summary=record(restored), run=run,
                       original_allocation=allocation, provider_calls=len(logged))
    except BaseException:
        outcome['error'] = traceback.format_exc()
        raise
    finally:
        try:
            if terminal:
                terminal.close()
        finally:
            if session and session.process:
                session.stop()
            after = dashboard.inventory(watched)
            (args.evidence / 'files-after.json').write_text(json.dumps(after, indent=2))
            outcome['input_files_unchanged'] = before == after
            if before != after:
                outcome['status'] = 'failed'
            (args.evidence / 'result.json').write_text(json.dumps(outcome, indent=2))
            require(before == after, 'Canonical evidence/config/provider files changed; inspect inventories')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--physical-evidence', type=Path, metavar='ROOT', help='Completed parent specimen root containing workbench-inputs.json')
    mode.add_argument('--failed-execution', type=Path, metavar='PHYSICAL_JSON', help='Real failed headless execution receipt; no finalization import')
    parser.add_argument('--example-root', type=Path, default=repo.parent / 'hardcaml_asic_example')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--outer-timeout', type=int, default=90)
    parser.add_argument('--expected-acceptance', choices=('not_evaluated', 'pass', 'fail'), default='not_evaluated',
                        help='Exact imported operation verdict; stage report acceptance remains not_evaluated')
    args = parser.parse_args()
    require(args.failed_execution is None or args.expected_acceptance == 'not_evaluated',
            '--failed-execution has no terminal result; --expected-acceptance must remain not_evaluated')
    for key in ('physical_evidence', 'failed_execution', 'example_root', 'client', 'daemon'):
        if getattr(args, key) is not None:
            setattr(args, key, getattr(args, key).resolve())
    require(0 < args.outer_timeout <= 300, 'Timeout must be 1..300 seconds')
    require(args.client.is_file() and args.daemon.is_file(), 'Existing client and daemon binaries required')
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-fs1-terminal-results-', dir='/tmp/opencode'))
    (args.evidence / 'commands.json').write_text(json.dumps(dict(argv=sys.argv, options={k: str(v) for k, v in vars(args).items()}, pty=dict(width=120, height=40)), indent=2))
    print('Evidence: ' + str(args.evidence), flush=True)

    def interrupted(signum, _frame):
        raise KeyboardInterrupt('Acceptance interrupted by signal %s' % signum)

    signal.signal(signal.SIGTERM, interrupted)
    try:
        exercise(args)
    except BaseException:
        if not (args.evidence / 'result.json').exists():
            (args.evidence / 'result.json').write_text(json.dumps(dict(status='failed', error=traceback.format_exc()), indent=2))
        raise
    print('PASS: private FS1 terminal-results HTTP / PTY / L2', flush=True)


if __name__ == '__main__':
    main()
