#!/usr/bin/env python3
"""Preview/apply a small native preset; journal each key before writing it."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / 'Library/Application Support/Neon Horizon Makeover'
CORE = ['appearance', 'dock', 'finder', 'desktop', 'calendar']
UI_DOMAINS = {'NSGlobalDomain', 'com.apple.dock', 'com.apple.finder',
              'com.apple.WindowManager', 'com.apple.screencapture',
              'com.apple.iCal', 'com.apple.Spotlight'}


def scalar(value):
    if type(value) is float:
        try:
            # defaults -float writes single precision; reject lossy apply/undo values.
            return math.isfinite(value) and struct.unpack('f', struct.pack('f', value))[0] == value
        except OverflowError:
            return False
    return (type(value) is bool or (type(value) is int and -(2**63) <= value < 2**63)
            or (type(value) is str and '\0' not in value))


def valid_key(domain, key):
    return (isinstance(domain, str) and domain in UI_DOMAINS and isinstance(key, str)
            and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_. -]{0,200}', key))


def same(a, b):
    return type(a) is type(b) and a == b


def read_domain(domain):
    raw = subprocess.check_output(['/usr/bin/defaults', 'export', domain, '-'])
    result = plistlib.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('Unexpected preference format: ' + domain)
    return result


def write_key(domain, key, value):
    if value is None:
        subprocess.run(['/usr/bin/defaults', 'delete', domain, key], check=True,
                       stdout=subprocess.DEVNULL)
        return
    flag = {bool: '-bool', int: '-int', float: '-float', str: '-string'}[type(value)]
    text = str(value).lower() if type(value) is bool else str(value)
    subprocess.run(['/usr/bin/defaults', 'write', domain, key, flag, text], check=True)


def load_settings(groups):
    catalog = json.loads((ROOT / 'preset.json').read_text())
    if not isinstance(catalog, dict) or not all(isinstance(g, str) for g in catalog):
        raise ValueError('Unexpected preset catalog')
    selected = list(catalog) if groups == ['all'] else groups
    if not selected or set(selected) - set(catalog):
        raise ValueError('Groups: ' + ', '.join(catalog) + ', all')
    settings, seen = [], set()
    for group in dict.fromkeys(selected):
        if not isinstance(catalog[group], list):
            raise ValueError('Unexpected preset group: ' + group)
        for entry in catalog[group]:
            if not isinstance(entry, list) or len(entry) != 4:
                raise ValueError('Unexpected preset entry')
            domain, key, value, label = entry
            if not valid_key(domain, key) or (domain, key) in seen or not isinstance(label, str):
                raise ValueError('Unexpected or duplicate preset key')
            if isinstance(value, str) and value.startswith('~/'):
                value = str(Path(value).expanduser())
            if not scalar(value):
                raise ValueError('Preset value cannot be written exactly: ' + key)
            settings.append({'domain': domain, 'key': key, 'after': value, 'label': label})
            seen.add((domain, key))
    return settings


def plan(settings, reader=read_domain):
    domains = {domain: reader(domain) for domain in {s['domain'] for s in settings}}
    changes = []
    for setting in settings:
        before = domains[setting['domain']].get(setting['key'])
        if before is not None and not scalar(before):
            raise ValueError('Cannot safely restore original value: ' + setting['key'])
        if not same(before, setting['after']):
            changes.append(dict(setting, before=before))
    return changes


def save(path, data):
    # Journal lives outside the repository, with owner-only access.
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        os.chmod(temp, 0o600)
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)  # Publish the journal name before changing preferences.
    finally:
        os.close(descriptor)


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / '.lock').open('a') as lock:
        os.chmod(directory / '.lock', 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def apply(changes, directory, reader=read_domain, writer=write_key):
    if not changes:
        return None
    journal = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
                           + '-' + uuid.uuid4().hex[:8] + '.json')
    record = {'format': 1, 'changes': []}
    for change in changes:
        current = reader(change['domain']).get(change['key'])
        if not same(current, change['before']):
            raise RuntimeError('Setting changed during setup; stopped at ' + change['key'])
        record['changes'].append(change)
        save(journal, record)  # Record before attempting the write, including partial failures.
        if not same(reader(change['domain']).get(change['key']), change['before']):
            raise RuntimeError('Setting changed during setup; stopped at ' + change['key'])
        writer(change['domain'], change['key'], change['after'])
        if not same(reader(change['domain']).get(change['key']), change['after']):
            raise RuntimeError('Could not verify ' + change['key'] + '; undo file: ' + str(journal))
    return journal


def undo(record, reader=read_domain, writer=write_key):
    conflicts = []
    for change in reversed(record['changes']):
        current = reader(change['domain']).get(change['key'])
        if same(current, change['before']):
            continue
        if not same(current, change['after']):
            conflicts.append(change['key'])  # Keep edits made after the makeover.
            continue
        writer(change['domain'], change['key'], change['before'])
        if not same(reader(change['domain']).get(change['key']), change['before']):
            raise RuntimeError('Restore verification failed: ' + change['key'])
    return conflicts


def validate_record(record):
    # Keep old backups usable when the selectable preset evolves.
    if (not isinstance(record, dict) or type(record.get('format')) is not int
            or record['format'] != 1 or not isinstance(record.get('changes'), list)):
        raise ValueError('Not a makeover backup')
    seen = set()
    for change in record['changes']:
        if (not isinstance(change, dict) or not {'domain', 'key', 'before', 'after'} <= change.keys()
                or not valid_key(change['domain'], change['key'])):
            raise ValueError('Unexpected backup entry')
        pair = (change['domain'], change['key'])
        if pair in seen or not scalar(change['after']):
            raise ValueError('Unexpected or duplicate backup key')
        if change['before'] is not None and not scalar(change['before']):
            raise ValueError('Unexpected backup value')
        seen.add(pair)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='plan', choices=['plan', 'apply', 'undo', 'backups'])
    parser.add_argument('--groups', default=','.join(CORE), help='Comma-separated groups; use all for every preset group')
    parser.add_argument('--backup', type=Path, help='Exact backup JSON file to undo (see backups command)')
    parser.add_argument('--confirm', action='store_true', help='Ask before applying the displayed changes')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Native setup requires macOS. The wallpaper HTML also works in modern browsers.')
    if os.geteuid() == 0:
        parser.error('Run as your normal user, without sudo.')
    if args.action == 'backups':
        for path in sorted(STATE.glob('*.json'), key=lambda p: p.stat().st_mtime_ns, reverse=True):
            print(path)
        return
    if args.action == 'undo':
        if not args.backup:
            parser.error('Choose an exact file with --backup. Run backups to list them.')
        with locked(STATE):
            record = json.loads(args.backup.expanduser().read_text())
            validate_record(record)
            conflicts = undo(record)
        print('Restored unchanged makeover values. Backups and created folders are retained.')
        if conflicts:
            print('Kept your later edits: ' + ', '.join(conflicts))
        print('Log out and back in when convenient to refresh all affected apps.')
        return
    version = tuple(map(int, subprocess.check_output(['/usr/bin/sw_vers', '-productVersion'], text=True).strip().split('.')))
    if version < (26, 1) or version[0] > 27:
        parser.error('This preset targets macOS 26.1–27. Use the manual guide on other versions.')
    settings = load_settings(args.groups.split(','))
    changes = plan(settings)
    for change in changes:
        print(f"{change['label']}: {change['before']!r} → {change['after']!r}")
    print(f'{len(changes)} changes; {len(settings) - len(changes)} already match.')
    if args.action == 'plan':
        print('Preview only. Use apply with the same --groups to save a backup and apply.')
        return
    if args.confirm:
        try:
            answer = input('Save a backup and apply these settings? Type yes: ')
        except EOFError:
            answer = ''
        if answer != 'yes':
            print('No changes made.')
            return
    with locked(STATE):
        # apply() rejects edits since this exact preview; never silently rebase it.
        for setting in settings:
            if (setting['domain'], setting['key']) == ('com.apple.screencapture', 'location'):
                Path(setting['after']).mkdir(parents=True, exist_ok=True)
        journal = apply(changes, STATE)
    print('Settings saved and read back.' if journal else 'Already configured; no new backup needed.')
    if journal:
        print('Undo backup: ' + str(journal))
    print('Finish the native UI checklist in docs/SETUP.md. Log out/in when convenient to refresh apps.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Stopped: {error}. Any attempted changes are recorded by the backups command.', file=sys.stderr)
        sys.exit(1)
