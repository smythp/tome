
'''Lifecycle and headless-safety tests for tome.py.'''

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from listener import EventType, KeyEvent, MockListener, NoListener, PynputListener
from tome import App, DEFAULT_DB_PATH, get_default_db


ROOT = Path(__file__).resolve().parent


def headless_env(**updates):
    env = os.environ.copy()
    env.pop('DISPLAY', None)
    env.update(updates)
    return env


def run_python(code, env=None, timeout=10):
    return subprocess.run(
        [sys.executable, '-c', textwrap.dedent(code)],
        cwd=ROOT,
        env=headless_env(**(env or {})),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def q_event():
    return KeyEvent(
        char='q',
        key=None,
        modifiers=frozenset(),
        event_type=EventType.PRESS,
    )


class SigtermDuringStartListener:
    def __init__(self, pid_file):
        self.pid_file = pid_file
        self.started = False
        self.stopped = False

    def start(self, callback):
        self.started = True
        wait_for_pid_file(self.pid_file)
        os.kill(os.getpid(), signal.SIGTERM)

    def stop(self):
        self.stopped = True


class CallbackDuringStartListener:
    def __init__(self):
        self.running = False

    def start(self, callback):
        self.running = True
        callback(q_event())

    def stop(self):
        self.running = False


class RecordingListener:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self, callback):
        self.started = True

    def stop(self):
        self.stopped = True


class GuardedSignalStream:
    def __init__(self):
        self.events = []
        self.in_write = False
        self.signal_handler = None
        self.triggered = False
        self.flushes_during_write = 0

    def write(self, text):
        if text == 'ready\n' and not self.triggered:
            self.triggered = True
            self.in_write = True
            self.events.append('write-entered')
            try:
                self.signal_handler(signal.SIGTERM, None)
            finally:
                self.events.append('write-unwound')
                self.in_write = False
        else:
            self.events.append(f'write:{text}')
        return len(text)

    def flush(self):
        self.events.append('flush')
        if self.in_write:
            self.flushes_during_write += 1
            raise RuntimeError('flush re-entered output')


class GuardedCleanupListener:
    def __init__(self, stream):
        self.stream = stream
        self.started = False
        self.stopped = False

    def start(self, callback):
        self.started = True
        self.stream.write('ready\n')

    def stop(self):
        self.stream.events.append('listener-stop')
        if self.stream.in_write:
            raise RuntimeError('listener cleanup re-entered output')
        self.stopped = True


class GuardedCleanupTeller:
    def __init__(self, stream):
        self.stream = stream
        self.spoken = []
        self.stopped = False

    def speak(self, text, speed=270, wait=False):
        self.spoken.append(text)

    def stop(self):
        self.stream.events.append('teller-stop')
        if self.stream.in_write:
            raise RuntimeError('teller cleanup re-entered output')
        self.stopped = True


class ShutdownOnSpeechTeller:
    def __init__(self, trigger):
        self.trigger = trigger
        self.spoken = []
        self.stopped = False
        self.app = None

    def speak(self, text, speed=270, wait=False):
        self.spoken.append(text)
        if text == self.trigger:
            self.app.request_shutdown()

    def stop(self):
        self.stopped = True


def process_exists(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_pid_file(pid_file):
    deadline = time.time() + 5
    while not pid_file.exists() and time.time() < deadline:
        time.sleep(0.01)
    if not pid_file.exists():
        raise AssertionError('fake espeak pid file was not created')


def read_pids(pid_file):
    if not pid_file.exists():
        return []
    pids = []
    for line in pid_file.read_text().splitlines():
        parts = line.split()
        if parts:
            pids.append(int(parts[0]))
    return pids


@pytest.fixture
def fake_espeak(tmp_path):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    pid_file = tmp_path / 'espeak-pids.txt'
    executable = bin_dir / 'espeak-ng'
    executable.write_text(
        textwrap.dedent(
            '''
            #!/usr/bin/env python3
            import os
            import signal
            import sys
            import time
            from pathlib import Path

            pid_file = Path(os.environ['FAKE_ESPEAK_PIDS'])
            text = sys.argv[-1] if len(sys.argv) > 1 else ''
            with pid_file.open('a') as handle:
                handle.write(f'{os.getpid()} {text}\\n')
                handle.flush()

            def terminate(signum, frame):
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, terminate)
            if text == 'quit':
                raise SystemExit(0)
            time.sleep(30)
            '''
        ).lstrip()
    )
    executable.chmod(0o755)
    env = {
        'PATH': f'{bin_dir}{os.pathsep}{os.environ.get("PATH", "")}',
        'FAKE_ESPEAK_PIDS': str(pid_file),
    }
    return env, pid_file


def test_headless_import_does_not_import_pynput():
    result = run_python(
        '''
        import sys
        import tempfile
        from pathlib import Path
        import listener
        import tome
        db_path = Path(tempfile.mkdtemp()) / 'lore.db'
        print('pynput' in sys.modules)
        print(type(tome.App(db_path=str(db_path), teller_mode='text').listener).__name__)
        '''
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['False', 'PynputListener']


def test_production_default_selects_pynput_listener(tmp_path):
    app = App(db_path=str(tmp_path / 'lore.db'), teller_mode='text')

    assert isinstance(app.listener, PynputListener)


def test_help_does_not_create_default_data_dir(tmp_path):
    result = subprocess.run(
        [sys.executable, 'tome.py', '--help'],
        cwd=ROOT,
        env=headless_env(HOME=str(tmp_path)),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert DEFAULT_DB_PATH in result.stdout
    assert not (tmp_path / '.tome').exists()


def test_default_db_path_is_home_tome_and_created_on_app_start(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    expected = tmp_path / '.tome' / 'lore.db'

    assert get_default_db() == str(expected)
    assert not expected.parent.exists()

    app = App(teller_mode='text', listener=NoListener())

    assert app.store.db_path == expected
    assert expected.parent.exists()


def test_mock_listener_end_to_end_quit_without_display(tmp_path, capsys):
    listener = MockListener()
    app = App(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=listener,
    )

    app.run(block=False)
    listener.inject(q_event())

    captured = capsys.readouterr()
    assert 'Tome of lore' in captured.out
    assert 'quit' in captured.out
    assert app.running is False
    assert listener.running is False


def test_no_listener_headless_path_starts_and_stops(tmp_path, capsys):
    app = App(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=NoListener(),
    )

    app.run(block=False)
    app.request_shutdown()

    captured = capsys.readouterr()
    assert 'Tome of lore' in captured.out
    assert app.running is False


def test_callback_shutdown_during_listener_start_is_not_resurrected(tmp_path, capsys):
    listener = CallbackDuringStartListener()
    app = App(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=listener,
    )

    app.run(block=False)

    captured = capsys.readouterr()
    assert 'Tome of lore' in captured.out
    assert 'quit' in captured.out
    assert app.running is False
    assert listener.running is False


def test_shutdown_during_mode_registration_aborts_remaining_startup(tmp_path):
    class ShutdownDuringRegisterApp(App):
        def _register_modes(self):
            super()._register_modes()
            self.request_shutdown()

    listener = RecordingListener()
    app = ShutdownDuringRegisterApp(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=listener,
    )

    app.run(block=False)

    assert app.running is False
    assert listener.started is False
    assert listener.stopped is True
    assert app.mode.current is None


def test_shutdown_during_initial_mode_announcement_aborts_remaining_startup(tmp_path):
    listener = RecordingListener()
    app = App(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=listener,
    )
    teller = ShutdownOnSpeechTeller('Read from tome')
    teller.app = app
    app.teller = teller
    app.mode._teller = teller

    app.run(block=False)

    assert teller.spoken == ['Read from tome']
    assert teller.stopped is True
    assert app.running is False
    assert listener.started is False
    assert listener.stopped is True


def test_sigterm_at_pre_listener_boundary_aborts_listener_start(tmp_path):
    class SigtermAtListenerBoundaryApp(App):
        def _start_listener(self):
            self._handle_signal(signal.SIGTERM, None)
            super()._start_listener()

    listener = RecordingListener()
    app = SigtermAtListenerBoundaryApp(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=listener,
    )

    app.run(block=True)

    assert app.running is False
    assert listener.started is False
    assert listener.stopped is True


def test_blocking_run_sigterm_defers_cleanup_until_output_unwinds(tmp_path, monkeypatch):
    stream = GuardedSignalStream()
    listener = GuardedCleanupListener(stream)
    app = App(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='text',
        listener=listener,
    )
    teller = GuardedCleanupTeller(stream)
    app.teller = teller
    app.mode._teller = teller
    stream.signal_handler = app._handle_signal
    monkeypatch.setattr(sys, 'stdout', stream)

    app.run(block=True)

    assert listener.started is True
    assert listener.stopped is True
    assert teller.stopped is True
    assert app.running is False
    assert stream.flushes_during_write == 0
    assert stream.events.index('write-unwound') < stream.events.index('flush')
    assert stream.events.index('write-unwound') < stream.events.index('listener-stop')
    assert stream.events.index('write-unwound') < stream.events.index('teller-stop')


def test_redirected_text_output_survives_quit(tmp_path):
    result = run_python(
        f'''
        from listener import EventType, KeyEvent, MockListener
        from tome import App

        listener = MockListener()
        app = App(db_path={str(tmp_path / 'lore.db')!r}, teller_mode='text', listener=listener)
        app.run(block=False)
        listener.inject(KeyEvent(char='q', key=None, modifiers=frozenset(), event_type=EventType.PRESS))
        '''
    )

    assert result.returncode == 0, result.stderr
    assert 'Tome of lore' in result.stdout
    assert 'quit' in result.stdout


def test_normal_quit_reaps_tome_owned_espeak_children(tmp_path, fake_espeak):
    env, pid_file = fake_espeak
    result = run_python(
        f'''
        from listener import EventType, KeyEvent, MockListener
        from tome import App

        listener = MockListener()
        app = App(db_path={str(tmp_path / 'lore.db')!r}, teller_mode='espeak', listener=listener)
        app.run(block=False)
        listener.inject(KeyEvent(char='q', key=None, modifiers=frozenset(), event_type=EventType.PRESS))
        ''',
        env=env,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    pids = read_pids(pid_file)
    assert pids
    assert all(not process_exists(pid) for pid in pids)


def test_blocking_run_sigterm_during_listener_start_reaps_espeak(tmp_path, fake_espeak, monkeypatch):
    env, pid_file = fake_espeak
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    listener = SigtermDuringStartListener(pid_file)
    app = App(
        db_path=str(tmp_path / 'lore.db'),
        teller_mode='espeak',
        listener=listener,
    )

    app.run(block=True)

    assert listener.started is True
    assert listener.stopped is True
    assert app.running is False
    pids = read_pids(pid_file)
    assert pids
    assert all(not process_exists(pid) for pid in pids)


def test_sigterm_reaps_tome_owned_espeak_children(tmp_path, fake_espeak):
    env, pid_file = fake_espeak
    proc = subprocess.Popen(
        [
            sys.executable,
            '-c',
            textwrap.dedent(
                f'''
                import time
                from listener import NoListener
                from tome import App

                app = App(db_path={str(tmp_path / 'lore.db')!r}, teller_mode='espeak', listener=NoListener())
                app.run(block=False)
                app._install_signal_handlers()
                print('ready', flush=True)
                while app.running:
                    time.sleep(0.05)
                app._restore_signal_handlers()
                '''
            ),
        ],
        cwd=ROOT,
        env=headless_env(**env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert proc.stdout is not None
        assert proc.stdout.readline().strip() == 'ready'
        deadline = time.time() + 5
        while not pid_file.exists() and time.time() < deadline:
            time.sleep(0.05)
        os.kill(proc.pid, signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    assert proc.returncode == 0, stderr
    pids = read_pids(pid_file)
    assert pids
    assert all(not process_exists(pid) for pid in pids)


def run_blocking_sigterm_normal_loop(db_path):
    proc = subprocess.Popen(
        [
            sys.executable,
            '-c',
            textwrap.dedent(
                f'''
                from tome import App

                class ReadyListener:
                    def start(self, callback):
                        print('ready', flush=True)

                    def stop(self):
                        print('stopped', flush=True)

                app = App(db_path={str(db_path)!r}, teller_mode='text', listener=ReadyListener())
                app.run(block=True)
                print('done', flush=True)
                '''
            ),
        ],
        cwd=ROOT,
        env=headless_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert proc.stdout is not None
        lines = []
        deadline = time.time() + 5
        while time.time() < deadline:
            line = proc.stdout.readline()
            if line:
                lines.append(line.strip())
                if line.strip() == 'ready':
                    break
        assert 'ready' in lines
        os.kill(proc.pid, signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    all_stdout = '\n'.join(lines)
    if stdout:
        all_stdout = f'{all_stdout}\n{stdout}'
    assert proc.returncode == 0, stderr
    assert 'stopped' in all_stdout
    assert 'done' in all_stdout


def test_blocking_run_sigterm_during_normal_loop_exits_cleanly(tmp_path):
    for iteration in range(20):
        run_blocking_sigterm_normal_loop(tmp_path / f'lore-{iteration}.db')


def test_listener_start_failure_cleans_owned_startup_resources(tmp_path, fake_espeak):
    env, pid_file = fake_espeak
    result = run_python(
        f'''
        import os
        import time
        from pathlib import Path
        from tome import App

        class FailingStartListener:
            def __init__(self):
                self.stopped = False

            def start(self, callback):
                pid_file = Path(os.environ['FAKE_ESPEAK_PIDS'])
                deadline = time.time() + 5
                while not pid_file.exists() and time.time() < deadline:
                    time.sleep(0.01)
                raise RuntimeError('listener start failed')

            def stop(self):
                self.stopped = True

        listener = FailingStartListener()
        app = App(db_path={str(tmp_path / 'lore.db')!r}, teller_mode='espeak', listener=listener)
        try:
            app.run(block=False)
        except RuntimeError as exc:
            print(exc)
        print(app.running)
        print(listener.stopped)
        ''',
        env=env,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        'listener start failed',
        'False',
        'True',
    ]
    pids = read_pids(pid_file)
    assert pids
    assert all(not process_exists(pid) for pid in pids)
