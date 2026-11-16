"""Buffer invariants and real terminal sessions; no third-party dependencies."""
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "fmedit"


class BufferTests(unittest.TestCase):
    def run_bash(self, script):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", "-c", '''
source "$1"
cd "$2" || exit 1
eq() { [[ $1 == "$2" ]] || { printf 'expected <%s>, got <%s>\\n' "$2" "$1" >&2; exit 1; }; }
ok() { "$@" || { printf 'failed: %s\\n' "$*" >&2; exit 1; }; }
z_reset
''' + script, "test", str(EDITOR), directory],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_english_help_and_invalid_option(self):
        help_result = subprocess.run([str(EDITOR), "--help"], capture_output=True, text=True, check=True)
        self.assertIn("Usage: fmedit", help_result.stdout)
        self.assertIn("F2 save", help_result.stdout)
        invalid = subprocess.run([str(EDITOR), "--unknown"], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("Unknown option:", invalid.stderr)

    def test_edit_selection_history(self):
        self.run_bash('''
z_insert $'uno\ndue'
pos=3; z_insert '!'
eq "$text" $'uno!\ndue'
z_undo; eq "$text" $'uno\ndue'
z_redo; eq "$text" $'uno!\ndue'
anchor=1; pos=6; z_copy; eq "$clipboard" $'no!\nd'
z_cut; eq "$text" 'uue'
z_insert "$clipboard"; eq "$text" $'uno!\ndue'
z_undo; z_insert X; eq "${#redo_text[@]}" 0
''')

    def test_movement_and_deletion(self):
        self.run_bash('''
text=$'abcdef\nx\nabcdef'; pos=5
z_move down; eq "$pos" 8
z_move down; eq "$pos" 14
z_move home; eq "$pos" 9
z_backspace; eq "$text" $'abcdef\nxabcdef'; eq "$pos" 8
z_undo; eq "$text" $'abcdef\nx\nabcdef'
pos=6; z_delete; eq "$text" $'abcdefx\nabcdef'
z_move top; z_move right 1; z_insert Z
eq "$text" $'Zbcdefx\nabcdef'
''')

    def test_literal_search_and_wrap(self):
        self.run_bash('''
text='a [*] b [*]'; pos=0
ok z_find '[*]' 0; eq "$pos" 2; eq "$anchor" 5
ok z_find '[*]'; eq "$pos" 8
ok z_find '[*]'; eq "$pos" 2
if z_find missing; then exit 1; fi
eq "$pos" 2
''')

    def test_exact_file_roundtrip(self):
        self.run_bash('''
for value in '' abc $'abc\n' $'abc\n\n' $'uno\r\ndue\r\n' 'caffè'; do
    printf '%s' "$value" > original
    ok z_load original; eq "$text" "$value"
    file=copy; ok z_save; ok cmp original copy
done
printf 'abc\\0def' > binary
if z_load binary; then exit 1; fi
''')

    def test_save_permissions_symlink_and_failure(self):
        self.run_bash('''
printf old > original; chmod 640 original; ln -s original link
ok z_load link; z_insert new; ok z_save
ok test -L link
eq "$(cat original)" newold
eq "$(stat -c %a original)" 640
file=new; ok z_save; eq "$(stat -c %a new)" 600
file=missing/path; z_insert X
if z_save 2>/dev/null; then exit 1; fi
eq "$saved" newold; eq "$text" newXold
file=.; if z_save; then exit 1; fi
''')

    def test_large_buffer_navigation_and_render(self):
        self.run_bash(r'''
# No external commands in indexing, movement, editing or rendering.
PATH=/nonexistent
printf -v text 'abcdefghi\n%.0s' {1..40000}
saved=$text
exec 3>/dev/null
z_move bottom; z_render
z_move up; z_render
z_insert X; z_render
z_undo; z_render
z_redo; z_render
z_location
eq "$row" 39999
eq "$column" 1
''')

    def test_locations_after_edits_and_history(self):
        self.run_bash(r'''
check_locations() {
    local expected_row=0 expected_column=0 p row column line_start line_end tail
    for ((p=0; p<=${#text}; p++)); do
        pos=$p; z_location
        eq "$row" "$expected_row"; eq "$column" "$expected_column"
        eq "$line_start" "$((p-expected_column))"
        tail=${text:p}; tail=${tail%%$'\n'*}
        eq "$line_end" "$((p+${#tail}))"
        if [[ ${text:p:1} == $'\n' ]]; then
            ((expected_row+=1)); expected_column=0
        else ((expected_column+=1)); fi
    done
}
for text in '' abc $'\n' $'a\n\n' $'caffè\tX\r\n猫\nend'; do
    check_locations
    pos=0; z_insert $'nuova\nriga\n'; check_locations
    anchor=1; pos=$((${#text}-1)); z_insert X; check_locations
    z_undo; check_locations; z_redo; check_locations
done
''')

    def test_history_stores_edits_and_restores_cursor(self):
        self.run_bash(r'''
text=$'caffè\n猫\n'; saved=$text
pos=2; anchor=7; z_insert $'X\nY'
eq "${undo_text[0]}" $'ffè\n猫'
eq "${undo_value[0]}" $'X\nY'
pos=0; z_undo; eq "$text" "$saved"; eq "$pos" 2
z_redo; eq "$text" $'caX\nY\n'; eq "$pos" 0
z_undo; z_insert '!'; eq "${#redo_text[@]}" 0
''')

    def test_history_limit(self):
        self.run_bash('''
Z_HISTORY_LIMIT=3
for value in a b c d e; do z_insert "$value"; done
eq "${#undo_text[@]}" 3
z_undo; z_undo; z_undo; z_undo
eq "$text" ab
z_redo; z_redo; z_redo; eq "$text" abcde
''')


class Terminal:
    def __init__(self, *args):
        state_read, state_write = os.pipe()
        self.pid, self.master = pty.fork()
        if self.pid == 0:
            os.close(state_read)
            os.write(state_write, json.dumps(termios.tcgetattr(0), default=lambda x: list(x)).encode())
            os.close(state_write)
            os.execvpe("bash", ["bash", str(EDITOR), *map(str, args)], {**os.environ, "TERM": "xterm-256color", "LC_ALL": "C.UTF-8"})
        os.close(state_write)
        self.initial = json.loads(os.read(state_read, 8192))
        os.close(state_read)
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        self.output = b""
        self.status = None
        self.until(b"Ctrl+S: save")

    def drain(self, timeout=0.05):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([self.master], [], [], max(0, deadline-time.monotonic()))[0]:
                try:
                    chunk = os.read(self.master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                self.output += chunk

    def until(self, marker, timeout=4):
        deadline = time.monotonic() + timeout
        while marker not in self.output and time.monotonic() < deadline:
            self.drain()
        if marker not in self.output:
            raise AssertionError(f"Missing {marker!r}, terminal output: {self.output[-2000:]!r}")

    def send(self, data):
        os.write(self.master, data)
        self.drain(0.1)

    def finish(self):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            self.drain()
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self.status = os.waitstatus_to_exitcode(status)
                return self.status
        raise AssertionError("Editor did not exit")

    def assert_restored(self, test):
        current = json.loads(json.dumps(termios.tcgetattr(self.master), default=lambda x: list(x)))
        test.assertEqual(current, self.initial)
        test.assertIn(b"\x1b[?2004l", self.output)
        test.assertIn(b"\x1b[?1049l", self.output)

    def close(self):
        if self.status is None:
            try:
                os.kill(self.pid, signal.SIGKILL)
                os.waitpid(self.pid, 0)
            except ProcessLookupError:
                pass
        os.close(self.master)


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "test.sh"

    def terminal(self, *args):
        terminal = Terminal(*args)
        self.addCleanup(terminal.close)
        return terminal

    def test_typing_keys_save_and_restore(self):
        terminal = self.terminal(self.path)
        terminal.send(b"ciao\rmondo")
        terminal.send(b"\x1b[H\x1b[3~M\x1b[F!")
        terminal.send(b"\x1bOQ")  # F2
        terminal.until(b"Saved")
        self.assertEqual(self.path.read_bytes(), b"ciao\nMondo!")
        terminal.send(b"\x11")
        self.assertEqual(terminal.finish(), 0)
        terminal.assert_restored(self)

    def test_large_file_edit_history_and_save(self):
        original = "caffè\tuno\r\n".encode() * 10000
        self.path.write_bytes(original)
        terminal = self.terminal(self.path)
        terminal.send(b"\x1b[1;5F" + "猫".encode() + b"\x1a\x19")
        terminal.send(b"\x1b[1;5H!\x1b[21~")
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_bytes(), b"!" + original + "猫".encode())
        terminal.assert_restored(self)

    def test_paste_is_one_undo_and_preserves_control_bytes(self):
        terminal = self.terminal(self.path)
        terminal.send(b"\x1b[200~uno\r\ndue\x13\x11\x1b[201~")
        terminal.send(b"\x1a\x19")  # undo then redo the whole paste
        terminal.send(b"\x1b[21~")  # F10
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_bytes(), b"uno\ndue\x13\x11")
        terminal.assert_restored(self)

    def test_selection_search_copy_paste(self):
        self.path.write_bytes(b"uno due uno")
        terminal = self.terminal(self.path)
        terminal.send(b"\x06due\r")
        terminal.send(b"\x03\x1b[1;5F\x16")
        terminal.send(b"\x1b[1;5H\x1b[1;2C\x18")
        terminal.send(b"\x1b[21~")
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_bytes(), b"no due unodue")

    def test_quit_cancel_save_as_and_empty_backspace(self):
        terminal = self.terminal()
        terminal.send(b"test\x11")
        terminal.until(b"Unsaved changes")
        terminal.send(b"\r")  # cancel quitting
        terminal.send(b"\x13")
        terminal.until(b"Save as:")
        terminal.send(b"\x7f" + str(self.path).encode() + b"\r")
        terminal.until(b"Saved")
        terminal.send(b"\x11")
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_bytes(), b"test")

    def test_english_overwrite_confirmation_and_quit_save(self):
        self.path.write_bytes(b"original")
        terminal = self.terminal()
        terminal.send(b"replacement\x11")
        terminal.until(b"Unsaved changes: (s)ave / (d)iscard")
        terminal.send(b"s\r")
        terminal.until(b"Save as:")
        terminal.send(str(self.path).encode() + b"\r")
        terminal.until(b"Overwrite? (y/N):")
        terminal.send(b"\r")
        self.assertEqual(self.path.read_bytes(), b"original")
        terminal.send(b"\x11s\r")
        terminal.send(str(self.path).encode() + b"\r")
        terminal.send(b"y\r")
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_bytes(), b"replacement")
        terminal.assert_restored(self)

    def test_discard_and_signal_restore(self):
        self.path.write_bytes(b"originale")
        terminal = self.terminal(self.path)
        terminal.send(b"X\x11d\r")
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_bytes(), b"originale")
        terminal.assert_restored(self)
        terminal = self.terminal(self.path)
        os.kill(terminal.pid, signal.SIGTERM)
        self.assertEqual(terminal.finish(), 143)
        terminal.assert_restored(self)

    def test_terminal_escape_in_file_is_not_executed(self):
        payload = b"\x1b]2;untrusted-title\x07"
        self.path.write_bytes(payload)
        terminal = self.terminal(self.path)
        self.assertNotIn(payload, terminal.output)
        terminal.send(b"\x11")
        self.assertEqual(terminal.finish(), 0)

    def test_unicode_prompt_paste_and_resize(self):
        terminal = self.terminal()
        terminal.send("caffè più".encode())
        terminal.send(b"\x13")
        terminal.until(b"Save as:")
        terminal.send(b"\x1b[200~" + str(self.path).encode() + b"\x11\x13\x1b[201~\r")
        terminal.until(b"Saved")
        fcntl.ioctl(terminal.master, termios.TIOCSWINSZ, struct.pack("HHHH", 15, 40, 0, 0))
        terminal.send(b"\x11")
        self.assertEqual(terminal.finish(), 0)
        self.assertEqual(self.path.read_text(), "caffè più")
        terminal.assert_restored(self)


if __name__ == "__main__":
    unittest.main()
