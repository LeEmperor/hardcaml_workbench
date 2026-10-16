#!/usr/bin/env python3
"""Deterministic FS2 fault producer; --control is a JSON file read per launch.

The append-only calls file proves discovery/run counts and restart non-replay.
slow/cancel wait for supervisor termination after preserving the first case.
"""
import argparse
import json
import os
from pathlib import Path
import time
import sys
sys.dont_write_bytecode = True
from fs2_wire import EventWriter, catalog, parse, record, sexp


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control', type=Path, required=True)
    p.add_argument('--calls', type=Path, required=True)
    p.add_argument('operation', choices=['discover', 'run'])
    p.add_argument('--protocol-version', type=int, required=True, choices=[1])
    p.add_argument('--request', type=Path)
    p.add_argument('--events', type=Path)
    p.add_argument('--artifact-dir', type=Path)
    a = p.parse_args()
    control = json.loads(a.control.read_text())
    mode = control.get('mode', 'pass')
    with a.calls.open('a') as out:
        out.write(json.dumps(dict(operation=a.operation, mode=mode, pid=os.getpid(), pgid=os.getpgrp(),
            request=parse(a.request.read_text()) if a.request else None)) + '\n')
    if a.operation == 'discover':
        if mode == 'discovery-malformed':
            print('(not a catalog)')
        elif mode == 'discovery-version':
            print(sexp([('protocol_version', 2), ('suites', [])]))
        else:
            print(sexp(catalog(cases=['other'] if mode == 'discovery-mismatch' else ['first', 'second'])))
        return
    req = record(parse(a.request.read_text()))
    sel = record(req['selection'])
    w = EventWriter(a.events, req['attempt_id'])
    first = w.emit('Started')
    if mode == 'duplicate':
        w.file.write(first + '\n'); w.file.flush(); return
    if mode == 'malformed':
        w.file.write('(broken\n'); w.file.flush(); return
    if mode == 'truncated':
        w.file.write(first); w.file.flush(); return
    if mode == 'wrong-attempt':
        w.attempt = 'different-attempt'
    if mode == 'gap':
        w.sequence += 1
    failed = mode == 'fail'
    for index, case in enumerate(sel['cases']):
        w.emit(['Case_started', case])
        w.progress(case, 0)
        if mode in ('slow', 'cancel') and index == len(sel['cases']) - 1:
            for completed in range(1, 601):
                w.progress(case, completed)
                print('live fixture cycle', completed, flush=True)
                time.sleep(.1)
        status = 'Failed' if failed and index == 0 else 'Passed'
        path = a.artifact_dir / (case + '.bin')
        # Explicit non-UTF8 and NUL bytes exercise byte rather than text export.
        path.write_bytes(bytes(range(256)) * 300 + b'\x00\xff\r\nFS2\n')
        w.artifact(case + '-raw', case, 'waveform', 'application/octet-stream', path.name)
        if mode == 'missing-artifact':
            w.artifact(case + '-missing', case, 'report', 'text/plain', 'not-created.txt')
        if mode == 'rejected-artifact':
            w.artifact(case + '-escape', case, 'report', 'text/plain', '../escape.txt')
        if status == 'Failed':
            report = a.artifact_dir / 'failure.txt'
            report.write_text('Deterministic assertion: expected 7, observed 6; seed=' + sel['seed'] + '\n')
            w.artifact('failure', case, 'failure-report', 'text/plain', report.name)
        w.finish_case(case, status, 'expected 7, observed 6' if status == 'Failed' else None)
    if mode == 'missing-finished':
        return
    w.emit(['Finished', 'Failed' if failed else 'Passed'])
    if mode == 'post-finished':
        w.emit(['Finished', 'Passed'])
    if mode == 'nonzero':
        raise SystemExit(7)


if __name__ == '__main__':
    main()
