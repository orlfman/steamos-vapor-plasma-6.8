#!/usr/bin/env python3
"""Verify appearance setup preserves existing profile data and refuses conflicts."""
import base64
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader('vapor_firefox_setup', str(ROOT/'tools/vapor-firefox'))
spec = importlib.util.spec_from_loader(loader.name, loader)
setup = importlib.util.module_from_spec(spec); loader.exec_module(setup)


class ProfileSetup(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='vapor-firefox-setup-')
        self.profile = Path(self.temporary.name)
        (self.profile/'prefs.js').write_bytes(b'// Test profile only\nuser_pref("example.setting", 7);\n')

    def tearDown(self):
        self.temporary.cleanup()

    def image(self):
        return {str(p.relative_to(self.profile)):(p.read_bytes(),p.stat().st_mode & 0o777)
                for p in self.profile.rglob('*') if p.is_file() and p.name != '.parentlock'}

    def test_missing_empty_and_existing_files_round_trip(self):
        for content in [None,b'',b'body { color: red; }',b'\xef\xbb\xbf@charset "UTF-8";\n@namespace url(example);\nbody {}']:
            with self.subTest(content=content):
                for rel in ['chrome/userChrome.css','chrome/userContent.css','user.js']:
                    path=self.profile/rel
                    if content is None:path.unlink(missing_ok=True)
                    else:path.parent.mkdir(exist_ok=True);path.write_bytes(content);path.chmod(0o640)
                before=self.image()
                setup.manage(self.profile,'install')
                installed=self.image();setup.manage(self.profile,'install')
                self.assertEqual(installed,self.image())
                setup.manage(self.profile,'remove');self.assertEqual(before,self.image())

    def test_import_follows_charset_without_newline(self):
        path=self.profile/'chrome/userChrome.css';path.parent.mkdir()
        path.write_bytes(b'@charset "UTF-8";body {}')
        setup.manage(self.profile,'install')
        self.assertTrue(path.read_bytes().startswith(b'@charset "UTF-8";/* BEGIN'))

    def test_preserves_later_css_and_preferences(self):
        setup.manage(self.profile,'install')
        css=self.profile/'chrome/userChrome.css'
        css.write_bytes(css.read_bytes()+b'/* Later user styling */\n')
        prefs=self.profile/'prefs.js'
        prefs.write_bytes(prefs.read_bytes()+b'user_pref("'+setup.KEY.encode()+b'", true);\nuser_pref("later.setting", false);\n')
        setup.manage(self.profile,'remove')
        self.assertEqual(css.read_bytes(),b'/* Later user styling */\n')
        self.assertTrue(setup.pref_value(prefs.read_bytes()))
        self.assertIn(b'later.setting',prefs.read_bytes())

    def test_restores_original_stylesheet_preference_after_browser_persists_it(self):
        for previous in [None,False,True]:
            with self.subTest(previous=previous):
                prefs=self.profile/'prefs.js';original=b'user_pref("other.setting", 7);\n'
                if previous is not None:original+=b'user_pref("'+setup.KEY.encode()+b'", '+str(previous).lower().encode()+b');\n'
                prefs.write_bytes(original)
                setup.manage(self.profile,'install')
                prefs.write_bytes(b'user_pref("other.setting", 7);\nuser_pref("'+setup.KEY.encode()+b'", true);\n')
                setup.manage(self.profile,'remove')
                self.assertEqual(setup.pref_value(prefs.read_bytes()),previous)
                self.assertIn(b'user_pref("other.setting", 7);',prefs.read_bytes())

    def test_edited_asset_and_marker_refuse_without_changes(self):
        setup.manage(self.profile,'install')
        asset=self.profile/'chrome/vapor-firefox/userChrome.css'
        original=asset.read_bytes();asset.write_bytes(original+b'/* edit */')
        before=self.image()
        for action in ['install','remove']:
            with self.assertRaises(ValueError):setup.manage(self.profile,action)
            self.assertEqual(before,self.image())
        asset.write_bytes(original)
        css=self.profile/'chrome/userChrome.css';css.write_bytes(css.read_bytes().replace(b'BEGIN Vapor',b'BEGIN Edited'))
        before=self.image()
        with self.assertRaises(ValueError):setup.manage(self.profile,'remove')
        self.assertEqual(before,self.image())

    def test_malformed_ownership_never_deletes_user_content(self):
        setup.manage(self.profile,'install')
        state=self.profile/setup.STATE;data=json.loads(state.read_text())
        data['files']['user.js']['block']=base64.b64encode((self.profile/'user.js').read_bytes()).decode()
        data['files']['user.js']['block']=base64.b64encode(b'arbitrary user data').decode()
        state.write_text(json.dumps(data));before=self.image()
        with self.assertRaises(ValueError):setup.manage(self.profile,'remove')
        self.assertEqual(before,self.image())

    def test_symlink_and_readonly_targets_refuse(self):
        css=self.profile/'chrome/userChrome.css';css.parent.mkdir()
        outside=self.profile/'untouched';outside.write_bytes(b'keep me')
        css.symlink_to(outside)
        with self.assertRaises(ValueError):setup.manage(self.profile,'install')
        self.assertEqual(outside.read_bytes(),b'keep me')
        css.unlink();css.write_bytes(b'keep');css.chmod(0o400)
        with self.assertRaises(ValueError):setup.manage(self.profile,'install')

    def test_existing_asset_folder_is_not_overwritten(self):
        folder=self.profile/'chrome/vapor-firefox';folder.mkdir(parents=True)
        (folder/'userChrome.css').write_bytes(b'Unowned existing file')
        before=self.image()
        with self.assertRaises(ValueError):setup.manage(self.profile,'install')
        self.assertEqual(before,self.image())

    def test_live_profile_lock_refuses(self):
        # A separate lock owner is required because POSIX record locks are per-process.
        import subprocess
        program='import fcntl,sys,time; f=open(sys.argv[1],"a+"); fcntl.lockf(f,fcntl.LOCK_EX); print("locked",flush=True); time.sleep(20)'
        child=subprocess.Popen([os.sys.executable,'-c',program,str(self.profile/'.parentlock')],stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'locked')
            before=self.image()
            with self.assertRaises(ValueError):setup.manage(self.profile,'install')
            self.assertEqual(before,self.image())
        finally:child.terminate();child.wait();child.stdout.close()

    def test_write_failure_rolls_back(self):
        for failure_at in range(1,7):
            with self.subTest(failure_at=failure_at):
                before=self.image();actual=setup.write;counter=0
                def failing(*args):
                    nonlocal counter
                    counter+=1
                    if counter==failure_at:raise OSError('Injected write failure')
                    return actual(*args)
                with patch.object(setup,'write',failing):
                    with self.assertRaises(OSError):setup.manage(self.profile,'install')
                self.assertEqual(before,self.image())
                setup.manage(self.profile,'install')
                setup.manage(self.profile,'remove')
                self.assertEqual(before,self.image())


if __name__=='__main__':unittest.main()
