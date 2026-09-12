#!/usr/bin/env python3
"""Host recovery checks: temporary files, loopback sockets and mocked launchctl only."""
from contextlib import contextmanager, redirect_stdout
from http.client import HTTPConnection
import importlib.util
import io
import os
from pathlib import Path
import plistlib
import socket
import stat
import subprocess
import tempfile
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wallpaper_host', ROOT / 'wallpaper/host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


def rejected(action, message):
    try:
        action()
    except (ValueError, OSError, RuntimeError) as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError('Expected rejection: ' + message)


@contextmanager
def installation():
    with tempfile.TemporaryDirectory(prefix='neon-host-check-') as temporary:
        directory = Path(temporary)
        calls = []
        state = {'loaded': False, 'foreign': False, 'bootstrap_failure': False}
        def launch(args, **kwargs):
            calls.append(args)
            if args[1] == 'print':
                if not state['loaded']:
                    return subprocess.CompletedProcess(args, 113, '', f'Could not find service "{host.LABEL}"')
                config = host.agent_config(port)
                arguments = config['ProgramArguments']
                program = '/foreign/python' if state['foreign'] else arguments[0]
                output = (f'gui/{os.getuid()}/{host.LABEL} = {{\n'
                          f'\tpath = {host.AGENT}\n\tstate = running\n\tprogram = {program}\n'
                          '\targuments = {\n' + ''.join('\t\t' + value + '\n' for value in arguments)
                          + '\t}\n\tpid = 12345\n}\n')
                return subprocess.CompletedProcess(args, 0, output, '')
            if args[1] == 'bootstrap':
                if state['bootstrap_failure']:
                    raise subprocess.CalledProcessError(5, args)
                state['loaded'] = True
            if args[1] == 'bootout':
                state['loaded'] = False
            return subprocess.CompletedProcess(args, 0, '', '')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with patch.object(host, 'INSTALL', directory / 'Wallpaper'), patch.object(host, 'AGENT', directory / 'agent.plist'), patch.object(host.subprocess, 'run', launch), redirect_stdout(io.StringIO()):
            yield directory, state, calls, port


def missing_loaded_artwork():
    with installation() as (directory, state, calls, port):
        host.INSTALL.mkdir()
        (host.INSTALL / 'host.py').write_bytes(Path(host.__file__).read_bytes())
        host.AGENT.write_bytes(plistlib.dumps(host.agent_config(port)))
        state['loaded'] = True
        # No real service exists in these lifecycle checks; health has its own real HTTP check.
        with patch.object(host, 'wait_ready', create=True):
            host.install(port)
        assert (host.INSTALL / 'index.html').read_bytes() == host.ARTWORK.read_bytes()
        assert not any(call[1] == 'bootstrap' for call in calls)
        (host.INSTALL / 'host.py').unlink()
        with patch.object(host, 'wait_ready'):
            host.install(port)
        assert (host.INSTALL / 'host.py').read_bytes() == Path(host.__file__).read_bytes()


def foreign_job_preserved():
    with installation() as (directory, state, calls, port):
        state.update(loaded=True, foreign=True)
        rejected(lambda: host.install(port), 'loaded service')
        assert not host.INSTALL.exists() and not host.AGENT.exists()
        host.AGENT.write_bytes(plistlib.dumps(host.agent_config(port)))
        rejected(host.uninstall, 'loaded service')
        assert host.AGENT.exists() and not any(call[1] == 'bootout' for call in calls)


def malformed_plist_preserved():
    with installation() as (directory, state, calls, port):
        for data in [b'<?xml version="1.0"?><plist', plistlib.dumps(['wrong shape'])]:
            host.AGENT.write_bytes(data)
            rejected(lambda: host.install(port), 'preserved')
            rejected(host.uninstall, 'preserved')
            assert host.AGENT.read_bytes() == data
        assert not calls


def partial_publication():
    with installation() as (directory, state, calls, port):
        def fail_dump(value, stream, **kwargs):
            stream.write(b'partial')
            raise OSError('injected plist write failure')
        with patch.object(host.plistlib, 'dump', fail_dump):
            rejected(lambda: host.install(port), 'injected plist write failure')
        assert not host.AGENT.exists(), 'partial plist was published'
        assert not any(call[1] == 'bootstrap' for call in calls)


def symlink_install_preserved():
    with installation() as (directory, state, calls, port):
        outside = directory / 'outside'
        outside.mkdir()
        host.INSTALL.symlink_to(outside, target_is_directory=True)
        rejected(lambda: host.install(port), 'symbolic link')
        assert list(outside.iterdir()) == [] and not host.AGENT.exists()


def lifecycle_and_durability():
    with installation() as (directory, state, calls, port), patch.object(host, 'wait_ready') as ready:
        state['bootstrap_failure'] = True
        try:
            host.install(port)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('Bootstrap failure was swallowed')
        assert host.AGENT.exists() and not state['loaded']
        assert plistlib.loads(host.AGENT.read_bytes()) == host.agent_config(port)
        ready.assert_not_called()
        state['bootstrap_failure'] = False
        host.install(port)
        host.install(port)
        assert state['loaded'] and ready.call_count == 2
        for file in [host.AGENT, host.INSTALL / 'host.py', host.INSTALL / 'index.html']:
            assert file.stat().st_mode & 0o777 == 0o600
        with patch.object(host.os, 'fsync', wraps=os.fsync) as synchronized:
            host.uninstall()
            assert synchronized.called, 'Uninstall did not synchronize removal of the login plist'
        assert not state['loaded'] and not host.AGENT.exists()
        assert (host.INSTALL / 'index.html').exists()
        host.uninstall()
        host.install(port)
        host.uninstall()
        (host.INSTALL / 'index.html').write_text('user edit')
        rejected(lambda: host.install(port), 'Changed install files')
        assert (host.INSTALL / 'index.html').read_text() == 'user edit'


def publication_does_not_clobber():
    with installation() as (directory, state, calls, port):
        host.INSTALL.mkdir()
        target = host.INSTALL / 'index.html'
        with patch.object(host.os, 'fsync', side_effect=OSError('injected synchronization failure')):
            rejected(lambda: host.publish(target, b'complete'), 'synchronization failure')
        assert not target.exists() and not list(directory.glob('.neon-wallpaper-*.tmp'))
        target.write_bytes(b'user file')
        rejected(lambda: host.publish(target, b'replacement'), 'File exists')
        assert target.read_bytes() == b'user file'
        target.unlink()
        synchronized = []
        original = os.fsync
        def sync(descriptor):
            synchronized.append('directory' if stat.S_ISDIR(os.fstat(descriptor).st_mode) else 'file')
            original(descriptor)
        with patch.object(host.os, 'fsync', sync):
            host.publish(target, b'complete')
        assert synchronized == ['file', 'directory', 'directory'], synchronized
        assert target.read_bytes() == b'complete'


def ambiguous_service_preserved():
    with installation() as (directory, state, calls, port):
        state['loaded'] = True
        config = host.agent_config(port)
        original = host.subprocess.run
        output = original(['/bin/launchctl', 'print', 'unused']).stdout
        variants = [
            output.replace(str(host.AGENT), '/different/agent.plist'),
            output.replace('\t\t--open-plash\n', '\t\t--unexpected\n'),
            output.replace('\targuments = {', '\tunknown = {'),
        ]
        for value in variants:
            with patch.object(host.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, value, '')):
                rejected(lambda: host.loaded_job(config), 'loaded service')
        with patch.object(host.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Permission denied')):
            rejected(lambda: host.loaded_job(config), 'Could not inspect')
        rejected(host.uninstall, 'loaded service')  # Loaded job exists but its plist is absent.
        assert not any(call[1] == 'bootout' for call in calls)
        actual = directory / 'saved.plist'
        actual.write_bytes(plistlib.dumps(config))
        host.AGENT.symlink_to(actual)
        rejected(lambda: host.install(port), 'symbolic link')
        rejected(host.uninstall, 'symbolic link')
        assert actual.read_bytes() == plistlib.dumps(config)


def missing_artwork_startup():
    with tempfile.TemporaryDirectory(prefix='neon-artwork-check-') as directory:
        with patch.object(host, 'ARTWORK', Path(directory) / 'absent.html'), patch.object(host.sys, 'argv', ['host.py']), patch.object(host, 'ThreadingHTTPServer') as server:
            rejected(host.main, 'absent.html')
            server.assert_not_called()


def missing_artwork_http():
    with tempfile.TemporaryDirectory(prefix='neon-http-check-') as directory:
        with patch.object(host, 'ARTWORK', Path(directory) / 'absent.html'):
            with host.ThreadingHTTPServer(('127.0.0.1', 0), host.Wallpaper) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    for method in ['GET', 'HEAD']:
                        connection = HTTPConnection('127.0.0.1', server.server_port, timeout=2)
                        connection.request(method, '/')
                        response = connection.getresponse()
                        assert response.status == 503
                        assert str(directory).encode() not in response.read()
                        connection.close()
                finally:
                    server.shutdown()
                    thread.join()


def readiness_verifies_content():
    with tempfile.TemporaryDirectory(prefix='neon-ready-check-') as directory:
        artwork = Path(directory) / 'index.html'
        artwork.write_bytes(b'expected wallpaper')
        with patch.object(host, 'ARTWORK', artwork), patch.object(host, 'loaded_job', return_value={'state': 'running'}):
            with host.ThreadingHTTPServer(('127.0.0.1', 0), host.Wallpaper) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    host.wait_ready(server.server_port, {}, artwork.read_bytes())
                    with patch.object(host.time, 'monotonic', side_effect=[0, 1, 6]), patch.object(host.time, 'sleep'):
                        rejected(lambda: host.wait_ready(server.server_port, {}, b'different content'), 'did not serve')
                    with patch.object(host, 'loaded_job', return_value={'state': 'waiting'}), patch.object(host, 'HTTPConnection') as connection, patch.object(host.time, 'monotonic', side_effect=[0, 1, 6]), patch.object(host.time, 'sleep'):
                        rejected(lambda: host.wait_ready(server.server_port, {}, artwork.read_bytes()), 'did not serve')
                        connection.assert_not_called()
                finally:
                    server.shutdown()
                    thread.join()


def stopped_port_is_reusable():
    with installation() as (directory, state, calls, port), patch.object(host, 'wait_ready'):
        with host.ThreadingHTTPServer(('127.0.0.1', port), host.Wallpaper) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
                    connection.sendall(b'GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
                    response = b''.join(iter(lambda: connection.recv(65536), b''))
                    assert response.startswith(b'HTTP/1.0 200')
                    # Read through the server's FIN before closing, leaving its port in TIME_WAIT.
            finally:
                server.shutdown()
                thread.join()
        host.install(port)
        assert state['loaded'] and host.AGENT.exists()


def active_listener_is_preserved():
    with installation() as (directory, state, calls, port):
        with host.ThreadingHTTPServer(('127.0.0.1', port), host.Wallpaper):
            try:
                host.install(port)
            except OSError as error:
                import errno
                assert error.errno == errno.EADDRINUSE
            else:
                raise AssertionError('Installer accepted an actively occupied port')
        assert not host.INSTALL.exists() and not host.AGENT.exists()
        assert not any(call[1] == 'bootstrap' for call in calls)


def late_install_changes_preserved():
    variants = ['host file', 'host symlink', 'saved plist', 'plist symlink', 'install symlink']
    for variant, loaded in [(variant, loaded) for variant in variants for loaded in [False, True]]:
        with installation() as (directory, state, calls, port), patch.object(host, 'wait_ready') as ready:
            config = host.agent_config(port)
            state['loaded'] = loaded
            if 'plist' in variant or loaded:
                host.AGENT.write_bytes(plistlib.dumps(config))
            foreign = directory / 'foreign'
            foreign.write_bytes(b'User-owned late content')
            original = host.subprocess.run
            changed = []
            def late_change(args, **kwargs):
                if args[:3] == ['/usr/bin/open', '-Ra', 'Plash']:
                    if variant == 'install symlink':
                        outside = directory / 'outside'
                        outside.mkdir()
                        host.INSTALL.symlink_to(outside, target_is_directory=True)
                        changed.append(host.INSTALL)
                    elif 'host' in variant:
                        host.INSTALL.mkdir()
                        target = host.INSTALL / 'host.py'
                        if variant == 'host symlink':
                            target.symlink_to(foreign)
                        else:
                            target.write_bytes(foreign.read_bytes())
                        changed.append(target)
                    else:
                        if variant == 'plist symlink':
                            host.AGENT.unlink()
                            host.AGENT.symlink_to(foreign)
                        else:
                            altered = dict(config, ProgramArguments=['/different/python', '/different/script'])
                            host.AGENT.write_bytes(plistlib.dumps(altered))
                        changed.append(host.AGENT)
                return original(args, **kwargs)
            with patch.object(host.subprocess, 'run', side_effect=late_change):
                try:
                    host.install(port)
                except (ValueError, OSError):
                    pass
                else:
                    raise AssertionError('Late ' + variant + ' reached installation success')
            assert not any(call[1] == 'bootstrap' for call in calls), variant
            ready.assert_not_called()
            assert changed[0].exists() and foreign.read_bytes() == b'User-owned late content'
            if variant.endswith('symlink'):
                assert changed[0].is_symlink()
                if variant == 'install symlink':
                    assert list(changed[0].iterdir()) == [], 'Published assets through a changed install directory'
            elif variant == 'host file':
                assert changed[0].read_bytes() == foreign.read_bytes()
            else:
                assert plistlib.loads(changed[0].read_bytes())['ProgramArguments'] == ['/different/python', '/different/script']


def changes_during_publication_preserved():
    for variant in ['host.py', 'index.html', 'extra.txt', 'missing artwork', 'reformatted plist']:
        with installation() as (directory, state, calls, port), patch.object(host, 'wait_ready') as ready:
            original = host.publish
            edited = b'Late user edit after assets were published'
            def changed_after_publication(path, content):
                original(path, content)
                if path == host.AGENT:
                    if variant == 'reformatted plist':
                        host.AGENT.write_bytes(content + b'\n')
                    elif variant == 'missing artwork':
                        (host.INSTALL / 'index.html').unlink()
                    else:
                        (host.INSTALL / variant).write_bytes(edited)
            with patch.object(host, 'publish', side_effect=changed_after_publication):
                message = 'Service file changed' if variant == 'reformatted plist' else 'Changed install files'
                rejected(lambda: host.install(port), message)
            assert not any(call[1] == 'bootstrap' for call in calls)
            ready.assert_not_called()
            if variant == 'reformatted plist':
                assert host.AGENT.read_bytes() == plistlib.dumps(host.agent_config(port)) + b'\n'
            elif variant == 'missing artwork':
                assert not (host.INSTALL / 'index.html').exists()
            else:
                assert (host.INSTALL / variant).read_bytes() == edited


def replacement_during_uninstall_preserved():
    for variant in ['edited', 'identical replacement', 'in-place edit', 'reformatted', 'symlink']:
        with installation() as (directory, state, calls, port):
            config = host.agent_config(port)
            host.AGENT.write_bytes(plistlib.dumps(config))
            state['loaded'] = True
            replacement = directory / 'replacement.plist'
            content = plistlib.dumps(dict(config, ThrottleInterval=60) if variant in ['edited', 'in-place edit'] else config)
            if variant == 'reformatted':
                content += b'\n'
            replacement.write_bytes(content)
            original = host.subprocess.run
            def replace_during_stop(args, **kwargs):
                if args[1] == 'bootout':
                    if variant == 'symlink':
                        host.AGENT.unlink()
                        host.AGENT.symlink_to(replacement)
                    elif variant in ['in-place edit', 'reformatted']:
                        host.AGENT.write_bytes(content)
                    else:
                        os.replace(replacement, host.AGENT)
                return original(args, **kwargs)
            with patch.object(host.subprocess, 'run', side_effect=replace_during_stop):
                try:
                    host.uninstall()
                except (ValueError, OSError):
                    pass
                else:
                    raise AssertionError('Uninstall removed a late ' + variant + ' plist')
            assert host.AGENT.read_bytes() == content and not state['loaded']
            assert any(call[1] == 'bootout' for call in calls)
            if variant == 'symlink':
                assert host.AGENT.is_symlink() and replacement.read_bytes() == content


if __name__ == '__main__':
    failures = []
    for check in [missing_loaded_artwork, foreign_job_preserved, malformed_plist_preserved,
                  partial_publication, symlink_install_preserved, lifecycle_and_durability,
                  publication_does_not_clobber, ambiguous_service_preserved,
                  missing_artwork_startup, missing_artwork_http, readiness_verifies_content,
                  stopped_port_is_reusable, active_listener_is_preserved,
                  late_install_changes_preserved, changes_during_publication_preserved,
                  replacement_during_uninstall_preserved]:
        try:
            check()
            print('PASS:', check.__name__)
        except Exception as error:
            failures.append(check.__name__)
            print('FAIL:', check.__name__, type(error).__name__, str(error))
    assert not failures, failures
