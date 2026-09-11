#!/usr/bin/env python3
"""Optional loopback-only wallpaper host. Prefer Plash's local-file picker."""
import argparse
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import plistlib
import shutil
import socket
import subprocess
import sys
from urllib.parse import urlsplit

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
        content = ARTWORK.read_bytes()
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


def install(port):
    sources = [Path(__file__).resolve(), ARTWORK]
    config = agent_config(port)
    if AGENT.exists() and plistlib.loads(AGENT.read_bytes()) != config:
        raise ValueError('Different service configuration found; disable it before changing the port or Python path.')
    if INSTALL.exists():
        expected = {source.name: source.read_bytes() for source in sources}
        for file in INSTALL.iterdir():
            if file.is_symlink() or file.name not in expected or not file.is_file() or file.read_bytes() != expected[file.name]:
                raise ValueError('Changed install files found; keep them as a backup before updating. See docs/SETUP.md.')
    subprocess.run(['/usr/bin/open', '-Ra', 'Plash'], check=True, capture_output=True)
    if AGENT.exists() and subprocess.run(['/bin/launchctl', 'print', f'gui/{os.getuid()}/{LABEL}'], capture_output=True).returncode == 0:
        print(f'Already installed. Plash URL: http://127.0.0.1:{port}/')
        return
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))  # Do not interfere with another service using this port.
    INSTALL.mkdir(parents=True, exist_ok=True, mode=0o700)
    for source in sources:
        target = INSTALL / source.name
        if not target.exists():
            shutil.copyfile(source, target)
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    if not AGENT.exists():
        with AGENT.open('xb') as stream:
            os.chmod(AGENT, 0o600)
            plistlib.dump(config, stream)
    subprocess.run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(AGENT)], check=True)
    print(f'Host installed for login. In Plash, add http://127.0.0.1:{port}/')
    print('Select that website and enable Show on all Spaces. The host starts Plash at login.')


def uninstall():
    if not AGENT.exists():
        print('No Neon Horizon login service file found.')
        return
    config = plistlib.loads(AGENT.read_bytes())
    args = config.get('ProgramArguments', [])
    if config.get('Label') != LABEL or len(args) < 2 or args[1] != str(INSTALL / 'host.py'):
        raise ValueError('Unrecognized service file; refusing to remove it.')
    target = f'gui/{os.getuid()}/{LABEL}'
    loaded = subprocess.run(['/bin/launchctl', 'print', target], capture_output=True).returncode == 0
    if loaded:
        subprocess.run(['/bin/launchctl', 'bootout', target], check=True)
    AGENT.unlink()
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
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Stopped: {error}', file=sys.stderr)
        sys.exit(1)
