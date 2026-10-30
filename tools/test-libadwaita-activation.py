#!/usr/bin/env python3
"""Exercise reversible activation and failure recovery using disposable configs."""
import json
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT/'tools/vapor-libadwaita'
PROFILE = ROOT/'libadwaita/vapor.css'
MODULE = runpy.run_path(str(HELPER))
BLOCK = MODULE['BLOCK']
NAMES = MODULE['NAMES']


class Activation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vapor-activation-check-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root/'config'
        self.directory = self.config/'gtk-4.0'

    def run_helper(self, action, *extra, ok=True):
        result = subprocess.run([sys.executable, '-I', str(HELPER), action, '--json',
                                 '--config-home', str(self.config), '--profile', str(PROFILE), *extra],
                                capture_output=True, text=True, timeout=10)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result

    def original(self, data=b"@import 'colors.css';", mode=0o640):
        self.directory.mkdir(parents=True)
        path = self.directory/'gtk.css';path.write_bytes(data);path.chmod(mode)
        return path

    def test_kde_import_and_mode_round_trip(self):
        path = self.original()
        original = path.read_bytes()
        self.run_helper('enable')
        self.assertEqual(path.read_bytes(), BLOCK+original)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertEqual((self.directory/NAMES[3]).read_bytes(), original)
        self.run_helper('disable')
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['gtk.css'])

    def test_missing_config_and_idempotence(self):
        self.assertEqual(self.run_helper('status')['status'], 'disabled')
        self.assertFalse(self.config.exists())
        self.run_helper('enable')
        first = {p.name:p.read_bytes() for p in self.directory.iterdir()}
        self.assertEqual(self.run_helper('enable')['changes'], [])
        self.assertEqual(first, {p.name:p.read_bytes() for p in self.directory.iterdir()})
        self.run_helper('disable')
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertEqual(self.run_helper('disable')['changes'], [])

    def test_dry_run_creates_nothing(self):
        self.run_helper('enable', '--dry-run')
        self.assertFalse(self.config.exists())
        path = self.original()
        before = path.read_bytes()
        self.run_helper('enable', '--dry-run')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['gtk.css'])

    def test_preserves_later_user_edits(self):
        path = self.original()
        original = path.read_bytes()
        self.run_helper('enable')
        edit = b'\n.my-custom-style { color: red; }\n'
        path.write_bytes(path.read_bytes()+edit)
        self.run_helper('disable')
        self.assertEqual(path.read_bytes(), original+edit)

    def test_external_rewrite_and_reapply(self):
        path = self.original()
        self.run_helper('enable')
        replacement = b"@import 'colors.css';\n/* KDE rewrote this file */\n"
        path.write_bytes(replacement)
        self.assertTrue(self.run_helper('status')['status'].startswith('inactive'))
        self.run_helper('enable')
        self.assertEqual(path.read_bytes(), BLOCK+replacement)
        self.run_helper('disable')
        self.assertEqual(path.read_bytes(), replacement)

    def test_profile_update_preserves_backup(self):
        self.original();self.run_helper('enable')
        backup = (self.directory/NAMES[3]).read_bytes()
        profile = self.root/'updated.css'
        profile.write_bytes(PROFILE.read_bytes()+b'\n/* profile update */\n')
        self.run_helper('enable', '--profile', str(profile))
        self.assertEqual((self.directory/NAMES[1]).read_bytes(), profile.read_bytes())
        self.assertEqual((self.directory/NAMES[3]).read_bytes(), backup)
        self.assertTrue(self.run_helper('status')['profile_update_available'])
        self.run_helper('disable')

    def test_deleted_config_reapply_removes_only_new_file(self):
        path=self.original();self.run_helper('enable');path.unlink()
        self.run_helper('enable');self.run_helper('disable')
        self.assertFalse(path.exists())
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_readonly_directory_refused(self):
        path=self.original();before=path.read_bytes()
        self.directory.chmod(0o555)
        try:self.run_helper('enable',ok=False)
        finally:self.directory.chmod(0o755)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['gtk.css'])

    def test_managed_profile_edits_are_preserved(self):
        self.original();self.run_helper('enable')
        path = self.directory/NAMES[1]
        edited = path.read_bytes()+b'\n/* personal edit */\n';path.write_bytes(edited)
        self.run_helper('enable', ok=False)
        self.run_helper('disable', ok=False)
        self.assertEqual(path.read_bytes(), edited)

    def test_symlinks_and_dangling_links_refused(self):
        self.directory.mkdir(parents=True)
        target = self.root/'target';target.write_bytes(b'untouched')
        for name in NAMES:
            with self.subTest(name=name):
                path = self.directory/name;path.symlink_to(target)
                self.run_helper('enable', ok=False)
                self.assertTrue(path.is_symlink());self.assertEqual(target.read_bytes(), b'untouched')
                path.unlink()
        (self.directory/'gtk.css').symlink_to(self.root/'missing')
        self.run_helper('enable', ok=False)
        self.assertTrue((self.directory/'gtk.css').is_symlink())

    def test_directory_symlink_refused(self):
        self.config.mkdir()
        target = self.root/'elsewhere';target.mkdir()
        self.directory.symlink_to(target, target_is_directory=True)
        self.run_helper('enable', ok=False)
        self.assertEqual(list(target.iterdir()), [])

    def test_readonly_and_collision_preserved(self):
        path = self.original(mode=0o444);before = path.read_bytes()
        self.run_helper('enable', ok=False)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['gtk.css'])
        path.chmod(0o640)
        collision = self.directory/NAMES[1];collision.write_bytes(b'not ours')
        self.run_helper('enable', ok=False)
        self.assertEqual(collision.read_bytes(), b'not ours')

    def test_bad_state_or_backup_prevents_deletion(self):
        path = self.original();self.run_helper('enable');before = path.read_bytes()
        (self.directory/NAMES[3]).write_bytes(b'changed backup')
        self.run_helper('disable', ok=False)
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_created_import_flag_changes_nothing(self):
        self.original(data=b'');self.run_helper('enable')
        statepath=self.directory/NAMES[2]
        valid=json.loads(statepath.read_text())
        for value in ('false','true',0,1,None,[],{}):
            with self.subTest(value=value):
                state=dict(valid,created_import_file=value)
                statepath.write_text(json.dumps(state))
                before={name:MODULE['inspect'](self.directory/name) for name in NAMES}
                for action in ('status','enable','disable'):
                    result=self.run_helper(action,ok=False)
                    self.assertIn('Managed state/backup is inconsistent',result.stderr)
                    self.assertEqual(before,{name:MODULE['inspect'](self.directory/name) for name in NAMES})

    def test_legacy_state_without_created_flag(self):
        for existed in (True,False):
            with self.subTest(original_exists=existed):
                if existed:self.original(data=b'')
                self.run_helper('enable')
                statepath=self.directory/NAMES[2]
                state=json.loads(statepath.read_text());del state['created_import_file']
                statepath.write_text(json.dumps(state))
                self.run_helper('disable')
                self.assertEqual((self.directory/'gtk.css').exists(),existed)
                if existed:(self.directory/'gtk.css').unlink()
                self.directory.rmdir()

    def test_edited_or_duplicate_import_refused(self):
        path = self.original();self.run_helper('enable')
        path.write_bytes(BLOCK+path.read_bytes())
        before = path.read_bytes();self.run_helper('disable', ok=False)
        self.assertEqual(path.read_bytes(), before)

    def test_transaction_restores_every_file_after_failure(self):
        path = self.original();before = {name:MODULE['inspect'](self.directory/name) for name in NAMES}
        changes = {name:(b'new content',0o600) for name in NAMES}
        function = MODULE['transaction'];real = MODULE['atomic_write'];calls = 0
        def fail_once(*args):
            nonlocal calls
            calls += 1
            if calls == 3:raise OSError('intentional write failure')
            return real(*args)
        with patch.dict(function.__globals__, {'atomic_write':fail_once}):
            with self.assertRaisesRegex(OSError, 'intentional write failure'):
                function(self.directory, before, changes)
        self.assertEqual(before, {name:MODULE['inspect'](self.directory/name) for name in NAMES})
        self.assertEqual(path.read_bytes(), b"@import 'colors.css';")
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['gtk.css'])


if __name__ == '__main__':
    unittest.main()
