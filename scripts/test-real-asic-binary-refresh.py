#!/usr/bin/env python3
"""Filesystem-only publication/rollback checks; no daemon, compiler or EDA."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('real_demo', Path(__file__).with_name('real-asic-example-demo.py'))
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class BinaryRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='real-demo-refresh-', dir='/tmp/opencode')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        for name in ('bin', 'receipts', 'sources'):
            (self.base / name).mkdir()
        self.names = ('daemon', 'client', 'preset-export')
        for name in self.names:
            (self.base / 'bin' / name).write_bytes(b'old-' + name.encode())
            source = self.base / 'sources' / name
            source.write_bytes(b'new-' + name.encode())
            source.chmod(0o700)
        self.manifest = dict(binaries={name: demo.digest(self.base / 'bin' / name) for name in self.names})
        demo.save(self.base / 'manifest.json', self.manifest)
        self.args = argparse.Namespace(daemon=self.base / 'sources/daemon', client=self.base / 'sources/client',
                                       preset_export=self.base / 'sources/preset-export')

    def unchanged(self):
        self.assertEqual(json.loads((self.base / 'manifest.json').read_text()), self.manifest)
        demo.verify_binaries(self.base, self.manifest)

    def test_success_records_exact_before_after_and_sources(self):
        demo.refresh_binaries(self.args, self.base)
        manifest = json.loads((self.base / 'manifest.json').read_text())
        demo.verify_binaries(self.base, manifest)
        receipt = json.loads((Path(manifest['binary_refresh_receipts']) / 'result.json').read_text())
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(receipt['before'], self.manifest['binaries'])
        self.assertEqual(receipt['after'], manifest['binaries'])
        self.assertTrue(receipt['restart_required'])
        for name in self.names:
            self.assertEqual(manifest['binaries'][name], demo.digest(self.base / 'sources' / name))

    def test_missing_input_never_publishes(self):
        self.args.client = self.base / 'missing'
        with self.assertRaises(FileNotFoundError):
            demo.refresh_binaries(self.args, self.base)
        self.unchanged()

    def test_second_publish_failure_restores_previous_candidate(self):
        replace = demo.os.replace
        def fail_second(source, destination):
            if Path(source).parent.name == 'staged' and Path(source).name == 'client':
                raise OSError('injected publication failure')
            return replace(source, destination)
        with patch.object(demo.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'injected'):
                demo.refresh_binaries(self.args, self.base)
        self.unchanged()


if __name__ == '__main__':
    unittest.main(verbosity=2)
