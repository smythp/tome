
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
from tome import App


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


def process_exists(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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
