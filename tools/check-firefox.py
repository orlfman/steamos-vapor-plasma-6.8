#!/usr/bin/env python3
"""Check the Vapor Firefox theme in disposable normal/private browser windows."""
import argparse
import base64
import configparser
from contextlib import contextmanager
import gc
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import zipfile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'firefox/vapor/manifest.json'
HOME_BASELINE = None

PROBE = r'''
const root = document.documentElement;
function sample(selector) {
  const e = document.querySelector(selector);
  if (!e) return null;
  const s = getComputedStyle(e), r = e.getBoundingClientRect();
  return {background:s.backgroundColor, image:s.backgroundImage, color:s.color,
    fill:s.fill, border:s.borderColor, outline:s.outlineColor,
    borderWidth:s.borderTopWidth,outlineWidth:s.outlineWidth,outlineStyle:s.outlineStyle,
    radius:s.borderTopLeftRadius,
    rect:{x:r.x,y:r.y,width:r.width,height:r.height}};
}
return {
  theme:root.getAttribute('theme-effective-id'), themed:root.hasAttribute('lwtheme'),
  vapor:getComputedStyle(root).getPropertyValue('--vapor-window').trim(),
  private:ChromeUtils.importESModule('resource://gre/modules/PrivateBrowsingUtils.sys.mjs')
    .PrivateBrowsingUtils.isWindowPrivate(window),
  privateMode:root.getAttribute('privatebrowsingmode'),
  privateIndicator:['.private-browsing-indicator-button',
    '.private-browsing-indicator-with-label'].map(sample)
    .find(e=>e && e.rect.width>0 && e.rect.height>0) || null,
  forced:matchMedia('(forced-colors: active)').matches, active:document.hasFocus(),
  darkSystem:matchMedia('(-moz-system-dark-theme)').matches,
  width:innerWidth,height:innerHeight,dpr:devicePixelRatio,
  navbar:sample('#nav-bar'), field:sample('.urlbar-background'),
  input:sample('#urlbar-input'),
  tab:sample('.tabbrowser-tab[selected] .tab-background'),
  label:sample('.tabbrowser-tab[selected] .tab-label'),
  close:sample('.tabbrowser-tab[selected] .tab-close-button'),
  menu:sample('#PanelUI-menu-button'),
  menuIcon:sample('#PanelUI-menu-button > .toolbarbutton-badge-stack, #PanelUI-menu-button > .toolbarbutton-icon'),
  selection:(() => { const s=getComputedStyle(window.gURLBar.inputField,'::selection');
    return {background:s.backgroundColor,color:s.color}; })()
};
'''


def rgb(value):
    if value.startswith('#'):
        return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))
    match = re.fullmatch(r'rgba?\(([^)]+)\)', value)
    if not match:
        raise ValueError(f'Unsupported computed color: {value}')
    values = [float(v.strip()) for v in match[1].split(',')]
    if len(values) == 4 and values[3] != 1:
        raise ValueError(f'Expected opaque color: {value}')
    return tuple(round(v) for v in values[:3])


def contrast(first, second):
    def lum(c):
        channels = [v / 255 for v in c]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
    low, high = sorted((lum(first), lum(second)))
    return (high + .05) / (low + .05)


def expected_palette():
    scheme = configparser.ConfigParser()
    scheme.read(ROOT / 'usr/share/color-schemes/Vapor.colors')
    def color(section, name):
        return tuple(int(v) for v in scheme[section][name].split(','))
    return {'window': color('Colors:Window', 'BackgroundNormal'),
            'view': color('Colors:View', 'BackgroundNormal'),
            'text': color('Colors:View', 'ForegroundNormal'),
            'selected': color('Colors:Selection', 'BackgroundNormal'),
            'selected_text': color('Colors:Selection', 'ForegroundNormal')}


def wait_for(predicate, description, timeout=8):
    limit = time.monotonic() + timeout
    while time.monotonic() < limit:
        result = predicate()
        if result:
            return result
        time.sleep(.05)
    raise AssertionError(f'Timed out: {description}')


def capture(m, target):
    # Firefox paints a red automation-only overlay in the address bar. Remove
    # only that attribute in test-owned windows, equally for stock and themes.
    m.execute_script("document.documentElement.removeAttribute('remotecontrol');")
    m.execute_async_script('''
      const done=arguments[arguments.length-1];
      requestAnimationFrame(async()=>{
        const finite=document.getAnimations({subtree:true}).filter(a=>
          a.effect && a.effect.getComputedTiming().iterations !== Infinity);
        await Promise.all(finite.map(a=>a.finished.catch(()=>null)));
        requestAnimationFrame(()=>requestAnimationFrame(()=>done(true)));
      });
    ''')
    result = m.execute_script(PROBE)
    target.write_bytes(base64.b64decode(m.screenshot()))
    from PIL import Image
    image = Image.open(target).convert('RGB')
    sx, sy = image.width / result['width'], image.height / result['height']
    def pixel(x, y):
        return tuple(image.getpixel((round(x*sx), round(y*sy))))
    tab = result['tab']['rect']; nav = result['navbar']['rect']
    result['pixels'] = {'tab': pixel(tab['x']+40, tab['y']+4),
                        'strip': pixel(tab['x']+tab['width']+80, tab['y']+4),
                        # Use the clear left gutter, away from the address
                        # field's native drop shadow in the classic layout.
                        'navbar': pixel(nav['x']+3, nav['y']+4)}
    result['screenshot'] = target.name
    return result


def check_window(sample, expected, addon_id, private):
    errors = []
    def check(condition, name):
        if not condition:
            errors.append(name)
    if addon_id is not None:
        check(sample['theme'] == addon_id and sample['themed'], 'theme-loaded')
    else:
        check(sample['vapor'] == '#24272c', 'default-appearance-loaded')
        check(sample['tab']['radius'] == '3px', 'breeze-tab-shape')
        check(sample['field']['radius'] == '3px', 'breeze-field-shape')
        check(sample['menuIcon']['radius'] == '3px', 'breeze-button-shape')
    check(sample['private'] == private, 'private-state')
    if private:
        indicator = sample['privateIndicator']
        check(sample['privateMode'] == 'temporary', 'private-mode-retained')
        check(indicator and indicator['rect']['width'] > 0 and indicator['rect']['height'] > 0,
              'private-indicator-visible')
    check(rgb(sample['navbar']['background']) == expected['window'], 'toolbar-background')
    check(rgb(sample['tab']['background']) == expected['selected'], 'selected-tab-background')
    check(rgb(sample['label']['color']) == expected['selected_text'], 'selected-tab-text')
    check(rgb(sample['close']['fill']) == expected['selected_text'], 'selected-tab-close-icon')
    check(sample['pixels']['tab'] == expected['selected'], 'painted-selected-tab')
    check(sample['pixels']['strip'] == expected['window'], 'painted-tab-strip')
    check(sample['pixels']['navbar'] == expected['window'], 'painted-toolbar')
    check(rgb(sample['input']['color']) == expected['text'], 'address-text')
    check(sample['field'] and rgb(sample['field']['background']) == expected['view'], 'address-background')
    check(sample['field'] and sample['field']['image'] == 'none', 'automation-overlay-absent')
    pairs = {'selected_text': contrast(rgb(sample['label']['color']), sample['pixels']['tab']),
             'selected_close': contrast(rgb(sample['close']['fill']), sample['pixels']['tab']),
             'toolbar_text': contrast(rgb(sample['navbar']['color']), sample['pixels']['navbar']),
             'address_text': contrast(rgb(sample['input']['color']), rgb(sample['field']['background']))}
    for name, value in pairs.items():
        check(value >= 4.5, f'contrast:{name}')
    return errors, pairs



def setup_profile(profile, action):
    completed = subprocess.run([os.sys.executable, '-I', str(ROOT/'tools/vapor-firefox'),
                                action, '--profile', str(profile)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


@contextmanager
def launched(profile, out, port):
    from marionette_driver.marionette import Marionette
    with (out/'firefox.log').open('ab') as log:
        environment = dict(os.environ, MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1')
        process = subprocess.Popen([ARGS.firefox, '--headless', '--no-remote',
            '--profile', str(profile), '--marionette', '--remote-allow-system-access'],
            stdout=log, stderr=log, env=environment)
        m = Marionette(host='127.0.0.1', port=port, socket_timeout=30)
        try:
            def listening():
                if process.poll() is not None:
                    raise AssertionError(f'Test Firefox exited: {out}/firefox.log')
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1):
                        return True
                except OSError:
                    return False
            wait_for(listening, 'test-owned Firefox startup', timeout=40)
            m.start_session(); m.set_context('chrome')
            yield m
        finally:
            try:
                if m.session:
                    m._request_in_app_shutdown()
            finally:
                m.cleanup(); del m; gc.collect()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()


def browser_case(out, nova, dark, scale, negatives=False):
    global HOME_BASELINE
    out.mkdir()
    profile = out/'profile'; profile.mkdir()
    (profile/'prefs.js').write_text('// Disposable browser test profile\n')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    prefs = {'marionette.port':port, 'browser.shell.checkDefaultBrowser':False,
             'browser.startup.page':0, 'browser.startup.homepage':'about:blank',
             'browser.aboutwelcome.enabled':False, 'browser.startup.firstrunSkipsHomepage':True,
             'browser.nova.enabled':nova, 'ui.systemUsesDarkTheme':int(dark),
             'layout.css.devPixelsPerPx':str(scale),
             'browser.search.suggest.enabled':False, 'browser.urlbar.suggest.searches':False,
             'browser.urlbar.speculativeConnect.enabled':False, 'network.prefetch-next':False,
             'app.update.auto':False, 'extensions.update.enabled':False,
             'datareporting.healthreport.uploadEnabled':False,
             'datareporting.policy.dataSubmissionEnabled':False}
    original_userjs=''.join(f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k,v in prefs.items()).encode()
    (profile/'user.js').write_bytes(original_userjs)
    result={'nova':nova,'system_dark':dark,'scale':scale,'windows':{},'negative_controls':[]}
    try:
        if negatives:
            with launched(profile,out,port) as m:
                result['baseline']=capture(m,out/'baseline.png')
                m.set_context('content');m.navigate('about:newtab')
                try:
                    wait_for(lambda:m.execute_script('return !!document.querySelector(".outer-wrapper");'),'stock Firefox Home interface')
                    HOME_BASELINE={'status':'rendered'}
                except AssertionError:
                    snapshot=m.execute_script('return {url:location.href,root:document.querySelector("#root")?.innerHTML,ready:document.readyState};')
                    assert snapshot['url']=='about:newtab' and snapshot['root']=='' and snapshot['ready']=='complete'
                    HOME_BASELINE={'status':'BLOCKED_BASELINE','detail':'Stock Firefox Home React root remains empty without any custom stylesheet enabled.','snapshot':snapshot}
                result['stock_firefox_home']=HOME_BASELINE
        result['setup']=setup_profile(profile,'install')
        with launched(profile,out,port) as m:
            result['browser_version']=m.session_capabilities['browserVersion']
            normal=m.current_chrome_window_handle
            handles=[('normal',normal,False)]
            for name in ('private-first','private-new'):
                old=set(m.chrome_window_handles);m.open(type='window',private=True,focus=True)
                handles.append((name,(set(m.chrome_window_handles)-old).pop(),True))
            for label,handle,is_private in handles:
                m.switch_to_window(handle,focus=True)
                wait_for(lambda:m.execute_script("return getComputedStyle(document.documentElement).getPropertyValue('--vapor-window').trim()")=='#24272c',label)
                sample=capture(m,out/f'{label}.png');result['windows'][label]=sample
                errors,ratios=check_window(sample,EXPECTED,None,is_private)
                sample['contrast']=ratios
                assert not errors,f'{label}: {errors}'
                assert sample['darkSystem']==dark and sample['dpr']==scale
                m.execute_script('window.gURLBar.focus(); window.gURLBar.inputField.select();')
                focused=capture(m,out/f'{label}-focused.png')
                result['windows'][label]['focused']=focused
                errors,_=check_window(focused,EXPECTED,None,is_private)
                assert not errors,f'{label} focused: {errors}'
                assert rgb(focused['selection']['background'])==EXPECTED['selected']
                assert rgb(focused['selection']['color'])==EXPECTED['selected_text']
                field=focused['field']
                border_visible=rgb(field['border'])==EXPECTED['selected'] and float(field['borderWidth'].removesuffix('px'))>0
                outline_visible=rgb(field['outline'])==EXPECTED['selected'] and field['outlineStyle']!='none' and float(field['outlineWidth'].removesuffix('px'))>0
                assert border_visible or outline_visible,'Address field focus indicator is missing'
                focused['focus_contrast']=min(contrast(EXPECTED['selected'],EXPECTED['view']),contrast(EXPECTED['selected'],EXPECTED['window']))
                assert focused['focus_contrast']>=3
                controls={}
                try:
                    for name,pseudo,background in [('hover',':hover',(45,49,54)),('pressed',':active',EXPECTED['view'])]:
                        m.execute_script('InspectorUtils.addPseudoClassLock(document.getElementById("PanelUI-menu-button"),arguments[0]);',script_args=[pseudo])
                        control=capture(m,out/f'{label}-button-{name}.png')
                        assert rgb(control['menuIcon']['background'])==background,f'{label}: {name} button fill'
                        assert control['menuIcon']['radius']=='3px'
                        assert control['menu']['rect']['width']==sample['menu']['rect']['width']
                        assert control['menu']['rect']['height']==sample['menu']['rect']['height']
                        assert contrast(rgb(control['menuIcon']['fill']),background)>=4.5
                        controls[name]=control['menuIcon']
                finally:
                    m.execute_script('for(const pseudo of [":hover",":active"]) InspectorUtils.removePseudoClassLock(document.getElementById("PanelUI-menu-button"),pseudo);')
                result['windows'][label]['button_states']=controls
                m.set_context('content');m.navigate('about:privatebrowsing' if is_private else 'about:newtab')
                if not is_private:
                    if HOME_BASELINE['status']=='rendered':
                        wait_for(lambda:m.execute_script('return !!document.querySelector(".outer-wrapper");'),'Firefox Home interface')
                content=m.execute_script('return {url:location.href,background:getComputedStyle(document.documentElement).backgroundColor,image:getComputedStyle(document.documentElement).backgroundImage,body:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color,dark:matchMedia("(prefers-color-scheme:dark)").matches};')
                result['windows'][label]['start_page']=content
                if not is_private:
                    content['widget_coverage']=HOME_BASELINE['status']
                assert rgb(content['body'])==EXPECTED['view'],f'{label}: start page not Vapor'
                assert contrast(rgb(content['text']),rgb(content['body']))>=4.5
                if is_private:
                    search=m.execute_script('const host=document.querySelector("content-search-handoff-ui"),e=host?.shadowRoot?.querySelector(".search-handoff-button")||document.querySelector(".search-handoff-button"),s=getComputedStyle(e); return {background:s.backgroundColor,text:s.color,radius:s.borderTopLeftRadius,width:e.getBoundingClientRect().width};')
                    assert search['width']>0 and search['radius']=='3px'
                    assert rgb(search['background'])==EXPECTED['window'],'Private search field retained the Firefox purple background'
                    assert contrast(rgb(search['text']),rgb(search['background']))>=4.5
                    content['search_field']=search
                m.set_context('chrome');capture(m,out/f'{label}-start-page.png')
            # Test only our explicit browser-page scope, without changing websites.
            m.switch_to_window(normal,focus=True);m.set_context('content')
            m.navigate('data:text/html,<title>Vapor local fixture</title><p>Ordinary website fixture</p>')
            website=m.execute_script('return {dark:matchMedia("(prefers-color-scheme:dark)").matches,accent:getComputedStyle(document.documentElement).getPropertyValue("--in-content-accent-color").trim()};')
            assert website['dark']==dark and not website['accent'], 'Browser styles leaked into a website'
            result['ordinary_website']=website;m.set_context('chrome')
            # An actual open browser must be refused by the profile setup tool.
            locked=subprocess.run([os.sys.executable,'-I',str(ROOT/'tools/vapor-firefox'),'install','--profile',str(profile)],capture_output=True,text=True)
            assert locked.returncode!=0 and 'Close all Firefox' in locked.stderr
            result['live_profile_refusal']='PASS'
            if negatives:
                private=handles[1][1]
                controls=[
                    ('wrong-toolbar',':root #nav-bar {background-color:#203356 !important}',normal,'toolbar-background'),
                    ('wrong-selected-text',':root .tabbrowser-tab[selected] .tab-label {color:#eff0f1 !important}',normal,'contrast:selected_text'),
                    ('purple-private-window',':root[privatebrowsingmode] #TabsToolbar {background-color:#25003e !important}',private,'painted-tab-strip'),
                    ('rounded-private-tab',':root[privatebrowsingmode] .tabbrowser-tab[selected] .tab-background {border-radius:99px !important}',private,'breeze-tab-shape')]
                for name,css,target,expected_error in controls:
                    m.switch_to_window(target,focus=True)
                    uri='data:text/css,'+quote(css)
                    m.execute_script('window.windowUtils.loadSheetUsingURIString(arguments[0],window.windowUtils.USER_SHEET);',script_args=[uri])
                    try:
                        sample=capture(m,out/f'{name}.png')
                        errors,_=check_window(sample,EXPECTED,None,target==private)
                        assert expected_error in errors,f'{name}: not detected: {errors}'
                        result['negative_controls'].append({'name':name,'detected':expected_error,'errors':errors})
                    finally:
                        m.execute_script('window.windowUtils.removeSheetUsingURIString(arguments[0],window.windowUtils.USER_SHEET);',script_args=[uri])
            result['css_diagnostics']=m.execute_script('return Services.console.getMessageArray().filter(e=>e.sourceName && e.sourceName.includes("/vapor-firefox/")).map(e=>({source:e.sourceName,message:e.errorMessage||e.message}));')
            assert not result['css_diagnostics'],result['css_diagnostics']
        result['remove']=setup_profile(profile,'remove')
        assert (profile/'user.js').read_bytes()==original_userjs,'Existing setup preferences changed'
        if negatives:
            with launched(profile,out,port) as m:
                restored=capture(m,out/'restored.png')
                assert not restored['vapor'],'Default appearance did not remove after restart'
                assert restored['tab']['radius']!='3px','Breeze styles persisted after removal'
                result['recovery']=restored
        result['status']='PASS'
        return result
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


def main():
    global ARGS, EXPECTED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--firefox', default='/usr/lib/firefox/firefox')
    parser.add_argument('--web-ext', default=shutil.which('web-ext'))
    parser.add_argument('--quick', action='store_true', help='Run only Nova/light/scale-1; report limited coverage')
    ARGS = parser.parse_args()
    if not ARGS.web_ext:
        parser.error('Mozilla web-ext is required; see firefox/README.md for maintainer setup')
    try:
        import marionette_driver
        from PIL import Image
    except ImportError:
        parser.error('Browser-test dependencies are missing; see firefox/README.md')
    out = ARGS.output or Path(tempfile.mkdtemp(prefix='vapor-firefox-check-'))
    if out.is_symlink() or (out.exists() and any(out.iterdir())):
        parser.error('--output must be a new or empty directory')
    out.mkdir(parents=True, exist_ok=True)
    EXPECTED = expected_palette()
    manifest = json.loads(MANIFEST.read_text())
    assert manifest['theme'] == manifest['dark_theme'], 'Private/dark palette must match Vapor'
    lint = subprocess.run([ARGS.web_ext, 'lint', '--source-dir', str(MANIFEST.parent),
                           '--warnings-as-errors', '--output', 'json'], capture_output=True, text=True)
    (out/'mozilla-lint.json').write_text(lint.stdout)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    artifacts = []
    for n in ('build-a','build-b'):
        built = subprocess.check_output([os.sys.executable,'-I',str(ROOT/'tools/build-firefox-themes.py'),'--output',str(out/n)],text=True)
        artifacts.append(json.loads(built))
    assert artifacts[0]['sha256'] == artifacts[1]['sha256'], 'Build is not reproducible'
    assert artifacts[0]['bundle_sha256'] == artifacts[1]['bundle_sha256'], 'Default bundle is not reproducible'
    setup_checks = subprocess.run([os.sys.executable,'-I',str(ROOT/'tools/test-firefox-setup.py')],capture_output=True,text=True)
    (out/'setup-tests.log').write_text(setup_checks.stdout+setup_checks.stderr)
    assert setup_checks.returncode==0, setup_checks.stdout+setup_checks.stderr
    os.environ['MOZ_AUTOMATION'] = '1'
    cases = [(True,False,1)] if ARGS.quick else list(itertools.product((True,False),(False,True),(1,2)))
    report = {'theme':'Vapor','id':manifest['browser_specific_settings']['gecko']['id'],
              'manifest_sha256':hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
              'artifact':artifacts[0], 'mozilla_lint':json.loads(lint.stdout),
              'disposable_profiles':True,'default_setup':'Vapor colors and Breeze-inspired UI',
              'color_component_signed':False,'quick':ARGS.quick,'setup_tests':'PASS','cases':[]}
    try:
        for index,(nova,dark,scale) in enumerate(cases):
            name=f'{"nova" if nova else "classic"}-{ "dark" if dark else "light"}-scale-{scale}'
            case=browser_case(out/name,nova,dark,scale,negatives=index==0)
            report['cases'].append(case)
            print(f'PASS {name}: normal, first/new private, Breeze shapes, start pages and focus',flush=True)
        report['firefox_home']=HOME_BASELINE
        report['status']='PASS_WITH_LIMITATIONS' if HOME_BASELINE['status']=='BLOCKED_BASELINE' else 'PASS'
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Firefox verification: {out}/report.json')


if __name__ == '__main__':
    main()
