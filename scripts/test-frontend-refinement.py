#!/usr/bin/env python3
"""Private native HTTP/PTY refinement acceptance; existing binaries, no builds/EDA.

Uses exported OCaml presets and real provider evidence. Retains SVG cell screenshots,
ANSI/color cells, key/HTTP/provider logs and result.json under /tmp/opencode.
Only owned client/daemon processes are cleaned up. Default wall-clock budget: 300s.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('refinement_composition', HERE / 'test-frontend-composition.py')
composition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composition)
field, sexp, require, wait = composition.field, composition.sexp, composition.require, composition.wait


def pane_body(screen, title):
    """Actual framed pane cells, excluding title/borders and horizontal inset."""
    lines = screen.lines()
    top = next(y for y, line in enumerate(lines) if title.casefold() in line.casefold())
    title_x = lines[top].casefold().index(title.casefold())
    left = lines[top].rfind('╭', 0, title_x)
    right = lines[top].index('╮', title_x)
    bottom = next(y for y in range(top + 1, len(lines)) if lines[y][left:left + 1] == '╰')
    return [line[left + 1:right].strip() for line in lines[top + 1:bottom]]


def acceptance(t, check, http, runs, presets):
    def snapshot(): return http.rpc(domain='workspace')
    def mutate(op): return http.mutate(snapshot(), op)
    def calls():
        return [json.loads(line)['argv'] for line in (t.base / 'project/provider-calls.jsonl').read_text().splitlines()]
    def producers(): return [a for a in calls() if a[:2] == ['flow', 'run'] or a[:1] == ['finalize']]
    def plans(): return [a for a in calls() if a[:2] == ['flow', 'plan']]
    producers_before, plans_before = producers(), plans()
    original = snapshot()
    main_id = field(original, 'main_context')
    main_before = next(c for c in field(original, 'contexts') if field(c, 'id') == main_id)
    overview = next(w for w in field(original, 'workspaces') if field(w, 'preset') == ['overview'])
    overview_id = field(overview, 'id')

    t.command('Appearance: Color Vivid')
    t.command('Switch to Overview')
    overview_screen = t.capture('refinement-overview-120x40', [
        'Session', 'Runs', 'Stage checklist', 'Synthesis', 'timing',
        'placement', 'routing', 'checks', 'finalization', 'Reported cells (agg.): 128',
        'Aggregate Setup slack: 0.42 ns', 'Check drc: pass'])
    lines = overview_screen.lines()
    nav_y = next(y for y, line in enumerate(lines) if '[1 Overview]' in line)
    session_y = next(y for y, line in enumerate(lines) if 'SESSION' in line)
    check(session_y == nav_y + 2 and not lines[nav_y + 1].strip(), 'One-row workspace tabs followed by exactly one normal gutter')
    check('╭' in lines[session_y] and '╮' in lines[session_y], 'Short Session and selector retain rounded title frames')
    selector_y = next(y for y, line in enumerate(lines) if 'RUNS ' in line)
    check(selector_y == session_y, 'Session and wide shallow selector share the upper band')
    for number in (3, 4):
        label = f'synthetic-long-distinguishable-run-reference-{number}-suffix'
        check(label in overview_screen.text(), 'Run selector uses available width for full distinguishable label: ' + label)
    stage_names = ['Synthesis', 'Floorplan', 'Placement', 'CTS', 'Routing', 'Signoff']
    strip = [line for line in lines if ': completed' in line and any(name in line for name in stage_names)]
    check(all(any(name + ': completed' in line for line in strip) for name in stage_names), 'Horizontal progression exposes all six explicit stage outcomes')
    check(any(sum(name + ': completed' in line for name in stage_names) > 1 for line in strip), 'Multiple stages share horizontal rows')
    check('Selected:' in overview_screen.text(), 'Horizontal strip retains a separate selected-stage line')
    check('Acceptance (agg.): not_evaluated' in overview_screen.text(), 'Compact finalization preserves explicit not-evaluated acceptance despite completed physical flow')

    # Assert palette chrome against actual ANSI cell attributes and bounded geometry.
    t.open_palette('ap col')
    palette = t.capture('refinement-palette-rounded', ['COMMAND PALETTE', 'Color Vivid'])
    top = next(y for y, line in enumerate(palette.lines()) if 'COMMAND PALETTE' in line)
    left = palette.lines()[top].index('╭ COMMAND PALETTE')
    right = palette.lines()[top].index('╮', left) + 1
    check(right - left == 88, 'Palette title is embedded in rounded bounded top border')
    footer_y = next(y for y, line in enumerate(palette.lines()) if 'Esc' in line and ('Tab' in line or 'execute' in line))
    check(not palette.lines()[footer_y - 1][left:right].strip(' │'), 'Palette reserves a blank separator before footer')
    query_y = next(y for y, line in enumerate(palette.lines()) if 'ap col' in line)
    query_line = palette.lines()[query_y]
    prompt_x = query_line.index('>', left)
    check(palette.cells[query_y][prompt_x][1][0] != 'default', 'Palette prompt has explicit ANSI foreground styling')
    check(any(char in ('│', '▏', '█', '▌') and attrs[0] != 'default'
              for char, attrs in palette.cells[query_y][prompt_x + 1:-1]), 'Palette query caret is visible and colored')
    t.key(b'\x1b')

    # Selector row-cap changes must increase its real viewport, not merely metadata.
    before_expand = t.capture('selector-height-before')
    t.command('Run selector: More visible rows (+1)')
    t.capture('selector-five-row-cap', ['5/6'])
    t.command('Run selector: More visible rows (+1)')
    expanded = t.capture('selector-height-after', ['6/6'])
    bottom = lambda s: next(y for y, line in enumerate(s.lines()) if y > session_y and line.count('╰') >= 1 and line.rfind('╰') > 20)
    check(bottom(expanded) > bottom(before_expand), 'Increasing row cap grows the actual selector outer viewport')
    check(sum('asic/' in line for line in expanded.lines()[selector_y + 1:bottom(expanded)]) == 6, 'Expanded selector renders six distinct real runs')
    t.command('Reset presentation overrides (inherit)')
    t.capture('selector-height-reset', ['4/6'])
    t.key(b'/'); t.key(b'synthetic-long-distinguishable'); t.key(b'\r')
    two = t.capture('selector-two-matching-runs', ['Runs 2/2 (cap 4)'])
    check(sum('asic/synthetic-long-distinguishable' in line for line in two.lines()[selector_y + 1:bottom(two)]) == 2, 'Selector reports actual two matching runs, not requested four-row capacity')
    t.key(b'\x15'); t.capture('selector-filter-reset', ['Runs 4/6 (cap 4)'])

    # Focus the exact checklist through public zoom semantics, then browse without
    # executing its advertised action. Identity is independently checked over HTTP.
    checklist = next(tile for tile in field(snapshot(), 'tiles') if field(tile, 'workspace') == overview_id and field(tile, 'kind') == 'stage-checklist')
    mutate('(Set_zoom (workspace %s) (tile (%s)))' % (sexp(overview_id), sexp(field(checklist, 'id'))))
    t.capture('stage-focused', ['Stage checklist', 'Selected:'], ['Session'])
    t.key(b'j'); t.key(b'j'); t.key(b'\r')
    t.capture('stage-placement-exact-detail', ['Stage ID: placement', 'endpoint placement', 'Requested: true'])
    t.key(b'\x1b')
    check(plans() == plans_before and producers() == producers_before, 'Stage selection/detail browsing invokes neither planner nor producer')
    t.key(b'r')
    preview = wait(lambda: field(http.rpc(wait=False), 'preview'), 'exact checklist plan')[0]
    check(dict(field(preview, 'selection')) == dict(flow='synthetic', profile='success', endpoint='placement', assignments=[]), 'Explicit stage plan retains exact advertised endpoint/assignments')
    check(len(plans()) == len(plans_before) + 1 and producers() == producers_before, 'Explicit stage plan occurs exactly once without launching a producer')
    t.command('Unzoom workspace')

    # Dedicated Timing workspace, not a full-screen inspector. Increase available
    # cells for numeric ordering and full exact-row detail assertions.
    t.resize(180, 55)
    t.command('Inspect timing paths ' + field(runs[0], 'id'))
    timing = t.capture('refinement-timing-180x55', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', '12 paths', 'signoff'])
    check('session' in timing.text().casefold(), 'Timing investigation remains a composed workspace with Session visible')
    check(all(title.upper() in timing.text().upper() for title in ('Timing · Paths', 'Timing · Selected path', 'Timing · Provenance')), 'Timing has independent path/detail/provenance panes')
    # Zoom list only for complete row-order evidence, then restore all panes.
    t.command('Zoom focused tile')
    ascending = t.capture('timing-ascending', ['12 paths', 'hold path clk:reg16 -> reg23', 'setup path clk:reg5 -> reg12'])
    check(ascending.text().index('hold path clk:reg16 -> reg23') < ascending.text().index('setup path clk:reg5 -> reg12'), 'Timing numeric ascending order uses actual signed values')
    index = next(i for i in field(http.rpc(wait=False), 'inspections') if field(i, 'run') == runs[0] and field(i, 'domain') == 'timing' and field(i, 'stage') == 'signoff')
    ordered = sorted(field(index, 'rows'), key=lambda row: (float(field(row, 'value')[0]), field(row, 'id')))
    second_id = field(ordered[1], 'id')
    t.key(b'j'); t.key(b'\r')
    selected_detail = wait(lambda: [d for d in field(http.rpc(wait=False), 'inspection_details') if field(d, 'run') == runs[0] and field(d, 'source_digest') == field(index, 'source_digest') and field(d, 'row_id') == second_id], 'non-first selected path detail')[0]
    t.command('Unzoom workspace')
    second_screen = t.capture('timing-selected-second-row', ['Path: ' + field(ordered[1], 'name'), 'Timing · Paths', 'Timing · Provenance'])
    manifest = composition.demo.provider.load(t.base / 'manifest.json')
    source_details = composition.demo.provider.load(Path(manifest['runs'][0]['attempt']) / 'inspection-timing-signoff.json')['details']
    check(field(selected_detail, 'text') == source_details[second_id], 'j selects a non-first numeric row and cooperating detail loads that exact row/digest evidence')
    check(pane_body(second_screen, 'Timing · Selected path')[4] == source_details[second_id].splitlines()[0], 'Non-first selected path shows actual provider payload immediately on Detail line five')
    t.key(b'k')
    t.command('Zoom focused tile')
    t.key(b's')
    descending = t.capture('timing-descending', ['value ↓', 'hold path clk:reg16 -> reg23', 'setup path clk:reg5 -> reg12'])
    check(descending.text().index('setup path clk:reg5 -> reg12') < descending.text().index('hold path clk:reg16 -> reg23'), 'Timing sort reverses actual path order')
    t.key(b'c'); t.capture('timing-corner', ['Corner synthetic_'])
    t.key(b'c'); t.key(b'c')
    t.capture('timing-corner-all', ['Corner ALL'])
    t.key(b'g'); t.capture('timing-group', ['Group clk'])
    t.key(b'g'); t.key(b'g'); t.capture('timing-group-all', ['Group ALL'])
    t.key(b'/'); t.key(b'clk:reg0 -> reg7'); t.key(b'\r')
    t.capture('timing-filter', ['1 paths', 'Filter: clk:reg0 -> reg7', '0.42 ns'], ['hold path clk:reg16 -> reg23'])
    t.key(b'\r')
    t.command('Unzoom workspace')
    t.capture('timing-cooperating-detail', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', 'Path: SYNTHETIC setup path clk:reg0 -> reg7', 'Slack: 0.42 ns'])
    detail = wait(lambda: [d for d in field(http.rpc(wait=False), 'inspection_details') if field(d, 'run') == runs[0] and field(d, 'stage') == 'signoff' and field(d, 'row_id') == 'synthetic-timing-signoff'], 'exact selected Timing detail')[0]
    expected = source_details['synthetic-timing-signoff']
    check(field(detail, 'text') == expected and field(detail, 'error') == [], 'Enter loads exact retained selected-row detail, fenced by run/stage/digest/row')
    # Inspect actual cells at the target viewport: metadata occupies four rows,
    # with the real provider payload immediately below, without opening an overlay.
    t.resize(120, 40)
    polished = t.capture('refinement-timing-120x40', ['Slack: 0.42 ns', 'signoff: completed', 'No tool report or binary layout is claimed.'])
    body = pane_body(polished, 'Timing · Selected path')
    check(all(body[i].startswith(prefix) for i, prefix in enumerate(('Path:', 'Slack:', 'Corner:', 'Endpoints:'))), '120x40 Detail uses exactly four compact path/slack/axis/endpoint summary rows')
    check(body[4:4 + len(expected.splitlines())] == expected.splitlines(), '120x40 Detail exposes the complete exact provider text from line five within the actual visible panel height')
    lines = polished.lines()
    path_y = next(y for y, line in enumerate(lines) if 'TIMING · PATHS' in line)
    detail_y = next(y for y, line in enumerate(lines) if 'TIMING · SELECTED PATH' in line)
    context_y = next(y for y, line in enumerate(lines) if 'TIMING · PROVENANCE' in line)
    check(path_y == detail_y and context_y > detail_y and 'STAGE CHECKLIST' not in polished.text(), 'Fresh Timing preset has Paths left and Detail-over-Context right, without a vertical checklist')

    # Pane focus/scroll is independent of selected path and shared filter state.
    # At the polished large size this short provider payload fits without scrolling;
    # use a bounded shorter viewport to exercise real scroll rather than a no-op.
    t.resize(120, 32)
    t.key(b'\t'); t.key(b'j')
    scrolled = t.capture('timing-detail-pane-scrolled', ['1 paths', 'Filter: clk:reg0 -> reg7', 'Slack: 0.42 ns'])
    check(not pane_body(scrolled, 'Timing · Selected path')[0].startswith('Path:'), 'Independent Detail scroll moves its compact prefix while Paths selection/filter remain visible')
    t.key(b'k'); t.key(b'\x1b[Z')
    t.capture('timing-detail-pane-restored', ['Path: SYNTHETIC setup path clk:reg0 -> reg7', 'Slack: 0.42 ns'])
    check(True, 'Tab/Shift-Tab pane focus and detail scrolling retain exact path selection and filter')
    t.resize(180, 55)
    t.capture('refinement-timing-polished-180x55', ['Slack: 0.42 ns', 'No tool report or binary layout is claimed.'])

    # Full identity/source data moved to Context, so prove it is actually accessible
    # by scrolling that pane, without changing Paths or the selected Detail reader.
    selected_row = next(row for row in field(index, 'rows') if field(row, 'id') == 'synthetic-timing-signoff')
    normalize = lambda text: ''.join(text.split())
    t.key(b'\t'); t.key(b'\t')
    context_top = t.capture('timing-context-digest', ['Source digest:'])
    check(field(index, 'source_digest') in normalize(''.join(pane_body(context_top, 'Timing · Provenance'))), 'Context visibly preserves the full exact source digest')
    seen_row = seen_source = seen_fields = False
    for _ in range(100):
        screen = t.drain(.05)
        context = '\n'.join(pane_body(screen, 'Timing · Provenance'))
        seen_row |= 'Row: synthetic-timing-signoff' in context
        seen_source |= normalize(field(selected_row, 'source')) in normalize(context)
        seen_fields |= all(normalize(key + ': ' + value) in normalize(context) for key, value in field(selected_row, 'fields'))
        if seen_row and seen_source and seen_fields:
            t.save('timing-context-full-provenance', screen)
            break
        t.key(b'j')
    check(seen_row and seen_source and seen_fields, 'Context scrolling exposes exact selected-row identity, complete raw source JSON and all reported fields')
    check(expected.splitlines()[2] in '\n'.join(pane_body(screen, 'Timing · Selected path')), 'Context scrolling leaves the exact selected provider Detail visible and unchanged')
    t.key(b'k' * 100); t.key(b'\x1b[Z'); t.key(b'\x1b[Z')
    source = t.capture('timing-palette-source')
    t.open_palette('ap col'); t.key(b'\t'); t.key(b'\x1b[Z'); t.key(b'\x1b')
    check(t.capture('timing-palette-restored').cells == source.cells, 'Palette Tab/Shift-Tab/Esc restores exact Timing pane source and selection')
    t.resize(120, 40)
    t.capture('refinement-timing-polished-final-120x40', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', 'signoff: completed'])
    t.resize(180, 55)

    # Preserve an explicit pin in the existing Timing arrangement. Opening another
    # captured run must make an independent investigation instead of rebinding it.
    prior = snapshot()
    existing_timing = next(w for w in field(prior, 'workspaces') if field(w, 'preset') == ['timing'])
    pinned = next(tile for tile in field(prior, 'tiles') if field(tile, 'workspace') == field(existing_timing, 'id') and field(tile, 'kind') == 'timing-detail')
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(field(pinned, 'id')), sexp(runs[0])))
    t.capture('timing-pin-ready', ['PIN asic/' + field(runs[0], 'id')])
    prior = snapshot()
    t.command('Inspect timing paths ' + field(runs[1], 'id'))
    def opened_independent():
        current = snapshot()
        new = [w for w in field(current, 'workspaces') if field(w, 'id') not in {field(w, 'id') for w in field(prior, 'workspaces')}]
        return current if any(field(w, 'preset') == ['timing'] and any(field(c, 'id') == field(w, 'context') and field(c, 'selected_run') == [runs[1]] for c in field(current, 'contexts')) for w in new) else None
    after = wait(opened_independent, 'fully initialized independent captured-run Timing arrangement')
    t.capture('timing-independent-run-b', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', 'Run: ' + field(runs[1], 'id')])
    new_workspaces = [w for w in field(after, 'workspaces') if field(w, 'id') not in {field(w, 'id') for w in field(prior, 'workspaces')}]
    check(len(new_workspaces) == 1 and field(new_workspaces[0], 'preset') == ['timing'], 'Different captured run creates exactly one dedicated Timing arrangement when an existing pin conflicts')
    investigation = new_workspaces[0]
    context_id = field(investigation, 'context')
    check(context_id != main_id, 'Captured-run investigation has an independent context')
    check(next(c for c in field(after, 'contexts') if field(c, 'id') == main_id) == main_before, 'Opening different-run Timing protects Main selection and revision')
    check(next(tile for tile in field(after, 'tiles') if field(tile, 'id') == field(pinned, 'id')) == next(tile for tile in field(prior, 'tiles') if field(tile, 'id') == field(pinned, 'id')), 'Opening different-run Timing preserves exact existing pinned tile')
    context = next(c for c in field(after, 'contexts') if field(c, 'id') == context_id)
    check(field(context, 'selected_run') == [runs[1]], 'Independent investigation selects the exact captured run')
    for run, label in ((runs[0], 'a'), (runs[1], 'b')):
        current = snapshot()
        context = next(c for c in field(current, 'contexts') if field(c, 'id') == context_id)
        mutate('(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
               (sexp(field(investigation, 'id')), sexp(context_id), field(context, 'selection_revision'), sexp(run)))
        t.capture('timing-selection-invalidation-' + label, ['Run: ' + field(run, 'id')], ['Run: ' + field(runs[1 if label == 'a' else 0], 'id')])
    check(producers() == producers_before, 'All Timing browsing/filter/sort/detail/open/run changes invoke no EDA/finalization producer')
    check(len(plans()) == len(plans_before) + 1, 'Timing browsing invokes no additional planner')

    # FS1 non-timing overlays remain available above the workspace.
    for domain, title in [('clocks', 'Inspect clocks'), ('routing', 'Inspect routing')]:
        t.command(title + ' ' + field(runs[0], 'id'))
        t.capture('fs1-' + domain + '-overlay', ['INSPECT ' + domain])
        t.key(b'\x1b')
        t.capture('fs1-' + domain + '-restored', ['Timing · Paths', 'Timing · Provenance'], ['INSPECT ' + domain])
    t.command('Switch to Overview')
    t.resize(80, 24)
    t.capture('refinement-overview-80x24', ['Compact: focused tile only', 'Stage checklist'])
    check(t.process.poll() is None, 'Tiny focused fallback remains interactive')
    t.resize(240, 80)
    t.capture('refinement-overview-240x80', ['Reported cells (agg.)', 'placement', 'routing', 'checks', 'finalization'])
    t.resize(120, 40)
    t.capture('refinement-overview-final', ['Overview', 'Reported cells (agg.)'])
    (t.base / 'provider-calls-final.json').write_text(json.dumps(calls(), indent=2))
    return 'Overview'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    args.palette_only = False
    args.harness = 'frontend refinement'
    for name in ('daemon', 'client', 'preset_export'): setattr(args, name, getattr(args, name).resolve(strict=True))
    if args.evidence:
        require(args.evidence.resolve().is_relative_to('/tmp/opencode'), 'Evidence must be private /tmp/opencode state')
    else:
        args.evidence = Path('/tmp/opencode') / ('frontend-refinement-' + secrets.token_hex(6))
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Refinement wall-clock budget exhausted')))
    signal.alarm(args.timeout)
    def two_run_count(t, check, http, startup):
        check(len(field(http.rpc(wait=False), 'runs')) == 2, 'Two-run capacity fixture has exactly two real registered observations')
        screen = t.capture('selector-only-two-registered-runs', ['Runs 2/2 (cap 4)'])
        check(sum('asic/' in line for line in screen.lines()[:10]) == 2, 'With only two registered runs, selector labels and renders 2/2 instead of claiming four visible runs')
    try:
        two = argparse.Namespace(**vars(args))
        two.evidence = args.evidence.with_name(args.evidence.name + '-two-runs')
        two.palette_only = True
        two.harness = 'frontend refinement two-run capacity'
        composition.run(two, extra_runs=(), startup_check=two_run_count)
        args.related_evidence = [str(two.evidence)]
        composition.run(args, acceptance=acceptance)
    finally: signal.alarm(0)


if __name__ == '__main__': main()
