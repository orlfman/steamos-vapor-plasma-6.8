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
HELPER = Path(os.environ.get('VAPOR_TEST_HELPER',str(ROOT/'tools/vapor-libadwaita')))
PROFILE = ROOT/'libadwaita/vapor.css'
MODULE = runpy.run_path(str(HELPER))
BLOCK = MODULE['BLOCK']
NAMES = MODULE['NAMES']
DISABLED_NAME = MODULE['DISABLED_NAME']
ALL_NAMES = (*NAMES, DISABLED_NAME)


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

    def theme(self, name, version='gtk-4.0'):
        directory=self.config/version;directory.mkdir(parents=True,exist_ok=True)
        (directory/'settings.ini').write_text('[Settings]\ngtk-theme-name='+name+'\n')

    def snapshot(self):
        return {name:MODULE['inspect'](self.directory/name) for name in ALL_NAMES}

    def selected_helper(self, action, *extra, ok=True):
        result=subprocess.run([sys.executable,'-I',str(HELPER),action,'--json',
                               '--config-home',str(self.config),*extra],capture_output=True,text=True,timeout=10)
        if not ok:
            self.assertNotEqual(result.returncode,0);return result
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def test_family_round_trip_preserves_backup_and_css(self):
        for original in (None,b'',b"@import 'colors.css';\n"):
            with self.subTest(original=original):
                if self.config.exists():
                    import shutil
                    shutil.rmtree(self.config)
                if original is not None:self.original(original)
                self.theme('Vapor');self.selected_helper('auto')
                backup=MODULE['inspect'](self.directory/NAMES[3])
                for theme,profile_id in (('VGUI2Classic','vgui2'),('Vapor-dark','vapor'),('VGUI2Classic','vgui2')):
                    self.theme(theme);result=self.selected_helper('auto')
                    self.assertEqual(result['profile_id'],profile_id)
                    self.assertEqual((self.directory/NAMES[1]).read_bytes(),(ROOT/'libadwaita'/(profile_id+'.css')).read_bytes())
                    self.assertEqual(MODULE['inspect'](self.directory/NAMES[3]),backup)
                    self.assertEqual((self.directory/'gtk.css').read_bytes().count(BLOCK),1)
                    self.assertEqual(self.selected_helper('auto')['changes'],[])
                self.theme('Breeze');self.selected_helper('auto')
                self.assertEqual((self.directory/'gtk.css').exists(),original is not None)
                if original is not None:self.assertEqual((self.directory/'gtk.css').read_bytes(),original)
                self.assertFalse((self.directory/DISABLED_NAME).exists())

    def test_explicit_selection_and_legacy_enable_default(self):
        self.assertEqual(self.selected_helper('enable')['profile_id'],'vapor')
        self.assertEqual(self.selected_helper('enable','--theme','vgui2')['profile_id'],'vgui2')
        self.assertEqual(self.selected_helper('status')['profile_id'],'vgui2')
        self.theme('VGUI2Classic')
        self.assertEqual(self.selected_helper('enable')['profile_id'],'vgui2')
        self.theme('Breeze')
        self.assertEqual(self.selected_helper('enable')['profile_id'],'vapor')

    def test_shared_disable_survives_family_changes(self):
        self.theme('Vapor');self.selected_helper('auto');self.selected_helper('disable')
        for theme in ('VGUI2Classic','Vapor','VGUI2Classic'):
            self.theme(theme);before=self.snapshot()
            result=self.selected_helper('auto')
            self.assertFalse(result['automatic_enabled']);self.assertEqual(result['changes'],[])
            self.assertEqual(before,self.snapshot())
        self.selected_helper('enable')
        self.assertFalse((self.directory/DISABLED_NAME).exists())
        self.assertEqual(self.selected_helper('status')['profile_id'],'vgui2')

    def test_legacy_vapor_state_migrates_without_new_backup(self):
        self.original();self.selected_helper('enable')
        path=self.directory/NAMES[2];state=json.loads(path.read_text());state.pop('profile_id')
        path.write_text(json.dumps(state));backup=MODULE['inspect'](self.directory/NAMES[3])
        self.assertEqual(self.selected_helper('status')['profile_id'],'vapor')
        self.theme('VGUI2Classic');self.selected_helper('auto')
        self.assertEqual(json.loads(path.read_text())['profile_id'],'vgui2')
        self.assertEqual(MODULE['inspect'](self.directory/NAMES[3]),backup)

    def test_invalid_profile_id_refused_without_writes(self):
        self.selected_helper('enable');path=self.directory/NAMES[2]
        original=json.loads(path.read_text())
        for invalid in ('unknown','../vapor',None,[],{}):
            state=dict(original,profile_id=invalid);path.write_text(json.dumps(state));before=self.snapshot()
            for action in ('enable','disable','auto','status'):
                self.selected_helper(action,ok=False);self.assertEqual(before,self.snapshot())

    def test_missing_and_edited_profile_switches(self):
        path=self.original();self.theme('Vapor');self.selected_helper('auto')
        (self.directory/NAMES[1]).unlink();self.theme('VGUI2Classic');self.selected_helper('auto')
        self.assertEqual(self.selected_helper('status')['profile_id'],'vgui2')
        (self.directory/NAMES[1]).write_bytes(b'personal profile edits');self.theme('Vapor')
        before=self.snapshot();self.selected_helper('auto',ok=False);self.assertEqual(before,self.snapshot())
        path.write_bytes(b"@import 'colors.css';\n/* regenerated */\n")
        before=self.snapshot();self.selected_helper('auto',ok=False);self.assertEqual(before,self.snapshot())

    def test_family_switch_dry_run_and_runtime_failure(self):
        self.original();self.theme('Vapor');self.selected_helper('auto');self.theme('VGUI2Classic')
        before=self.snapshot();result=self.selected_helper('auto','--dry-run')
        self.assertEqual(result['profile_id'],'vgui2');self.assertEqual(before,self.snapshot())
        function=MODULE['manage']
        with patch.dict(function.__globals__,{'check_runtime':lambda:(_ for _ in ()).throw(ValueError('runtime unavailable'))}):
            with self.assertRaisesRegex(ValueError,'runtime unavailable'):
                function(self.directory,None,'auto',False)
        self.assertEqual(before,self.snapshot())

    def test_failed_family_switch_rolls_back_everything(self):
        self.original();self.theme('Vapor');self.selected_helper('auto');self.theme('VGUI2Classic')
        before=self.snapshot();function=MODULE['manage'];real=MODULE['atomic_write'];calls=0
        def fail_once(*args):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('intentional profile switch failure')
            return real(*args)
        with patch.dict(function.__globals__,{'atomic_write':fail_once}):
            with self.assertRaisesRegex(OSError,'intentional profile switch failure'):
                function(self.directory,None,'auto',False)
        self.assertEqual(before,self.snapshot())

    def test_status_uses_active_family_and_reports_pending_switch(self):
        self.theme('VGUI2Classic');self.selected_helper('auto')
        result=self.selected_helper('status')
        self.assertEqual(result['profile_id'],'vgui2');self.assertFalse(result['profile_update_available'])
        self.theme('Vapor');result=self.selected_helper('status')
        self.assertTrue(result['profile_switch_available']);self.assertFalse(result['profile_update_available'])

    def test_gtk_selection_precedence_and_diagnostic_override_for_vgui(self):
        self.theme('VGUI2Classic','gtk-3.0');self.assertEqual(self.selected_helper('auto')['profile_id'],'vgui2')
        self.theme('Vapor');self.assertEqual(self.selected_helper('auto')['profile_id'],'vapor')
        self.theme('VGUI2Classic')
        custom=self.root/'custom.css';custom.write_bytes((ROOT/'libadwaita/vgui2.css').read_bytes()+b'\n/* custom */\n')
        self.selected_helper('auto','--profile',str(custom))
        self.assertEqual((self.directory/NAMES[1]).read_bytes(),custom.read_bytes())

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
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), [DISABLED_NAME,'gtk.css'])

    def test_missing_config_and_idempotence(self):
        self.assertEqual(self.run_helper('status')['status'], 'disabled')
        self.assertFalse(self.config.exists())
        self.run_helper('enable')
        first = {p.name:p.read_bytes() for p in self.directory.iterdir()}
        self.assertEqual(self.run_helper('enable')['changes'], [])
        self.assertEqual(first, {p.name:p.read_bytes() for p in self.directory.iterdir()})
        self.run_helper('disable')
        self.assertEqual([p.name for p in self.directory.iterdir()], [DISABLED_NAME])
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
        self.assertEqual([p.name for p in self.directory.iterdir()], [DISABLED_NAME])

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
                before=self.snapshot()
                for action in ('status','enable','disable','auto'):
                    result=self.run_helper(action,ok=False)
                    self.assertIn('Managed state/backup is inconsistent',result.stderr)
                    self.assertEqual(before,self.snapshot())

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
                (self.directory/DISABLED_NAME).unlink()
                self.directory.rmdir()

    def test_auto_other_or_missing_theme_creates_nothing(self):
        self.assertEqual(self.run_helper('auto')['changes'],[])
        self.assertFalse(self.config.exists())
        self.theme('Breeze')
        before=self.snapshot()
        self.assertEqual(self.run_helper('auto')['changes'],[])
        self.assertEqual(before,self.snapshot())

    def test_auto_selected_vapor_preserves_kde_and_is_idempotent(self):
        path=self.original();original=path.read_bytes();self.theme('Vapor')
        self.assertEqual(self.run_helper('auto')['status'],'enabled')
        self.assertEqual(path.read_bytes(),BLOCK+original)
        self.assertEqual((self.directory/NAMES[3]).read_bytes(),original)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o640)
        before=self.snapshot()
        self.assertEqual(self.run_helper('auto')['changes'],[])
        self.assertEqual(before,self.snapshot())

    def test_auto_selected_dark_variant(self):
        self.theme('Vapor-dark')
        self.assertEqual(self.run_helper('auto')['status'],'enabled')

    def test_auto_disable_persists_and_enable_clears_optout(self):
        self.theme('Vapor');self.run_helper('auto');self.run_helper('disable')
        before=self.snapshot()
        self.assertFalse(self.run_helper('status')['automatic_enabled'])
        for _ in range(3):
            self.assertEqual(self.run_helper('auto')['changes'],[])
            self.assertEqual(before,self.snapshot())
        self.run_helper('enable')
        self.assertFalse((self.directory/DISABLED_NAME).exists())
        self.assertTrue(self.run_helper('status')['automatic_enabled'])
        self.assertEqual(self.run_helper('auto')['changes'],[])

    def test_auto_switch_away_and_back_restores(self):
        path=self.original();original=path.read_bytes();self.theme('Vapor');self.run_helper('auto')
        self.theme('Breeze')
        self.assertEqual(self.run_helper('auto')['status'],'disabled')
        self.assertEqual(path.read_bytes(),original)
        self.assertFalse((self.directory/DISABLED_NAME).exists())
        self.theme('Vapor')
        self.assertEqual(self.run_helper('auto')['status'],'enabled')
        self.assertEqual(path.read_bytes(),BLOCK+original)

    def test_auto_reapply_and_update(self):
        path=self.original();self.theme('Vapor');self.run_helper('auto')
        replacement=b"@import 'colors.css';\n/* KDE regeneration */\n";path.write_bytes(replacement)
        profile=self.root/'updated.css';profile.write_bytes(PROFILE.read_bytes()+b'\n/* update */\n')
        self.run_helper('auto','--profile',str(profile))
        self.assertEqual(path.read_bytes(),BLOCK+replacement)
        self.assertEqual((self.directory/NAMES[1]).read_bytes(),profile.read_bytes())
        self.run_helper('disable')
        self.assertEqual(path.read_bytes(),replacement)

    def test_auto_and_disable_dry_runs_preserve_every_file(self):
        self.theme('Vapor');before=self.snapshot()
        self.run_helper('auto','--dry-run')
        self.assertEqual(before,self.snapshot())
        self.run_helper('enable');before=self.snapshot()
        self.run_helper('disable','--dry-run')
        self.assertEqual(before,self.snapshot())

    def test_automatic_preference_collision_and_symlink_refused(self):
        self.theme('Vapor');marker=self.directory/DISABLED_NAME
        marker.write_bytes(b'not managed by Vapor');before=self.snapshot()
        for action in ('status','auto','enable','disable'):
            self.run_helper(action,ok=False);self.assertEqual(before,self.snapshot())
        marker.unlink();target=self.root/'foreign';target.write_bytes(b'untouched');marker.symlink_to(target)
        for action in ('status','auto','enable','disable'):
            self.run_helper(action,ok=False)
            self.assertTrue(marker.is_symlink());self.assertEqual(target.read_bytes(),b'untouched')

    def test_auto_gtk4_precedence_and_gtk3_fallback(self):
        self.theme('Vapor','gtk-3.0')
        self.assertEqual(self.run_helper('auto')['status'],'enabled')
        self.theme('Breeze','gtk-4.0')
        self.assertEqual(self.run_helper('auto')['status'],'disabled')

    def test_auto_malformed_theme_refused_without_writes(self):
        self.theme('Vapor')
        (self.directory/'settings.ini').write_text('[Settings]\n[Settings]\n')
        before=self.snapshot()
        result=self.run_helper('auto',ok=False)
        self.assertIn('Cannot read GTK theme preference',result.stderr)
        self.assertEqual(before,self.snapshot())

    def test_disable_preference_rolls_back_with_css_after_failure(self):
        self.original();self.run_helper('enable');before=self.snapshot()
        function=MODULE['manage'];real=MODULE['atomic_write'];calls=0
        def fail_once(*args):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('intentional disable failure')
            return real(*args)
        with patch.dict(function.__globals__,{'atomic_write':fail_once}):
            with self.assertRaisesRegex(OSError,'intentional disable failure'):
                function(self.directory,PROFILE,'disable',False)
        self.assertEqual(before,self.snapshot())

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
