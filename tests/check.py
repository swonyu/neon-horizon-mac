#!/usr/bin/env python3
"""Small standard-library checks; no personal preferences or login services changed."""
import base64
from contextlib import contextmanager, ExitStack, redirect_stdout
import io
from collections import Counter
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import urlopen, Request
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

m = module('makeover', ROOT / 'makeover.py')
host = module('wallpaper_host', ROOT / 'wallpaper/host.py')


def check_preference_edit_during_publication():
    with tempfile.TemporaryDirectory(prefix='neon-publication-edit-') as temporary:
        directory = Path(temporary)
        values, writes = {'size': 72}, []
        change = {'domain': 'com.apple.dock', 'key': 'size', 'before': 72, 'after': 48, 'label': 'Size'}
        original_save = m.save
        def edited_during_save(path, record):
            original_save(path, record)
            values['size'] = 90
        def writer(domain, key, value):
            writes.append((domain, key, value))
            values[key] = value
        with patch.object(m, 'save', side_effect=edited_during_save):
            try:
                m.apply([change], directory, lambda _: dict(values), writer)
            except RuntimeError as error:
                assert 'changed' in str(error)
            else:
                raise AssertionError('Edit made during journal publication was overwritten')
        assert values == {'size': 90} and not writes
        records = list(directory.glob('*.json'))
        assert len(records) == 1 and json.loads(records[0].read_text())['changes'] == [change]


def check_screenshot_directory_repair():
    with tempfile.TemporaryDirectory(prefix='neon-screenshot-repair-') as temporary:
        directory = Path(temporary)
        destination = directory / 'Screenshots'
        setting = {'domain': 'com.apple.screencapture', 'key': 'location',
                   'after': str(destination), 'label': 'Screenshots'}
        values, writes = {'location': str(destination), 'size': 72}, []
        reader = lambda _: dict(values)
        def writer(domain, key, value):
            writes.append((domain, key, value))
            values[key] = value
        actual_plan, actual_apply = m.plan, m.apply
        with ExitStack() as stack:
            stack.enter_context(patch.object(m, 'STATE', directory / 'state'))
            stack.enter_context(patch.object(m.sys, 'platform', 'darwin'))
            stack.enter_context(patch.object(m.os, 'geteuid', return_value=501))
            stack.enter_context(patch.object(m.subprocess, 'check_output', return_value='27.0'))
            selected = stack.enter_context(patch.object(m, 'load_settings', return_value=[setting]))
            stack.enter_context(patch.object(m, 'plan', side_effect=lambda s: actual_plan(s, reader)))
            stack.enter_context(patch.object(m, 'apply', side_effect=lambda c, d: actual_apply(c, d, reader, writer)))
            stack.enter_context(redirect_stdout(io.StringIO()))
            for arguments, answer in [(['plan'], None), (['apply', '--confirm'], 'no'),
                                      (['apply', '--confirm'], EOFError)]:
                with patch.object(m.sys, 'argv', ['makeover.py', *arguments]), patch('builtins.input', return_value=answer, side_effect=answer if answer is EOFError else None):
                    m.main()
                assert not destination.exists() and not writes
            selected.return_value = []
            with patch.object(m.sys, 'argv', ['makeover.py', 'apply', '--groups', 'appearance']):
                m.main()
            assert not destination.exists() and not writes
            selected.return_value = [setting]
            with patch.object(m.sys, 'argv', ['makeover.py', 'apply']):
                m.main()
            assert destination.is_dir(), 'Already-matching screenshot destination was not repaired'
            assert not writes, 'Directory repair unnecessarily rewrote a preference'
            destination.rmdir()
            destination.write_text('Existing user file')
            selected.return_value = [setting, {'domain': 'com.apple.dock', 'key': 'size', 'after': 48, 'label': 'Size'}]
            with patch.object(m.sys, 'argv', ['makeover.py', 'apply']):
                try:
                    m.main()
                except OSError:
                    pass
                else:
                    raise AssertionError('Unusable screenshot destination was accepted')
            assert not writes and destination.read_text() == 'Existing user file'


check_preference_edit_during_publication()
check_screenshot_directory_repair()
print('PASS: late preference edits and repeat screenshot-directory repair')

# Simulate partial writes, concurrent invocations, later user edits and repeated undo.
with tempfile.TemporaryDirectory(prefix='neon-check-') as temporary:
    directory = Path(temporary)
    values = {'unchanged': True, 'old': 'original', 'later': 3}
    reader = lambda domain: dict(values)
    def writer(domain, key, value):
        if value is None:
            values.pop(key, None)
        else:
            values[key] = value
    settings = [{'domain': 'test', 'key': k, 'after': v, 'label': k}
                for k, v in [('unchanged', True), ('old', 'new'), ('later', 4), ('absent', False)]]
    changes = m.plan(settings, reader)
    assert len(changes) == 3
    with m.locked(directory):
        try:
            with m.locked(directory):
                raise AssertionError('second process acquired the lock')
        except BlockingIOError:
            pass
        backup = m.apply(changes, directory, reader, writer)
    assert os.stat(backup).st_mode & 0o777 == 0o600
    assert not m.plan(settings, reader)
    assert m.apply([], directory, reader, writer) is None
    record = json.loads(backup.read_text())
    values['later'] = 999
    assert m.undo(record, reader, writer) == ['later']
    assert values == {'unchanged': True, 'old': 'original', 'later': 999}
    assert m.undo(record, reader, writer) == ['later']
    assert values['later'] == 999
    def fail_after_write(domain, key, value):
        writer(domain, key, value)
        raise RuntimeError('simulated failure after system write')
    try:
        m.apply(m.plan(settings[:2], reader), directory, reader, fail_after_write)
        raise AssertionError('failure was swallowed')
    except RuntimeError:
        pass
    partial = max(directory.glob('*.json'), key=lambda p: p.stat().st_mtime_ns)
    assert not m.undo(json.loads(partial.read_text()), reader, writer)
    assert values['old'] == 'original'
    stale = m.plan(settings[:2], reader)
    values['old'] = 'edited after preview'
    try:
        m.apply(stale, directory, reader, writer)
        raise AssertionError('stale plan overwrote later edit')
    except RuntimeError:
        pass
    assert values['old'] == 'edited after preview'
print('PASS: journal, absent keys, idempotence, edit conflicts, partial failure and locking')

all_settings = m.load_settings(['all'])
assert len(all_settings) == 39
assert len({(s['domain'],s['key']) for s in all_settings}) == 39
assert not any(s['key'] in ('KeyRepeat', 'InitialKeyRepeat', 'persistent-apps') for s in all_settings)
for bad in [{'format': 0}, {'format': 1, 'changes': [{'domain': 'unknown', 'key': 'bad', 'after': True, 'before': None}]}]:
    try:
        m.validate_record(bad)
        raise AssertionError('invalid backup accepted')
    except (ValueError, KeyError):
        pass
m.validate_record({'format':1, 'changes':[{'domain':'com.apple.dock', 'key':'oldPresetKey', 'after':True, 'before':None}]})
assert not m.scalar(float('nan')) and not m.scalar(float('inf'))
for value in (2**63, -(2**63)-1, 'bad\0text', 1e308, 1e-308, 0.12345678901234568):
    assert not m.scalar(value)
try:
    m.plan([{'domain':'com.apple.dock','key':'size','after':48,'label':'Size'}], lambda _: {'size':0.1})
    raise AssertionError('Preview accepted an original float that undo would round')
except ValueError:
    pass
for bad in ({'format':True, 'changes':[]}, {'format':1, 'changes':[{}]},
            {'format':1, 'changes':[{'domain':[], 'key':'size', 'before':None, 'after':True}]}):
    try:
        m.validate_record(bad)
        raise AssertionError('Malformed backup accepted')
    except ValueError:
        pass

# Exercise command boundaries, not just their lower-level helpers.
with tempfile.TemporaryDirectory(prefix='neon-command-check-') as temporary:
    directory = Path(temporary)
    values = {'size':72}
    reader = lambda domain: dict(values)
    def writer(domain, key, value):
        if value is None:
            values.pop(key, None)
        else:
            values[key] = value
    settings = [{'domain':'com.apple.dock', 'key':'size', 'after':48, 'label':'Size'}]
    actual_plan, actual_apply, actual_undo = m.plan, m.apply, m.undo
    @contextmanager
    def intervening_edit(_):
        values['size'] = 90
        yield
    with ExitStack() as stack:
        stack.enter_context(patch.object(m, 'STATE', directory))
        stack.enter_context(patch.object(m.sys, 'platform', 'darwin'))
        stack.enter_context(patch.object(m.os, 'geteuid', return_value=501))
        stack.enter_context(patch.object(m.subprocess, 'check_output', return_value='27.0'))
        stack.enter_context(patch.object(m, 'load_settings', return_value=settings))
        stack.enter_context(patch.object(m, 'plan', side_effect=lambda s: actual_plan(s, reader)))
        stack.enter_context(patch.object(m, 'apply', side_effect=lambda c,d: actual_apply(c,d,reader,writer)))
        stack.enter_context(patch.object(m, 'undo', side_effect=lambda r: actual_undo(r,reader,writer)))
        stack.enter_context(redirect_stdout(io.StringIO()))
        with patch.object(m.sys, 'argv', ['makeover.py','apply']), patch.object(m, 'locked', intervening_edit):
            try:
                m.main()
                raise AssertionError('Command replaced its displayed preview')
            except RuntimeError:
                pass
        assert values == {'size':90}
        journal = directory/'journal.json'
        changes = [dict(settings[0], before=72),
                   {'domain':'com.apple.dock', 'key':'other', 'before':None, 'after':True}]
        journal.write_text(json.dumps({'format':1, 'changes':changes[:1]}))
        values.update(size=48, other=True)
        @contextmanager
        def completed_apply(_):
            journal.write_text(json.dumps({'format':1, 'changes':changes}))
            yield
        with patch.object(m.sys, 'argv', ['makeover.py','undo','--backup',str(journal)]), patch.object(m, 'locked', completed_apply):
            m.main()
        assert values == {'size':72}, 'Undo missed the last journal entry'
        with patch.object(m.sys, 'argv', ['makeover.py','apply','--confirm']), patch('builtins.input', return_value='no'):
            m.main()
        with patch.object(m.sys, 'argv', ['makeover.py','apply','--confirm']), patch('builtins.input', side_effect=EOFError):
            m.main()
        assert values == {'size':72}, 'Declined preview changed preferences'

    events = []
    sync = os.fsync
    def synchronized(fd):
        events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file')
        sync(fd)
    def durable_writer(domain, key, value):
        assert events[-2:] == ['file', 'directory']
        writer(domain, key, value)
    with patch.object(m.os, 'fsync', side_effect=synchronized):
        actual_apply(actual_plan(settings, reader), directory, reader, durable_writer)
    values['size'] = 72
    def failed_publication(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError('simulated directory synchronization failure')
        sync(fd)
    with patch.object(m.os, 'fsync', side_effect=failed_publication):
        try:
            actual_apply(actual_plan(settings, reader), directory, reader, writer)
            raise AssertionError('Failed journal publication permitted a preference write')
        except OSError:
            pass
    assert values == {'size':72}
    with patch.object(m, 'ROOT', directory):
        for bad in ([], {'dock':None}, {'dock':[['unapproved.domain','size',48,'Size']]},
                    {'dock':[['com.apple.dock','size',48,'Size']]*2},
                    {'dock':[['com.apple.dock','size',0.1,'Size']]}):
            (directory/'preset.json').write_text(json.dumps(bad))
            try:
                m.load_settings(['all'])
                raise AssertionError('Malformed preset accepted')
            except ValueError:
                pass
    for path in directory.glob('*.json'):
        path.unlink()
    older, newer = directory/'z.json', directory/'a.json'
    older.write_text('{}'); newer.write_text('{}')
    os.utime(older, ns=(1_000_000_000,1_000_000_000))
    os.utime(newer, ns=(2_000_000_000,2_000_000_000))
    output = io.StringIO()
    with patch.object(m, 'STATE', directory), patch.object(m.sys, 'platform', 'darwin'), patch.object(m.os, 'geteuid', return_value=501), patch.object(m.sys, 'argv', ['makeover.py','backups']), redirect_stdout(output):
        m.main()
    assert output.getvalue().splitlines() == [str(newer), str(older)]
print('PASS: command preview/undo races, confirmation, journal publication, input validation and backup ordering')

if Path('/bin/zsh').exists():
    with tempfile.TemporaryDirectory(prefix='neon-launcher-check-') as temporary:
        directory = Path(temporary)
        log = directory/'opened'
        (directory/'open').write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$NEON_TEST_OPEN_LOG"\n')
        (directory/'open').chmod(0o755)
        env = dict(os.environ, PATH=str(directory), NEON_TEST_OPEN_LOG=str(log))
        for choice, expected in [('4', ['wallpaper/sakura-park.png']), ('5', ['-t','docs/SETUP.md'])]:
            result = subprocess.run(['/bin/zsh',str(ROOT/'Start.command')], input=choice+'\n\n', text=True, capture_output=True, env=env)
            assert result.returncode == 0 and log.read_text().splitlines() == expected
        (directory/'python3').write_text('#!/bin/sh\nexit 7\n')
        (directory/'python3').chmod(0o755)
        for choice in ('1', '2', '3', '6', '7', '8'):
            result = subprocess.run(['/bin/zsh',str(ROOT/'Start.command')], input=choice+'\n\n', text=True, capture_output=True, env=env)
            assert result.returncode == 7, 'Launcher lost the setup error status'
        (directory/'python3').write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$NEON_TEST_OPEN_LOG"\n')
        backup_path = '/tmp/backup with a \\ literal.json'
        result = subprocess.run(['/bin/zsh',str(ROOT/'Start.command')], input='3\n'+backup_path+'\nyes\n\n', text=True, capture_output=True, env=env)
        assert result.returncode == 0 and log.read_text().splitlines() == ['makeover.py','undo','--backup',backup_path]
        for choice, expected in [('6', ['dock.py','plan']), ('7', ['dock.py','apply','--confirm'])]:
            result = subprocess.run(['/bin/zsh',str(ROOT/'Start.command')], input=choice+'\n\n', text=True, capture_output=True, env=env)
            assert result.returncode == 0 and log.read_text().splitlines() == expected
        result = subprocess.run(['/bin/zsh',str(ROOT/'Start.command')], input='8\n'+backup_path+'\nyes\n\n', text=True, capture_output=True, env=env)
        assert result.returncode == 0 and log.read_text().splitlines() == ['dock.py','undo','--backup',backup_path]
    print('PASS: launcher preview/help without Python and preserved error status')

# Exercise the actual defaults adapter in a brand-new, disposable domain only.
if sys.platform == 'darwin':
    domain = 'org.neonhorizon.selfcheck.' + uuid.uuid4().hex
    try:
        with tempfile.TemporaryDirectory(prefix='neon-native-check-') as temporary:
            m.write_key(domain, 'before', 'original')
            settings = [{'domain':domain, 'key':key, 'after':value, 'label':key} for key,value in
                        [('before','new'),('bool',True),('int',7),('float',1.25),('text','A space & $value "quote"')]]
            changes = m.plan(settings)
            backup = m.apply(changes, Path(temporary))
            assert not m.plan(settings)
            m.write_key(domain, 'int', 9)
            assert m.undo(json.loads(backup.read_text())) == ['int']
            assert m.read_domain(domain) == {'before':'original','int':9}
            print('PASS: actual macOS preference adapter and conflict-safe undo in isolated domain')
    finally:
        subprocess.run(['/usr/bin/defaults','delete',domain], check=True, stdout=subprocess.DEVNULL)

page = host.ARTWORK.read_text()
class Elements(HTMLParser):
    def __init__(self):
        super().__init__(); self.counts = Counter()
    def handle_starttag(self, tag, attrs):
        self.counts.update(dict(attrs).get('class','').split())
p = Elements(); p.feed(page)
assert all(p.counts[k] == v for k,v in
           {'boat-anchor':2,'rain':4,'cascade':2,'plane-near':1,'bloom':1,
            'traffic':1,'lane':7,'emit':4,'ballast':3,'win':8,'bolt':2,
            'water-light':1,'near-rain-region':1}.items()), p.counts
assert p.counts['puddle'] == 0          # replaced by the depth-graded impact field
assert p.counts['wake'] == 0            # replaced by the boats' vertical light columns
assert p.counts['sp'] == 50 and p.counts['glint'] == 30
assets = [base64.b64decode(data, validate=True) for data in re.findall(r'data:image/webp;base64,([A-Za-z0-9+/=]+)',page)]
assert len(assets) == 3, len(assets)    # city, boat, pillarbox plate
assert all(data[:4] == b'RIFF' and data[8:12] == b'WEBP' for data in assets)
assert (ROOT / 'wallpaper/still.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
assert len(page.encode()) < 1_500_000, len(page)   # was 5.0 MB before the re-encode

# REGRESSION: the rain tiles reference their gradient as url(%23r). Writing the
# '#' pre-encoded and then percent-encoding the whole SVG yields %2523, a
# dangling paint-server reference — every drop renders with no fill and the rain
# is silently invisible.
tiles = re.findall(r'data:image/svg\+xml,([^"]+)', page)
assert len(tiles) == 6, len(tiles)      # 4 rain tiles + waterfall + water mask
assert all('%2523' not in t for t in tiles)
assert sum('url%28%23r%29' in t for t in tiles) == 4

# REGRESSION: under Reduce Motion `animation:none` makes an element render its
# DECLARED value. Any element whose visible opacity comes only from keyframes
# renders at 1 and becomes a solid blob, so .emit must declare a base.
emit_rule = re.search(r'\.emit\{[^}]*\}', page).group(0)
assert 'opacity:calc((var(--lo) + var(--hi))/2)' in emit_rule

# REGRESSION: `.rain::before` takes its duration from var(--speed). A variant
# that omits --speed makes the whole `animation` SHORTHAND invalid at
# computed-value time, which resets every longhand it sets — animation-name
# included — so that layer's drops freeze while the rule still looks live.
assert 'var(--speed,calc(' in page, 'the .rain::before shorthand needs a --speed fallback'
for variant in set(re.findall(r'\.rain\.(\w+)\{', page)):
    block = re.search(r'\.rain\.%s\{[^}]*\}' % variant, page).group(0)
    assert '--speed:' in block, f'.rain.{variant} does not declare --speed'

# REGRESSION: an element with an opacity animation is an isolated group, so a
# mix-blend-mode inside it cannot reach the painting. .storm-wrap contains three
# screen-blended layers, so it must modulate a custom property, never opacity.
storm_wrap = re.search(r'\.storm-wrap\{[^}]*\}', page).group(0)
assert 'storm-var' in storm_wrap and 'opacity' not in storm_wrap
assert '@property --storm' in page and '@keyframes storm-var{' in page

# REGRESSION: a percentage in translateY resolves against the element's OWN box.
# .flyer i is 1.6px tall, so a percentage bob there moves nothing.
assert re.search(r'@keyframes bobAir\{[^}]*translateY\(-?1px\)', page)

# REGRESSION: the river impacts must sit in .world, not inside .plane-near —
# that mask goes transparent on exactly the river side of the parapet.
promenade = re.search(r'<div class="plane-near"><div class="wet">(.*?)</div>', page, re.S).group(1)
assert promenade.count('class="sp"') == 36, promenade.count('class="sp"')
river = re.search(r'<div class="wet river">(.*?)</div>', page, re.S).group(1)
assert river.count('class="sp"') == 14, river.count('class="sp"')

reduced = re.search(r'@media\(prefers-reduced-motion:reduce\)\{.*?\n\}', page, re.S).group(0)
assert '.rain.mid,.rain.near,.rain.warm{display:none}' in reduced  # far rain MUST survive
assert '.rain.far{opacity:.17}' in reduced                         # brighter than animated floor
assert 'filter:blur' not in re.search(r'\.rain\.near\{[^}]*\}', page).group(0)

# Durations stay fixed: changing them would change phase at the current elapsed
# time. The generated script changes native playback rates instead.
assert '--t:1' in page and 'body.calm{--t:3}' not in page
for decl in re.findall(r'animation(?:-duration|-delay)?:[^;}]+', page):
    for time in re.finditer(r'\d+(?:\.\d+)?s\b', decl):
        if time.group(0) == '0s':
            continue                     # zero is the same at any tier
        before = decl[:time.start()]
        assert before.endswith('var(--t)*') or before.endswith('var(--t)*-'), decl

assert 'prefers-reduced-motion:reduce' in page
assert 'visibilitychange' in page and 'document.hidden' in page
assert not re.search(r'(?:src|href)=["\x27]https?://',page)
assert all(url.startswith('data:') for url in re.findall(r'url\(["\x27]?([^"\x27)]+)',page))

with host.ThreadingHTTPServer(('127.0.0.1',0),host.Wallpaper) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        for route in host.ROUTES:
            with urlopen(base + route, timeout=5) as response:
                assert response.read() == host.ARTWORK.read_bytes()
                assert response.headers['X-Content-Type-Options'] == 'nosniff'
        with urlopen(Request(base+'/', method='HEAD'), timeout=5) as response:
            assert response.read() == b''
        for route in ['/../makeover.py','/%2e%2e/preset.json','/docs/SETUP.md','/index.html/']:
            try:
                urlopen(base+route, timeout=5)
                raise AssertionError('Unexpected route served: '+route)
            except HTTPError as error:
                assert error.code == 404
    finally:
        server.shutdown(); thread.join()
agent = plistlib.loads(plistlib.dumps(host.agent_config(8767)))
assert agent['ProgramArguments'][1] == str(host.INSTALL/'host.py')
assert agent['ProgramArguments'][-3:] == ['--port','8767','--open-plash']
assert agent['RunAtLoad'] is True
print('PASS: embedded art, scene layers, loopback HTTP allowlist, HEAD, headers and portable login service data')

subprocess.run([sys.executable, str(ROOT/'tests/host-selfcheck.py')], check=True)
subprocess.run([sys.executable, str(ROOT/'tests/build-selfcheck.py')], check=True)
subprocess.run([sys.executable, str(ROOT/'tests/water-selfcheck.py')], check=True)
subprocess.run([sys.executable, str(ROOT/'tests/framing-selfcheck.py')], check=True)

if shutil.which('node'):
    script = re.search(r'<script>(.*?)</script>',page,re.S).group(1)
    stub = """
const assert=require('node:assert/strict');
const classes={},listeners={};
function motion(time){return {currentTime:time,rate:1,updates:0,
  updatePlaybackRate(rate){this.rate=rate;this.updates++}}}
let animations=[motion(713),motion(8241)];
const original=animations.slice();
const document={hidden:false,body:{classList:{toggle:(name,state)=>classes[name]=state}},
  getAnimations:()=>animations,addEventListener:(name,callback)=>listeners[name]=callback};
const window={addEventListener:(name,callback)=>listeners[name]=callback,
  matchMedia:query=>{assert.equal(query,'(prefers-reduced-motion: reduce)');
    return {addEventListener:(name,callback)=>{assert.equal(name,'change');listeners.motion=callback}}}};
function rates(rate){for(const animation of animations) assert.equal(animation.rate,rate)}
"""
    for initial in ('', '#calm'):
        probe = stub + "const location={hash:" + json.dumps(initial) + "};" + script + (
            "\nassert.equal(classes.paused,false);assert.equal(classes.calm,location.hash==='#calm');"
            "rates(location.hash==='#calm'?1/3:1);"
            "document.hidden=true;listeners.visibilitychange();assert.equal(classes.paused,true);"
            "document.hidden=false;listeners.visibilitychange();assert.equal(classes.paused,false);"
            "location.hash='#calm';listeners.hashchange();assert.equal(classes.calm,true);rates(1/3);"
            "location.hash='';listeners.hashchange();assert.equal(classes.calm,false);rates(1);"
            "assert.deepEqual(animations,original);"
            "assert.deepEqual(animations.map(a=>a.currentTime),[713,8241]);"
            "assert.ok(animations.every(a=>a.updates===3));"
            "location.hash='#calm';listeners.hashchange();"
            "animations=[];listeners.motion();"
            "animations=[motion(0),motion(0)];listeners.motion();rates(1/3);"
            "assert.ok(animations.every(a=>a.updates===1));")
        subprocess.run(['node','-e',probe], check=True)
    print('PASS: wallpaper script visibility, phase-preserving rate calls and recreated animations (DOM/API mocked)')
else:
    print('SKIP: optional visibility execution check needs Node.js')

profile = plistlib.loads((ROOT/'controls/Neon-Minimal.terminal').read_bytes())
assert 'CommandString' not in profile and 'Shell' not in profile
# Prune local-only directories before reading package content, including nested worktrees.
def distributable_files():
    ignored = {'.git', '.venv', '.worktrees', '__pycache__', 'generated-icons', 'backups'}
    for parent, directories, files in os.walk(ROOT):
        directories[:] = [d for d in directories if d not in ignored
                          and Path(parent, d) != ROOT/'wallpaper/build/out']
        for name in files:
            file = Path(parent, name)
            if name not in ('.git', '.DS_Store') and file.suffix not in ('.pyc', '.log') and not file.is_symlink():
                yield file
for file in distributable_files():
    raw = file.read_bytes()
    assert not re.search(rb'/(?:Users)/[A-Za-z0-9_. -]+/', raw), f'Personal path: {file.relative_to(ROOT)}'
    assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',raw)
    assert file.name not in ('Mac-Makeover-Session.txt','settings-before.json'), 'Private session record copied'
for value in profile.values():
    if isinstance(value, bytes):
        assert b'/Users/' not in value
print('PASS: package privacy checks and inert Terminal profile')
for doc in [ROOT/'README.md', *list((ROOT/'docs').rglob('*.md'))]:
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if not target.startswith(('http:', 'https:', '#')):
            assert (doc.parent/target.split('#')[0]).exists(), f'Broken link in {doc.name}: {target}'
print('PASS: local documentation links')
