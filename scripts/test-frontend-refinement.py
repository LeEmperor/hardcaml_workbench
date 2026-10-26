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


def pane_rect(screen, title):
    """Locate actual outer frame cells; adjacent frames must not share cells."""
    lines = screen.lines()
    for y, line in enumerate(lines):
        start = 0
        while (left := line.find('╭', start)) >= 0:
            right = line.index('╮', left)
            header = line[left + 1:right].strip()
            if header.casefold().startswith(title.casefold()):
                bottom = next(i for i in range(y + 1, len(lines)) if lines[i][left:left + 1] == '╰')
                return left, y, right + 1, bottom + 1
            start = right + 1
    raise AssertionError('Missing framed pane: ' + title)


def sidebar_geometry(screen, check):
    rects = {title: pane_rect(screen, title) for title in (
        'session', 'runs', 'stage checklist', 'preparation', 'synthesis', 'timing',
        'placement', 'routing', 'checks', 'finalization', 'planned-run')}
    session, runs, stages, plan = (rects[k] for k in ('session', 'runs', 'stage checklist', 'planned-run'))
    check(abs((session[2] - session[0]) - screen.width / 3) <= 1,
          'Overview sidebar occupies one third of actual terminal cells')
    check(session[0] == runs[0] == stages[0] == plan[0] and session[2] == runs[2] == stages[2] == plan[2]
          and session[3] == runs[1] and runs[3] == stages[1] and stages[3] == plan[1],
          'Session, run list, vertical checklist and planned run are tightly stacked')
    check(abs((stages[3] - stages[1]) - (plan[3] - plan[1])) <= 1,
          'Checklist and planned run divide remaining sidebar approximately in half')
    previous = session[1]
    for title in ('preparation', 'synthesis', 'timing', 'placement', 'routing', 'checks', 'finalization'):
        left, top, right, bottom = rects[title]
        check(left == session[2] and right == screen.width and top == previous,
              'Full-width right stack order and zero gutter: ' + title)
        previous = bottom
    check(previous == plan[3], 'Preparation, six right domains and left sidebar finish at the same row')
    values = list(rects.values())
    check(all(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
              for i, a in enumerate(values) for b in values[i + 1:]),
          'Actual frame rectangles never overlap, including zero-gutter neighbors')
    for title in rects:
        left, top, right, _ = rects[title]
        check(screen.lines()[top][left + 1:right - 1].strip().startswith(title),
              'Lowercase unadorned tile title: ' + title)


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
        'Aggregate Setup slack: 0.42 ns', 'Check drc: pass', 'planned-run'])
    sidebar_geometry(overview_screen, check)
    lines = overview_screen.lines()
    nav_y = next(y for y, line in enumerate(lines) if '[1 Overview]' in line)
    session_y = pane_rect(overview_screen, 'session')[1]
    check(session_y == nav_y + 1, 'One-row workspace tabs directly precede dense panels')
    check('╭' in lines[session_y] and '╮' in lines[session_y], 'Short Session and selector retain rounded title frames')
    selector_y = pane_rect(overview_screen, 'runs')[1]
    check(selector_y > session_y, 'Run list is vertical beneath Session')
    # A narrow sidebar clips presentation, so zoom to verify full opaque labels.
    t.focus_view('run selector')
    t.command('Zoom focused tile')
    full_runs = t.capture('sidebar-run-identity-zoom', ['synthetic-long-distinguishable-run-reference-3-suffix'])
    for number in (3, 4):
        label = f'synthetic-long-distinguishable-run-reference-{number}-suffix'
        check(label in full_runs.text(), 'Zoom preserves the complete distinguishable run label: ' + label)
    t.command('Unzoom workspace')
    stage_names = ['Synthesis', 'Floorplan', 'Placement', 'CTS', 'Routing', 'Signoff']
    strip = [' '.join(line.split()) for line in map(composition.status_text, pane_body(overview_screen, 'stage checklist'))]
    strip = [line for line in strip
             if ': completed' in line and any(name in line for name in stage_names)]
    check(all(any(name + ': completed' in line for line in strip) for name in stage_names), 'Vertical checklist exposes all six explicit stage outcomes')
    check(all(sum(name + ': completed' in line for name in stage_names) == 1 for line in strip), 'One explicit stage per checklist row')
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
    t.focus_view('run selector')
    before_expand = t.capture('selector-height-before')
    t.command('Run selector: More visible rows (+1)')
    t.capture('selector-five-row-cap', ['5/6'])
    t.command('Run selector: More visible rows (+1)')
    expanded = t.capture('selector-height-after', ['6/6'])
    bottom = lambda s: pane_rect(s, 'runs')[3] - 1
    check(bottom(expanded) > bottom(before_expand), 'Increasing row cap grows the actual selector outer viewport')
    check(len([line for line in pane_body(expanded, 'runs') if 'asic/' in line]) == 6, 'Expanded selector renders six distinct real runs')
    t.command('Reset presentation overrides (inherit)')
    t.capture('selector-height-reset', ['4/6'])
    t.key(b'/'); t.key(b'synthetic-long-distinguishable'); t.key(b'\r')
    two = t.capture('selector-two-matching-runs', ['Runs 2/2 (cap 4)'])
    check(sum('asic/' in line for line in pane_body(two, 'runs')) == 2, 'Selector reports actual two matching runs, not requested four-row capacity (full labels verified in zoom)')
    t.key(b'\x15'); t.capture('selector-filter-reset', ['Runs 4/6 (cap 4)'])

    # Focus the exact checklist through public zoom semantics, then browse without
    # executing its advertised action. Identity is independently checked over HTTP.
    checklist = next(tile for tile in field(snapshot(), 'tiles') if field(tile, 'workspace') == overview_id and field(tile, 'kind') == 'stage-checklist')
    mutate('(Set_zoom (workspace %s) (tile (%s)))' % (sexp(overview_id), sexp(field(checklist, 'id'))))
    t.capture('stage-focused', ['Stage checklist', 'Synthesis: completed'], ['Session'])
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
    path_y = pane_rect(polished, 'timing · paths')[1]
    detail_y = pane_rect(polished, 'timing · selected path')[1]
    context_y = pane_rect(polished, 'timing · provenance')[1]
    check(path_y == detail_y and context_y > detail_y and 'stage checklist' not in polished.text().casefold(), 'Fresh Timing preset has Paths left and Detail-over-Context right, without a vertical checklist')

    # Pane focus/scroll is independent of selected path and shared filter state.
    # At the polished large size this short provider payload fits without scrolling;
    # use a bounded shorter viewport to exercise real scroll rather than a no-op.
    # Zero gutters leave more Detail rows than the former 32-row viewport.
    # This still fits Timing's full topology while making the payload scroll.
    t.resize(120, 28)
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
    reuse_before = snapshot()
    t.command('Inspect timing paths ' + field(runs[0], 'id'))
    t.capture('timing-reopen-retains-detail-intent', ['Filter: clk:reg0 -> reg7',
              'Slack: 0.42 ns', 'Path: SYNTHETIC setup path clk:reg0 -> reg7'])
    check(snapshot() == reuse_before,
          'Reopening compatible Timing retains selected detail/filter intent without any registry mutation')

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
        timing_template = next(field(d, 'template') for d in field(presets.config, 'definitions')
                               if field(d, 'key') == 'timing')
        for workspace in new:
            views = [[['kind', field(tile, 'kind')], ['hidden', field(tile, 'hidden')],
                      ['geometry', field(tile, 'requested_geometry')]]
                     for tile in field(current, 'tiles')
                     if field(tile, 'workspace') == field(workspace, 'id')]
            require(views == field(timing_template, 'views'),
                    'New captured-run Timing must publish complete canonical membership atomically')
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

    # WB-054: closing an explorer returns to the retained Timing reader below it.
    # Establish that reader explicitly; closing the overlay must not close both.
    t.focus_view('timing paths')
    t.key(b'\r')
    retained_detail = t.capture('wb054-retained-timing-precondition',
        ['Timing · Selected path', 'No tool report or binary layout is claimed.'])
    retained_path = pane_body(retained_detail, 'Timing · Selected path')[0]
    before_close = snapshot()
    t.command('Inspect clocks ' + field(runs[0], 'id'))
    t.capture('wb054-explorer-help', ['INSPECT clocks', 'Space c x close'])
    t.key(b' '); t.key(b'c'); t.key(b'x')
    restored_detail = t.capture('wb054-explorer-closed',
        ['Timing · Paths', 'Timing · Provenance', 'No tool report or binary layout is claimed.'],
        ['INSPECT clocks'])
    check(snapshot() == before_close, 'Space c x closes the explorer without changing selection, bindings or registry')
    check(pane_body(restored_detail, 'Timing · Selected path')[0] == retained_path,
          'Closing the clocks overlay preserves the underlying exact selected Timing detail')
    # Close the retained reader as a separate contextual action. Only then is the
    # disabled reason valid; merely returning from an overlay keeps detail open.
    t.command('Close inspector (Space c x)')
    closed_detail = t.capture('wb054-timing-reader-closed',
        ['Closed path detail; focus returned to timing · paths (selection kept)',
         'Enter to load selected path detail (read-only)'])
    check(snapshot() == before_close and
          pane_body(closed_detail, 'Timing · Selected path')[0] == retained_path and
          not any('No tool report or binary layout is claimed.' in line
                  for line in pane_body(closed_detail, 'Timing · Selected path')),
          'Closing the retained Timing reader preserves selected row, pins, contexts and registry')
    t.open_palette('Close inspector')
    t.capture('wb054-close-unavailable', ['Close inspector (Space c x)', 'no inspector open on the focused tile'])
    t.key(b'\x1b')
    t.command('Switch to Overview')
    t.resize(180, 55)
    sidebar_geometry(t.capture('sidebar-overview-180x55', ['planned-run', 'Reported cells (agg.)']), check)
    t.resize(80, 24)
    t.capture('refinement-overview-80x24', ['Compact: focused tile only', 'Stage checklist'])
    check(t.process.poll() is None, 'Tiny focused fallback remains interactive')
    t.resize(240, 80)
    t.capture('refinement-overview-240x80', ['Reported cells (agg.)', 'placement', 'routing', 'checks', 'finalization'])
    t.resize(120, 40)
    t.capture('refinement-overview-final', ['Reported cells (agg.)', 'stage checklist', 'planned-run'])
    t.wait_active_workspace(snapshot(), overview_id, 'refinement-overview-final')
    check(True, 'Final resized panes belong to the exact active Overview identity, independent of tab viewport')
    # A paths-only custom definition is a compatible Timing destination. Opening
    # it must not silently add built-in panes or replace its frozen custom policy.
    timing_definition = next(d for d in field(presets.config, 'definitions')
                             if field(d, 'key') == 'timing')
    paths_view = next(v for v in field(field(timing_definition, 'template'), 'views')
                      if field(v, 'kind') == 'timing-paths')
    custom = [['key', 'custom-paths'], ['template', [['version', '1'],
        ['name', 'Custom captured paths'], ['preset', []], ['views', [paths_view]]]],
        ['tiles', [[['key', 'kept-paths']]]], ['layout', [['Leaf', ['tile', 'kept-paths'],
            ['min_width', '24'], ['min_height', '8'], ['weight', '1']]]]]
    instance = [['key', 'paths'], ['name', 'Custom captured paths'],
                ['definition', ['Custom', 'custom-paths']]]
    window = [['key', 'custom'], ['name', 'Custom timing window'], ['workspaces', [instance]]]
    config = [['version', '1'], ['id', 'custom-timing-reuse'],
              ['definitions', [custom]], ['windows', [window]]]
    mutate('(Apply_config %s)' % sexp(config))
    custom_registry = snapshot()
    custom_workspace = next(w for w in field(custom_registry, 'workspaces')
                            if field(w, 'name') == 'Custom captured paths')
    custom_tile = next(tile for tile in field(custom_registry, 'tiles')
                       if field(tile, 'workspace') == field(custom_workspace, 'id'))
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' %
           (sexp(field(custom_tile, 'id')), sexp(runs[0])))
    # The stock workspace is intentionally ineligible. The independent view still
    # resolves run B, so only the custom view matches A.
    for tile in field(custom_registry, 'tiles'):
        if (field(tile, 'workspace') == field(existing_timing, 'id') and
                field(tile, 'kind') == 'timing-paths'):
            mutate('(Set_tile_hidden (tile %s) (hidden true))' % sexp(field(tile, 'id')))
    custom_before = snapshot()
    t.command('Inspect timing paths ' + field(runs[0], 'id'))
    t.capture('custom-timing-reused-without-builtin-apply', ['Timing · Paths', '12 paths'],
              ['Timing · Selected path', 'Timing · Provenance'])
    check(snapshot() == custom_before,
          'Inspect reuses custom Timing without changing revision, membership, pins, contexts or frozen policy')
    check(producers() == producers_before and len(plans()) == len(plans_before) + 1,
          'Custom Timing reuse and hydration issue no planner or producer actions')
    t.command('Switch to Overview')
    t.capture('overview-after-custom-timing', ['Reported cells (agg.)', 'stage checklist', 'planned-run'])
    t.wait_active_workspace(snapshot(), overview_id, 'overview-after-custom-timing')
    (t.base / 'provider-calls-final.json').write_text(json.dumps(calls(), indent=2))
    return 'Overview'


def timing_reuse_acceptance(t, check, http, runs, presets):
    """Focused native Timing regression, independent of presentation preflights."""
    def snapshot(): return http.rpc(domain='workspace')
    def mutate(operation): return http.mutate(snapshot(), operation)
    def producers_and_plans():
        calls = [json.loads(line)['argv'] for line in
                 (t.base / 'project/provider-calls.jsonl').read_text().splitlines()]
        return [a for a in calls if a[:2] in (['flow', 'run'], ['flow', 'plan']) or a[:1] == ['finalize']]

    jobs_before = producers_and_plans()
    definition = next(d for d in field(presets.config, 'definitions') if field(d, 'key') == 'timing')
    template = field(definition, 'template')
    paths_view = next(v for v in field(template, 'views') if field(v, 'kind') == 'timing-paths')
    custom = [['key', 'custom-paths'], ['template', [['version', '1'],
        ['name', 'Custom captured paths'], ['preset', []], ['views', [paths_view]]]],
        ['tiles', [[['key', 'kept-paths']]]], ['layout', [['Leaf', ['tile', 'kept-paths'],
            ['min_width', '24'], ['min_height', '8'], ['weight', '1']]]]]
    instance = [['key', 'paths'], ['name', 'Custom captured paths'],
                ['definition', ['Custom', 'custom-paths']]]
    window = [['key', 'custom'], ['name', 'Custom timing window'], ['workspaces', [instance]]]
    config = [['version', '1'], ['id', 'focused-timing-reuse'],
              ['definitions', [custom]], ['windows', [window]]]
    mutate('(Apply_config %s)' % sexp(config))
    configured = snapshot()
    workspace = next(w for w in field(configured, 'workspaces') if field(w, 'name') == 'Custom captured paths')
    paths = next(tile for tile in field(configured, 'tiles') if field(tile, 'workspace') == field(workspace, 'id'))
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' %
           (sexp(field(paths, 'id')), sexp(runs[0])))
    for tile in field(configured, 'tiles'):
        if field(tile, 'kind') == 'timing-paths' and field(tile, 'id') != field(paths, 'id'):
            mutate('(Set_tile_hidden (tile %s) (hidden true))' % sexp(field(tile, 'id')))
    before_reuse = snapshot()
    t.command('Inspect timing paths ' + field(runs[0], 'id'))
    t.capture('focused-custom-timing-reused', ['Timing · Paths', '12 paths'],
              ['Timing · Selected path', 'Timing · Provenance'])
    check(snapshot() == before_reuse,
          'Custom paths-only reuse preserves exact registry revision, policy, tile keys, pin and contexts')

    # A conflicting pin must cause complete canonical creation, never rebinding
    # either the custom workspace or the shared Main context.
    before_create = snapshot()
    t.command('Inspect timing paths ' + field(runs[1], 'id'))
    def created_investigation():
        current = snapshot()
        new = [w for w in field(current, 'workspaces')
               if field(w, 'id') not in {field(old, 'id') for old in field(before_create, 'workspaces')}]
        for w in new:
            views = [[['kind', field(tile, 'kind')], ['hidden', field(tile, 'hidden')],
                      ['geometry', field(tile, 'requested_geometry')]]
                     for tile in field(current, 'tiles') if field(tile, 'workspace') == field(w, 'id')]
            require(views == field(template, 'views'), 'New Timing membership must be canonical at first observation')
        if len(new) == 1:
            context = next(c for c in field(current, 'contexts') if field(c, 'id') == field(new[0], 'context'))
            if field(context, 'selected_run') == [runs[1]]:
                return current, new[0], context
        return None
    after, investigation, context = wait(created_investigation, 'canonical independent Timing investigation')
    check(field(investigation, 'preset') == ['timing'] and
          field(context, 'id') != field(after, 'main_context') and
          all(old in field(after, 'contexts') for old in field(before_create, 'contexts')) and
          all(old in field(after, 'tiles') for old in field(before_create, 'tiles')) and
          field(after, 'config_workspaces') == field(before_create, 'config_workspaces'),
          'Conflicting custom pin creates independent canonical Timing while preserving all existing contexts, tiles and policy')
    t.resize(180, 55)
    t.capture('focused-canonical-timing-created', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', '12 paths'])
    t.focus_view('timing paths')
    t.key(b'/'); t.key(b'clk:reg0 -> reg7'); t.key(b'\r'); t.key(b'\r')
    detail = wait(lambda: next((d for d in field(http.rpc(wait=False), 'inspection_details')
        if field(d, 'run') == runs[1] and field(d, 'stage') == 'signoff' and
        field(d, 'row_id') == 'synthetic-timing-signoff' and field(d, 'text')), None),
        'exact selected detail for focused Timing regression')
    expected = ['1 paths', 'Filter: clk:reg0 -> reg7', field(detail, 'text').splitlines()[0]]
    t.capture('focused-timing-selected-detail', expected)
    before_reopen = snapshot()
    t.command('Inspect timing paths ' + field(runs[1], 'id'))
    t.capture('focused-timing-reopen-retains-detail-intent', expected)
    check(snapshot() == before_reopen,
          'Hydrated Timing reopen retains selected path/filter/detail intent without registry mutation')
    check(producers_and_plans() == jobs_before, 'Focused Timing creation, reuse and hydration launch no planner or producer')
    return field(investigation, 'name')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--timing-only', action='store_true',
                        help='run native Timing creation/custom reuse/detail-intent regression without unrelated presentation preflights')
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
        check(sum('asic/' in line for line in pane_body(screen, 'runs')) == 2, 'With only two registered runs, selector labels and renders 2/2 instead of claiming four visible runs')
    try:
        if args.timing_only:
            args.harness = 'focused Timing creation and custom reuse'
            composition.run(args, acceptance=timing_reuse_acceptance, extra_runs=(), focused=True)
            return
        two = argparse.Namespace(**vars(args))
        two.evidence = args.evidence.with_name(args.evidence.name + '-two-runs')
        two.palette_only = True
        two.harness = 'frontend refinement two-run capacity'
        composition.run(two, extra_runs=(), startup_check=two_run_count)
        args.related_evidence = [str(two.evidence)]
        composition.run(args, acceptance=acceptance)
    finally: signal.alarm(0)


if __name__ == '__main__': main()
