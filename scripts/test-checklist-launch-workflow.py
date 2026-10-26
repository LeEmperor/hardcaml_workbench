#!/usr/bin/env python3
"""Normal private daemon/PTY checklist acceptance; real metadata, synthetic Run only.

Matching binaries must be supplied. No builds, publication, live daemon access or
real EDA. Reuses the native composition/consistency transport and terminal oracle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util

spec = importlib.util.spec_from_file_location('checklist_consistency', Path(__file__).with_name('test-launch-stage-consistency.py'))
consistency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consistency)
c, real = consistency.composition, consistency.real
field, sexp, require, wait, save = c.field, c.sexp, c.require, c.wait, consistency.save


def calls(base):
    path = base / 'provider-calls.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


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


def preference(base, selection):
    # Match Sexp.to_string_mach in main.ml, rather than a human-formatted sexp.
    key = '(' + str(base / 'project') + '(Opam_switch ' + c.demo.switch_name() + '))'
    directory = base / 'client-state/hardcaml-workbench/terminal'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('launch-' + hashlib.sha256(key.encode()).hexdigest() + '.sexp')
    path.write_text(sexp([['schema_version', '1'], ['project_key', key], ['selection', selection]]))
    save(base / 'remembered-selection.json', dict(project_key=key, path=str(path), selection=selection))


def real_case(args, manifest, reference, presets, mode, check):
    base = args.evidence / ('real-' + mode)
    for name in ('project', 'state', 'home', 'config', 'client-state'):
        (base / name).mkdir(parents=True)
    root = base / 'project'
    (root / 'dune-project').write_text('(lang dune 3.22)\n(name checklist_private)\n')
    config = c.parse((Path(manifest['project_root']) / 'hardcaml-workbench-asic.sexp').read_text())
    project = field(config, 'project_executable')
    wrapper = root / 'prospective-readonly'
    # Exact known public references and exact declared flow/profile/endpoint only.
    # The private source-root is forwarded to the real source tree for genuine
    # planning metadata; both argv versions are retained. Run/finalize fail closed.
    wrapper.write_text('#!' + sys.executable + '\n' +
        'import json, os, sys, subprocess, copy, time\nfrom pathlib import Path\n' +
        'a=sys.argv[1:]; b=list(a); target=None\n' +
        'ref=' + repr({k: reference[k] for k in ('attempt', 'stream_id', 'execution_file')}) + '\n' +
        'if a==["--version","--json"]: target=' + repr(manifest['provider']) + '\n' +
        'if a==["observation","inspect",ref["attempt"],"--json"] or a==["report",ref["execution_file"],"--json"]: target=' + repr(manifest['provider']) + '\n' +
        'if len(a)==8 and a[:6]==["observation","read-updates",ref["attempt"],"--stream-id",ref["stream_id"],"--after"] and a[6].isdigit() and a[7]=="--json": target=' + repr(manifest['provider']) + '\n' +
        'if a==["flow","list","--json"] or a==["flow","describe","--flow","standard","--json"]: target=' + repr(project) + '\n' +
        'head=["flow","plan","--flow","standard","--profile"]\n' +
        'if len(a)>=11 and a[:5]==head and a[5] in ["balanced","synth_delay"] and a[6:11]==["--endpoint","routing","--source-root",' + repr(str(root)) + ',"--json"] and a[11:] in [[],["--set","SYNTH_ABC_BUFFERING=true"]]:\n' +
        ' target=' + repr(project) + '; b[9]=' + repr(manifest['project_root']) + '\n' +
        'with Path(' + repr(str(base / 'provider-calls.jsonl')) + ').open("a") as f: f.write(json.dumps(dict(argv=a,forwarded=b,allowed=target is not None))+"\\n")\n' +
        'if target is None: raise SystemExit("prospective/read-only exact allowlist rejected command")\n' +
        'os.chdir(' + repr(manifest['project_root']) + ')\n' +
        'mode=' + repr(mode) + '\n' +
        'if a==["flow","list","--json"] and mode=="changed-context":\n' +
        ' gate=Path(' + repr(str(base / 'discovery-gate')) + '); gate.with_suffix(".entered").write_text("entered")\n' +
        ' deadline=time.monotonic()+20\n' +
        ' while not gate.with_suffix(".release").exists():\n' +
        '  if time.monotonic()>deadline: raise SystemExit("private discovery gate timeout")\n' +
        '  time.sleep(.05)\n' +
        'if a==["flow","list","--json"] and mode in ["default-not-first","nonfresh","unsupported-endpoint"]:\n' +
        ' j=json.loads(subprocess.check_output([target]+b))\n' +
        ' if mode=="default-not-first":\n' +
        '  decoy=copy.deepcopy(j["declaration"]["entries"][0]); decoy["methodology"]["id"]="decoy-first"; j["declaration"]["entries"].insert(0,decoy)\n' +
        ' elif mode=="nonfresh": j["capabilities"]["input"]="checkpoint"\n' +
        ' else: j["declaration"]["entries"][0]["methodology"]["endpoints"].remove("routing")\n' +
        ' print(json.dumps(j)); raise SystemExit(0)\n' +
        'os.execv(target,[target]+b)\n')
    wrapper.chmod(0o700)
    for entry in config:
        if entry[0] in ('project_executable', 'provider_executable'): entry[1] = str(wrapper)
        if entry[0] == 'results_root': entry[1] = str(base / 'results')
    (root / 'hardcaml-workbench-asic.sexp').write_text(sexp(config))
    profile = 'synth_delay' if mode == 'remembered' else 'balanced'
    assignments = ['SYNTH_ABC_BUFFERING=true'] if mode == 'remembered' else []
    if mode in ('remembered', 'stale-profile'):
        preference(base, [['flow', 'standard'], ['profile', 'obsolete-explicit' if mode == 'stale-profile' else profile], ['endpoint', 'synthesis'], ['assignments', assignments]])
    daemon, terminal = consistency.PrivateDaemon(args, base), None
    try:
        http = daemon.start()
        ref = [[k, reference[k]] for k in ('attempt', 'stream_id')]
        http.rpc('(Register %s)' % sexp(ref), wait=False)
        run = wait(lambda: next(iter(field(http.rpc(wait=False), 'runs')), None), 'exact registration')
        require(field(run, 'reference') == ref, 'Registered actual public stream identity')
        http.rpc('(Observe %s)' % sexp(field(run, 'run')), wait=False)
        run = wait(lambda: r if (r := field(http.rpc(wait=False), 'runs')[0]) and consistency.stage_status(r) == dict(zip(consistency.STAGES, ['Completed'] + ['Not_requested'] * 5)) else None, 'actual synthesis-only stages')
        check(not field(run, 'selection'), mode + ': historical Register has selection=None; cannot infer launch inputs from history')
        setup_workspace(http, field(run, 'run'), presets)
        daemon.stop()
        http = daemon.start()  # persisted observation, deliberately cold catalog
        cold = http.rpc(wait=False)
        check(not field(cold, 'flows') and not field(cold, 'preview'), mode + ': restarted daemon has no catalog/preview')
        check(all(not field(s, 'action') for s in field(field(cold, 'runs')[0], 'stages')), mode + ': real observation has no explicit stage actions')
        save(base / 'cold-snapshot.json', cold)
        terminal = c.Terminal(base, args, daemon.url, 180, 55)
        terminal.capture('cold-overview', ['stage checklist', 'Synthesis:', 'completed'])
        terminal.open_palette('Launch planned run without view')
        terminal.capture('launch-visible-before-plan', ['Launch', 'No preview:', 'stage r'])
        terminal.key(b'\x1b')
        check(not any(x['argv'][:2] in (['flow', 'list'], ['flow', 'describe'], ['flow', 'plan']) for x in calls(base)), mode + ': passive rendering/palette does not discover or plan')
        zoom(http, 'stage-checklist')
        terminal.capture('checklist-focused', ['stage checklist', 'Overview | run'], ['╭ session'])
        terminal.key(b'k' * 10)
        terminal.key(b'j' * 6)
        terminal.key(b'k')
        terminal.capture('routing-selected', ['> · routing:', 'not requested'])
        terminal.key(b'r')
        if mode == 'changed-context':
            wait(lambda: (base / 'discovery-gate.entered').exists(), 'real metadata discovery gated')
            ws = http.rpc(domain='workspace')
            overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
            context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
            http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run ()))' %
                        (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision')))
            terminal.capture('captured-context-changed', ['run none', 'Run: none selected'])
            (base / 'discovery-gate.release').write_text('release')
            wait(lambda: field(http.rpc(wait=False), 'flows'), 'late discovery response completed')
            terminal.drain(1)
            terminal.open_palette('Launch planned run without view')
            terminal.capture('late-reply-launch-disabled', ['Launch', 'context changed'])
            terminal.key(b'\r'); terminal.key(b'\x1b')
            final = http.rpc(wait=False)
            check(not field(final, 'preview') and not field(final, 'launches'), 'Changed captured context fences late discovery reply')
            check(not any(x['argv'][:2] == ['flow', 'plan'] for x in calls(base)), 'Late discovery cannot retarget Plan after context change')
            save(base / 'final-snapshot.json', final)
            return
        if mode in ('stale-profile', 'nonfresh', 'unsupported-endpoint'):
            reason = 'Selected profile unavailable' if mode == 'stale-profile' else 'Unsupported fresh endpoint'
            wait(lambda: field(http.rpc(wait=False), 'flows'), 'negative discovery completed')
            terminal.drain(1)
            terminal.open_palette('Launch planned run without view')
            terminal.capture('negative-visible-disabled-launch', ['Launch', reason])
            terminal.key(b'\r'); terminal.key(b'\x1b')
            final = http.rpc(wait=False)
            check(not field(final, 'preview') and not field(final, 'launches'), mode + ': rejected mapping has no preview or producer')
            check(not any(x['argv'][:2] == ['flow', 'plan'] for x in calls(base)), mode + ': rejected mapping never reaches real planner')
            save(base / 'final-snapshot.json', final)
            return
        preview = wait(lambda: next(iter(field(http.rpc(wait=False), 'preview')), None), 'real explicit routing preview', timeout=40)
        check(dict(field(preview, 'selection')) == dict(flow='standard', profile=profile, endpoint='routing', assignments=assignments), mode + ': exact resolved selection/profile/assignments')
        check(field(preview, 'plan_identity'), mode + ': genuine plan identity retained')
        plan_json = json.loads(field(preview, 'plan_json'))
        check(plan_json['contract'] == 'hardcaml-asic.methodology-plan' and plan_json['methodology']['snapshot']['selected'] == dict(flow='standard', profile=profile), mode + ': real public plan metadata confirms exact flow/profile')
        terminal.command('Unzoom workspace')
        terminal.capture('real-ready-plan', ['ready:', 'flow: standard / profile: ' + profile, 'endpoint: routing'])
        terminal.open_palette('Launch planned run without view standard / ' + profile + ' → routing')
        terminal.capture('real-launch-enabled-never-pressed', ['Launch planned run without view standard / ' + profile + ' → routing'], ['No preview:', 'pending, failed', 'No matching commands'])
        terminal.key(b'\x1b')
        final = http.rpc(wait=False)
        check(not field(final, 'launches') and len(field(final, 'runs')) == 1, mode + ': planning never launches/allocates a real producer')
        observed_calls = calls(base)
        check(all(x['allowed'] for x in observed_calls), mode + ': every provider call was allowlisted')
        check(sum(x['argv'] == ['flow', 'list', '--json'] for x in observed_calls) == 1 and sum(x['argv'][:2] == ['flow', 'plan'] for x in observed_calls) == 1, mode + ': explicit r performs one bounded discovery and one plan')
        save(base / 'final-snapshot.json', final)
        save(base / 'exact-preview.json', preview)
    finally:
        if terminal is not None: terminal.close()
        daemon.stop()


def synthetic_case(args, check):
    base = c.demo.prepare(args.evidence / 'synthetic', manual=True, delay=.05)
    for name in ('home', 'config', 'client-state'): (base / name).mkdir()
    wrapper = base / 'project/synthetic-flow'
    original = wrapper.read_text()
    control = base / 'plan-control'
    wrapper.write_text('#!' + sys.executable + '\nimport sys,time\nfrom pathlib import Path\n' +
        'c=Path(' + repr(str(control)) + ')\n' +
        'if sys.argv[1:3]==["flow","plan"] and c.exists():\n' +
        ' c.with_suffix(".entered").write_text("entered")\n' +
        ' deadline=time.monotonic()+25\n' +
        ' while not c.with_suffix(".release").exists():\n' +
        '  if time.monotonic()>deadline: raise SystemExit("private plan gate timeout")\n' +
        '  time.sleep(.05)\n' +
        ' if c.read_text()=="fail": raise SystemExit("INJECTED checklist plan failure")\n' + original.split('\n', 1)[1])
    daemon, terminal = consistency.PrivateDaemon(args, base), None
    try:
        daemon.start()
        http, _ = c.demo.seed(base, daemon.url, args.preset_export)
        daemon.histories.append(http.history)
        def snapshot(): return http.rpc(wait=False)
        def producers():
            return [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()
                    if json.loads(line)['argv'][:2] == ['flow', 'run'] or json.loads(line)['argv'][:1] == ['finalize']]
        terminal = c.Terminal(base, args, daemon.url, 180, 55)
        terminal.capture('synthetic-initial', ['stage checklist'])
        terminal.open_palette('Launch planned run without view')
        terminal.capture('synthetic-launch-visible-unprepared', ['Launch', 'No preview:', 'stage r'])
        terminal.key(b'\r')
        check(not field(snapshot(), 'launches') and not producers(), 'Synthetic disabled Launch Enter starts no producer')
        terminal.key(b'\x1b')
        zoom(http, 'stage-checklist')
        terminal.capture('synthetic-checklist-focused', ['stage checklist', 'Overview | run'], ['╭ session'])
        terminal.key(b'k' * 10); terminal.key(b'j' * 3); terminal.key(b'r')
        old = wait(lambda: next(iter(field(snapshot(), 'preview')), None), 'synthetic placement preview')
        check(field(field(old, 'selection'), 'endpoint') == 'placement', 'Synthetic r plans exact keyboard-selected placement')
        control.write_text('fail')
        terminal.key(b'j'); terminal.key(b'r')
        wait(lambda: control.with_suffix('.entered').exists(), 'gated synthetic plan pending')
        terminal.command('Unzoom workspace')
        terminal.capture('synthetic-new-plan-pending', ['pending:', 'endpoint: cts'])
        terminal.open_palette('Launch planned run without view')
        terminal.capture('synthetic-launch-pending-disabled', ['Launch', 'No preview: Requested plan pending;'], ['Launch planned run without view synthetic / success → placement ['])
        terminal.key(b'\r'); terminal.key(b'\x1b')
        check(not producers() and not field(snapshot(), 'launches'), 'Pending replacement cannot launch old ready preview')
        control.with_suffix('.release').write_text('release')
        terminal.capture('synthetic-plan-failed', ['failed:'])
        terminal.open_palette('Launch planned run without view')
        terminal.capture('synthetic-launch-failed-visible', ['Launch', 'No preview:'])
        terminal.key(b'\r'); terminal.key(b'\x1b')
        check(not producers() and not field(snapshot(), 'launches'), 'Failed replacement cannot launch old ready preview')
        control.unlink()
        zoom(http, 'stage-checklist')
        terminal.capture('synthetic-retry-checklist-focused', ['stage checklist', 'Overview | run'], ['╭ session'])
        terminal.key(b'r')
        preview = wait(lambda: next((p for p in field(snapshot(), 'preview') if field(field(p, 'selection'), 'endpoint') == 'cts'), None), 'synthetic retry ready')
        terminal.command('Unzoom workspace')
        terminal.capture('synthetic-retry-ready', ['ready:', 'endpoint: cts'])
        terminal.type_action('launch and vi', 'Launch and view planned run', 'synthetic-manual-selected-action')
        launch = wait(lambda: next((l for l in field(snapshot(), 'launches') if field(l, 'run_id')), None), 'exact one synthetic allocation')
        check(field(launch, 'preview') == preview and len(field(snapshot(), 'launches')) == 1, 'Synthetic exact submitted preview and one durable launch reservation')
        run = next(r for r in field(snapshot(), 'runs') if field(field(r, 'run'), 'id') in field(launch, 'run_id'))
        check(field(run, 'selection') == [field(preview, 'selection')], 'Synthetic allocation keeps exact selected recipe')
        check(len(producers()) == 1 and producers()[0][:2] == ['flow', 'run'], 'Exactly one synthetic producer from explicit Launch')
        save(base / 'exact-preview.json', preview)
        save(base / 'exact-launch.json', launch)
        save(base / 'final-snapshot.json', snapshot())
        http.rpc('(Cancel %s)' % sexp('run:' + field(launch, 'key')), wait=False)
        wait(lambda: any(field(op, 'key') == 'run:' + field(launch, 'key') and field(op, 'state') == 'failed' for op in field(snapshot(), 'operations')), 'owned synthetic cleanup')
    finally:
        if terminal is not None: terminal.close()
        daemon.stop()


def quick_case(args, check, view=True, failure=False, changed=False, named=False):
    label = 'named-view' if named else 'quick-' + ('changed' if changed else 'failure' if failure else 'view' if view else 'no-view')
    base = c.demo.prepare(args.evidence / label, manual=True, delay=.05)
    for name in ('home', 'config', 'client-state'): (base / name).mkdir()
    gate = base / 'plan-gate'
    wrapper = base / 'project/synthetic-flow'
    original = wrapper.read_text()
    wrapper.write_text('#!' + sys.executable + '\nimport sys,time\nfrom pathlib import Path\n' +
        'g=Path(' + repr(str(gate)) + ')\n' +
        'if sys.argv[1:3]==["flow","plan"] and "placement" in sys.argv:\n' +
        ' g.with_suffix(".entered").write_text("entered")\n' +
        (' while not g.exists(): time.sleep(.05)\n' if changed else '') +
        (' raise SystemExit("INJECTED quick plan failure")\n' if failure else '') +
        original.split('\n', 1)[1])
    daemon, terminal = consistency.PrivateDaemon(args, base), None
    try:
        daemon.start()
        http, _ = c.demo.seed(base, daemon.url, args.preset_export)
        daemon.histories.append(http.history)
        def snapshot(): return http.rpc(wait=False)
        def context_run():
            ws = http.rpc(domain='workspace')
            overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
            return field(next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context')), 'selected_run')
        before = context_run()
        if failure or changed:
            http.rpc('(Plan ((flow synthetic) (profile success) (endpoint synthesis) (assignments ())))', wait=False)
            wait(lambda: field(snapshot(), 'preview'), 'unrelated retained synthesis preview')
        terminal = c.Terminal(base, args, daemon.url, 180, 55)
        terminal.capture(label + '-initial', ['stage checklist'])
        if not view:
            terminal.command('Quick-launch behavior: keep current context')
            terminal.drain(.5)
            terminal.close()
            terminal = c.Terminal(base, args, daemon.url, 180, 55)
            terminal.capture(label + '-restarted', ['stage checklist'])
            terminal.open_palette('Quick-launch behavior: keep current context')
            terminal.capture(label + '-restart-preference', ['keep current context (selected)'])
            terminal.key(b'\x1b')
            check(True, 'No-view R preference survives a fresh client process')
        zoom(http, 'stage-checklist')
        terminal.capture(label + '-focused', ['stage checklist'])
        terminal.key(b'k' * 12); terminal.key(b'j' * 3)
        if named:
            # Keep the actual palette action captured while an ordinary Observe
            # replaces the advertised action. Enter must reject the stale closure.
            ref_run = next(r for r in field(snapshot(), 'runs') if [field(r, 'run')] == before)
            reference = field(ref_run, 'reference')
            observation = Path(field(reference, 'attempt')) / 'observation.json'
            original_observation = observation.read_text()
            stale = json.loads(original_observation)
            stage = next(s for s in stale['stage_plan']['stages'] if s['id'] == 'synthesis')
            stage.pop('action', None)
            terminal.open_palette('launch syn')
            terminal.capture(label + '-captured-before-drift', ['> Launch synthesis and view'])
            observation.write_text(json.dumps(stale))
            http.rpc('(Observe %s)' % sexp(field(ref_run, 'run')), wait=False)
            wait(lambda: not field(next(s for r in field(snapshot(), 'runs') if field(r, 'run') == field(ref_run, 'run')
                                        for s in field(r, 'stages') if field(s, 'id') == 'synthesis'), 'action'),
                 'advertised synthesis action withdrawn')
            terminal.drain(1)
            terminal.key(b'\r'); terminal.key(b'\x1b')
            terminal.drain(1)
            check(not field(snapshot(), 'launches'), 'Stale captured named action cannot launch after capability withdrawal')
            check(not any(json.loads(line)['argv'][:2] == ['flow', 'plan']
                          for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()),
                  'Stale named action is rejected before planning')
            observation.write_text(original_observation)
            http.rpc('(Observe %s)' % sexp(field(ref_run, 'run')), wait=False)
            wait(lambda: field(next(s for r in field(snapshot(), 'runs') if field(r, 'run') == field(ref_run, 'run')
                                    for s in field(r, 'stages') if field(s, 'id') == 'synthesis'), 'action'),
                 'advertised synthesis action restored')
            terminal.drain(1)
            terminal.type_action('launch syn', 'Launch synthesis and view', label + '-selected-action')
        elif failure or changed:
            terminal.key(b'R')
        else:
            terminal.type_action('quick lau', 'Quick launch selected stage', label + '-selected-action')
        if not named:
            wait(lambda: gate.with_suffix('.entered').exists(), 'quick plan dispatched')
        if changed:
            ws = http.rpc(domain='workspace')
            overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
            context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
            http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run ()))' %
                        (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision')))
            terminal.capture(label + '-changed', ['Run: none selected'])
            gate.write_text('release')
        if failure or changed:
            terminal.drain(2)
            check(not field(snapshot(), 'launches'), label + ': async plan never launches stale unrelated preview after failure/selection change')
            return
        launch = wait(lambda: next((l for l in field(snapshot(), 'launches') if field(l, 'run_id')), None), label + ' exact allocation')
        endpoint = 'synthesis' if named else 'placement'
        check(field(field(launch, 'preview'), 'selection') == [['flow', 'synthetic'], ['profile', 'success'], ['endpoint', endpoint], ['assignments', []]], label + ': launches exact selected plan')
        wait(lambda: context_run() == [field(next(r for r in field(snapshot(), 'runs') if field(field(r, 'run'), 'id') in field(launch, 'run_id')), 'run')] if view or named else context_run() == before, label + ' context policy')
        terminal.drain(1)
        provider_calls = [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]
        producer_calls = [a for a in provider_calls if a[:2] == ['flow', 'run']]
        check(sum(a[:2] == ['flow', 'plan'] for a in provider_calls) == 1,
              label + ': action plans exactly once')
        check(len(field(snapshot(), 'launches')) == 1 and len(producer_calls) == 1, label + ': action stages then launches exactly once')
        check(context_run() != before if view or named else context_run() == before, label + ': selected linked context follow=' + str(view or named))
        expected_pref = 'view launched run' if view else 'keep current context'
        terminal.open_palette('Quick-launch behavior: ' + expected_pref)
        terminal.capture(label + '-preference-unchanged', [expected_pref + ' (selected)'])
        terminal.key(b'\x1b')
        check(True, label + ': action does not mutate quick-launch preference')
        save(base / 'exact-launch.json', launch)
    finally:
        if terminal is not None: terminal.close()
        daemon.stop()


def selected_async_case(args, check, change):
    """Hold a real Plan after palette acceptance, then invalidate only client-local
    selection or current capability evidence. Neither mutation changes the context."""
    label = 'selected-async-' + change
    base = c.demo.prepare(args.evidence / label, manual=True, delay=.05)
    for name in ('home', 'config', 'client-state'): (base / name).mkdir()
    gate, withdraw = base / 'plan-gate', base / 'withdraw-capability'
    wrapper = base / 'project/synthetic-flow'
    original = wrapper.read_text()
    wrapper.write_text('#!' + sys.executable + '\nimport sys,time\nfrom pathlib import Path\n' +
        'g=Path(' + repr(str(gate)) + ')\n' +
        'if sys.argv[1:3]==["flow","plan"] and "placement" in sys.argv:\n' +
        ' g.with_suffix(".entered").write_text("entered")\n' +
        ' deadline=time.monotonic()+30\n' +
        ' while not g.exists():\n' +
        '  if time.monotonic()>deadline: raise SystemExit("selected Plan gate timeout")\n' +
        '  time.sleep(.05)\n' + original.split('\n', 1)[1])
    if change == 'capability':
        settings = base / 'project/synthetic-settings.json'
        settings.write_text(json.dumps(dict(json.loads(settings.read_text()), executable_timing=True)))
        provider = base / 'project/synthetic-provider/provider.py'
        provider.write_text(provider.read_text().replace("STAGES = SCENARIOS['stages']",
            "STAGES = SCENARIOS['stages']\n" +
            'if sys.argv[1:3] in (["flow","list"],["flow","describe"]) and Path(' + repr(str(withdraw)) + ').exists():\n' +
            '    STAGES = [s for s in STAGES if s != "placement"]'))
    daemon, terminal = consistency.PrivateDaemon(args, base), None
    try:
        daemon.start()
        http, _ = c.demo.seed(base, daemon.url, args.preset_export)
        daemon.histories.append(http.history)
        def snapshot(): return http.rpc(wait=False)
        registry = http.rpc(domain='workspace')
        overview = next(w for w in field(registry, 'workspaces') if field(w, 'preset') == ['overview'])
        context = next(x for x in field(registry, 'contexts') if field(x, 'id') == field(overview, 'context'))
        run = field(context, 'selected_run')[0]
        execution = next(r for r in field(snapshot(), 'runs') if field(r, 'run') == run)
        observation = Path(field(field(execution, 'reference'), 'attempt')) / 'observation.json'
        def withdraw_action():
            payload = json.loads(observation.read_text())
            next(s for s in payload['stage_plan']['stages'] if s['id'] == 'placement').pop('action', None)
            observation.write_text(json.dumps(payload))
            http.rpc('(Observe %s)' % sexp(run), wait=False)
            wait(lambda: not field(next(s for r in field(snapshot(), 'runs') if field(r, 'run') == run
                                       for s in field(r, 'stages') if field(s, 'id') == 'placement'), 'action'),
                 label + ' action withdrawn')
        if change == 'capability':
            withdraw_action()
            check('placement' in field(next(f for f in field(snapshot(), 'flows') if field(f, 'id') == 'synthetic'), 'fresh_stage_endpoints'),
                  label + ': initial selected row is authorized by fresh capability, not an action')
        terminal = c.Terminal(base, args, daemon.url, 180, 55)
        terminal.capture(label + '-initial', ['stage checklist'])
        zoom(http, 'stage-checklist')
        terminal.capture(label + '-focused', ['stage checklist'])
        terminal.key(b'k' * 12); terminal.key(b'j' * 3)
        terminal.type_action('quick lau', 'Quick launch selected stage', label + '-captured-action')
        wait(lambda: gate.with_suffix('.entered').exists(), label + ' Plan held')
        before = http.rpc(domain='workspace')
        if change == 'cursor':
            terminal.key(b'j')
            terminal.capture(label + '-changed-local-cursor', ['> ✓ CTS:'])
        elif change == 'action':
            withdraw_action()
        else:
            withdraw.write_text('withdraw')
            http.rpc('Discover', wait=False)
            wait(lambda: (flow := next((f for f in field(snapshot(), 'flows') if field(f, 'id') == 'synthetic'), None)) is not None
                         and 'placement' not in field(flow, 'fresh_stage_endpoints'),
                 label + ' fresh capability withdrawn')
        terminal.drain(1)
        after = http.rpc(domain='workspace')
        check(before == after, label + ': invalidation does not change registry/context capture')
        gate.write_text('release')
        wait(lambda: any(field(field(p, 'selection'), 'endpoint') == 'placement' for p in field(snapshot(), 'preview')),
             label + ' exact old-row Plan completed')
        terminal.drain(1.5)
        calls = [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]
        check(sum(a[:2] == ['flow', 'plan'] for a in calls) == 1, label + ': captured old selection planned exactly once')
        check(not field(snapshot(), 'launches') and not any(a[:2] == ['flow', 'run'] for a in calls),
              label + ': invalidated selected shortcut allocates no run and starts no producer')
        save(base / 'final-snapshot.json', snapshot())
        terminal.capture(label + '-stopped')
    finally:
        gate.write_text('release')
        if terminal is not None: terminal.close()
        daemon.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--real-demo', type=Path, default=real.EXAMPLE / '.dev/workbench-real-demo')
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--case', action='append', choices=('historical-default', 'remembered', 'default-not-first', 'stale-profile', 'nonfresh', 'unsupported-endpoint', 'changed-context', 'synthetic', 'selected-async'), help='diagnostic subset; omit for complete acceptance')
    args = parser.parse_args()
    args.evidence = (args.evidence or Path('/tmp/opencode') / ('checklist-workflow-' + secrets.token_hex(6))).resolve()
    require(args.evidence.is_relative_to('/tmp/opencode'), 'Private evidence required')
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=False)
    for name in ('daemon', 'client', 'preset_export'): setattr(args, name, getattr(args, name).resolve(strict=True))
    result = dict(status='failed', checks=[], evidence=str(args.evidence), cases=args.case or 'complete', binaries=consistency.hashes([args.daemon, args.client, args.preset_export]))
    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)
    before = None
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Checklist budget exhausted')))
    signal.alarm(args.timeout)
    try:
        manifest, references, before = consistency.inventory(args)
        presets = c.demo.workspace_presets(args.preset_export)
        for mode in ('historical-default', 'remembered', 'default-not-first', 'stale-profile', 'nonfresh', 'unsupported-endpoint', 'changed-context'):
            if args.case and mode not in args.case: continue
            real_case(args, manifest, references[1], presets, mode, check)
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
        if before is not None:
            after = consistency.hashes(map(Path, before))
            save(args.evidence / 'canonical-after.json', after)
            if after != before:
                result['status'] = 'failed'
                result['canonical_hash_error'] = 'Canonical files changed'
        save(args.evidence / 'result.json', result)
    require(result['status'] == 'passed', str(result))
    print('PASS checklist launch workflow: ' + str(args.evidence), flush=True)


if __name__ == '__main__': main()
