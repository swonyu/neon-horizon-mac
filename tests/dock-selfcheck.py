#!/usr/bin/env python3
"""Dock policy and recovery checks; temporary apps and mocked native commands only."""
import contextlib
import copy
from datetime import datetime
import importlib.util
import io
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
assert (ROOT / 'dock.py').is_file(), 'Dock personalization command has not been implemented'
spec = importlib.util.spec_from_file_location('dock', ROOT / 'dock.py')
dock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dock)


class DockChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.apps = self.root / 'Applications'
        self.apps.mkdir()
        self.screen = self.app('Screen Sharing')
        self.a, self.b, self.c = [self.app(n) for n in ('Alpha & One', 'Beta', 'Gamma')]
        self.domain = {'persistent-apps': [], 'persistent-others': [{'keep': b'folder'}], 'tilesize': 47}
        self.metadata = {}
        self.calls = []
        self.write_hook = None
        self.addCleanup(patch.stopall)
        patch.object(dock, 'SCREEN_SHARING_PATHS', (self.screen,)).start()
        patch.object(dock.subprocess, 'run', side_effect=self.native).start()

    def app(self, name, parent=None):
        app = (parent or self.apps) / (name + '.app')
        (app / 'Contents').mkdir(parents=True)
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({
            'CFBundlePackageType': 'APPL', 'CFBundleIdentifier': 'example.' + name,
            'CFBundleExecutable': name,
        }))
        return app

    def tile(self, path, guid=123):
        return {'GUID': guid, 'tile-type': 'file-tile', 'tile-data': {
            'file-data': {'_CFURLString': path.as_uri(), '_CFURLStringType': 15},
            'file-label': path.stem, 'book': b'original bookmark\x00\xff', 'custom': True,
        }}

    def native(self, args, **kwargs):
        self.calls.append(args)
        if args[:3] == ['/usr/bin/defaults', 'export', 'com.apple.dock']:
            return subprocess.CompletedProcess(args, 0, plistlib.dumps(self.domain))
        if args[:4] == ['/usr/bin/defaults', 'write', 'com.apple.dock', 'persistent-apps']:
            self.assertEqual(args[4], '-array')
            if self.write_hook:
                self.write_hook()
            self.domain['persistent-apps'] = [plistlib.loads(t.encode()) for t in args[5:]]
            return subprocess.CompletedProcess(args, 0, b'')
        if args[0] == '/usr/bin/mdls':
            self.assertEqual(args[1:3], ['-plist', '-'])
            value = self.metadata.get(Path(args[-1]), {})
            if isinstance(value, Exception):
                raise value
            return subprocess.CompletedProcess(args, 0, value if isinstance(value, bytes) else plistlib.dumps(value))
        self.fail('Unexpected native call: ' + repr(args))

    def paths(self, tiles):
        return [dock.app_path(t) for t in tiles if t.get('tile-type') != 'small-spacer-tile']

    def test_ranks_measured_pins_keeps_fallback_and_original_objects(self):
        offline = self.tile(self.root / 'Offline.app', 9)
        opaque = {'tile-type': 'unknown-tile', 'tile-data': {'file-label': 'Keep me'}}
        before = [self.tile(self.a), offline, self.tile(self.b, 2), opaque, self.tile(self.c, 3)]
        self.domain['persistent-apps'] = copy.deepcopy(before)
        self.metadata[self.a] = {'kMDItemUseCount': 2}
        self.metadata[self.b] = {'kMDItemUseCount': 8}
        result = dock.plan()
        self.assertEqual(self.paths(result['applied'])[:3], [self.screen, self.b, self.a])
        self.assertEqual(result['applied'][4:], [offline, opaque, before[4]])
        self.assertEqual(result['applied'][2], before[2])
        self.assertEqual(result['before'], before)
        self.assertEqual(self.domain['persistent-apps'], before)

    def test_missing_metadata_keeps_existing_order(self):
        self.domain['persistent-apps'] = [self.tile(self.c), self.tile(self.a), self.tile(self.b)]
        self.metadata[self.a] = b'not a plist'
        self.metadata[self.b] = subprocess.CalledProcessError(1, ['mdls'])
        result = dock.plan()
        self.assertEqual(self.paths(result['applied']), [self.screen, self.c, self.a, self.b])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            dock.show_plan(result)
        self.assertIn('original order', out.getvalue())
        self.assertIn('not Screen Time', out.getvalue())

    def test_count_then_recency_and_stable_ties(self):
        self.domain['persistent-apps'] = [self.tile(self.a), self.tile(self.b), self.tile(self.c)]
        self.metadata[self.a] = {'kMDItemUseCount': 5, 'kMDItemLastUsedDate': datetime(2025, 1, 1)}
        self.metadata[self.b] = {'kMDItemUseCount': 5, 'kMDItemLastUsedDate': datetime(2026, 1, 1)}
        self.metadata[self.c] = dict(self.metadata[self.b])
        self.assertEqual(self.paths(dock.plan()['applied']), [self.screen, self.b, self.c, self.a])

    def test_date_without_count_stays_in_original_order(self):
        self.domain['persistent-apps'] = [self.tile(self.a), self.tile(self.b), self.tile(self.c)]
        self.metadata[self.b] = {'kMDItemLastUsedDate': datetime(2026, 1, 1)}
        self.assertEqual(self.paths(dock.plan()['applied']), [self.screen, self.a, self.b, self.c])

    def test_discovery_requires_positive_count_even_when_date_is_present(self):
        self.domain['persistent-apps'] = []
        self.metadata[self.a] = {'kMDItemLastUsedDate': datetime(2026, 1, 1)}
        self.metadata[self.b] = {'kMDItemUseCount': 0, 'kMDItemLastUsedDate': datetime(2026, 1, 1)}
        self.metadata[self.c] = {'kMDItemUseCount': 1}
        self.assertEqual(self.paths(dock.plan(discover=True, directories=(self.apps,))['applied']),
                         [self.screen, self.c])

    def test_deduplicates_paths_preserves_screen_tile_and_is_repeatable(self):
        screen = self.tile(self.screen, 55)
        alias = self.apps / 'Alias.app'
        alias.symlink_to(self.a, target_is_directory=True)
        self.domain['persistent-apps'] = [self.tile(self.a), {'tile-type': 'spacer-tile'},
                                          screen, self.tile(alias, 99)]
        first = dock.plan()
        self.assertEqual(first['applied'][0], screen)
        self.assertEqual(self.paths(first['applied']), [self.screen, self.a])
        self.assertEqual(sum(t['tile-type'] == 'small-spacer-tile' for t in first['applied']), 1)
        self.domain['persistent-apps'] = first['applied']
        self.assertEqual(dock.plan()['applied'], first['applied'])

    def test_discovery_is_explicit_shallow_and_adds_at_most_three_used_apps(self):
        self.domain['persistent-apps'] = [self.tile(self.a)]
        extra = [self.app('New ' + str(i)) for i in range(5)]
        for i, app in enumerate(extra):
            self.metadata[app] = {'kMDItemUseCount': i + 1}
        self.metadata[self.b] = {'kMDItemUseCount': 0}
        nested = self.app('Helper', self.a / 'Contents')
        self.metadata[nested] = {'kMDItemUseCount': 1000}
        self.assertEqual(self.paths(dock.plan()['applied']), [self.screen, self.a])
        result = dock.plan(discover=True, directories=(self.apps,))
        self.assertEqual(set(self.paths(result['applied'])), {self.screen, self.a, *extra[-3:]})
        self.assertEqual(result['added'], 3)
        self.assertNotIn(nested, self.paths(result['applied']))

    def test_invalid_app_paths_do_not_become_new_tiles(self):
        for value in ('https://example.com/Alpha.app', 'file://remote/Alpha.app', 'file:///bad%00.app'):
            self.assertIsNone(dock.app_path({'tile-data': {'file-data': {'_CFURLString': value}}}))
        fake = self.apps / 'Fake.app'
        fake.mkdir()
        self.assertIsNone(dock.valid_app(fake))
        self.assertEqual(dock.app_path(self.tile(self.a)), self.a)

    def test_apply_journals_first_writes_one_key_and_verifies(self):
        self.domain['persistent-apps'] = [self.tile(self.a)]
        plan = dock.plan()
        directory = self.root / 'private'
        def before_write():
            records = list(directory.glob('*.plist'))
            self.assertEqual(len(records), 1)
            saved = plistlib.loads(records[0].read_bytes())
            self.assertEqual(saved['before'], plan['before'])
            self.assertEqual(saved['applied'], plan['applied'])
            self.assertEqual(os.stat(directory).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(records[0]).st_mode & 0o777, 0o600)
        self.write_hook = before_write
        with dock.locked(directory):
            journal = dock.apply(plan, directory)
        self.assertEqual(self.domain['persistent-apps'], plan['applied'])
        self.assertEqual(self.domain['persistent-others'], [{'keep': b'folder'}])
        self.assertEqual(self.domain['tilesize'], 47)
        self.assertTrue(journal.is_file())

    def test_stale_preview_refused_without_write(self):
        plan = dock.plan()
        self.domain['persistent-apps'] = [self.tile(self.a)]
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            dock.apply(plan, self.root)
        self.assertFalse(any(c[1] == 'write' for c in self.calls))
        self.assertEqual(list(self.root.glob('*.plist')), [])

    def test_undo_is_verified_idempotent_and_preserves_later_edits(self):
        self.domain['persistent-apps'] = [self.tile(self.a)]
        plan = dock.plan()
        journal = dock.apply(plan, self.root)
        record = dock.load_record(journal)
        self.assertTrue(dock.undo(record))
        self.assertEqual(self.domain['persistent-apps'], plan['before'])
        self.assertTrue(dock.undo(record))
        self.domain['persistent-apps'] = [self.tile(self.b)]
        self.assertFalse(dock.undo(record))
        self.assertEqual(self.domain['persistent-apps'], [self.tile(self.b)])

    def test_invalid_backups_and_preference_schema_fail_before_write(self):
        for bad in ({}, {'format': 'neon-horizon-dock-v1', 'before': [], 'applied': 'bad'}):
            with self.assertRaises(ValueError):
                dock.validate_record(bad)
        self.domain['persistent-apps'] = 'not an array'
        with self.assertRaises(ValueError):
            dock.plan()
        self.assertFalse(any(c[1] == 'write' for c in self.calls))

    def test_failed_or_unverified_writes_keep_the_recovery_record(self):
        self.domain['persistent-apps'] = [self.tile(self.a)]
        plan = dock.plan()
        with patch.object(dock, 'write_apps', side_effect=OSError('injected write failure')):
            with self.assertRaises(OSError):
                dock.apply(plan, self.root)
        records = list(self.root.glob('*.plist'))
        self.assertEqual(len(records), 1)
        self.assertEqual(dock.load_record(records[0])['before'], plan['before'])
        with patch.object(dock, 'write_apps'):
            with self.assertRaisesRegex(RuntimeError, 'readback'):
                dock.apply(plan, self.root)
        self.domain['persistent-apps'] = plan['applied']
        with patch.object(dock, 'write_apps'):
            with self.assertRaisesRegex(RuntimeError, 'restore readback'):
                dock.undo(dock.load_record(records[0]))

    def test_publication_failure_and_during_journal_edit_never_write(self):
        plan = dock.plan()
        with patch.object(dock.os, 'fsync', side_effect=OSError('injected fsync failure')):
            with self.assertRaises(OSError):
                dock.apply(plan, self.root)
        self.assertEqual(list(self.root.glob('*.plist')), [])
        original = dock.save
        def concurrent_edit(path, record):
            original(path, record)
            self.domain['persistent-apps'] = [self.tile(self.a)]
        with patch.object(dock, 'save', side_effect=concurrent_edit):
            with self.assertRaisesRegex(RuntimeError, 'changed before writing'):
                dock.apply(plan, self.root)
        self.assertFalse(any(c[1] == 'write' for c in self.calls))

    def test_backup_types_identity_and_private_directory(self):
        self.assertFalse(dock.same([{'number': 1}], [{'number': True}]))
        self.assertFalse(dock.same([{'number': 1}], [{'number': 1.0}]))
        plan = dock.plan()
        record = dock.load_record(dock.apply(plan, self.root))
        for key, value in [('uid', -1), ('home', '/somebody-else'), ('before', [False])]:
            invalid = dict(record, **{key: value})
            with self.assertRaises(ValueError):
                dock.validate_record(invalid)
        link = self.root / 'linked'
        link.symlink_to(self.apps, target_is_directory=True)
        with self.assertRaises(ValueError):
            with dock.locked(link):
                self.fail('Symlink must not be used for private backups')

    def test_noop_and_missing_screen_sharing(self):
        self.domain['persistent-apps'] = [self.tile(self.screen)]
        plan = dock.plan()
        self.assertEqual(plan['before'], plan['applied'])
        self.assertIsNone(dock.apply(plan, self.root))
        with patch.object(dock, 'SCREEN_SHARING_PATHS', (self.root / 'Missing.app',)):
            with self.assertRaisesRegex(ValueError, 'Screen Sharing'):
                dock.plan()
        self.assertFalse(any(c[1] == 'write' for c in self.calls))

    def test_metadata_timeout_and_malformed_xml_fall_back(self):
        self.domain['persistent-apps'] = [self.tile(self.a), self.tile(self.b)]
        self.metadata[self.a] = subprocess.TimeoutExpired(['mdls'], 3)
        self.metadata[self.b] = b'<?xml version="1.0"?><plist><dict>'
        self.assertEqual(self.paths(dock.plan()['applied']), [self.screen, self.a, self.b])

    def test_main_refuses_other_platform_before_native_commands(self):
        with patch.object(dock.sys, 'platform', 'linux'), patch.object(dock.sys, 'argv', ['dock.py', 'apply']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                dock.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
