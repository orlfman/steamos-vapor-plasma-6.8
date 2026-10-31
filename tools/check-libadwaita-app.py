#!/usr/bin/env python3
"""Optional smoke test for a selected installed/built native libadwaita application.

No application is downloaded or installed. Use --application /path/to/program
--app-id org.example.App --output /tmp/evidence. No app actions/input are sent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--application',type=Path,required=True)
    parser.add_argument('--app-id',required=True)
    parser.add_argument('--family',choices=('vapor','vgui2'),default='vapor')
    parser.add_argument('--profile',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--idle-seconds',type=int,default=0,choices=range(0,6),help='measure process CPU during a short idle interval')
    args=parser.parse_args()
    family=runpy.run_path(str(ROOT/'tools/libadwaita-families.py'))['get_family'](args.family)
    args.profile=args.profile or family['profile']
    if not args.application.is_file():parser.error('Application does not exist')
    from PIL import Image
    native=runpy.run_path(str(ROOT/'tools/check-libadwaita.py'))
    helpers=runpy.run_path(str(ROOT/'tools/check-widget-factory.py'))
    client=runpy.run_path(str(ROOT/'tools/broadway-test-client.py'))['FrameClient']
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').unlink(missing_ok=True)
    results=[]
    with tempfile.TemporaryDirectory(prefix='vapor-adw-app-') as folder:
        scratch=Path(folder);library=scratch/'probe.so'
        flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','libadwaita-1'],text=True))
        subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(ROOT/'tools/libadwaita-app-probe.c'),'-o',str(library),*flags,'-ldl','-lm'],check=True)
        for baseline in (True,False):
            case='baseline' if baseline else args.family;directory=scratch/case;directory.mkdir()
            options=argparse.Namespace(profile=args.profile,family=args.family,scale=1,hc=False)
            env,bus=native['make_environment'](directory,options,not baseline)
            command=['dbus-run-session','--config-file='+str(bus),'--','env',f'LD_PRELOAD={library}',
                     'VAPOR_APP_ID='+args.app_id,'VAPOR_APP_BASELINE='+('1' if baseline else '0'),
                     'VAPOR_APP_IDLE_SECONDS='+str(args.idle_seconds),
                     'VAPOR_APP_ACCENT=#'+family['colors']['accent-bg-color'],
                     'VAPOR_APP_FOREGROUND=#'+family['colors']['accent-fg-color'],
                     'VAPOR_APP_BACKGROUND=#'+family['colors']['window-bg-color'],
                     'VAPOR_APP_IMAGE='+str(output/(case+'.png')),str(args.application.resolve())]
            with helpers['private_display'](directory,env,output/(case+'-display')),client(directory/'http.socket'):
                code,stdout,stderr=helpers['run_application'](command,env,output,case)
            lines=[line for line in stderr.splitlines() if line.strip()]
            known=[line for line in lines if native['BROADWAY_WARNING'].fullmatch(line)]
            unexpected=[line for line in lines if not native['BROADWAY_WARNING'].fullmatch(line)]
            records=[line.removeprefix('VAPOR_ADW_APP ') for line in stdout.splitlines() if line.startswith('VAPOR_ADW_APP ')]
            if code or unexpected or len(records)!=1:raise RuntimeError(f'{case}: {code}\n{stdout}\n{stderr}')
            data=json.loads(records[0]);data['known_broadway_warnings']=known
            idle=[line.removeprefix('VAPOR_ADW_IDLE ') for line in stdout.splitlines() if line.startswith('VAPOR_ADW_IDLE ')]
            if args.idle_seconds:
                assert len(idle)==1,'Missing idle measurement'
                data['idle']=json.loads(idle[0])
            with Image.open(output/(case+'.png')) as image:
                assert image.size==(data['width'],data['height']) and len(image.getcolors(image.width*image.height) or [])>20
            results.append(data);print(f'{args.app_id}: {case} PASS',flush=True)
    report={'family':args.family,'application':str(args.application.resolve()),'application_id':args.app_id,
            'binary_sha256':hashlib.sha256(args.application.read_bytes()).hexdigest(),
            'profile_sha256':hashlib.sha256(args.profile.read_bytes()).hexdigest(),'cases':results,
            'limits':'startup rendering only; no menu, keyboard or application-action coverage'}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
