"""Small ASCII FS2 fixture codec. Production type authority: protocol/simulation.ml."""
import json
import re


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    pos = 0

    def value():
        nonlocal pos
        token = tokens[pos]
        pos += 1
        if token == '(':
            result = []
            while tokens[pos] != ')':
                result.append(value())
            pos += 1
            return result
        assert token != ')'
        if token.startswith('"'):
            token = re.sub(r'\\([0-9]{3})', lambda m: '\\u%04x' % int(m[1]), token)
            return json.loads(token)
        return token
    result = value()
    assert pos == len(tokens), 'trailing sexp data'
    return result


def sexp(value):
    if isinstance(value, (list, tuple)):
        return '(' + ' '.join(map(sexp, value)) + ')'
    value = str(value)
    assert value.isascii(), 'fixture codec accepts ASCII only'
    return json.dumps(value)


def record(value):
    return dict(value)


def catalog(suite='fixture', cases=('first', 'second'), parameters=()):
    return [('protocol_version', 1), ('suites', [[
        ('id', suite), ('label', suite),
        ('cases', [[('id', c), ('label', c)] for c in cases]),
        ('parameters', [[('key', k), ('label', k), ('default', d), ('choices', ch)] for k, d, ch in parameters]),
        ('default_seed', '42')]])]


class EventWriter:
    def __init__(self, path, attempt):
        self.file = path.open('a', buffering=1)
        self.attempt = attempt
        self.sequence = 0

    def emit(self, payload):
        line = sexp([('protocol_version', 1), ('attempt_id', self.attempt),
                     ('sequence', self.sequence), ('payload', payload)])
        self.file.write(line + '\n')
        self.file.flush()
        self.sequence += 1
        return line

    def progress(self, case, completed, total=None):
        self.emit(['Progress', [('case_id', [] if case is None else [case]),
                   ('completed', completed), ('total', [] if total is None else [total]), ('unit_', 'cycles')]])

    def finish_case(self, case, status='Passed', message=None):
        self.emit(['Case_finished', [('case_id', case), ('status', status),
                                   ('message', [] if message is None else [message])]])

    def artifact(self, id_, case, kind, media_type, path):
        self.emit(['Artifact', [('id', id_), ('case_id', [] if case is None else [case]),
                  ('label', id_), ('kind', kind), ('media_type', media_type), ('path', path)]])
