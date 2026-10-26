#!/usr/bin/env python3
"""Private read-only RTL projection fixture for the normal project-driver adapter."""
import json
from pathlib import Path
import sys


def sexp(value):
    if isinstance(value, (list, tuple)):
        return '(' + ' '.join(map(sexp, value)) + ')'
    return json.dumps(str(value))


args = sys.argv[1:]
if args == ['describe', '--protocol-version', '1']:
    print(sexp([('protocol_version', 1), ('capabilities', ['describe', 'generate-rtl']),
                ('targets', [[('key', 'counter'), ('name', 'WB004 generic counter'),
                              ('top', 'counter'), ('backend', 'simulation'), ('clocks', []), ('facts', [])]]),
                ('configurations', [[('key', 'default'), ('target', 'counter'),
                                     ('name', 'WB004 default'), ('description', [])]])]))
elif len(args) == 9 and args[:3] == ['generate-rtl', '--protocol-version', '1']:
    target, configuration, output = args[4], args[6], Path(args[8])
    (output / 'counter.v').write_text('// WB004 generic RTL only; not ASIC publication\nmodule counter(); endmodule\n')
    print('WB004 exact generic RTL job log', file=sys.stderr, flush=True)
    print(sexp([('protocol_version', 1), ('target', target), ('configuration', configuration),
                ('outputs', [[('path', 'counter.v'), ('namespace', 'hardcaml'), ('name', 'verilog'),
                              ('role', 'Deliverable'), ('media', ['text/x-verilog']),
                              ('display_name', 'WB004 generic counter RTL'), ('description', [])]]),
                ('tools', []), ('build', []), ('run', [])]))
else:
    raise SystemExit('Only describe and generate-rtl are permitted')
