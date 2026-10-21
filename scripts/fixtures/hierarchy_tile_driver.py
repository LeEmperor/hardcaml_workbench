#!/usr/bin/env python3
"""Private acceptance-only Dune/driver stand-in; never builds or launches tools.

The response records follow test/fixtures/example_project/workbench/project_driver.ml.
Invoked through a private `dune` symlink, it accepts only the adapter's exact
metadata and driver argv. Its -j argument is consumed, never passed to Dune.
"""
import json
import os
from pathlib import Path
import sys
import time


def sexp(value):
    if isinstance(value, (list, tuple)):
        return '(' + ' '.join(map(sexp, value)) + ')'
    return json.dumps(str(value))


def hierarchy(target, configuration, generation):
    def node(key, parent, instance, circuit, width):
        return [('key', key), ('parent', [] if parent is None else [parent]),
                ('instance_name', [] if instance is None else [instance]),
                ('circuit_name', circuit),
                ('input_ports', [[('name', 'clock_i'), ('width', 1)]]),
                ('output_ports', [[('name', 'count_o'), ('width', width)]]),
                ('metadata', [[('name', 'fixture_generation'), ('value', generation)]])]
    width = 8 if configuration == 'eight-bit' else 4
    # Deliberately distinct nested child and sibling names expose selection leakage.
    return [('protocol_version', 1), ('target', target), ('configuration', configuration),
            ('root', '/'), ('nodes', [node('/', None, None, 'counter_top', width),
             node('/11:u_counter_0', '/', 'u_counter_0', 'counter_branch', width),
             node('/11:u_counter_0/6:u_leaf', '/11:u_counter_0', 'u_leaf', 'counter_leaf', width),
             node('/11:u_counter_1', '/', 'u_counter_1', 'counter_sibling', width)])]


def main():
    base = Path(os.environ['HIERARCHY_FIXTURE_BASE']).resolve(strict=True)
    root = base / 'project'
    args = sys.argv[1:]
    metadata = args in (['--version'], ['describe', 'workspace', '--root', str(root),
                                         '--format=sexp', '--lang=0.1'])
    driver = (len(args) >= 8 and args[0] == 'exec' and args[1] in ('-j20', '-j6')
              and args[2:7] == ['--root', str(root), '--no-buffer', './hierarchy-driver.exe', '--'])
    op = args[7:] if driver else []
    allowed = metadata or (op == ['describe', '--protocol-version', '1']) or (
        len(op) == 9 and op[:3] == ['generate-rtl', '--protocol-version', '1']
        and op[3] == '--target' and op[5] == '--configuration' and op[7] == '--output-dir')
    with (base / 'driver-calls.jsonl').open('a') as out:
        out.write(json.dumps(dict(argv=args, allowed=allowed, monotonic=time.monotonic())) + '\n')
    if not allowed:
        sys.exit('hierarchy acceptance forbids this Dune/tool operation')
    if args == ['--version']:
        print('3.22.0')
        return
    if metadata:
        print(sexp([['root', str(root)], ['build_context', '_build/default']]))
        return
    if op[0] == 'describe':
        control_path = base / 'control.json'
        mode = json.loads(control_path.read_text()).get('mode') if control_path.exists() else 'valid'
        capabilities = ['describe', 'generate-rtl']
        if mode != 'unsupported':
            capabilities.append('generate-rtl-hierarchy')
        print(sexp([('protocol_version', 1), ('capabilities', capabilities),
            ('targets', [[('key', t), ('name', n), ('top', 'counter_top'),
                          ('backend', 'simulation'), ('clocks', []), ('facts', [])]
                         for t, n in [('counter', 'Counter'), ('other', 'Other counter')]]),
            ('configurations', [[('key', c), ('target', t), ('name', n), ('description', [])]
              for t, c, n in [('counter', 'four-bit', '4-bit counter'),
                               ('counter', 'eight-bit', '8-bit counter'),
                               ('other', 'other-four', 'Other 4-bit counter')]])]))
        return
    target, configuration, output = op[4], op[6], Path(op[8]).resolve(strict=True)
    if not any(output.is_relative_to(base / name) for name in ('state', 'tmp')):
        sys.exit('output must belong to private daemon state or TMPDIR')
    control = json.loads((base / 'control.json').read_text())
    mode = control.get('mode', 'valid')
    if mode == 'pending':
        deadline = time.monotonic() + 45
        while not (base / 'release-generation').exists():
            if time.monotonic() > deadline:
                sys.exit('fixture generation gate expired')
            time.sleep(.05)
    if mode == 'failed':
        sys.exit('deliberate hierarchy acceptance generation failure')
    (output / 'counter.v').write_text('// acceptance fixture only, no EDA execution\n')
    outputs = []
    def declare(path, name, role, media):
        outputs.append([('path', path), ('namespace', 'hardcaml'), ('name', name),
            ('role', role), ('media', [media]), ('display_name', path), ('description', [])])
    declare('counter.v', 'verilog', 'Deliverable', 'text/x-verilog')
    if mode != 'unsupported':
        data = '(' if mode == 'malformed' else sexp(hierarchy(target, configuration, control['generation']))
        (output / 'counter.hierarchy.sexp').write_text(data)
        declare('counter.hierarchy.sexp', 'elaboration-hierarchy', 'Report',
                'application/x-hardcaml-workbench-hierarchy-sexp')
    print(sexp([('protocol_version', 1), ('target', target), ('configuration', configuration),
                ('outputs', outputs), ('tools', [[('name', 'hierarchy-acceptance-replay'), ('version', ['1'])]]),
                ('build', []), ('run', [])]))


if __name__ == '__main__':
    main()
