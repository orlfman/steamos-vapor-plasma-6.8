#!/usr/bin/env python3
"""Test the installed GTK 4 Widget Factory on a private display.

Requires gtk4-demos, GTK 4.24 development/pkg-config files, a C compiler,
dbus-run-session, python-pillow and fonts. A temporary LD_PRELOAD helper is
passed only to the factory child. No theme/config/helper is installed and no
desktop input is sent. --strict also rejects the known Broadway timing warning.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
FAMILY_TOOLS=runpy.run_path(str(ROOT/'tools/theme-families.py'))
PAGES = ('page1', 'page2', 'page3')
# Reproduced on GTK 4.24.1 with only two named colors and no Vapor rules.
# Retain/count it; never ignore CSS diagnostics.
BROADWAY_WARNING = re.compile(
    r'\(gtk4-widget-factory:\d+\): Gdk-WARNING \*\*: [\d:.]+: '
    r'gdk_frame_timings_submitted\(\) called on submitted frame\.')


def terminate(process):
    """Stop only a process group started by this runner, including its children."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.communicate(timeout=5)


@contextmanager
def private_display(scratch, env):
    socket = scratch / 'http.socket'
    socket.unlink(missing_ok=True)
    server = subprocess.Popen(
        ['gtk4-broadwayd', '-u', str(socket), ':1'], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError(f'Private display exited: {server.communicate()}')
            if socket.exists():
                break
            time.sleep(.02)
        else:
            raise RuntimeError('Private display failed to start')
        yield
    finally:
        terminate(server)


def run_application(launch, env, output, case):
    process = subprocess.Popen(launch, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = terminate(process)
    except BaseException:
        terminate(process)
        raise
    (output / f'{case}.stdout').write_text(stdout)
    (output / f'{case}.stderr').write_text(stderr)
    if timed_out:
        raise RuntimeError(f'{case}: application timed out (logs: {output})')
    return process.returncode, stdout, stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='retain screenshots/logs; otherwise discard temporary output')
    parser.add_argument('--family',choices=tuple(FAMILY_TOOLS['FAMILIES']),default='vapor')
    parser.add_argument('--theme', type=Path)
    parser.add_argument('--user-css', type=Path, help='stage a libadwaita overlay to check plain GTK coexistence')
    parser.add_argument('--quick', action='store_true', help='one normal capture per page')
    parser.add_argument('--strict', action='store_true', help='also reject the known Broadway timing warning')
    args = parser.parse_args()
    family=FAMILY_TOOLS['get_family'](args.family)
    args.theme=args.theme or ROOT/'usr/share/themes'/family['name']
    from PIL import Image
    for command in ('gtk4-widget-factory', 'gtk4-broadwayd', 'pkg-config', 'cc', 'dbus-run-session'):
        if not shutil.which(command):
            parser.error(f'Missing {command}; see the requirements above.')
    binary = shutil.which('gtk4-widget-factory')
    source_theme = args.theme.resolve()
    source_css = source_theme / 'gtk-4.0/gtk.css'
    if not source_css.is_file():
        parser.error(f'Missing GTK 4 stylesheet: {source_css}')
    with tempfile.TemporaryDirectory(prefix='vapor-factory-check-') as name:
        scratch = Path(name)
        output = args.output.resolve() if args.output else scratch / 'output'
        output.mkdir(parents=True, exist_ok=True)
        # A failed repeat must not leave an earlier run's success report.
        (output / 'results.json').unlink(missing_ok=True)
        library = scratch / 'factory-probe.so'
        flags = shlex.split(subprocess.check_output(
            ['pkg-config', '--cflags', '--libs', 'gtk4 >= 4.24'], text=True))
        subprocess.run(['cc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
                        str(ROOT / 'tools/widget-factory-probe.c'), '-o', str(library),
                        *flags, '-ldl', '-lm'], check=True)
        env = os.environ.copy()
        for variable, folder in (('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'),
                                 ('XDG_CACHE_HOME', 'cache'), ('XDG_DATA_HOME', 'data'),
                                 ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'runtime')):
            path = scratch / folder
            path.mkdir(mode=0o700)
            env[variable] = str(path)
        theme = scratch / 'data/themes'/family['name']
        shutil.copytree(source_theme, theme)
        css = theme / 'gtk-4.0/gtk.css'
        # Unused marker proves discovery of this disposable copy. It changes
        # no widget selector or existing color.
        css.write_text(css.read_text() + '\n@define-color vapor_factory_test_marker #11171d;\n')
        settings = scratch / 'config/gtk-4.0'
        settings.mkdir()
        (settings / 'settings.ini').write_text(
            '[Settings]\ngtk-theme-name='+family['name']+'\ngtk-font-name=DejaVu Sans 10\n')
        if args.user_css:
            subprocess.run([sys.executable, '-I', str(ROOT/'tools/vapor-libadwaita'), 'enable',
                            '--config-home', str(scratch/'config'), '--profile', str(args.user_css.resolve()),
                            '--json'], capture_output=True, text=True, check=True)
        env.update({
            'XDG_CONFIG_DIRS': str(scratch / 'config'), 'XDG_DATA_DIRS': '/usr/share',
            'GDK_BACKEND': 'broadway', 'BROADWAY_DISPLAY': ':1', 'GSK_RENDERER': 'cairo',
            'GDK_DEBUG': 'no-portals', 'GDK_DISABLE': 'gl:vulkan:offload',
            'VK_LOADER_DRIVERS_DISABLE': '*', 'VK_LOADER_DRIVERS_SELECT': '',
            'VK_LOADER_DRIVERS_ENABLE': '', 'GTK_A11Y': 'none', 'GTK_MODULES': '',
            'GTK_IM_MODULE': 'gtk-im-context-simple', 'GSETTINGS_BACKEND': 'memory',
            'GTK_USE_PORTAL': '0', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/nonexistent',
            'GDK_SCALE': '1', 'GDK_DPI_SCALE': '1', 'LC_ALL': 'C.UTF-8'})
        for variable in ('GTK_THEME', 'GTK_PATH', 'GTK_DATA_PREFIX', 'DISPLAY', 'WAYLAND_DISPLAY',
                         'GTK_DEBUG', 'GSK_DEBUG', 'LD_PRELOAD', 'GTK_DEBUG_AUTO_QUIT',
                         'VK_LOADER_DEBUG', 'DBUS_STARTER_ADDRESS', 'DBUS_STARTER_BUS_TYPE'):
            env.pop(variable, None)
        bus_config = scratch / 'dbus.conf'
        bus_config.write_text(
            '<busconfig><type>session</type><listen>unix:tmpdir=' + str(scratch / 'runtime') +
            '</listen><policy context="default"><allow send_destination="*"/>'
            '<allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
        # No D-Bus service directories: no desktop/portal service activation.
        cases = [(page, 'normal', False) for page in PAGES]
        if not args.quick:
            cases += [(page, 'normal', True) for page in PAGES]
            cases += [(page, 'backdrop', False) for page in PAGES]
            cases += [('page1', 'rtl', False)]
        results = []
        for page, state, dark in cases:
            case = f'{page}-{state}-' + ('dark' if dark else 'normal')
            # Only the final application child loads the helper.
            launch = ['dbus-run-session', '--config-file=' + str(bus_config), '--', 'env',
                      f'LD_PRELOAD={library}', f'VAPOR_FACTORY_PAGE={page}',
                      f'VAPOR_FACTORY_STATE={state}', f'VAPOR_FACTORY_DARK={1 if dark else 0}',
                      'VAPOR_FACTORY_THEME='+family['name'],
                      'VAPOR_FACTORY_SELECTION_BG=#'+''.join(f'{v:02x}' for v in family['selection']),
                      'VAPOR_FACTORY_SELECTION_FG=#'+''.join(f'{v:02x}' for v in family['selection_foreground']),
                      f'VAPOR_FACTORY_OUTPUT={output}', binary]
            with private_display(scratch, env):
                returncode, stdout, stderr = run_application(launch, env, output, case)
            lines = [line for line in stderr.splitlines() if line.strip()]
            known_warnings = [line for line in lines if BROADWAY_WARNING.fullmatch(line)]
            unexpected = [line for line in lines if not BROADWAY_WARNING.fullmatch(line)]
            records = [line.removeprefix('VAPOR_FACTORY_RESULT ') for line in stdout.splitlines()
                       if line.startswith('VAPOR_FACTORY_RESULT ')]
            if returncode or len(records) != 1 or unexpected or (args.strict and known_warnings):
                raise RuntimeError(f'{case}: exit {returncode}\n{stdout}\n{stderr}')
            record = json.loads(records[0])
            assert (record['page'], record['state'], record['dark']) == (page, state, dark)
            assert record['theme_marker'] and record['mapped_widgets'] >= 20
            assert record['theme']==family['name']
            image_path = output / record['file']
            with Image.open(image_path) as image:
                image = image.convert('RGBA')
                assert image.size == (record['width'], record['height'])
                assert image.width >= 200 and image.height >= 200
                assert len(image.getcolors(image.width * image.height) or []) > 20, 'Blank page'
                assert image.getchannel('A').getextrema() == (255, 255), 'Missing content background'
                if family['classic']:
                    count=sum(n for n,pixel in image.getcolors(image.width*image.height) if pixel[:3]==family['window'])
                    assert count>image.width*image.height*.02,'GTK4-SURFACE: missing olive page background'
                record['pixel_sha256'] = hashlib.sha256(image.tobytes()).hexdigest()
            record['known_broadway_warnings'] = known_warnings
            results.append(record)
            print(f"Widget Factory {case}: {record['width']}x{record['height']}, "
                  f"{record['mapped_widgets']} mapped widgets, theme verified, "
                  f"{len(known_warnings)} known Broadway warning(s)", flush=True)
        assert len({record['pixel_sha256'] for record in results[:3]}) == 3, 'Pages look identical'
        report = {
            'application': binary,
            'family':args.family,'theme_name':family['name'],
            'binary_sha256': hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
            'theme_css_sha256': hashlib.sha256(source_css.read_bytes()).hexdigest(),
            'user_css_sha256': hashlib.sha256(args.user_css.read_bytes()).hexdigest() if args.user_css else None,
            'renderer': 'Cairo', 'display_scale': 1, 'strict': args.strict,
            'cases': results}
        (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    warnings = sum(len(record['known_broadway_warnings']) for record in results)
    print(f'Installed GTK Widget Factory checks: PASS ({len(results)} cases; '
          f'{warnings} known Broadway timing warnings retained)')
    if args.output:
        print('Retained evidence:', output)


if __name__ == '__main__':
    main()
