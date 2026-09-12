#!/usr/bin/env python3
"""Optional loopback-only wallpaper host. Prefer Plash's local-file picker."""
import argparse
import fcntl
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import plistlib
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from xml.parsers.expat import ExpatError

ARTWORK = Path(__file__).resolve().with_name('index.html')
LABEL = 'org.neonhorizon.wallpaper'
INSTALL = Path.home() / 'Library/Application Support/Neon Horizon Makeover/Wallpaper'
AGENT = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
ROUTES = {'/', '/index.html', '/Neon-Horizon-Live/', '/Neon-Horizon-Live/index.html'}


class Wallpaper(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond(False)

    def do_HEAD(self):
        self.respond(True)

    def respond(self, head):
        if urlsplit(self.path).path not in ROUTES:
            self.send_error(404)
            return
        try:
            content = ARTWORK.read_bytes()
        except OSError:
            self.send_error(503, 'Wallpaper unavailable')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        if not head:
            self.wfile.write(content)

    def log_message(self, *_):
        pass


def agent_config(port):
    return {'Label': LABEL,
            'ProgramArguments': [str(Path(sys.executable).resolve()), str(INSTALL / 'host.py'),
                                 '--port', str(port), '--open-plash'],
            'RunAtLoad': True, 'KeepAlive': {'SuccessfulExit': False}, 'ThrottleInterval': 30,
            'ProcessType': 'Background'}


def sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish(path, content):
    # Stage artwork outside INSTALL so an interrupted staging file cannot block retry.
    staging = INSTALL.parent if path.parent == INSTALL else path.parent
    descriptor, name = tempfile.mkstemp(prefix='.neon-wallpaper-', suffix='.tmp', dir=staging)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Publish complete bytes without replacing an existing file.
        temporary.unlink()
        for directory in {staging, path.parent}:
            sync_directory(directory)
    finally:
        temporary.unlink(missing_ok=True)


def read_agent():
    if AGENT.is_symlink():
        raise ValueError('Service file is a symbolic link; preserved without changes: ' + str(AGENT))
    if not AGENT.exists():
        return None
    try:
        config = plistlib.loads(AGENT.read_bytes())
    except (ValueError, ExpatError) as error:
        raise ValueError('Unreadable service file; preserved without changes: ' + str(AGENT)) from error
    if not isinstance(config, dict):
        raise ValueError('Unrecognized service file; preserved without changes: ' + str(AGENT))
    return config


def loaded_job(config):
    result = subprocess.run(['/bin/launchctl', 'print', f'gui/{os.getuid()}/{LABEL}'],
                            capture_output=True, text=True)
    if result.returncode:
        if f'Could not find service "{LABEL}"' in result.stderr:
            return None
        raise ValueError('Could not inspect the loaded service; preserved without changes.')
    output = result.stdout
    arguments = re.search(r'^\targuments = \{\n((?:\t\t[^\n]*\n)*)\t\}', output, re.M)
    fields = dict(re.findall(r'^\t(path|program|state) = (.*)$', output, re.M))
    expected = config.get('ProgramArguments') if config else None
    if (not expected or fields.get('path') != str(AGENT)
            or fields.get('program') != expected[0] or arguments is None
            or [line[2:] for line in arguments[1].splitlines()] != expected):
        raise ValueError('Unrecognized loaded service; preserved without changes.')
    return fields


def wait_ready(port, config, content):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = loaded_job(config)
        if job and job.get('state') == 'running':
            connection = HTTPConnection('127.0.0.1', port, timeout=0.5)
            try:
                connection.request('GET', '/')
                response = connection.getresponse()
                if response.status == 200 and response.read(len(content) + 1) == content:
                    return
            except (OSError, HTTPException):
                pass
            finally:
                connection.close()
        time.sleep(0.1)
    raise RuntimeError('Host did not serve the installed wallpaper within 5 seconds. '
                       'Files are retained; retry install or use --uninstall.')


def install(port):
    sources = [Path(__file__).resolve(), ARTWORK]
    config = agent_config(port)
    saved = read_agent()
    if saved is not None and saved != config:
        raise ValueError('Different service configuration found; disable it before changing the port or Python path.')
    loaded = loaded_job(config)
    if INSTALL.is_symlink():
        raise ValueError('Install directory is a symbolic link; preserved without changes: ' + str(INSTALL))
    expected = {source.name: source.read_bytes() for source in sources}
    if INSTALL.exists():
        for file in INSTALL.iterdir():
            if file.is_symlink() or file.name not in expected or not file.is_file() or file.read_bytes() != expected[file.name]:
                raise ValueError('Changed install files found; keep them as a backup before updating. See docs/SETUP.md.')
    subprocess.run(['/usr/bin/open', '-Ra', 'Plash'], check=True, capture_output=True)
    if not loaded:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))  # Do not interfere with another service using this port.
    INSTALL.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, content in expected.items():
        target = INSTALL / name
        if not target.exists():
            publish(target, content)
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    if saved is None:
        publish(AGENT, plistlib.dumps(config))
    if not loaded:
        subprocess.run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(AGENT)], check=True)
    wait_ready(port, config, expected[ARTWORK.name])
    print(f'Host installed for login. In Plash, add http://127.0.0.1:{port}/')
    print('Select that website and enable Show on all Spaces. The host starts Plash at login.')


def uninstall():
    config = read_agent()
    if config is None:
        loaded_job(None)  # Do not silently ignore a job whose plist disappeared.
        print('No Neon Horizon login service file found.')
        return
    args = config.get('ProgramArguments', [])
    if (config.get('Label') != LABEL or not isinstance(args, list) or len(args) != 5
            or not all(isinstance(arg, str) for arg in args) or not args[0]
            or args[1] != str(INSTALL / 'host.py') or args[2] != '--port'
            or not args[3].isdigit() or not 1024 <= int(args[3]) <= 65535
            or args[4] != '--open-plash' or config.get('Program', args[0]) != args[0]):
        raise ValueError('Unrecognized service file; refusing to remove it.')
    target = f'gui/{os.getuid()}/{LABEL}'
    loaded = loaded_job(config)
    if loaded:
        subprocess.run(['/bin/launchctl', 'bootout', target], check=True)
    AGENT.unlink()
    sync_directory(AGENT.parent)
    print('Login host disabled. Choose another Plash website or quit Plash. Artwork files are retained.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--install', action='store_true')
    actions.add_argument('--uninstall', action='store_true')
    parser.add_argument('--open-plash', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Choose a port from 1024 to 65535.')
    if args.install or args.uninstall or args.open_plash:
        if sys.platform != 'darwin' or os.geteuid() == 0:
            parser.error('Run the Mac login setup as your normal user, without sudo.')
    if args.install or args.uninstall:
        INSTALL.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (INSTALL.parent / '.wallpaper-lock').open('a') as lock:
            os.chmod(INSTALL.parent / '.wallpaper-lock', 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.install:
                install(args.port)
            else:
                uninstall()
    else:
        ARTWORK.read_bytes()  # Fail before binding a port or opening Plash if artwork is missing.
        with ThreadingHTTPServer(('127.0.0.1', args.port), Wallpaper) as server:
            if args.open_plash:
                subprocess.run(['/usr/bin/open', '-g', '-a', 'Plash'], check=True)
            print(f'Wallpaper: http://127.0.0.1:{server.server_port}/ — Control-C to stop.', flush=True)
            server.serve_forever()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Stopped: {error}', file=sys.stderr)
        sys.exit(1)
