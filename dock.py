#!/usr/bin/env python3
"""Personalize existing Dock pins using this Mac's available Spotlight usage metadata."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import uuid
from xml.parsers.expat import ExpatError

STATE = Path.home() / 'Library/Application Support/Neon Horizon Makeover/Dock'
SCREEN_SHARING_PATHS = (
    Path('/System/Applications/Utilities/Screen Sharing.app'),
    Path('/System/Library/CoreServices/Applications/Screen Sharing.app'),
)
FORMAT = 'neon-horizon-dock-v1'
SPACERS = {'spacer-tile', 'small-spacer-tile', 'flex-spacer-tile'}


def validate_apps(value):
    if not isinstance(value, list) or not all(isinstance(tile, dict) for tile in value):
        raise ValueError('Unsupported Dock persistent-apps format; nothing was replaced')
    try:
        plistlib.dumps(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError('Dock tiles cannot be preserved as a property list') from error


def same(a, b):
    return plistlib.dumps(a, fmt=plistlib.FMT_BINARY) == plistlib.dumps(b, fmt=plistlib.FMT_BINARY)


def read_apps():
    output = subprocess.run(['/usr/bin/defaults', 'export', 'com.apple.dock', '-'],
                            check=True, timeout=10, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    domain = plistlib.loads(output)
    if not isinstance(domain, dict):
        raise ValueError('Unsupported Dock preference domain')
    apps = domain.get('persistent-apps')
    validate_apps(apps)
    return apps


def write_apps(apps):
    validate_apps(apps)
    # Each XML argument is one tile. Never import or replace the whole Dock domain.
    subprocess.run(['/usr/bin/defaults', 'write', 'com.apple.dock', 'persistent-apps', '-array',
                    *(plistlib.dumps(tile).decode('utf-8') for tile in apps)],
                   check=True, timeout=10, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def valid_app(path):
    try:
        path = Path(path).resolve(strict=True)
        if path.suffix.lower() != '.app' or not path.is_dir():
            return None
        info = plistlib.loads((path / 'Contents/Info.plist').read_bytes())
        if (not isinstance(info, dict) or info.get('CFBundlePackageType') != 'APPL'
                or not isinstance(info.get('CFBundleIdentifier'), str) or not info['CFBundleIdentifier']):
            return None
        return path
    except (OSError, ValueError, RuntimeError, ExpatError, plistlib.InvalidFileException):
        return None


def app_path(tile):
    try:
        value = tile['tile-data']['file-data']['_CFURLString']
        if not isinstance(value, str):
            return None
        url = urlsplit(value)
        if url.scheme != 'file' or url.netloc not in ('', 'localhost') or url.query or url.fragment:
            return None
        decoded = unquote(url.path, errors='strict')
        if '\0' in decoded or not Path(decoded).is_absolute():
            return None
        return valid_app(decoded)
    except (KeyError, TypeError, ValueError):
        return None


def new_tile(path):
    return {'GUID': uuid.uuid4().int & 0x7fffffff, 'tile-type': 'file-tile', 'tile-data': {
        'file-data': {'_CFURLString': path.as_uri(), '_CFURLStringType': 15},
        'file-label': path.stem, 'file-type': 41,
    }}


def usage(path):
    try:
        raw = subprocess.run(['/usr/bin/mdls', '-plist', '-', '-name', 'kMDItemUseCount',
                              '-name', 'kMDItemLastUsedDate', str(path)], check=True,
                             timeout=3, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        info = plistlib.loads(raw)
        if not isinstance(info, dict):
            return None, None
        count, date = info.get('kMDItemUseCount'), info.get('kMDItemLastUsedDate')
        if type(count) is not int or count < 0:
            count = None
        if not isinstance(date, datetime):
            date = None
        return count, date
    except (OSError, ValueError, ExpatError, plistlib.InvalidFileException, subprocess.SubprocessError):
        return None, None


def rank(item):
    count, date = item['usage']
    return (-(count or 0), -date.replace(tzinfo=timezone.utc).timestamp() if date else float('inf'))


def plan(discover=False, directories=None):
    before = read_apps()
    screen = next((app for path in SCREEN_SHARING_PATHS if (app := valid_app(path))), None)
    if screen is None:
        raise ValueError('Native Screen Sharing.app was not found; Dock left unchanged')
    measured, fallback, seen = [], [], set()
    screen_tile, separator = None, None
    removed = 0
    for tile in before:
        if tile.get('tile-type') in SPACERS:
            if separator is None and tile.get('tile-type') == 'small-spacer-tile':
                separator = tile
            removed += 1
            continue
        path = app_path(tile)
        if path is not None:
            if path in seen:
                removed += 1
                continue
            seen.add(path)
        if path == screen:
            screen_tile = tile
            continue
        item = {'tile': tile, 'path': path, 'usage': usage(path) if path else (None, None)}
        (fallback if item['usage'][0] is None else measured).append(item)
    additions = []
    if discover:
        directories = directories if directories is not None else (Path('/Applications'), Path.home() / 'Applications')
        candidates = []
        for directory in directories:
            if not directory.is_dir():
                continue
            for candidate in sorted(directory.iterdir()):
                path = valid_app(candidate)
                if path is None or path in seen or path == screen:
                    continue
                seen.add(path)
                info = usage(path)
                if (info[0] or 0) > 0:
                    candidates.append({'path': path, 'usage': info})
        for candidate in sorted(candidates, key=rank)[:3]:
            additions.append(dict(candidate, tile=new_tile(candidate['path'])))
    ordered = sorted(measured + additions, key=rank) + fallback
    applied = [screen_tile if screen_tile is not None else new_tile(screen)]
    if ordered:
        applied.append(separator if separator is not None else {
            'GUID': uuid.uuid4().int & 0x7fffffff, 'tile-type': 'small-spacer-tile'})
    applied.extend(item['tile'] for item in ordered)
    return {'before': before, 'applied': applied, 'ranking': ordered,
            'added': len(additions), 'removed': removed}


def show_plan(result):
    print('Finder stays implicit; Screen Sharing is the first pinned app, followed by one separator.')
    print('Ranking: Spotlight use count, then last-used date; not Screen Time duration.')
    print('Missing use count or unavailable app: preserve original order after measured pins.')
    for item in result['ranking']:
        data = item['tile'].get('tile-data', {})
        label = item['path'].stem if item['path'] else data.get('file-label', 'Existing unavailable or non-app tile') if isinstance(data, dict) else 'Existing tile'
        count, date = item['usage']
        basis = 'original order (use count unavailable)' if count is None else (
            'use count ' + str(count)
            + '; last used ' + (date.isoformat() + ' UTC' if date else 'unavailable'))
        print(f'  {label}: {basis}')
    print(f"{result['added']} discovered apps added; {result['removed']} old spacer/duplicate tiles replaced.")


@contextmanager
def locked(directory):
    if directory.is_symlink():
        raise ValueError('Backup directory must not be a symbolic link')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_uid != os.getuid():
        raise ValueError('Backup directory belongs to another user')
    directory.chmod(0o700)
    descriptor = os.open(directory / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def save(path, record):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.dock-', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            plistlib.dump(record, stream, fmt=plistlib.FMT_BINARY)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def validate_record(record):
    if (not isinstance(record, dict) or record.get('format') != FORMAT
            or type(record.get('uid')) is not int or record['uid'] != os.getuid()
            or record.get('home') != str(Path.home())):
        raise ValueError('Not a Dock backup for this user and home folder')
    validate_apps(record.get('before'))
    validate_apps(record.get('applied'))


def load_record(path):
    record = plistlib.loads(path.read_bytes())
    validate_record(record)
    return record


def apply(result, directory):
    record = {'format': FORMAT, 'uid': os.getuid(), 'home': str(Path.home()),
              'before': result['before'], 'applied': result['applied']}
    validate_record(record)
    if not same(read_apps(), record['before']):
        raise RuntimeError('Dock changed since preview; run plan again')
    if same(record['before'], record['applied']):
        return None
    journal = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
                           + '-' + uuid.uuid4().hex[:8] + '.plist')
    save(journal, record)
    # Check again after durable publication; never silently rebase the preview.
    if not same(read_apps(), record['before']):
        raise RuntimeError('Dock changed before writing; preserved your layout. Backup: ' + str(journal))
    write_apps(record['applied'])
    if not same(read_apps(), record['applied']):
        raise RuntimeError('Dock readback did not match; inspect before retrying. Backup: ' + str(journal))
    return journal


def undo(record):
    validate_record(record)
    current = read_apps()
    if same(current, record['before']):
        return True
    # Preserve any difference, including Dock-generated metadata. Do not guess
    # which unknown tile fields macOS or the user intended to keep.
    if not same(current, record['applied']):
        return False
    write_apps(record['before'])
    if not same(read_apps(), record['before']):
        raise RuntimeError('Dock restore readback did not match; backup retained')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='plan', choices=('plan', 'apply', 'undo', 'backups'))
    parser.add_argument('--discover', action='store_true', help='Add up to three used top-level apps from local Applications folders')
    parser.add_argument('--backup', type=Path, help='Exact Dock backup plist to undo')
    parser.add_argument('--confirm', action='store_true', help='Ask before applying the displayed layout')
    args = parser.parse_args()
    if sys.platform != 'darwin' or os.geteuid() == 0:
        parser.error('Run on macOS as your normal user, without sudo')
    if args.action == 'backups':
        for path in sorted(STATE.glob('*.plist'), reverse=True):
            print(path)
        return
    if args.action == 'undo':
        if not args.backup:
            parser.error('Choose an exact --backup file from the backups command')
        with locked(STATE):
            restored = undo(load_record(args.backup.expanduser()))
        print('Original Dock restored (or already present).' if restored else
              'Dock contents differ from this backup, possibly including macOS metadata updates; nothing was restored.')
        if restored:
            print('Log out/in when convenient to refresh the visible Dock. Backup retained.')
        return
    result = plan(args.discover)
    show_plan(result)
    if args.action == 'plan':
        print('Preview only. Use apply with the same options to save a backup and apply.')
        return
    if args.confirm:
        try:
            answer = input('Back up and apply this Dock layout? Type yes: ')
        except EOFError:
            answer = ''
        if answer != 'yes':
            print('No changes made.')
            return
    with locked(STATE):
        journal = apply(result, STATE)
    print('Dock saved and read back. Undo backup: ' + str(journal) if journal else 'Already configured; no backup needed.')
    print('Log out/in when convenient to refresh the visible Dock.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, ExpatError, subprocess.SubprocessError) as error:
        print(f'Stopped: {error}. Dock backups remain available through the backups command.', file=sys.stderr)
        sys.exit(1)
