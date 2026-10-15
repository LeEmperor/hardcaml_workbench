#!/usr/bin/env python3
"""Parent-run real Workbench signoff cancellation acceptance (<180s; no builds).

Launches ONE real flow using the supplied existing timeout-capable project binary,
private copied source/config/state/results, and captured Discover/Describe/Plan
preview. Cancels only its own backend run key after an exact transport-record /
observation / running-container ownership match. Docker commands are read-only.

Risk under test: the ASIC launcher grants 15s after SIGTERM;
provider transport cleanup has its own grace/deadline. A failed backend operation
alone proves neither a terminal provider outcome nor container/descendant cleanup.
Missing receipts, survivors, or fallback signals FAIL acceptance. No docker rm/stop
is issued. Fallback SIGTERM is restricted to identity-checked owned provider PIDs.
Run serially; an existing LibreLane/Hardcaml container blocks launch.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('terminal_results', Path(__file__).with_name('test-fs1-terminal-results.py'))
terminal_results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal_results)
metrics, fs0 = terminal_results.metrics, terminal_results.fs0
field, record, require = fs0.field, fs0.record, fs0.require


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def proc_table():
    """PID/start-time identities, not reusable PID numbers or process-name guesses."""
    result = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            stat = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            result[int(path.name)] = dict(pid=int(path.name), state=stat[0], ppid=int(stat[1]),
                                          pgrp=int(stat[2]), start=stat[19],
                                          argv=(path / 'cmdline').read_bytes().decode(errors='replace').rstrip('\0').split('\0'))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return result


def same_process(identity, table):
    current = table.get(identity['pid'])
    return current is not None and current['start'] == identity['start'] and current['state'] != 'Z'


class Session(terminal_results.Session):
    def command(self, extra, label, timeout=90, success=True):
        timeout = min(timeout, 8., max(.1, self.deadline - time.monotonic()))
        return super().command(extra, label, timeout=timeout, success=success)

    def stop(self):
        # Keep shutdown inside the overall receipt/cleanup reserve. Only the
        # private daemon's new process group is signalled here.
        if not self.process:
            return
        for sig, grace in ((signal.SIGTERM, 3), (signal.SIGKILL, 1)):
            try:
                os.killpg(self.process.pid, sig)
            except ProcessLookupError:
                break
            try:
                self.process.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                pass
        self.log.close()


def exercise(args):
    started = time.monotonic()
    hard_end = started + args.budget
    work_end = hard_end - 24
    outcome = dict(status='failed', checks=[], evidence=str(args.evidence),
                   risk='Workbench launcher grace must allow provider cleanup and terminal receipt publication',
                   stage_timeout_seconds=2400, manual_docker_mutations=False, fallback_signals=[])
    session = None
    launched = cancelled = False
    reference = workspace = None
    tracked = {}
    owned_containers = {}
    sequence = 0
    key = 'fs1-cancel-' + args.evidence.name
    source_receipt = terminal_results.load(args.source_receipt)
    manifest = json.loads(source_receipt['plan']['bundle_manifest'])
    source_paths = []
    for item in manifest['source_inputs']:
        relative = Path(item['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe source manifest path')
        source = args.example_root / relative
        require(source.is_file() and not source.is_symlink(), 'Missing/nonregular source input: ' + str(source))
        source_paths.append(source)
    config_path = args.example_root / 'hardcaml-workbench-asic.sexp'
    cfg = metrics.parse(config_path.read_text())
    provider = Path(field(cfg, 'provider_executable')).resolve()
    source_git = args.example_root / '.git'
    require(source_git.is_dir() and not source_git.is_symlink(), 'A standalone source repository is required for the project bundle provenance reads')
    watched = source_paths + [source_git, config_path, args.project, provider, args.source_receipt]
    before = metrics.dashboard.inventory(watched)
    save(args.evidence / 'files-before.json', before)

    def check(ok, message):
        outcome['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def external(argv, label, success=True):
        nonlocal sequence
        sequence += 1
        stem = args.evidence / ('external-%03d-%s' % (sequence, label))
        timeout = min(4., max(.1, (work_end if not outcome.get('cleanup') else hard_end - 5) - time.monotonic()))
        p = subprocess.run([str(v) for v in argv], capture_output=True, timeout=timeout, start_new_session=True)
        stem.with_suffix('.stdout').write_bytes(p.stdout)
        stem.with_suffix('.stderr').write_bytes(p.stderr)
        save(stem.with_suffix('.json'), dict(argv=[str(v) for v in argv], returncode=p.returncode, timeout=timeout))
        if success:
            require(p.returncode == 0, label + ': ' + p.stderr.decode(errors='replace'))
        return p

    def docker_ps():
        p = external([args.docker, 'ps', '--no-trunc', '--format', '{{json .}}'], 'docker-ps')
        return [json.loads(line) for line in p.stdout.splitlines() if line.strip()]

    def inspect_observation():
        p = external([provider, 'observation', 'inspect', reference['attempt'], '--json'], 'observation')
        j = json.loads(p.stdout)
        require(j['stream_id'] == reference['stream_id'], 'Observation stream identity changed')
        return j

    def transport_records():
        if workspace is None:
            return {}
        records = {}
        for p in workspace.glob('*-transport.json'):
            try:
                j = terminal_results.load(p)
            except (FileNotFoundError, json.JSONDecodeError):
                continue  # A newly published launch record may still be writing.
            require(j['kind'] == 'backend_transport_launch' and Path(j['cwd']).is_relative_to(workspace), 'Transport outside exact owned workspace')
            records[str(p)] = j
        return records

    def track(table=None, container_pid=None):
        table = table if table is not None else proc_table()
        roots = {session.process.pid} if session and session.process and session.process.poll() is None else set()
        roots.update(p['pid'] for p in tracked.values() if same_process(p, table))
        if container_pid:
            roots.add(container_pid)
        selected = set(roots)
        while True:
            children = {pid for pid, p in table.items() if p['ppid'] in selected}
            if children <= selected:
                break
            selected.update(children)
        for pid in selected - ({session.process.pid} if session and session.process else set()):
            if pid in table:
                p = table[pid]
                tracked[(pid, p['start'])] = p
        return table

    def active_owned(records):
        running = {r['Names']: r for r in docker_ps()}
        matches = []
        for path, launch in records.items():
            name = launch['container_name']
            if name not in running:
                continue
            info = json.loads(external([args.docker, 'inspect', running[name]['ID']], 'docker-inspect').stdout)[0]
            request_path = Path(launch['request_path'])
            request = terminal_results.load(request_path)
            if request.get('operation') != 'execute_segment':
                continue  # Metadata/validation containers are not the EDA specimen.
            require(request_path.is_relative_to(workspace) and str(request_path) in launch['argv'], 'Transport/request correlation mismatch')
            require(request['request_id'] == launch['request_id'] and request['project'] == launch['cwd'], 'Transport launch/request configuration identity mismatch')
            require(info['Name'].lstrip('/') == name and info['State']['Running'], 'Exact owned container not running')
            require(info['Config']['WorkingDir'] == launch['cwd'] and
                    str(request_path) in (info['Config'].get('Cmd') or []) and
                    any(m['Source'] == str(workspace) and m['Destination'] == str(workspace) and m['RW'] for m in info['Mounts']),
                    'Running container does not match observed workspace/request mount')
            require(info['Image'] == launch['binding']['image_identity']['image_id'], 'Running container image differs from recorded binding')
            require(launch['timeout_seconds'] == 2400, 'Backend launch did not receive configured stage timeout 2400')
            table = track(container_pid=info['State']['Pid'])
            require(any(p['argv'] == launch['argv'] for p in tracked.values() if same_process(p, table)),
                    'No live owned daemon descendant matches exact Docker transport argv')
            owned_containers[info['Id']] = dict(id=info['Id'], name=name, init_pid=info['State']['Pid'], launch_record=path)
            save(args.evidence / ('container-' + info['Id'] + '.json'), info)
            matches.append((launch, request))
        return matches

    def live_tracked():
        table = track()
        return [p for p in tracked.values() if same_process(p, table)]

    def operation(snapshot):
        return next(o for o in field(snapshot, 'operations') if field(o, 'key') == 'run:' + key)

    def cancel():
        nonlocal cancelled
        session.rpc('asic', '(Cancel %s)' % fs0.sexp('run:' + key))
        cancelled = True

    try:
        initial_containers = docker_ps()
        check(not any('librelane' in c.get('Image', '').lower() or c.get('Names', '').startswith('hardcaml-asic-') for c in initial_containers),
              'No overlapping LibreLane/Hardcaml containers before launch')
        root = args.evidence / 'project'
        root.mkdir()
        (args.evidence / 'state').mkdir()
        for source in source_paths:
            target = root / source.relative_to(args.example_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        # Bundle.render requires a real HEAD even for read-only provenance. Copy
        # repository metadata rather than point Git at canonical index/config.
        # No Git command or mutation is performed by this harness. Production's
        # plan/run may read HEAD/status in this private copy only.
        shutil.copytree(source_git, root / '.git', ignore=shutil.ignore_patterns('hooks', 'logs', '*.lock'))
        # Source files are bundle inputs, not generic Dune build targets. Keep
        # metadata inspection from traversing the copied source stanzas.
        (root / 'dune').write_text('(dirs)\n')
        cfg = metrics.put(cfg, 'project_executable', str(args.project))
        cfg = metrics.put(cfg, 'results_root', str(args.evidence / 'results'))
        cfg = metrics.put(cfg, 'stage_timeout_seconds', ['2400'])
        (root / 'hardcaml-workbench-asic.sexp').write_text(fs0.sexp(cfg) + '\n')
        session = Session(args, args.evidence, root)
        session.deadline = work_end
        for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
            session.env.pop(name, None)
        session.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_OPTIONAL_LOCKS='0')
        metrics.guard_generic_builds(session)
        session.start()
        metrics.no_generic_jobs(session, 'before real launch')
        discovered = session.rpc('asic', 'Discover', wait=True)
        check(any(field(f, 'id') == 'standard' for f in field(discovered, 'flows')), 'HTTP Discover advertises standard flow')
        session.rpc('asic', '(Describe standard)', wait=True)
        planned = session.rpc('asic', '(Plan ((flow standard) (profile balanced) (endpoint signoff) (assignments ())))', wait=True)
        preview = field(planned, 'preview')[0]
        check(field(field(preview, 'selection'), 'endpoint') == 'signoff', 'Captured exact HTTP signoff preview')
        save(args.evidence / 'captured-preview.json', record(preview))
        launched = True  # Even a timed-out delivery must cancel this exact key.
        session.rpc('asic', '(Run (key %s) (preview %s))' % (fs0.sexp(key), fs0.sexp(preview)))
        # The Run RPC client has exited; daemon now owns execution.
        outcome['launch_key'] = 'run:' + key
        while True:
            track()
            require(time.monotonic() < min(work_end - 40, started + 85), 'No confirmed owned active backend container within launch budget')
            snapshot = session.rpc('asic')
            check_state = field(operation(snapshot), 'state')
            require(check_state in ('pending', 'executing'), 'Launcher ended before cancellable live specimen: ' + check_state)
            runs = field(snapshot, 'runs')
            if runs:
                require(len(runs) == 1, 'Unexpected second run allocation')
                reference = record(field(runs[0], 'reference'))
                require(Path(reference['attempt']).is_relative_to(args.evidence / 'results'), 'Allocation outside private results')
                observation = inspect_observation()
                observed_workspace = (observation.get('execution_request') or {}).get('workspace') or (observation.get('state') or {}).get('workspace')
                if observed_workspace:
                    workspace = Path(observed_workspace)
                    require(workspace.is_relative_to(args.evidence / 'results'), 'Observation workspace outside private results')
                    active = active_owned(transport_records())
                    if active:
                        break
            time.sleep(.25)
        check(field(operation(snapshot), 'state') == 'executing', 'Detached Run client leaves daemon-owned launcher executing')
        check(session.process.poll() is None, 'Private daemon alive while detached client work executes')
        # Preserve exact pre-cancel observation, process identities and transport set.
        observation = inspect_observation()
        before_records = transport_records()
        before_occurrences = {o['action_key'] for o in observation['state'].get('occurrences', [])}
        check(bool(before_occurrences), 'Exact observation records the active implementation occurrence before cancellation')
        check(all('implementation.' + request['boundary'] in before_occurrences for _, request in active),
              'Running EDA transport matches the exact active observation occurrence')
        save(args.evidence / 'before-cancel.json', dict(reference=reference, observation=observation,
             transports=before_records, processes=list(tracked.values()), containers=owned_containers))
        outcome['reference'] = reference
        outcome['cancelled_at'] = time.time()
        cancel()
        settled_at = None
        while time.monotonic() < work_end:
            snapshot = session.rpc('asic')
            observation = inspect_observation()
            track()
            running = docker_ps()
            remaining = [c for c in running if c['ID'] in owned_containers or c['Names'] in {v['name'] for v in owned_containers.values()}]
            provider_status = (observation.get('state', {}).get('outcome') or {}).get('status')
            save(args.evidence / 'last-cancel-poll.json', dict(
                operation=record(operation(snapshot)), provider_status=provider_status,
                writer_active=observation.get('writer_active'), cursor=observation.get('cursor'),
                containers=remaining, processes=live_tracked()))
            stopped = field(operation(snapshot), 'state') == 'failed' and provider_status in ('failed', 'interrupted', 'cancelled') and not observation.get('writer_active', True)
            if stopped and not remaining and not live_tracked():
                settled_at = settled_at or time.monotonic()
                if time.monotonic() - settled_at >= 3:
                    break
            else:
                settled_at = None
            time.sleep(.25)
        check(settled_at is not None and time.monotonic() - settled_at >= 3, 'Backend cancellation settles provider outcome and removes owned container/descendants, stable for 3s')
        check(field(operation(snapshot), 'state') == 'failed', 'Cancelled backend launcher is failed, never completed')
        check('cancel' in fs0.sexp(field(operation(snapshot), 'error')).lower(), 'Workbench launcher reports cancellation rather than unrelated execution failure')
        check(observation['state']['outcome']['status'] in ('failed', 'interrupted', 'cancelled'), 'Provider publishes interrupted/failed final outcome, not completed')
        check(any(word in str(observation['state']['outcome'].get('error', '')).lower() for word in ('interrupt', 'cancel', 'signal')),
              'Provider outcome attributes failure to interruption/cancellation')
        for launch, _ in active:
            terminal_record = terminal_results.load(launch['terminal_record'])
            check(not terminal_record['transport_succeeded'] and terminal_record['process']['outcome'] in ('cancelled', 'signaled') and
                  terminal_record['cleanup'] is not None and terminal_record['cleanup']['error'] is None,
                  'Actual transport receipt records interrupted process and successful owned-container cleanup')
            save(args.evidence / (Path(launch['terminal_record']).name), terminal_record)
        check(set(transport_records()) == set(before_records), 'No later backend transport/stage starts after cancellation')
        check({o['action_key'] for o in observation['state'].get('occurrences', [])} <= before_occurrences,
              'No later stage occurrence after exact-key cancellation')
        check(not any(o['action_key'] == 'implementation.signoff' and o['status'] == 'completed' for o in observation['state'].get('occurrences', [])),
              'Cancellation cannot claim completed signoff')
        check(not live_tracked(), 'All captured owned host/container descendants terminated (PID/start-time checked)')
        execution_file = observation.get('execution_file')
        check(bool(execution_file) and Path(execution_file).is_relative_to(workspace), 'Final interrupted execution reference retained')
        execution = terminal_results.load(execution_file)
        check(execution['status'] in ('failed', 'interrupted', 'cancelled') and execution['attempt_id'] == reference['stream_id'], 'Exact execution receipt is non-successful')
        # Explicit read-only Observe reconciles the registry after its automatic
        # reader was cancelled; it does not restart or advance provider execution.
        final = session.rpc('asic', '(Observe %s)' % fs0.sexp(field(field(snapshot, 'runs')[0], 'run')), wait=True)
        check(field(field(final, 'runs')[0], 'status') in ('failed', 'interrupted', 'cancelled'), 'Workbench run status reconciles actual failed/interrupted execution')
        check(session.process.poll() is None and session.rpc('workspace') is not None, 'Daemon remains live and accepts independent HTTP requests after client detach/cancel')
        metrics.no_generic_jobs(session, 'after cancellation')
        save(args.evidence / 'after-cancel.json', dict(observation=observation, snapshot=final, processes=list(tracked.values()), containers=owned_containers))
        outcome['status'] = 'passed'
    except BaseException:
        outcome['error'] = traceback.format_exc()
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        outcome['cleanup'] = True
        # Recovery is never acceptance evidence. Prefer exact backend Cancel, then
        # signal only still-identical provider owners if backend cleanup failed.
        if session and session.process and launched and not cancelled and session.process.poll() is None:
            try:
                session.deadline = hard_end - 12
                cancel()
            except BaseException as exc:
                outcome['cleanup_cancel_error'] = repr(exc)
        survivors = live_tracked() if session else []
        for p in survivors:
            if p['argv'] and p['argv'][0] == str(provider):
                try:
                    if same_process(p, proc_table()):
                        os.kill(p['pid'], signal.SIGTERM)
                        outcome['fallback_signals'].append(dict(pid=p['pid'], start=p['start'], signal='SIGTERM', argv=p['argv']))
                        outcome['status'] = 'failed'
                except ProcessLookupError:
                    pass
        if outcome['fallback_signals']:
            while time.monotonic() < hard_end - 7 and live_tracked():
                time.sleep(.2)
        if session and session.process:
            session.stop()
        outcome['surviving_processes'] = live_tracked() if session else []
        try:
            running = docker_ps()
            names = {v['name'] for v in owned_containers.values()}
            for p in tracked.values():
                argv = p['argv']
                if argv and Path(argv[0]).name == 'docker' and 'run' in argv and '--name' in argv:
                    index = argv.index('--name')
                    if index + 1 < len(argv):
                        names.add(argv[index + 1])
            # Include any illegal later transport as a survivor too, while
            # retaining the distinction from pre-cancel confirmed container IDs.
            names.update(j['container_name'] for j in transport_records().values() if j.get('container_name'))
            outcome['surviving_owned_containers'] = [c for c in running if c['ID'] in owned_containers or c['Names'] in names]
        except BaseException as exc:
            outcome['cleanup_docker_error'] = repr(exc)
            outcome['status'] = 'failed'
        if outcome['surviving_processes'] or outcome.get('surviving_owned_containers'):
            outcome['status'] = 'failed'
        after = metrics.dashboard.inventory(watched)
        save(args.evidence / 'files-after.json', after)
        outcome['input_files_unchanged'] = before == after
        outcome['elapsed_seconds'] = time.monotonic() - started
        if before != after or outcome['elapsed_seconds'] >= 180:
            outcome['status'] = 'failed'
        save(args.evidence / 'result.json', outcome)
        require(outcome['status'] == 'passed', 'Cancellation acceptance failed; inspect retained result.json (fallback never counts as success)')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('/tmp/opencode/fs1-timeout-project-SAuuX0/build/default/bin/project.exe'))
    parser.add_argument('--example-root', type=Path, default=repo.parent / 'hardcaml_asic_example')
    parser.add_argument('--source-receipt', type=Path, default=Path('/tmp/opencode/workbench-fs1-physical-w0rftdi0/physical.json'), help='Real specimen receipt whose source manifest is copied; never rerun')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--docker', default=shutil.which('docker') or '/usr/bin/docker')
    parser.add_argument('--budget', type=int, default=165, help='Total wall budget 120..170 seconds, includes failure cleanup reserve')
    args = parser.parse_args()
    require(120 <= args.budget <= 170, 'Budget must be 120..170 seconds')
    for key in ('project', 'example_root', 'source_receipt', 'client', 'daemon'):
        setattr(args, key, getattr(args, key).resolve())
    require(all(p.is_file() for p in (args.project, args.client, args.daemon, args.source_receipt)), 'Missing existing binaries/specimen receipt')
    args.outer_timeout = 6
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-fs1-cancellation-', dir='/tmp/opencode'))
    save(args.evidence / 'commands.json', dict(argv=sys.argv, options={k: str(v) for k, v in vars(args).items()}))
    print('Evidence: ' + str(args.evidence), flush=True)

    def interrupted(signum, _frame):
        raise KeyboardInterrupt('Cancellation acceptance interrupted by signal %s' % signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    # Interrupt even a stuck startup/read within the work budget, preserving a
    # separate bounded finally window for backend cancellation and own cleanup.
    signal.setitimer(signal.ITIMER_REAL, args.budget - 25)
    try:
        exercise(args)
    except BaseException:
        if not (args.evidence / 'result.json').exists():
            save(args.evidence / 'result.json', dict(status='failed', error=traceback.format_exc()))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print('PASS: owned real Workbench cancellation / provider cleanup', flush=True)


if __name__ == '__main__':
    main()
