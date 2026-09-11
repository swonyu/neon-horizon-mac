#!/usr/bin/env python3
"""Small standard-library checks; no personal preferences or login services changed."""
import base64
from contextlib import redirect_stdout
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
assert all(p.counts[k] == v for k,v in {'boat-anchor':5,'puddle':2,'rain':3,'cascade':2}.items())
assets = [base64.b64decode(data, validate=True) for data in re.findall(r'data:image/png;base64,([A-Za-z0-9+/=]+)',page)]
assert len(assets) == 2
assert (ROOT / 'wallpaper/still.png').read_bytes() in assets
assert all(data.startswith(b'\x89PNG\r\n\x1a\n') for data in assets)
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

# File operations are real in a temporary folder; launchctl and app launch are mocked.
with tempfile.TemporaryDirectory(prefix='neon-host-install-') as temporary:
    loaded = False
    fail_bootstrap = False
    def launch(args, **kwargs):
        global loaded
        if args[1] == 'print':
            return subprocess.CompletedProcess(args, 0 if loaded else 1)
        if args[1] == 'bootstrap':
            if fail_bootstrap:
                raise subprocess.CalledProcessError(1, args)
            loaded = True
        if args[1] == 'bootout':
            loaded = False
        return subprocess.CompletedProcess(args, 0)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    with patch.object(host, 'INSTALL', Path(temporary)/'Wallpaper'), patch.object(host, 'AGENT', Path(temporary)/'agent.plist'), patch.object(host.subprocess, 'run', launch), redirect_stdout(io.StringIO()):
        fail_bootstrap = True
        try:
            host.install(port)
            raise AssertionError('bootstrap failure swallowed')
        except subprocess.CalledProcessError:
            pass
        assert host.AGENT.exists() and not loaded
        fail_bootstrap = False
        host.install(port); assert loaded
        host.install(port); assert loaded
        host.uninstall(); assert not loaded and not host.AGENT.exists()
        assert (host.INSTALL/'index.html').exists()
        host.install(port); assert loaded
        host.uninstall()
        (host.INSTALL/'index.html').write_text('user edit')
        try:
            host.install(port)
            raise AssertionError('edited install overwritten')
        except ValueError:
            pass
        assert (host.INSTALL/'index.html').read_text() == 'user edit'
print('PASS: login install/retry/repeat/uninstall/reinstall and preservation of edited files (launch mocked)')

if shutil.which('node'):
    script = re.search(r'<script>(.*?)</script>',page,re.S).group(1)
    probe = "const assert=require('node:assert/strict');let paused,changed;const document={hidden:false,body:{classList:{toggle:(name,state)=>{assert.equal(name,'paused');paused=state;}}},addEventListener:(name,callback)=>{assert.equal(name,'visibilitychange');changed=callback;}};"
    probe += script + "\nassert.equal(paused,false);document.hidden=true;changed();assert.equal(paused,true);document.hidden=false;changed();assert.equal(paused,false);"
    subprocess.run(['node','-e',probe], check=True)
    print('PASS: actual wallpaper visibility script pauses and resumes (DOM mocked)')
else:
    print('SKIP: optional visibility execution check needs Node.js')

profile = plistlib.loads((ROOT/'controls/Neon-Minimal.terminal').read_bytes())
assert 'CommandString' not in profile and 'Shell' not in profile
# Inspect every distributable file, including decoded Terminal data and embedded artwork chunks.
for file in ROOT.rglob('*'):
    if not file.is_file() or any(x in ('.git','__pycache__','generated-icons') for x in file.parts):
        continue
    raw = file.read_bytes()
    assert not re.search(rb'/(?:Users)/[A-Za-z0-9_. -]+/', raw), f'Personal path: {file.relative_to(ROOT)}'
    assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',raw)
    assert file.name not in ('Mac-Makeover-Session.txt','settings-before.json'), 'Private session record copied'
for value in profile.values():
    if isinstance(value, bytes):
        assert b'/Users/' not in value
print('PASS: package privacy checks and inert Terminal profile')
for doc in [ROOT/'README.md', *list((ROOT/'docs').glob('*.md'))]:
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if not target.startswith(('http:', 'https:', '#')):
            assert (doc.parent/target.split('#')[0]).exists(), f'Broken link in {doc.name}: {target}'
print('PASS: local documentation links')
