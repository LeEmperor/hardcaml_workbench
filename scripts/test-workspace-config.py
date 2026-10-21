#!/usr/bin/env python3
"""Native workspace composition acceptance using prebuilt binaries only.

Run: python3 scripts/test-workspace-config.py [--skip-pty] [--evidence NEW-DIR]
Reuses FS3's strict metadata-only tool guards, HTTP codec and PTY decoder. No
builds, provider actions or Git mutations. All fixtures/state/evidence are private
under /tmp/opencode. The evidence directory is retained, including on failure.
"""
import argparse
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import struct
import subprocess
import sys
import tempfile
import termios
import time
import traceback

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'fs3', Path(__file__).with_name('test-fs3-adoption.py'))
fs3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs3)
field, require, sexp, parse = fs3.field, fs3.require, fs3.sexp, fs3.parse
replace = fs3.replace_field


def without_revision(snapshot):
    return replace(snapshot, 'revision', 'IGNORED')


def definition():
    # View order deliberately differs from tree order. Both panes are project
    # metadata readers, so rendering cannot launch provider/project jobs.
    views = []
    for kind in ('execution', 'project-tests'):
        views.append([['kind', kind], ['hidden', 'false'], ['geometry',
            [['x', '0'], ['y', '0'], ['width', '48'], ['height', '12']]]])
    leaf = lambda key: ['Leaf', ['tile', key], ['min_width', '24'],
                        ['min_height', '8'], ['weight', '1']]
    return [['key', 'custom-desk'], ['template', [['version', '1'],
        ['name', 'Custom desk'], ['preset', []], ['views', views]]],
        ['tiles', [[['key', key], ['presentation', [[['title', ['true']],
            ['frame', ['true']], ['padding', ['0']]]]]] for key in ('execution', 'tests')]],
        ['layout', [['Columns', [leaf('tests'), leaf('execution')]]]]]


def custom_config():
    return [['version', '1'], ['id', 'native-config-acceptance'],
        ['definitions', [definition()]], ['windows', [
            [['key', key], ['name', 'Desk ' + key], ['workspaces', [
                [['key', 'desk'], ['name', 'Config ' + key],
                 ['definition', ['Custom', 'custom-desk']]]]]]
            for key in ('one', 'two')]]]


class Terminal(fs3.Terminal):
    def __init__(self, test, label, config=None):
        self.test, self.label, self.data = test, label, bytearray()
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        argv = [str(test.args.terminal), '--connect', test.url,
                '--project-root', str(test.root)]
        if config is not None:
            argv += ['--workspace-config', str(config)]
        try:
            self.process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave,
                env=dict(test.env, TERM='xterm-256color'), start_new_session=True)
        except BaseException:
            os.close(self.master)
            raise
        finally:
            os.close(slave)

    def palette(self, title, dispatch=True):
        for key in (b' ', b'c', b'c'):
            self.key(key)
        self.wait('palette-open', ['COMMAND PALETTE'])
        self.key(title.encode())
        self.wait('palette-query', ['COMMAND PALETTE', title[:28]])
        if dispatch:
            self.key(b'\r')
            self.wait('palette-closed', absent=['COMMAND PALETTE'])

    def composed(self, label):
        deadline = time.monotonic() + 20
        while True:
            text = self.drain(.2)
            # Authored view order is execution/tests, while the custom tree puts
            # tests on the left. A generic membership shelf cannot satisfy this.
            if any(0 <= row.find('project-tests') < 55 and
                   row.find('execution', 55) >= 55 for row in text.splitlines()):
                (self.test.evidence / (self.label + '-' + label + '.txt')).write_text(text)
                self.test.check(True, label + ': native pane positions follow persisted custom Columns tree')
                return
            require(time.monotonic() < deadline, label + ': custom column layout timeout:\n' + text)


class Acceptance(fs3.Acceptance):
    def config_cli(self, action, extra, label, error=None):
        return self.command(self.args.workspace_cli, ['config', action] + extra,
                            label, error=error)

    def apply(self, path, label, error=None):
        return self.config_cli('apply', ['-endpoint', self.url, '-project', self.project,
                                       path], label, error=error)

    def disk(self):
        return {str(p.relative_to(self.state)):
                (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino)
                for p in self.state.glob('workspace-*.sexp')}

    def unchanged(self, snapshot, saved, label):
        self.check(self.workspace() == snapshot and self.disk() == saved,
                   label + ': no registry revision, partial state or disk writes')


def check_mapping(test, snapshot, config):
    windows = field(snapshot, 'config_windows')
    instances = field(snapshot, 'config_workspaces')
    test.check(len(windows) == 2 and len(instances) == 2,
               'Complete two-window composition has exactly two window/instance mappings')
    expected = field(config, 'definitions')[0]
    ids = set()
    for p in instances:
        actual = field(p, 'definition')
        # Generated snapshot codecs materialize unspecified presentation options.
        # Compare the policy fields rather than raw sparse-authoring record shape.
        presentation_matches = all(
            field(a, 'key') == field(e, 'key') and
            all(field(field(a, 'presentation')[0], name) == value
                for name, value in field(e, 'presentation')[0])
            for a, e in zip(field(actual, 'tiles'), field(expected, 'tiles')))
        test.check(field(p, 'config_id') == field(config, 'id') and
                   field(actual, 'key') == field(expected, 'key') and
                   field(actual, 'template') == field(expected, 'template') and
                   field(actual, 'layout') == field(expected, 'layout') and
                   len(field(actual, 'tiles')) == len(field(expected, 'tiles')) and
                   presentation_matches and
                   field(p, 'reference') == ['Custom', 'custom-desk'],
                   'Snapshot embeds exact resolved custom layout/presentation and provenance')
        mapping = dict(field(p, 'tiles'))
        test.check(set(mapping) == {'execution', 'tests'},
                   'Stable tile keys map to live identities')
        wid = field(p, 'workspace')
        workspace = next(w for w in field(snapshot, 'workspaces') if field(w, 'id') == wid)
        test.check(field(workspace, 'context') == field(snapshot, 'main_context'),
                   'New configured workspace is Main-linked')
        for key, tid in mapping.items():
            tile = next(t for t in field(snapshot, 'tiles') if field(t, 'id') == tid)
            test.check(field(tile, 'workspace') == wid and field(tile, 'binding') == 'Follow',
                       'New mapped tile belongs to its workspace and follows context')
            ids.add(tid)
    test.check(len(ids) == 4, 'All configured tile instances have distinct live IDs')


def authoring(test):
    for kind in ('stock', 'example'):
        text = test.config_cli('export', [kind], 'export-' + kind)
        path = test.evidence / (kind + '.sexp')
        path.write_text(text)
        decoded = parse(text)
        test.check(field(decoded, 'version') == '1' and bool(field(decoded, 'definitions')),
                   kind + ' export is a complete versioned specification')
        test.config_cli('validate', [path], 'validate-' + kind)
        again = test.config_cli('export', [kind], 'export-repeat-' + kind)
        test.check(parse(again) == decoded, kind + ' export is deterministic and independently valid')
        if kind == 'stock':
            for definition in field(decoded, 'definitions'):
                key = field(definition, 'key')
                portable = parse(test.command(test.args.workspace_cli,
                    ['starter', key], 'canonical-starter-' + key))
                test.check(portable == field(definition, 'template'),
                           key + ': version-1 starter is the exact canonical nested template')
    config = custom_config()
    path = test.evidence / 'multi-window.sexp'
    path.write_text(sexp(config) + '\n')
    test.config_cli('validate', [path], 'validate-custom-multi-window')
    return config, path


def registry(test, config, path):
    test.start()
    before = test.workspace()
    test.apply(path, 'apply-two-windows')
    current = test.workspace()
    test.check(int(field(current, 'revision')) == int(field(before, 'revision')) + 1 and
               len(field(current, 'windows')) == len(field(before, 'windows')) + 2 and
               len(field(current, 'workspaces')) == len(field(before, 'workspaces')) + 2 and
               len(field(current, 'tiles')) == len(field(before, 'tiles')) + 4,
               'CLI publishes both windows/workspaces and all tiles in one revision')
    check_mapping(test, current, config)
    for p in field(current, 'config_workspaces'):
        wid = field(p, 'workspace')
        workspace = next(w for w in field(current, 'workspaces') if field(w, 'id') == wid)
        exported = parse(test.cli('export', [wid], 'export-live-' + field(p, 'window_key')))
        expected = replace(field(definition(), 'template'), 'name', field(workspace, 'name'))
        test.check(exported == expected,
                   'Native CLI exports configured custom workspace portable membership and geometry')
    # Exercise edits before reapply; snapshot equality catches arrangement, context,
    # pin, order and definition-policy changes as well as duplicate IDs.
    p = field(current, 'config_workspaces')[0]
    wid, tid = field(p, 'workspace'), field(p, 'tiles')[0][1]
    current = test.mutate(current, ['Make_independent', wid])
    current = test.mutate(current, ['Rename_workspace', ['workspace', wid], ['name', 'Saved user edit']])
    current = test.mutate(current, ['Set_tile_hidden', ['tile', tid], ['hidden', 'true']])
    current = test.mutate(current, ['Resize_tile', ['tile', tid], ['geometry',
        [['x', '7'], ['y', '3'], ['width', '37'], ['height', '9']]]])
    current = test.mutate(current, ['Set_tile_binding', ['tile', tid], ['binding',
        ['Pin_run', [['backend', 'fixture'], ['id', 'retained-reference'], ['build', []], ['label', []]]]]])
    test.apply(path, 'reapply-two-windows')
    repeated = test.workspace()
    test.check(without_revision(repeated) == without_revision(current) and
               int(field(repeated, 'revision')) == int(field(current, 'revision')) + 1,
               'Reapply has no duplicates and preserves edits, pins, independent context and policy')
    current = repeated
    saved = test.disk()
    bad = copy.deepcopy(config)
    bad_window = copy.deepcopy(field(bad, 'windows')[-1])
    bad_window = replace(bad_window, 'key', 'invalid-last-window')
    bad_instance = replace(field(bad_window, 'workspaces')[0], 'definition', ['Custom', 'missing'])
    bad_window = replace(bad_window, 'workspaces', [bad_instance])
    bad = replace(bad, 'windows', field(bad, 'windows') + [bad_window])
    for label, text in [('missing-reference', sexp(bad)), ('malformed', '('),
                        ('unsupported-version', sexp(replace(config, 'version', '99')))]:
        invalid = test.evidence / ('invalid-' + label + '.sexp')
        invalid.write_text(text)
        test.config_cli('validate', [invalid], 'reject-validate-' + label, error='workspace config:')
        test.apply(invalid, 'reject-apply-' + label, error='workspace config:')
        test.unchanged(current, saved, label)
    rejected = test.mutate(current, ['Apply_config', bad], success=False)
    test.check(rejected[0] == 'Error' and field(rejected[1], 'kind') == 'Invalid_request',
               'Daemon independently rejects a bad final reference in a resolved HTTP application')
    test.unchanged(current, saved, 'invalid HTTP application')
    stale = replace(current, 'revision', str(int(field(current, 'revision')) - 1))
    rejected = test.mutate(stale, ['Apply_config', config], success=False)
    test.check(rejected[0] == 'Error' and field(rejected[1], 'kind') == 'Conflict',
               'HTTP composition CAS rejects stale revisions')
    test.unchanged(current, saved, 'stale HTTP application')
    path.unlink()
    test.close()
    test.start()
    test.check(not path.exists() and test.workspace() == current and test.disk() == saved,
               'Restart without source file preserves exact live state, mappings and custom tree')
    (test.evidence / 'registry-restored.sexp').write_text(sexp(current) + '\n')
    test.quiet()
    test.close()


def terminal_startup(test, config, path):
    # A second private state directory gives the terminal a genuinely fresh
    # registry; an HTTP Get beforehand intentionally persists its placeholders.
    test.state = test.evidence / 'terminal-daemon-state'
    test.state.mkdir(mode=0o700)
    path.write_text(sexp(config) + '\n')
    test.start()
    placeholders = test.workspace()
    test.check(field(placeholders, 'configuration_pending') == 'true',
               'Terminal scenario begins with saved untouched Get placeholders')
    terminal = None
    try:
        terminal = Terminal(test, 'fresh-config', path)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.wait('custom-ready', ['Config one', 'project-tests', 'execution'])
        terminal.composed('fresh-custom-tree')
        current = test.workspace()
        test.check(len(field(current, 'windows')) == 2 and
                   len(field(current, 'workspaces')) == 2 and
                   field(current, 'configuration_pending') == 'false' and
                   int(field(current, 'revision')) == int(field(placeholders, 'revision')) + 1,
                   'Native --workspace-config replaces placeholders atomically with custom-only session')
        check_mapping(test, current, config)
        terminal.close()
        terminal = None
        wid = field(field(current, 'workspaces')[0], 'id')
        current = test.mutate(current, ['Rename_workspace', ['workspace', wid], ['name', 'Saved config desk']])
        saved = test.disk()
        # A valid, changed file is supplied on reconnect: saved session must win.
        changed = replace(config, 'id', 'must-not-initialize-again')
        path.write_text(sexp(changed) + '\n')
        terminal = Terminal(test, 'saved-session-wins', path)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.wait('saved-ready', ['Saved config desk'])
        test.unchanged(current, saved, 'Saved session wins over changed startup configuration')
        terminal.close()
        terminal = None
        path.unlink()
        test.close()
        test.start()
        terminal = Terminal(test, 'fileless-restart')
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.wait('custom-restored', ['Saved config desk', 'project-tests', 'execution'])
        terminal.composed('fileless-custom-tree')
        test.check(not path.exists() and test.workspace() == current,
                   'Native terminal renders persisted custom composition after daemon restart without source file')
        # Recovery must remain independently available in a custom-only session.
        terminal.palette('Create built-in workspace: Overview')
        deadline = time.monotonic() + 20
        while True:
            recovered = test.workspace()
            if len(field(recovered, 'workspaces')) == len(field(current, 'workspaces')) + 1:
                break
            require(time.monotonic() < deadline, 'Built-in recovery did not create a workspace')
            terminal.drain(.15)
        created = [w for w in field(recovered, 'workspaces') if w not in field(current, 'workspaces')]
        test.check(len(created) == 1 and field(created[0], 'preset') == ['overview'] and
                   field(recovered, 'config_workspaces') == field(current, 'config_workspaces'),
                   'Palette creates canonical Overview from custom-only session without changing custom provenance')
        stock = parse((test.evidence / 'stock.sexp').read_text())
        definitions = {field(d, 'key'): d for d in field(stock, 'definitions')}
        exported = parse(test.cli('export', [field(created[0], 'id')], 'export-recovered-overview'))
        test.check(exported == field(definitions['overview'], 'template'),
                   'Built-in palette recovery uses exact canonical ordered membership, visibility and geometry')
        terminal.palette('Create Testing workspace')
        deadline = time.monotonic() + 20
        while True:
            testing = test.workspace()
            created = [w for w in field(testing, 'workspaces')
                       if field(w, 'preset') == ['testing']]
            if len(created) == 1:
                break
            require(time.monotonic() < deadline, 'Testing shortcut did not create a workspace')
            terminal.drain(.15)
        exported = parse(test.cli('export', [field(created[0], 'id')], 'export-testing-shortcut'))
        test.check(exported == field(definitions['testing'], 'template') and
                   field(testing, 'config_workspaces') == field(current, 'config_workspaces'),
                   'Testing shortcut uses the canonical catalog and preserves custom configuration provenance')
        test.quiet()
    finally:
        if terminal is not None:
            terminal.close()


def exercise(test):
    (test.root / 'dune-project').write_text('(lang dune 3.22)\n(name workspace_config_acceptance)\n')
    (test.root / 'dune').write_text('(dirs)\n')
    test.command(test.args.setup, ['--root', test.root, '--project-name', 'FS3 acceptance',
        '--build-alias', '@acceptance-build', '--test-alias', '@acceptance-test'], 'metadata-only-initialize')
    config, path = authoring(test)
    registry(test, config, path)
    if not test.args.skip_pty:
        terminal_startup(test, config, path)
    else:
        test.result['skipped'] = ['PTY startup/session precedence, fileless rendering and built-in recovery']
    test.result['status'] = 'passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, directory in [('setup', 'setup'), ('workspace-cli', 'workspace_cli'),
                            ('daemon', 'daemon'), ('terminal', 'terminal')]:
        parser.add_argument('--' + name, type=Path,
            default=fs3.REPO / '_build/default' / directory / 'main.exe')
    parser.add_argument('--skip-pty', action='store_true')
    parser.add_argument('--evidence', type=Path, help='New directory under /tmp/opencode')
    args = parser.parse_args()
    base = Path('/tmp/opencode')
    require(base.is_dir(), '/tmp/opencode must exist')
    for name in ('setup', 'workspace_cli', 'daemon', 'terminal'):
        binary = getattr(args, name).resolve()
        require(binary.is_file() and os.access(binary, os.X_OK), 'Missing prebuilt executable: ' + str(binary))
        setattr(args, name, binary)
    if args.evidence:
        args.evidence = args.evidence.resolve()
        require(args.evidence.is_relative_to(base) and args.evidence != base,
                'Evidence must be under /tmp/opencode')
        args.evidence.mkdir(mode=0o700)
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix='workspace-config-', dir=base))
    print('Evidence:', args.evidence, flush=True)
    test = Acceptance(args)
    try:
        exercise(test)
    except BaseException:
        test.result['failure'] = traceback.format_exc()
        (args.evidence / 'failure.txt').write_text(test.result['failure'])
        traceback.print_exc()
    finally:
        test.close()
        test.result['owned_daemon_stopped'] = test.process is None or test.process.poll() is not None
        (args.evidence / 'result.json').write_text(json.dumps(test.result, indent=2) + '\n')
    print(test.result['status'].upper() + ': ' + str(args.evidence / 'result.json'))
    return 0 if test.result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
