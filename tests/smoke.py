#!/usr/bin/env python3
"""Smoke test PTY; usa soltanto la libreria standard Python."""
from __future__ import annotations

import fcntl
import os
import pathlib
import pty
import signal
import subprocess
import struct
import tempfile
import termios
import time

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "fm")
F2 = b"\x1bOQ"
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

    def resize(self, cols: int):
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 28, cols, 0, 0))
        os.kill(self.pid, signal.SIGWINCH)
        self.drain(0.2)

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
        s.key(F5)
        s.type(str(dst))
        s.key(ENTER)
        s.close()
        assert (dst / "tree" / "deep.txt").read_text() == "profondo"
        assert (dst / "alpha.txt").read_text() == "alpha"
        assert (src / "alpha.txt").exists(), "Copia non deve spostare"


def test_cut_move():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        s.key(DOWN)      # alpha.txt
        s.key(F6)
        s.type(str(dst))
        s.key(ENTER)
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
        s.key(F5)
        s.type(str(dst))
        s.key(ENTER)
        s.close()
        assert (dst / "alpha.txt").read_text() == "preesistente", "File sovrascritto!"


def test_filename_with_spaces():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        s.key(END)       # file space.txt
        s.key(F5)
        s.type(str(dst))
        s.key(ENTER)
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
        s.key(F5)
        s.type("folder")
        s.key(ENTER)
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
            s.mouse(0, 33, 25)
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
            s.key(F5)
            s.type(str(dst))
            s.key(ENTER)
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
            s.mouse(0, 23, 25)
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
            session.key(F5)
            session.type(str(dst))
            session.key(ENTER)
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


def test_ctrl_s_symlink():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "origin.txt").write_text("source")
        session = Session(root)
        try:
            session.key(b"\x13")
            target = root / "origin.txt.lnk"
            assert target.is_symlink(), "link simbolico non creato"
            assert os.readlink(target) == str(root / "origin.txt"), "link deve essere assoluto"
            assert target.read_text() == "source"
            # Spostando il link, il target assoluto deve restare risolvibile.
            relocated_dir = root / "dest"
            relocated_dir.mkdir()
            relocated = relocated_dir / "moved-link.txt"
            relocated.symlink_to(os.readlink(target))
            assert relocated.read_text() == "source", "link assoluto rotto dopo spostamento"
            session.key(b"\x13")
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




def test_f2_rename_and_no_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "a.txt").write_text("originale")
        (root / "b.txt").write_text("esistente")
        session = Session(root)
        try:
            session.key(F2)
            session.type("b.txt")
            session.key(ENTER)
            assert (root / "a.txt").read_text() == "originale"
            assert (root / "b.txt").read_text() == "esistente"
            session.key(F2)
            session.type("nuovo nome.txt")
            session.key(ENTER)
            assert not (root / "a.txt").exists()
            assert (root / "nuovo nome.txt").read_text() == "originale"
        finally:
            session.close()


def test_f4_editor_interactive():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        target = root / "a file.txt"
        target.write_text("prima")
        editor = root / "editor"
        editor.write_text('#!/bin/sh\nprintf "Editor: "\nread value\nprintf "%s" "$value" > "$1"\n')
        editor.chmod(0o755)
        session = Session(root, env={"EDITOR": str(editor)})
        try:
            session.key(F4)
            assert b"Editor:" in session.output
            session.type("modificato")
            session.key(ENTER)
            assert target.read_text() == "modificato"
            session.key(F7)
            session.type("dopo-editor")
            session.key(ENTER)
            assert (root / "dopo-editor").is_dir()
        finally:
            session.close()


def test_move_no_overwrite_and_cancel():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        (dst / "alpha.txt").write_text("esistente")
        session = Session(src)
        try:
            session.key(DOWN)
            session.key(F6)
            session.type(str(dst))
            session.key(ENTER)
            assert (src / "alpha.txt").read_text() == "alpha"
            assert (dst / "alpha.txt").read_text() == "esistente"
            session.key(F5)
            session.key(b"\x1b")
            session.drain(0.15)
            assert not (dst / "tree").exists()
        finally:
            session.close()



def test_editor_fallback_and_arguments():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        commands = root / "commands"
        commands.mkdir()
        nano = commands / "nano"
        nano.write_text('#!/bin/sh\nif [ "$1" = "-w" ]; then shift; fi\nprintf "editato" > "$1"\n')
        nano.chmod(0o755)
        target = root / "a.txt"
        for editor in ("", str(nano) + " -w"):
            target.write_text("prima")
            session = Session(root, env={"EDITOR": editor, "PATH": str(commands) + os.pathsep + os.environ["PATH"]})
            try:
                session.key(DOWN)  # salta la directory commands
                session.key(F4)
                assert target.read_text() == "editato"
            finally:
                session.close()


def test_mouse_rename_directory_wide_bar():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "prima").mkdir()
        (root / "prima" / "file").write_text("intatto")
        session = Session(root, cols=120)
        try:
            session.mouse(0, 5, 25)  # F2 nella barra estesa
            session.type("dopo")
            session.key(ENTER)
            assert not (root / "prima").exists()
            assert (root / "dopo" / "file").read_text() == "intatto"
        finally:
            session.close()


def test_move_multiple_relative_destination():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        session = Session(src)
        try:
            session.key(F3)  # tree
            session.key(DOWN)
            session.key(F3)  # alpha.txt
            session.key(F6)
            session.type("../dest")
            session.key(ENTER)
            assert (dst / "tree" / "deep.txt").read_text() == "profondo"
            assert (dst / "alpha.txt").read_text() == "alpha"
            assert not (src / "tree").exists()
            assert not (src / "alpha.txt").exists()
        finally:
            session.close()



def test_filter_names_and_reset():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "ALPHA.txt").write_text("alpha")
        (root / "beta.txt").write_text("beta")
        session = Session(root)
        try:
            session.key(b"\x06")
            session.type("alpha")
            start = len(session.output)
            session.key(ENTER)
            assert b"ALPHA.txt" in session.output[start:]
            assert b"beta.txt" not in session.output[start:]
            session.key(F3)
            session.key(F8)
            session.type("s")
            session.key(ENTER)
            assert not (root / "ALPHA.txt").exists()
            assert (root / "beta.txt").exists()
            session.key(b"\x06")
            session.key(ENTER)
            session.key(F2)
            session.type("reset.txt")
            session.key(ENTER)
            assert (root / "reset.txt").read_text() == "beta"
        finally:
            session.close()


def test_dual_copy_move_and_independent_selection():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        session = Session(src, cols=120)
        try:
            session.key(F3)  # seleziona tree a sinistra
            session.key(DOWN)
            session.key(F3)  # seleziona alpha
            session.key(b"\t")
            session.key(LEFT)
            session.key(ENTER)  # dest a destra
            session.key(b"\t")
            session.key(F5)  # copia subito nell'altro pannello
            assert (dst / "tree" / "deep.txt").read_text() == "profondo"
            assert (dst / "alpha.txt").read_text() == "alpha"
            assert (src / "alpha.txt").exists()
            session.key(END)
            session.key(F6)  # sposta file space.txt
            assert (dst / "file space.txt").read_text() == "spazi"
            assert not (src / "file space.txt").exists()
            session.key(b"\t")
            session.key(END)
            session.key(F6)  # trasferimento nella direzione inversa
            assert (src / "file space.txt").exists()
            assert not (dst / "file space.txt").exists()
        finally:
            session.close()


def test_dual_filter_and_mouse_focus():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "alpha.txt").write_text("alpha")
        (root / "beta.txt").write_text("beta")
        session = Session(root, cols=120)
        try:
            session.key(b"\x06")
            session.type("alpha")
            session.key(ENTER)
            session.mouse(0, 70, 6)  # beta nel pannello destro non filtrato
            session.key(F2)
            session.type("gamma.txt")
            session.key(ENTER)
            assert (root / "gamma.txt").read_text() == "beta"
            session.key(b"\t")
            session.key(F2)
            session.type("filtered.txt")
            session.key(ENTER)
            assert (root / "filtered.txt").read_text() == "alpha"
        finally:
            session.close()



def test_resize_preserves_panes_and_selection():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        session = Session(src, cols=120)
        try:
            session.key(F3)  # tree a sinistra
            session.key(b"\t")
            session.key(LEFT)
            session.key(ENTER)  # dest a destra
            session.resize(80)
            session.key(F7)
            session.type("narrow")
            session.key(ENTER)
            assert (dst / "narrow").is_dir()
            session.resize(121)
            session.key(b"\t")
            session.key(F5)
            assert (dst / "tree" / "deep.txt").read_text() == "profondo"
            assert not (dst / "alpha.txt").exists()
        finally:
            session.close()


def test_dual_no_overwrite_and_literal_filter():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        src, dst = fixture(root)
        (src / "[a].txt").write_text("letterale")
        (dst / "[a].txt").write_text("esistente")
        session = Session(src, cols=120)
        try:
            session.key(b"\t")
            session.key(LEFT)
            session.key(ENTER)
            session.key(b"\t")
            session.key(b"\x06")
            session.type("[a]")
            session.key(ENTER)
            session.key(F6)
            assert (src / "[a].txt").read_text() == "letterale"
            assert (dst / "[a].txt").read_text() == "esistente"
            session.key(b"\x06")
            session.type("nessuna-corrispondenza")
            session.key(ENTER)
            session.key(F8)
            assert b"Seleziona prima un elemento" in session.output[-3000:]
        finally:
            session.close()



def test_ctrl_h_hidden_files_and_filter():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".hidden.txt").write_text("segreto")
        (root / ".hidden-dir").mkdir()
        (root / "visible.txt").write_text("visibile")
        session = Session(root)
        try:
            start = len(session.output)
            session.key(b"\x08")
            screen = session.output[start:]
            assert b".hidden.txt" not in screen
            assert b".hidden-dir" not in screen
            assert b"visible.txt" in screen
            session.key(b"\x06")
            session.type("hidden")
            start = len(session.output)
            session.key(ENTER)
            assert b".hidden.txt" not in session.output[start:]
            start = len(session.output)
            session.key(b"\x08")
            assert b".hidden.txt" in session.output[start:]
            assert b"/.hidden-dir" in session.output[start:]
            assert b"visible.txt" not in session.output[start:]
        finally:
            session.close()


def test_ctrl_h_independent_panes_and_resize():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".secret").write_text("segreto")
        session = Session(root, cols=120)
        try:
            session.key(b"\x08")  # nascosti a sinistra
            session.key(b"\t")
            session.resize(80)
            start = len(session.output)
            session.key(b"r")
            assert b".secret" in session.output[start:]
            session.resize(120)
            session.key(b"\t")  # torna a sinistra
            session.resize(80)
            start = len(session.output)
            session.key(b"r")
            assert b".secret" not in session.output[start:]
            start = len(session.output)
            session.key(b"\x08")
            assert b".secret" in session.output[start:]
        finally:
            session.close()


if __name__ == "__main__":
    tests = [test_ctrl_h_hidden_files_and_filter, test_ctrl_h_independent_panes_and_resize,
             test_resize_preserves_panes_and_selection, test_dual_no_overwrite_and_literal_filter,
             test_filter_names_and_reset, test_dual_copy_move_and_independent_selection,
             test_dual_filter_and_mouse_focus, test_editor_fallback_and_arguments, test_mouse_rename_directory_wide_bar,
             test_move_multiple_relative_destination, test_f2_rename_and_no_overwrite, test_f4_editor_interactive,
             test_move_no_overwrite_and_cancel, test_copy_multiple, test_cut_move, test_mkdir_and_delete, test_no_overwrite,
             test_filename_with_spaces, test_delete_cancelled, test_no_copy_into_self,
             test_mouse_double_click_opens_folder, test_mouse_button_mkdir,
             test_mouse_prompt_ignores_click, test_mouse_mark_copy,
             test_mouse_compact_bar_and_wheel, test_gray_palette_and_highlighting,
             test_no_color_fallback, test_ascii_fallback,
             test_hidden_and_mc_directory_prefix, test_mouse_exact_columns_and_rows,
             test_no_flicker_on_cursor_navigation,
             test_lynx_arrows_enter_and_back, test_millis_italian_decimal_comma,
             test_repeated_clicks_no_crash, test_execute_interactive_script,
             test_ctrl_x_chmod, test_ctrl_s_symlink, test_ctrl_x_chown_nonprivileged,
             test_f10_quits_and_restores_terminal, test_chmod_dialog_toggle_and_cancel,
             test_chown_dialog_group_tab_navigation]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"{len(tests)} test superati")
