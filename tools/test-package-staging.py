#!/usr/bin/env python3
"""Test staging-path containment and payload creation using tiny private sources."""
import contextlib
import io
from pathlib import Path
import runpy
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
MODULE=runpy.run_path(str(ROOT/'tools/stage-package.py'))


class Staging(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='vapor-staging-check-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'source';(self.source/'usr/share/theme').mkdir(parents=True)
        (self.source/'usr/share/theme/sentinel').write_bytes(b'x')
        for name in ('libadwaita/vapor.css','libadwaita/vgui2.css','tools/vapor-libadwaita','alacritty/vapor.toml','kitty/vapor.conf',
                     'autostart/steamos-vapor-libadwaita.desktop',
                     'docs/screenshots/vapor-libadwaita-mission-center-ffmpeg-converter-2026-10-30.png',
                     'VGUI2-GTK3.md','VGUI2-GTK4.md','VGUI2-LIBADWAITA.md','vgui2-audit.md','vgui2-plan.md',
                     'docs/screenshots/vgui2-libadwaita-preview.png',
                     'docs/screenshots/vgui2-libadwaita-ffmpeg-converter.png',
                     'docs/audits/vgui2-libadwaita-validation.json',
                     'docs/screenshots/vgui2-gtk3-preview.png','docs/screenshots/vgui2-gtk3-meld.png',
                     'docs/screenshots/vgui2-gtk3-states.png','docs/screenshots/vgui2-gtk3-notebooks.png',
                     'docs/screenshots/vgui2-gtk4-preview.png','docs/screenshots/vgui2-gtk4-widget-factory.png',
                     'docs/screenshots/vgui2-gtk4-states.png','docs/audits/vgui2-gtk4-validation.json',
                     'docs/screenshots/vgui2-gtk4-widget-factory-details.png',
                     'docs/screenshots/vgui2-qt-windows-reference.png','docs/audits/vgui2-feasibility.json',
                     'docs/audits/vgui2-gtk3-validation.json',
                     'README.md','CHANGES.txt','GTK3.md','gtk4port.md','LIBADWAITA.md','libadwaita-plan.md','audit.md'):
            p=self.source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name+'\n')

    def run_stager(self,destination):
        function=MODULE['main']
        with patch.dict(function.__globals__,{'ROOT':self.source}), \
             patch.object(sys,'argv',['stage-package.py','--destdir',str(destination)]), \
             contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            return function()

    def assert_rejected_before_copy(self,destination):
        before=sorted(str(p.relative_to(self.source)) for p in self.source.rglob('*'))
        # Bound the unfixed implementation: a failed guard can never start a
        # recursive copy, even when this negative control runs on old code.
        with patch('shutil.copytree',side_effect=AssertionError('copy must not start')) as copy:
            with self.assertRaises(SystemExit) as error:self.run_stager(destination)
            self.assertEqual(error.exception.code,2)
            copy.assert_not_called()
        self.assertEqual(before,sorted(str(p.relative_to(self.source)) for p in self.source.rglob('*')))

    def test_reject_inside_copied_usr(self):
        self.assert_rejected_before_copy(self.source/'usr/stage')

    def test_reject_normalized_inside_copied_usr(self):
        self.assert_rejected_before_copy(self.source/'usr/../usr/stage')

    def test_reject_parent_symlink_into_usr(self):
        alias=self.root/'usr-alias';alias.symlink_to(self.source/'usr',target_is_directory=True)
        self.assert_rejected_before_copy(alias/'stage')

    def test_reject_existing_empty_directory_inside_usr(self):
        destination=self.source/'usr/stage';destination.mkdir()
        self.assert_rejected_before_copy(destination)
        self.assertEqual(list(destination.iterdir()),[])

    def assert_payload(self,destination):
        self.run_stager(destination)
        self.assertEqual((destination/'usr/share/theme/sentinel').read_bytes(),b'x')
        self.assertEqual((destination/'usr/share/steamos-vapor/libadwaita/vapor.css').read_bytes(),
                         (self.source/'libadwaita/vapor.css').read_bytes())
        self.assertEqual((destination/'usr/share/steamos-vapor/libadwaita/vgui2.css').read_bytes(),
                         (self.source/'libadwaita/vgui2.css').read_bytes())
        self.assertEqual(stat.S_IMODE((destination/'usr/bin/vapor-libadwaita').stat().st_mode),0o755)
        for source,target in (
                ('autostart/steamos-vapor-libadwaita.desktop','etc/xdg/autostart/steamos-vapor-libadwaita.desktop'),
                ('docs/screenshots/vapor-libadwaita-mission-center-ffmpeg-converter-2026-10-30.png',
                 'usr/share/doc/plasma6-themes-steamos-vapor-fixed/docs/screenshots/vapor-libadwaita-mission-center-ffmpeg-converter-2026-10-30.png')):
            self.assertEqual((destination/target).read_bytes(),(self.source/source).read_bytes())
        self.assertEqual((self.source/'usr/share/theme/sentinel').read_bytes(),b'x')
        self.assertEqual((destination/'usr/share/doc/plasma6-themes-steamos-vapor-fixed/VGUI2-GTK3.md').read_bytes(),
                         (self.source/'VGUI2-GTK3.md').read_bytes())
        for source in ('VGUI2-LIBADWAITA.md','docs/audits/vgui2-libadwaita-validation.json',
                       'docs/screenshots/vgui2-libadwaita-preview.png',
                       'docs/screenshots/vgui2-libadwaita-ffmpeg-converter.png'):
            self.assertEqual((destination/'usr/share/doc/plasma6-themes-steamos-vapor-fixed'/source).read_bytes(),
                             (self.source/source).read_bytes())

    def test_allow_repository_build_directory_outside_usr(self):
        self.assert_payload(self.source/'build/package')

    def test_allow_external_parent_symlink(self):
        external=self.root/'external';external.mkdir()
        alias=self.root/'external-alias';alias.symlink_to(external,target_is_directory=True)
        self.assert_payload(alias/'package')

    def test_reject_final_symlink(self):
        target=self.root/'target';target.mkdir()
        alias=self.root/'final-alias';alias.symlink_to(target,target_is_directory=True)
        self.assert_rejected_before_copy(alias)
        self.assertEqual(list(target.iterdir()),[])

    def test_reject_relative_destination(self):
        self.assert_rejected_before_copy(Path('relative-stage'))


if __name__=='__main__':unittest.main()
