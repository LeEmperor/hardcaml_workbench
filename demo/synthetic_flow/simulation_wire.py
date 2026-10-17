"""Portable, stdlib-only FS2 S-expression codec and flushed event writer.

The authoritative types and framing rules are protocol/simulation.ml. This module
is copied alongside the demo provider; it has no Workbench/fixture dependencies.
"""
import json
import re


def sexp(value):
    if isinstance(value, (list, tuple)):
        return '(' + ' '.join(map(sexp, value)) + ')'
    # Direct UTF-8 is valid Sexplib; JSON's non-ASCII \\u escapes are not.
    return json.dumps(str(value), ensure_ascii=False)


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    position = 0

    def item():
        nonlocal position
        if position >= len(tokens):
            raise ValueError('Truncated S-expression')
        token = tokens[position]
        position += 1
        if token == '(':
            values = []
            while position < len(tokens) and tokens[position] != ')':
                values.append(item())
            if position == len(tokens):
                raise ValueError('Unclosed S-expression')
            position += 1
            return values
        if token == ')':
            raise ValueError('Unexpected closing parenthesis')
        if token.startswith('"'):
            def escape(match):
                if match[1] is None:
                    return match[0]
                byte = int(match[1])
                if byte > 255:
                    raise ValueError('Invalid Sexplib byte escape')
                return '\\u%04x' % (byte if byte < 128 else 0xdc00 + byte)
            token = re.sub(r'\\(?:([0-9]{3})|.)', escape, token)
            return json.loads(token).encode('utf-8', 'surrogateescape').decode('utf-8', 'surrogateescape')
        return token

    result = item()
    if position != len(tokens):
        raise ValueError('Trailing S-expression data')
    return result


class EventWriter:
    def __init__(self, file, attempt):
        self.file = file
        self.attempt = attempt
        self.sequence = 0

    def emit(self, payload):
        line = sexp([('protocol_version', 1), ('attempt_id', self.attempt),
                     ('sequence', self.sequence), ('payload', payload)])
        self.file.write(line + '\n')
        self.file.flush()
        self.sequence += 1

    def progress(self, case, completed, total):
        self.emit(['Progress', [('case_id', [case]), ('completed', completed),
                               ('total', [total]), ('unit_', 'synthetic steps')]])

    def artifact(self, case, label, kind, media_type, path):
        self.emit(['Artifact', [('id', path), ('case_id', [case]),
                               ('label', label), ('kind', kind),
                               ('media_type', media_type), ('path', path)]])
