"""Small stdlib S-expression HTTP client for the real Workbench daemon."""
import json
import re
import time
import urllib.request


class Atom(str):
    pass


def sexp(value):
    if isinstance(value, Atom):
        return str(value)
    if isinstance(value, list):
        return '(' + ' '.join(sexp(v) for v in value) + ')'
    return json.dumps(str(value), ensure_ascii=True)


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    position = 0
    def item():
        nonlocal position
        token = tokens[position]
        position += 1
        if token == '(':
            values = []
            while tokens[position] != ')':
                values.append(item())
            position += 1
            return values
        if token.startswith('"'):
            # Sexplib decimal escapes encode BYTES, including UTF-8 sequences.
            # Preserve high bytes as temporary surrogates while JSON handles
            # ordinary quoting/control escapes, then decode the assembled UTF-8.
            # Match other escape pairs too so a literal \\123 is not re-decoded.
            def escape(match):
                if match[1] is None:
                    return match[0]
                byte = int(match[1])
                if byte > 255:
                    raise ValueError('Invalid Sexplib byte escape')
                return '\\u%04x' % (byte if byte < 128 else 0xdc00 + byte)
            token = re.sub(r'\\(?:([0-9]{3})|.)', escape, token)
            return json.loads(token).encode('utf-8', 'surrogateescape').decode('utf-8', 'surrogateescape')
        if token == ')':
            raise ValueError('Unexpected closing parenthesis')
        return token
    result = item()
    if position != len(tokens):
        raise ValueError('Trailing protocol data')
    return result


def field(value, key):
    return dict(value)[key]


class Client:
    def __init__(self, url, root, switch=None):
        self.url = url.rstrip('/')
        self.history = []
        self.instance = field(self.raw('/api/hello'), 'instance_id')
        opened = self.raw('/api/v1/open-project', [
            ['instance_id', self.instance], ['root', str(root)],
            ['environment', Atom('Inherit_daemon') if switch is None else ['Opam_switch', switch]]])
        self.project = field(field(opened, 'project'), 'id')

    def raw(self, path, data=None):
        request = urllib.request.Request(self.url + path,
            data=None if data is None else sexp(data).encode(),
            headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1'})
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
        result = parse(text)
        self.history.append(dict(path=path, request=None if data is None else sexp(data), response=text))
        if path != '/api/hello':
            if result[0] != 'Ok':
                raise RuntimeError(text)
            return result[1]
        return result

    def rpc(self, operation='Get', domain='asic', wait=True):
        def request(op):
            return self.raw('/api/v1/' + domain, [['instance_id', self.instance],
                ['project', self.project], ['operation', Atom(op)]])
        result = request(operation)
        if wait and domain == 'asic':
            deadline = time.monotonic() + 30
            while any(field(o, 'state') in ('pending', 'executing') for o in field(result, 'operations')):
                if time.monotonic() > deadline:
                    raise TimeoutError('ASIC operation timeout: ' + sexp(result))
                time.sleep(.05)
                result = request('Get')
            errors = [o for o in field(result, 'operations') if field(o, 'state') == 'failed']
            if errors:
                raise RuntimeError('ASIC operation failed: ' + sexp(errors))
        return result

    def mutate(self, snapshot, mutation):
        return self.rpc('(Mutate (expected_revision %s) (mutation %s))' %
                        (field(snapshot, 'revision'), mutation), domain='workspace')
