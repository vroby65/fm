#!/usr/bin/env python3
"""Smoke test PTY; usa soltanto la libreria standard Python."""
from __future__ import annotations

import fcntl
import os
import pathlib
import pty
import subprocess
import struct
import tempfile
import termios
import time

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "fm")
F3 = b"\x1bOR"
F4 = b"\x1bOS"
F5 = b"\x1b[15~"
F6 = b"\x1b[17~"
F7 = b"\x1b[18~"
F8 = b"\x1b[19~"
F10 = b"\x1b[21~"
DOWN = b"\x1b[B"
UP = b"\x1b[A"
END = b"\x1b[F"
BACK = b"\x7f"
RIGHT = b"\x1b[C"
LEFT = b"\x1b[D"
ENTER = b"\r"


class Session:
    def __init__(self, cwd: pathlib.Path, cols: int = 96, env: dict[str, str] | None = None):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.environ["TERM"] = "xterm-256color"
            os.environ["LC_ALL"] = "C.UTF-8"
            os.environ.pop("NO_COLOR", None)
            os.environ.pop("ABFM_NO_COLOR", None)
            os.environ.pop("ABFM_ASCII", None)
            if env:
                os.environ.update(env)
            os.execl(SCRIPT, SCRIPT, str(cwd))
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 28, cols, 0, 0))
        os.set_blocking(self.fd, False)
        self.output = bytearray()
        self.drain(0.3)

    def drain(self, pause: float = 0.07):
        deadline = time.monotonic() + pause
        while time.monotonic() < deadline:
            try:
                data = os.read(self.fd, 65536)
                if data:
                    self.output.extend(data)
                    deadline = min(deadline + 0.005, time.monotonic() + 0.025)
                else:
                    break
            except BlockingIOError:
                time.sleep(0.005)
            except OSError:
                break

    def key(self, value: bytes):
        os.write(self.fd, value)
        self.drain()

    def mouse(self, button: int, x: int, y: int, release: bool = False):
        suffix = 'm' if release else 'M'
        self.key(f"\x1b[<{button};{x};{y}{suffix}".encode())

    def type(self, text: str):
        for ch in text.encode("utf-8"):
            self.key(bytes([ch]))

    def close(self):
        self.key(b"q")
        for _ in range(50):
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                os.close(self.fd)
                assert os.waitstatus_to_exitcode(status) == 0, f"Programma terminato con {status}"
                return
            time.sleep(0.02)
        os.kill(self.pid, 15)
        os.waitpid(self.pid, 0)
        os.close(self.fd)
        raise AssertionError("Il file manager non termina")


def fixture(root: pathlib.Path):
    source = root / "src"
    dest = root / "dest"
    source.mkdir()
    dest.mkdir()
    (source / "tree").mkdir()
    (source / "tree" / "deep.txt").write_text("profondo")
    (source / "alpha.txt").write_text("alpha")
    (source / "delete.txt").write_text("cancella")
    (source / "file space.txt").write_text("spazi")
    return source, dest


def test_copy_multiple():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        s.key(F3)        # tree/ (prima directory)
        s.key(DOWN)      # alpha.txt
        s.key(F3)
        s.key(F4)        # copia entrambi
        s.key(BACK)      # parent
        s.key(ENTER)     # dest (prima directory del parent)
        s.key(F6)
        s.close()
        assert (dst / "tree" / "deep.txt").read_text() == "profondo"
        assert (dst / "alpha.txt").read_text() == "alpha"
        assert (src / "alpha.txt").exists(), "Copia non deve spostare"


def test_cut_move():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        s.key(DOWN)      # alpha.txt
        s.key(F5)
        s.key(BACK)
        s.key(ENTER)
        s.key(F6)
        s.close()
        assert not (src / "alpha.txt").exists()
        assert (dst / "alpha.txt").read_text() == "alpha"


def test_mkdir_and_delete():
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp)
        s = Session(target)
        s.key(F7)
        s.type("nuova")
        s.key(ENTER)
        assert (target / "nuova").is_dir(), "F7 non ha creato la directory"
        s.key(END)
        s.key(F8)
        s.type("s")
        s.key(ENTER)
        s.close()
        assert not (target / "nuova").exists(), "F8 non ha rimosso la directory"


def test_no_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        (dst / "alpha.txt").write_text("preesistente")
        s = Session(src)
        s.key(DOWN)
        s.key(F4)
        s.key(BACK)
        s.key(ENTER)
        s.key(F6)
        s.close()
        assert (dst / "alpha.txt").read_text() == "preesistente", "File sovrascritto!"


def test_filename_with_spaces():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        s.key(END)       # file space.txt
        s.key(F4)
        s.key(BACK)
        s.key(ENTER)
        s.key(F6)
        s.close()
        assert (dst / "file space.txt").read_text() == "spazi"


def test_delete_cancelled():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "keep.txt").write_text("intatto")
        s = Session(root)
        s.key(F8)
        s.type("n")
        s.key(ENTER)
        s.close()
        assert (root / "keep.txt").read_text() == "intatto"


def test_no_copy_into_self():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "folder").mkdir()
        s = Session(root)
        s.key(F4)        # copia folder
        s.key(ENTER)     # entra in folder
        s.key(F6)        # non deve fare folder/folder
        s.close()
        assert not (root / "folder" / "folder").exists()


def test_mouse_double_click_opens_folder():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "folder").mkdir()
        s = Session(root)
        try:
            assert b"\x1b[?1000h\x1b[?1006h" in s.output, "Mouse non attivato"
            assert "┌".encode() in s.output, "Cornici Unicode mancanti"
            assert b"\x1b[38;5;252;48;5;240m" in s.output, "Palette classica MC mancante"
            s.mouse(0, 10, 5)
            s.mouse(0, 10, 5)
            s.key(F7)
            s.type("mouse-created")
            s.key(ENTER)
            assert (root / "folder" / "mouse-created").is_dir(), "Doppio click non apre"
        finally:
            s.close()


def test_mouse_button_mkdir():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        s = Session(root)
        try:
            s.mouse(0, 60, 25)
            s.type("button-made")
            s.key(ENTER)
            assert (root / "button-made").is_dir(), "F7 via mouse non funziona"
        finally:
            s.close()


def test_mouse_prompt_ignores_click():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        s = Session(root)
        try:
            s.key(F7)
            s.mouse(0, 10, 8)
            s.type("clean-name")
            s.key(ENTER)
            assert (root / "clean-name").is_dir(), "Mouse ha corrotto il prompt"
        finally:
            s.close()


def test_mouse_mark_copy():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        try:
            s.mouse(0, 3, 6)
            s.key(F4)
            s.key(BACK)
            s.key(ENTER)
            s.key(F6)
            assert (dst / "alpha.txt").read_text() == "alpha", "Selezione mouse non funziona"
        finally:
            s.close()


def test_mouse_compact_bar_and_wheel():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for i in range(30):
            (root / f"d{i:02d}").mkdir()
        s = Session(root, cols=40)
        try:
            s.mouse(0, 27, 25)
            s.type("small-window")
            s.key(ENTER)
            assert (root / "small-window").is_dir(), "F7 non cliccabile su finestra stretta"
            for _ in range(28):
                s.mouse(65, 10, 10)
            assert b"d25" in s.output[-2500:], "Rotella non porta ai file piu' in basso"
        finally:
            s.close()



def test_gray_palette_and_highlighting():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "dir").mkdir()
        (root / "regular.txt").write_text("text")
        exe = root / "executable.sh"
        exe.write_text("#!/bin/sh\nexit 0\n")
        exe.chmod(0o755)
        (root / "shortcut").symlink_to("regular.txt")
        (root / "broken").symlink_to("does-not-exist")
        s = Session(root)
        try:
            out = bytes(s.output)
            assert b"\x1b[38;5;252;48;5;240m" in out, "Sfondo blu / grigio mancante"
            assert b"\x1b[38;5;232;48;5;250m" in out, "Selezione nero / ciano mancante"
            assert b"\x1b[1;38;5;255;48;5;240m" in out, "Directory bianche mancanti"
            assert b"\x1b[38;5;120;48;5;240m" in out, "Eseguibili verdi mancanti"
            assert b"\x1b[38;5;117;48;5;240m" in out, "Link ciano mancanti"
            assert b"\x1b[38;5;210;48;5;240m" in out, "Link interrotti rossi mancanti"
            assert b"\x1b[38;5;254;48;5;236m" in out, "Barra nera comandi mancante"
            s.key(F3)
            assert b"\x1b[1;38;5;130;48;5;250m" in s.output, "Selezione marcata gialla mancante"
        finally:
            s.close()


def test_no_color_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        s = Session(pathlib.Path(tmp), env={"ABFM_NO_COLOR": "1"})
        try:
            assert b"\x1b[38;5;252;48;5;240m" not in s.output
            assert b"\x1b[38;5;232;48;5;250m" not in s.output
            assert b"\x1b[38;5;254;48;5;236m" not in s.output
            assert "┌".encode() in s.output
        finally:
            s.close()


def test_ascii_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        s = Session(pathlib.Path(tmp), env={"ABFM_ASCII": "1"})
        try:
            assert b"+" + b"-" * 94 + b"+" in s.output
            assert "┌".encode() not in s.output
        finally:
            s.close()


def test_hidden_and_mc_directory_prefix():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "folder").mkdir()
        (root / ".hiddenfile").write_text("secret")
        (root / ".hiddendir").mkdir()
        session = Session(root)
        try:
            screen = bytes(session.output)
            assert b"/.hiddendir" in screen, "Directory nascosta non visibile o senza prefisso /"
            assert b"/folder" in screen, "Le directory devono iniziare con /"
            assert b".hiddenfile" in screen, "File nascosti non visibili di default"
            assert b"folder/" not in screen, "La barra delle directory e' dalla parte sbagliata"
        finally:
            session.close()


def test_mouse_exact_columns_and_rows():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        session = Session(src)
        try:
            # Y=6 corrisponde ad alpha.txt, dopo ../ e tree.
            # X=4 e' il prefisso, non il marcatore * (solo X=3).
            session.mouse(0, 4, 6)
            session.mouse(0, 1, 5)  # bordo: non deve cambiare riga
            session.key(F4)
            session.key(BACK)
            session.key(ENTER)
            session.key(F6)
            assert (dst / "alpha.txt").is_file(), "Hitbox mouse sfalsata"
            assert not (dst / "tree").exists(), "Click sul bordo ha cambiato riga"
        finally:
            session.close()


def test_no_flicker_on_cursor_navigation():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for n in range(6):
            (root / f"f{n}.txt").write_text("v")
        session = Session(root)
        try:
            initial = bytes(session.output)
            assert initial.count(b"\x1b[2J") == 0, "Clear-screen iniziale superfluo"
            assert initial.endswith(b"\x1b[0m"), "CRLF all'ultima riga del terminale"
            length = len(session.output)
            session.key(DOWN)
            fresh = bytes(session.output[length:])
            assert b"\x1b[2J" not in fresh, "Sfarfallio: clear-screen a ogni tasto"
            assert "┌".encode() not in fresh, "Ridisegno completo ad ogni movimento"
            assert len(fresh) < 900, "Ridisegno troppo esteso per un solo movimento"
        finally:
            session.close()




def test_lynx_arrows_enter_and_back():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "a_directory").mkdir()
        (root / "a_directory" / "inside.txt").write_text("ok")
        (root / "b_directory").mkdir()
        session = Session(root)
        try:
            session.key(RIGHT)
            assert b"inside.txt" in session.output, "Destra non apre la directory"
            session.key(LEFT)
            assert b"/b_directory" in session.output, "Sinistra non torna al padre"
            session.key(DOWN)
            session.key(RIGHT)
            assert b"/b_directory" in session.output
            session.key(LEFT)
            assert b"/a_directory" in session.output
        finally:
            session.close()


def test_millis_italian_decimal_comma():
    source = pathlib.Path(SCRIPT).read_text()
    start = source.index("now_millis() {\n")
    end = source.index("\nreload() {", start)
    func = source[start:end]
    for stamp, expected in (("1793001314,090467", "1793001314090"),
                            ("1793001314.090467", "1793001314090"),
                            ("1793001314,009467", "1793001314009")):
        shell = "unset EPOCHREALTIME; EPOCHREALTIME='" + stamp + "'\n" + func + "\nnow_millis\n"
        result = subprocess.run(["bash", "-c", shell], capture_output=True, text=True, check=True)
        assert result.stdout.strip() == expected, (stamp, result.stdout, result.stderr)
        assert not result.stderr


def test_repeated_clicks_no_crash():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "afile.txt").write_text("test")
        (root / "adir").mkdir()
        session = Session(root)
        try:
            for _ in range(10):
                session.mouse(0, 10, 6)
            session.key(LEFT)
            assert b"valore troppo grande" not in session.output
            assert b"value too great" not in session.output
        finally:
            session.close()



def test_execute_interactive_script():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        runner = root / "run me.sh"
        marker = root / "result.txt"
        runner.write_text("#!/bin/sh\nprintf 'Type a word: '\nread value\nprintf '%s' \"$value\" > result.txt\n")
        runner.chmod(0o755)
        session = Session(root)
        try:
            session.key(ENTER)
            assert b"Type a word:" in session.output, "Non avvia lo script"
            session.type("working")
            session.key(ENTER)
            session.key(ENTER)  # conferma ritorno al TUI
            assert marker.read_text() == "working", "stdin del processo non interattivo"
            assert b"codice 0" in session.output, "Terminale non ripristinato"
        finally:
            session.close()


def test_ctrl_x_chmod():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        f = root / "plain.sh"
        f.write_text("#!/bin/sh\nexit 0\n")
        f.chmod(0o644)
        session = Session(root)
        try:
            session.key(b"\x18c")
            session.type("755")
            session.key(ENTER)
            assert f.stat().st_mode & 0o777 == 0o755, "chmod non applicato"
            session.key(b"\x18c")
            session.type("999")
            session.key(ENTER)
            assert f.stat().st_mode & 0o777 == 0o755, "chmod invalido applicato"
        finally:
            session.close()


def test_ctrl_x_symlink():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "origin.txt").write_text("source")
        session = Session(root)
        try:
            session.key(b"\x18s")
            session.type("alias.txt")
            session.key(ENTER)
            target = root / "alias.txt"
            assert target.is_symlink(), "link simbolico non creato"
            assert os.readlink(target) == str(root / "origin.txt"), "link deve essere assoluto"
            assert target.read_text() == "source"
            # Spostando il link, il target assoluto deve restare risolvibile.
            relocated_dir = root / "dest"
            relocated_dir.mkdir()
            relocated = relocated_dir / "moved-link.txt"
            relocated.symlink_to(os.readlink(target))
            assert relocated.read_text() == "source", "link assoluto rotto dopo spostamento"
            session.key(b"\x18s")
            session.type("alias.txt")
            session.key(ENTER)
            assert target.is_symlink(), "link esistente sovrascritto"
        finally:
            session.close()


def test_ctrl_x_chown_nonprivileged():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        file = root / "owned.txt"
        file.write_text("owned")
        session = Session(root)
        try:
            session.key(b"\x18o")
            session.type(f"{os.getuid()}:{os.getgid()}")
            session.key(ENTER)
            assert file.is_file(), "chown ha modificato il contenuto"
            assert file.stat().st_uid == os.getuid()
            assert b"chown " in session.output, "Non e' stato eseguito chown"
        finally:
            session.close()




def test_f10_quits_and_restores_terminal():
    with tempfile.TemporaryDirectory() as tmp:
        session = Session(pathlib.Path(tmp))
        session.key(F10)
        for _ in range(60):
            pid, status = os.waitpid(session.pid, os.WNOHANG)
            if pid:
                assert os.waitstatus_to_exitcode(status) == 0
                assert b"\x1b[?1000l\x1b[?1006l" in session.output
                os.close(session.fd)
                break
            time.sleep(0.02)
        else:
            os.kill(session.pid, 15)
            os.waitpid(session.pid, 0)
            os.close(session.fd)
            raise AssertionError("F10 non ha terminato il programma")


def test_chmod_dialog_toggle_and_cancel():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        f = root / "mode.txt"
        f.write_text("data")
        f.chmod(0o644)
        session = Session(root)
        try:
            session.key(b"\x18c")
            assert b"Permessi (chmod)" in session.output
            session.key(DOWN)   # gruppo / lettura
            session.key(RIGHT)  # gruppo / scrittura
            session.key(b" ")   # attiva il permesso scrittura al gruppo
            session.key(ENTER)
            assert f.stat().st_mode & 0o777 == 0o664
            session.key(b"\x18c")
            session.type("777")
            session.key(b"\x1b")
            assert f.stat().st_mode & 0o777 == 0o664, "Esc non annulla"
        finally:
            session.close()


def test_chown_dialog_group_tab_navigation():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        f = root / "owned.txt"
        f.write_text("data")
        session = Session(root)
        try:
            session.key(b"\x18o")
            assert b"Proprietario e gruppo" in session.output
            session.type(str(os.getuid()))
            session.key(b"\t")
            session.type(str(os.getgid()))
            session.key(ENTER)
            assert f.stat().st_uid == os.getuid()
            assert f.stat().st_gid == os.getgid()
            assert b"chown " in session.output
        finally:
            session.close()



if __name__ == "__main__":
    tests = [test_copy_multiple, test_cut_move, test_mkdir_and_delete, test_no_overwrite,
             test_filename_with_spaces, test_delete_cancelled, test_no_copy_into_self,
             test_mouse_double_click_opens_folder, test_mouse_button_mkdir,
             test_mouse_prompt_ignores_click, test_mouse_mark_copy,
             test_mouse_compact_bar_and_wheel, test_gray_palette_and_highlighting,
             test_no_color_fallback, test_ascii_fallback,
             test_hidden_and_mc_directory_prefix, test_mouse_exact_columns_and_rows,
             test_no_flicker_on_cursor_navigation,
             test_lynx_arrows_enter_and_back, test_millis_italian_decimal_comma,
             test_repeated_clicks_no_crash, test_execute_interactive_script,
             test_ctrl_x_chmod, test_ctrl_x_symlink, test_ctrl_x_chown_nonprivileged,
             test_f10_quits_and_restores_terminal, test_chmod_dialog_toggle_and_cancel,
             test_chown_dialog_group_tab_navigation]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"{len(tests)} test superati")
