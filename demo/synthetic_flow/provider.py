#!/usr/bin/env python3
"""SYNTHETIC CLI4 provider. Only flow run/advance/seed mutate run evidence.

Observation, report and inspection commands read exact retained bytes. Calls are
logged separately. No EDA, third-party imports, subprocesses or network access.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import uuid

SCENARIOS = json.loads(Path(__file__).with_name('scenarios.json').read_text())
STAGES = SCENARIOS['stages']
LABEL = SCENARIOS['label']
BUNDLE = hashlib.sha256(Path(__file__).with_name('scenarios.json').read_bytes()).hexdigest()


def envelope(contract, version=1, **fields):
    return dict(contract='hardcaml-asic.' + contract, schema_version=version, **fields)


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + '\n').encode()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.snapshot-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(encoded(value))
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load(path):
    return json.loads(Path(path).read_bytes())


def selection(profile='success', endpoint='signoff', assignments=None):
    if profile not in SCENARIOS['profiles'] or endpoint not in STAGES:
        raise ValueError('Unknown synthetic profile/endpoint')
    if assignments:
        raise ValueError('Synthetic flow accepts no assignments')
    return dict(flow='synthetic', profile=profile, endpoint=endpoint, assignments=[])


def stage_plan(selected, statuses=None):
    statuses = statuses or {}
    end = STAGES.index(selected['endpoint'])
    return envelope('stage-plan', stages=[dict(
        id=stage, name='Synthetic ' + stage.title(),
        status=statuses.get(stage, 'pending' if i <= end else 'not_requested'),
        requested=i <= end,
        reason=LABEL + '; action starts a NEW run through ' + stage,
        action=selection(selected['profile'], stage)) for i, stage in enumerate(STAGES)])


def plan(selected):
    identity = hashlib.sha256(encoded(dict(selection=selected, bundle=BUNDLE))).hexdigest()
    return envelope('methodology-plan', plan_identity=identity, bundle_identity=BUNDLE,
                    synthetic=True, label=LABEL, selection=selected,
                    configuration_bytes=json.dumps(dict(CLOCK_PORT='clk', CLOCK_PERIOD=10.0,
                        SYNTHETIC_DECLARED_CLOCKS=[dict(name='clk', period_ns=10.0), dict(name='io_clk', period_ns=20.0)])),
                    stage_plan=stage_plan(selected))


def allocate(results, selected, name=None):
    attempt = Path(results).resolve() / (name or 'synthetic-' + uuid.uuid4().hex)
    attempt.mkdir(parents=True, exist_ok=False)
    snapshot = plan(selected)
    save(attempt / 'methodology-plan.json', snapshot)
    reference = dict(attempt_id=attempt.name, snapshot_path=str(attempt / 'methodology-plan.json'),
                     snapshot_sha256=digest(attempt / 'methodology-plan.json'),
                     plan_identity=snapshot['plan_identity'], bundle_identity=BUNDLE)
    state = envelope('stage-observation', 2, stream_id=attempt.name, cursor=0,
                     writer_active=True, observation_status='active', state=dict(outcome=None),
                     execution_file=None, selection=selected, label=LABEL, events=[],
                     methodology=envelope('historical-methodology', state='pending',
                         plan_identity=snapshot['plan_identity'], bundle_identity=BUNDLE,
                         reference=reference, launch=dict(attempt_id=attempt.name,
                             expected_plan_identity=snapshot['plan_identity'])),
                     stage_plan=stage_plan(selected))
    state['stage_plan']['stages'][0]['status'] = 'running'
    save(attempt / 'observation.json', state)
    return attempt


def finish(attempt, state, status):
    selected = state['selection']
    completed = [s['id'] for s in state['stage_plan']['stages'] if s['status'] == 'completed']
    artifacts = []
    profile = SCENARIOS['profiles'][selected['profile']]
    for stage in completed:
        directory = attempt / stage
        directory.mkdir(exist_ok=True)
        segment = dict(synthetic=True, label=LABEL, stage=stage, metrics={
            'design__instance__count': profile['cells'], 'design__instance__area': profile['area'],
            'synthesis__check_error__count': 0})
        save(directory / 'segment.json', segment)
        artifacts.append(dict(path=str(directory), boundary=stage, identity=digest(directory / 'segment.json')))
    snapshot = load(attempt / 'methodology-plan.json')
    code = {'completed': 0, 'failed': 1, 'cancelled': 130}[status]
    execution = dict(attempt_id=attempt.name, execution_file=str(attempt / 'execution.json'), synthetic=True, label=LABEL,
                     status='interrupted' if status == 'cancelled' else status, exit_code=code,
                     plan=dict(schema_version=3, initial_boundary=None,
                               stages=STAGES[:STAGES.index(selected['endpoint']) + 1]),
                     artifacts=artifacts, occurrences=[dict(
                         action_key='implementation.' + s['id'],
                         occurrence_id=attempt.name + '/implementation.' + s['id'],
                         status=s['status'], exit_code=0 if s['status'] == 'completed' else code)
                         for s in state['stage_plan']['stages'] if s['requested']],
                     methodology=envelope('methodology-execution-reference',
                         **state['methodology']['reference'], expected_plan_identity=snapshot['plan_identity']))
    save(attempt / 'execution.json', execution)
    state.update(writer_active=False, observation_status='final',
                 execution_file=str(attempt / 'execution.json'), state=dict(outcome=dict(status=status, exit_code=code)))
    state['methodology']['state'] = 'recorded'
    # Finalization is precomputed synthetic collection evidence, never an EDA claim.
    if artifacts:
        finalize(attempt / 'execution.json', attempt / 'finalizations')


def advance(attempt, cancel=False):
    attempt = Path(attempt).resolve()
    with (attempt / '.writer-lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load(attempt / 'observation.json')
        if not state['writer_active']:
            return state
        rows = state['stage_plan']['stages']
        running = next(s for s in rows if s['status'] == 'running')
        failed = running['id'] == SCENARIOS['profiles'][state['selection']['profile']]['fail_stage']
        running['status'] = 'cancelled' if cancel else ('failed' if failed else 'completed')
        pending = [s for s in rows if s['status'] == 'pending']
        if cancel or failed or not pending:
            for row in pending:
                row.update(status='cancelled' if cancel else 'skipped',
                           reason=LABEL + ('; cancelled by user' if cancel else '; blocked by earlier failure'))
            finish(attempt, state, 'cancelled' if cancel else ('failed' if failed else 'completed'))
        else:
            pending[0]['status'] = 'running'
        state['cursor'] += 1
        state['events'].append(envelope('stage-observation', 2, stream_id=attempt.name,
            sequence=state['cursor'], event='synthetic_stage_snapshot', stage_plan=state['stage_plan']))
        if not state['writer_active']:
            materialize_inspections(attempt, state)
        save(attempt / 'observation.json', state)
        return state


def report(execution_file):
    execution_file = Path(execution_file).resolve()
    attempt = execution_file.parent
    execution = load(execution_file)
    state = load(attempt / 'observation.json')
    checkpoints = []
    for ref in execution['artifacts']:
        path = Path(ref['path']) / 'segment.json'
        if digest(path) != ref['identity']:
            raise ValueError('Checkpoint digest mismatch')
        metrics = load(path)['metrics']
        checkpoints.append(dict(reference=ref, metric_origin=dict(scope='boundary_snapshot'),
            metrics=[dict(raw_key=k, availability='available', value=v,
                          unit='cells' if k.endswith('instance__count') else ('µm²' if k.endswith('area') else 'count'),
                          source=dict(path=str(path), sha256=digest(path), field='metrics.' + k))
                     for k, v in metrics.items()],
            supplementary=[dict(mapped_cell_types={'SYNTHETIC_DFF': 32,
                                                  'SYNTHETIC_COMB': metrics['design__instance__count'] - 32})]))
    completed = [r['boundary'] for r in execution['artifacts']]
    return envelope('report', synthetic=True, label=LABEL, execution=execution,
                    methodology=dict(state['methodology'], state='recorded'),
                    completion=dict(physical='full' if 'signoff' in completed else (completed[-1] if completed else 'none')),
                    acceptance='not_evaluated', checkpoints=checkpoints)


def finalize(execution_file, store, unique=False):
    execution_file = Path(execution_file).resolve()
    execution = load(execution_file)
    attempt = Path(store).resolve() / ('synthetic-collection-' +
        (uuid.uuid4().hex if unique else execution['attempt_id']))
    attempt.mkdir(parents=True, exist_ok=False)
    state = load(execution_file.parent / 'observation.json')
    spec = SCENARIOS['profiles'][state['selection']['profile']]
    physical_available = any(r['boundary'] == 'placement' for r in execution['artifacts'])
    text = attempt / 'synthetic-summary.txt'
    text.write_text(LABEL + '\nRun: ' + execution['attempt_id'] + '\nOutcome: ' + execution['status'] +
                    '\nSetup slack: ' + str(spec['setup_slack']) + ' ns\n' +
                    ('Final retained standard-cell area: ' + str(spec['area']) + ' um^2\n' +
                     'Final retained utilization: ' + str(spec['utilization']) + ' fraction\n'
                     if physical_available else 'Physical resources unavailable: placement not completed\n'))
    def metric(value, unit, available=True):
        return dict(value=value if available else None, unit=unit, source=text.name,
                    unavailable_reason=None if available else 'placement not completed', synthetic=True)
    results = dict(schema_version=1, run_id=attempt.name, build_identity=BUNDLE, synthetic=True, label=LABEL,
        provenance=dict(contract='hardcaml-asic.segment-finalization', operation=str(attempt / 'operation.json')),
        metrics=dict(setup_slack=metric(spec['setup_slack'], 'ns'), hold_slack=metric(spec['hold_slack'], 'ns'),
                     mapped_area=metric(spec['area'], 'um^2'), mapped_cells=metric(spec['cells'], 'cells'),
                     final_standard_cell_area=metric(spec['area'], 'um^2', physical_available),
                     final_utilization=metric(spec['utilization'], 'fraction', physical_available)),
        synthesis_checks={key: metric(0, 'count') for key in ('unmapped_instances', 'synthesis_errors', 'inferred_latches')},
        checks={key: dict(status='fail' if key == 'drc' and execution['status'] == 'failed' else 'pass',
                          reason=LABEL, source=text.name) for key in ('drc', 'lvs', 'antenna')},
        timing_goal='fail' if spec['setup_slack'] < 0 else 'pass', raw_artifacts=[text.name])
    # Prefix/failure runs have no signoff verdict: explicitly unavailable checks/timing.
    if not any(r['boundary'] == 'signoff' for r in execution['artifacts']):
        results['checks'] = {key: dict(status='unknown', reason=LABEL + '; signoff not completed')
                             for key in ('drc', 'lvs', 'antenna')}
    save(attempt / 'results.json', results)
    receipt = envelope('segment-finalization', attempt_id=attempt.name, synthetic=True, label=LABEL,
        status='completed', phase='collection', ended_at='synthetic-recorded', exit_code=0,
        request=dict(execution=str(execution_file), accept=False), acceptance='not_evaluated',
        external_postcheck='not_evaluated', execution=dict(path=str(execution_file),
            sha256=digest(execution_file), attempt_id=execution['attempt_id']),
        selected_checkpoints=execution['artifacts'], evidence_context=dict(build_identity=BUNDLE),
        results=dict(path=str(attempt / 'results.json'), sha256=digest(attempt / 'results.json')),
        mapped_files={text.name: dict(sha256=digest(text))})
    save(attempt / 'operation.json', receipt)
    return attempt


def inspect(execution_file, domain, stage, row_id=None, expected=None):
    execution_file = Path(execution_file).resolve()
    if domain not in ('timing', 'clocks', 'physical', 'routing') or stage not in STAGES:
        raise ValueError('Invalid inspection domain/stage')
    execution = load(execution_file)
    evidence = execution_file.parent / ('inspection-' + domain + '-' + stage + '.json')
    source = load(evidence)
    result = envelope('inspection', execution_file=str(execution_file), execution_sha256=digest(execution_file),
                      attempt_id=execution['attempt_id'], domain=domain, stage=stage,
                      source_digest=digest(evidence), diagnostics=[LABEL], truncated=False, rows=source['rows'])
    if row_id is not None:
        if expected != result['source_digest'] or row_id not in source['details']:
            raise ValueError('Inspection digest/row fence mismatch')
        result.update(row_id=row_id, detail=source['details'][row_id])
    return result


def materialize_inspections(attempt, state=None):
    state = state or load(attempt / 'observation.json')
    spec = SCENARIOS['profiles'][state['selection']['profile']]
    for stage in STAGES:
        stage_status = next(s['status'] for s in state['stage_plan']['stages'] if s['id'] == stage)
        domains = {
            'timing': [dict(path, value=round(spec[path['check'] + '_slack'] + path['offset'], 6),
                            unit='ns', kind=path['check']) for path in SCENARIOS['timing_paths']],
            'clocks': [
                dict(key='', name='clk declared period', value=10.0, unit='ns', kind='declared_constraint'),
                dict(key='io-period', name='io_clk declared period', value=20.0, unit='ns', kind='declared_constraint', group='io'),
                dict(key='clk-arrival', name='clk SYNTHETIC measured insertion delay', value=0.18, unit='ns', kind='synthetic_measurement'),
                dict(key='clk-skew', name='clk SYNTHETIC measured skew', value=0.025, unit='ns', kind='synthetic_measurement'),
                dict(key='io-skew', name='io_clk SYNTHETIC measured skew', value=0.04, unit='ns', kind='synthetic_measurement', group='io')],
            'physical': [
                dict(key='', name='standard-cell area', value=spec['area'], unit='um^2'),
                dict(key='utilization', name='cell utilization (fraction)', value=spec['utilization'], unit='fraction'),
                dict(key='core-area', name='core area', value=round(spec['area'] / spec['utilization'], 3), unit='um^2'),
                dict(key='cells', name='standard-cell count', value=spec['cells'], unit='cells'),
                dict(key='sequential-area', name='sequential-cell area', value=240.0, unit='um^2')],
            'routing': [
                dict(key='', name='illustrative wire length', value=1234.0, unit='um'),
                dict(key='signal-wire', name='illustrative signal wire length', value=1080.0, unit='um'),
                dict(key='vias', name='illustrative via count', value=96, unit='count'),
                dict(key='overflow', name='illustrative routing overflow', value=0, unit='count'),
                dict(key='metal', name='illustrative metal utilization (fraction)', value=0.18, unit='fraction')],
        }
        for domain, entries in domains.items():
            rows, details = [], {}
            for entry in entries:
                row_id = 'synthetic-' + domain + '-' + stage + ('-' + entry['key'] if entry['key'] else '')
                available = stage_status == 'completed'
                kind = entry.get('kind', 'synthetic_measurement')
                name, value, unit = entry['name'], entry['value'], entry['unit']
                row = dict(id=row_id, category=domain, producer='synthetic.' + stage,
                    corner=entry.get('corner', 'synthetic_typical'), group=entry.get('group', 'clk'),
                    name='SYNTHETIC ' + name, value=value if available else None,
                    unit=unit, status='available' if available else 'unavailable',
                    source=json.dumps(dict(path=str(attempt / ('inspection-' + domain + '-' + stage + '.json')),
                                           row_id=row_id, synthetic=True, stage_status=stage_status)),
                    fields=[['evidence', LABEL], ['stage_status', stage_status], ['evidence_kind', kind]])
                rows.append(row)
                details[row_id] = (LABEL + '\n' + stage + ': ' + stage_status + '\n' + name + ': ' +
                    (str(value) + ' ' + unit if available else 'not available') + '\nEvidence kind: ' + kind +
                    '\nCorner: ' + row['corner'] + '; group: ' + row['group'] +
                    '\nNo tool report or binary layout is claimed.\n')
            save(attempt / ('inspection-' + domain + '-' + stage + '.json'),
                 dict(synthetic=True, rows=rows, details=details))


def seed(results):
    runs = []
    for profile, name in [('success', 'synthetic-reference'), ('failure', 'synthetic-failed')]:
        attempt = allocate(results, selection(profile), name)
        while load(attempt / 'observation.json')['writer_active']:
            advance(attempt)
        runs.append(dict(attempt=str(attempt), stream_id=attempt.name,
                         finalization=str(attempt / 'finalizations' / ('synthetic-collection-' + attempt.name))))
    return runs


def main():
    args = sys.argv[1:]
    # Append with O_APPEND, one record per invocation (including rejected requests).
    record = encoded(dict(argv=args, synthetic=True, time_ns=time.time_ns(), pid=os.getpid())).replace(b'\n', b'') + b'\n'
    project = Path(__file__).resolve().parent.parent
    if not (project / 'synthetic-settings.json').exists():
        project = Path.cwd()
    fd = os.open(project / 'provider-calls.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, record)
    finally:
        os.close(fd)
    def option(flag, default=None):
        return args[args.index(flag) + 1] if flag in args else default
    def emit(value):
        print(json.dumps(value), flush=True)
    if args == ['--version', '--json']:
        emit(dict(cli_contract=dict(version=4, capabilities=dict(namedflow1=True)), synthetic=True))
    elif args[:2] == ['flow', 'list']:
        emit(envelope('flow-list', declaration=envelope('flow-catalog',
            entries=[dict(methodology=dict(id='synthetic', name=LABEL), default_profile='success',
                          profiles=[dict(id=p) for p in SCENARIOS['profiles']])],
            default=dict(flow='synthetic', profile='success'))))
    elif args[:2] == ['flow', 'describe']:
        if option('--flow') != 'synthetic':
            raise ValueError('Unknown flow')
        emit(envelope('flow-describe', entry=dict(methodology=dict(id='synthetic', name=LABEL, endpoints=STAGES),
            profiles=[dict(id=p) for p in SCENARIOS['profiles']]),
            capabilities=dict(stage_selection='complete-prefix-through-declared-endpoint')))
    elif args[:2] in (['flow', 'plan'], ['flow', 'run']):
        if option('--flow') != 'synthetic':
            raise ValueError('Unknown flow')
        selected = selection(option('--profile'), option('--endpoint'), ['set'] if '--set' in args else [])
        preview = plan(selected)
        if args[1] == 'plan':
            emit(preview)
            return
        if option('--expected-plan-identity') != preview['plan_identity']:
            raise ValueError('Expected plan identity mismatch')
        attempt = allocate(option('--results-root'), selected)
        cancelled = False
        def stop(_sig, _frame):
            # Do not reacquire the writer lock inside a signal handler.
            nonlocal cancelled
            cancelled = True
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        emit(envelope('stage-observation', event='observation_allocated', attempt=str(attempt), stream_id=attempt.name))
        settings = load(project / 'synthetic-settings.json')
        deadline = time.monotonic() + settings['max_run_seconds']
        while load(attempt / 'observation.json')['writer_active']:
            if time.monotonic() > deadline:
                cancelled = True
            time.sleep(settings['delay_seconds'])
            if cancelled:
                advance(attempt, cancel=True)
            elif not settings['manual']:
                advance(attempt)
        emit(envelope('stage-observation', event='observation_terminal', execution_file=str(attempt / 'execution.json')))
        emit(load(attempt / 'execution.json'))
        if cancelled:
            sys.exit(130)
    elif args[:2] == ['observation', 'inspect']:
        emit(load(Path(args[2]) / 'observation.json'))
    elif args[:2] == ['observation', 'read-updates']:
        state = load(Path(args[2]) / 'observation.json')
        after = int(option('--after'))
        if option('--stream-id') != state['stream_id'] or not 0 <= after <= state['cursor']:
            raise ValueError('Observation stream/cursor mismatch')
        emit(envelope('stage-observation', 2, stream_id=state['stream_id'], after=after,
                      cursor=state['cursor'], events=[e for e in state['events'] if e['sequence'] > after]))
    elif args[:1] == ['report']:
        emit(report(args[1]))
    elif args[:1] == ['inspect']:
        emit(inspect(args[1], option('--domain'), option('--stage'), option('--row-id'), option('--expected-digest')))
    elif args[:1] == ['finalization-inspect']:
        emit(load(Path(args[1]) / 'operation.json'))
    elif args[:1] == ['finalize']:
        if '--accept' in args:
            raise ValueError('Synthetic provider does not run external acceptance tools')
        attempt = finalize(args[1], option('--operation-store'), unique=True)
        emit(envelope('segment-finalization', event='allocated', attempt=str(attempt), attempt_id=attempt.name))
        emit(dict(load(attempt / 'operation.json'), attempt=str(attempt)))
    elif args[:1] == ['advance']:
        state = advance(args[1], cancel='--cancel' in args)
        emit(state)
    else:
        raise ValueError('Unsupported synthetic command: ' + repr(args))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print('SYNTHETIC provider: ' + str(error), file=sys.stderr)
        sys.exit(2)
