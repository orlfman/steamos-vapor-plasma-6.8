#!/usr/bin/env python3
"""Build the complete Vapor Firefox setup and its unsigned color component."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def build(source, output):
    source = source.resolve()
    manifest_path = source / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('theme') != manifest.get('dark_theme'):
        raise ValueError('Normal/dark variants must share the approved Vapor palette')
    if any(key in manifest for key in ('background', 'permissions', 'host_permissions',
                                      'content_scripts', 'theme_experiment')):
        raise ValueError('Only a static color theme is supported')
    version = manifest['version']
    if not version or any(c not in '0123456789.' for c in version):
        raise ValueError('Expected a numeric theme version')
    output = output.resolve()
    if output.is_relative_to(source):
        raise ValueError('Build output must be outside the theme source directory')
    output.mkdir(parents=True, exist_ok=True)
    target = output / f'vapor-firefox-{version}-unsigned.xpi'
    if target.is_symlink():
        raise ValueError('Refusing a symlink artifact')
    with tempfile.NamedTemporaryFile(dir=output, suffix='.xpi', delete=False) as f:
        temporary = Path(f.name)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in [('manifest.json', manifest_path.read_bytes()),
                               ('COPYING', (ROOT / 'firefox/COPYING').read_bytes())]:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        temporary.chmod(0o644)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    bundle = output / f'vapor-firefox-{version}.zip'
    if bundle.is_symlink():
        raise ValueError('Refusing a symlink bundle')
    files = [('README.md', ROOT/'firefox/INSTALL.md', 0o644),
             ('COPYING', ROOT/'firefox/COPYING', 0o644),
             ('Apply Vapor to Firefox', ROOT/'firefox/Apply Vapor to Firefox', 0o755),
             ('tools/vapor-firefox', ROOT/'tools/vapor-firefox', 0o755),
             ('firefox/vapor/userChrome.css', source/'userChrome.css', 0o644),
             ('firefox/vapor/userContent.css', source/'userContent.css', 0o644)]
    with tempfile.NamedTemporaryFile(dir=output, suffix='.zip', delete=False) as f:
        temporary = Path(f.name)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, path, mode in files:
                info = zipfile.ZipInfo(f'vapor-firefox-{version}/{name}', date_time=(1980,1,1,0,0,0))
                info.create_system = 3
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, path.read_bytes())
        temporary.chmod(0o644)
        temporary.replace(bundle)
    finally:
        temporary.unlink(missing_ok=True)
    return {'bundle':str(bundle), 'bundle_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
            'artifact':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'signed':False,'default_appearance':'Vapor colors and Breeze-inspired UI'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'firefox/vapor')
    parser.add_argument('--output', type=Path, default=ROOT / 'firefox/build')
    args = parser.parse_args()
    try:
        result = build(args.source, args.output)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'Firefox build failed: {exc}\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
