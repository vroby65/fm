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
F1 = b"\x1bOP"
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
        self.drain(0.6 if value == b"\x1b" else 0.07)

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
        self.key(F10)
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


def test_escape_digit_and_insert_decoding():
    source = pathlib.Path(SCRIPT).read_text()
    decoder = source[source.index("input_key() {"):source.index("# Inserimento in modalita'")]
    for sequence, expected in [(b"\x1b" + str(n).encode(), f"F{n or 10}") for n in range(10)] + [(b"\x1b[2~", "F3")]:
        result = subprocess.run(
            ["bash", "-c", decoder + '\nexec 9<&0; PENDING_CHAR=; filter_editing=0; input_key; printf "%s" "$KEY"'],
            input=sequence, capture_output=True, check=True,
        )
        assert result.stdout.decode() == expected, (sequence, result.stdout)


def test_selection_keys_advance_and_stop_at_last_entry():
    for key in (F3, b"\x1b[2~", b" ", b"\x1b3"):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "a").write_text("a")
            (root / "b").write_text("b")
            session = Session(root)
            try:
                session.key(key)  # marca a e passa a b
                session.key(key)  # marca l'ultimo senza tornare all'inizio
                session.key(key)  # deseleziona l'ultimo
                session.key(F8)
                session.type("s")
                session.key(ENTER)
                assert not (root / "a").exists()
                assert (root / "b").read_text() == "b"
                session.key(F2)
                session.type("c")
                session.key(ENTER)
                assert (root / "c").read_text() == "b"
                session.key(b"\x1b[H")
                session.key(key)  # .. non selezionabile e non avanza
                session.key(F2)
                assert b"Seleziona prima un elemento." in session.output[-1000:]
            finally:
                session.close()


def test_escape_then_digit_with_typing_delay():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "originale").write_text("intatto")
        session = Session(root)
        try:
            os.write(session.fd, b"\x1b")
            session.drain(0.2)
            session.key(b"2")
            session.type("rinominato")
            session.key(ENTER)
            assert (root / "rinominato").read_text() == "intatto"
            session.key(b"\x1b0")
        finally:
            session.close()


def test_queued_navigation_keeps_following_command_responsive():
    for cols in (96, 120):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for n in range(120):
                (root / f"file{n:03}").write_text(str(n))
            session = Session(root, cols=cols)
            try:
                start = len(session.output)
                session.key(DOWN * 80 + F2)
                session.drain(0.3)
                assert len(session.output) - start < 15000, "Troppi ridisegni durante la raffica"
                session.type("rinominato")
                session.key(ENTER)
                session.drain(0.5)
                assert (root / "rinominato").read_text() == "80"
            finally:
                session.close()


def test_scrolling_redraws_only_active_list():
    for cols in (96, 120):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for n in range(40):
                (root / f"file{n:03}").write_text(str(n))
            session = Session(root, cols=cols)
            try:
                start = len(session.output)
                session.key(b"\x1b[6~")
                screen = session.output[start:]
                assert b"file020" in screen
                assert b"\x1b[1;" not in screen, "Scorrere non deve ridisegnare le cornici"
                assert b"Dimensione" not in screen
                session.key(F2)
                session.type("scelto")
                session.key(ENTER)
                assert (root / "scelto").read_text() == "20"
            finally:
                session.close()


def test_column_separators_continue_through_empty_rows():
    import re

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "solo.txt").write_text("un file")
        for cols, ascii_mode in ((96, False), (120, False), (80, True)):
            session = Session(root, cols=cols, env={"ABFM_ASCII": str(int(ascii_mode))})
            try:
                for width in (cols, 121):
                    if width != cols:
                        session.output.clear()
                        session.resize(width)
                        session.key(b"\x1b")
                        session.drain(.15)
                    panes = [(1, width)] if width < 100 else [(1, width // 2), (width // 2 + 1, width - width // 2)]
                    separator = "|" if ascii_mode else "│"
                    for x, pane_width in panes:
                        expected = separator + " " * (pane_width - 30) + separator + " " * 10 + separator + " " * 16 + separator
                        for row in range(6, 24):
                            match = re.search(rb"\x1b\[" + f"{row};{x}H".encode() + rb"([^\r\n]*)", bytes(session.output))
                            assert match, (row, x)
                            text = re.sub(rb"\x1b\[[0-9;]*m", b"", match[1]).decode()
                            assert text == expected, (width, row, text)
            finally:
                session.close()


def test_q_does_not_quit():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        session = Session(root)
        try:
            session.key(b"qQ")
            session.key(F7)
            session.type("ancora-aperto")
            session.key(ENTER)
            assert (root / "ancora-aperto").is_dir()
            session.resize(30)
            session.key(b"qQ")
            session.resize(80)
            session.key(F7)
            session.type("dopo-resize")
            session.key(ENTER)
            assert (root / "dopo-resize").is_dir()
        finally:
            session.close()


def test_f1_mc_menu_context_macros_and_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        work, config = root / "work", root / "config"
        work.mkdir()
        (config / "mc").mkdir(parents=True)
        name = 'file "$(touch pwned)".txt'
        (work / name).write_text("conserva")
        (config / "mc" / "menu").write_text(r"""shell_patterns=0
+ f \.txt$ & ! t t
a Comando file singolo
    printf '%%s\n' %f > singolo
+ t t
b Comando marcati
    printf '%%s\n' %t > marcati
+ f \.deb$
i Installa pacchetto
    touch installato
p Richiesta nome
    value=%{Nome file}
    printf '%%s\n' "$value" > richiesta
v Visualizza risultato
    %view{ascii} printf 'vista'
""")
        session = Session(work, env={"XDG_CONFIG_HOME": str(config), "PAGER": "cat"})
        try:
            session.key(F1)
            assert b"Comando file singolo" in session.output
            assert b"Comando marcati" not in session.output
            assert b"Installa pacchetto" not in session.output
            session.key(b"a")
            assert (work / "singolo").read_text().strip() == name
            assert not (work / "pwned").exists()
            session.key(ENTER)
            session.key(F1)
            session.key(b"p")
            session.type("nome con spazi")
            session.key(ENTER)
            assert (work / "richiesta").read_text().strip() == "nome con spazi"
            session.key(ENTER)
            session.key(F1)
            start = len(session.output)
            session.key(b"v")
            assert b"vista" in session.output[start:]
            session.key(F1)
            session.key(b"\x1b")
            session.drain(.2)
            assert (work / name).read_text() == "conserva"
        finally:
            session.key(b"\x1b")
            session.close()


def test_f1_mc_menu_tagged_and_opposite_directory():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        work, config = root / "work", root / "config"
        work.mkdir()
        dest = root / "dest"
        dest.mkdir()
        (config / "mc").mkdir(parents=True)
        for name in ("a file.txt", "b.txt"):
            (work / name).write_text("demo")
        (config / "mc" / "menu").write_text(r"""shell_patterns=1
+ t t
s Selezione e percorsi
    printf '%%s\n' %s > scelti
    printf '%%s\n' %d %D > percorsi
u Smarca selezione
    printf '%%s\n' %u > smarcati
""")
        session = Session(work, cols=120, env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.key(F3)
            session.key(F3)
            session.key(b"\t")
            session.key(LEFT)
            session.key(b"\x06")
            session.type("dest")
            session.key(ENTER)
            session.key(b"\t")
            session.key(F1)
            session.key(b"s")
            assert (work / "scelti").read_text().splitlines() == ["a file.txt", "b.txt"]
            assert (work / "percorsi").read_text().splitlines() == [str(work), str(dest)]
            session.key(ENTER)
            session.key(F1)
            session.key(b"u")
            assert (work / "smarcati").read_text().splitlines() == ["a file.txt", "b.txt"]
            session.key(ENTER)
        finally:
            session.key(b"\x1b")
            session.close()


def test_f1_menu_mouse_scroll_and_resize():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        work, config = root / "work", root / "config"
        work.mkdir()
        (work / "input.txt").write_text("demo")
        (config / "mc").mkdir(parents=True)
        (config / "mc" / "menu").write_text("".join(
            f"{chr(97+i)} Comando numero {i}\n    printf done > comando-{i}\n" for i in range(26)))
        session = Session(work, env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.mouse(0, 4, 25)  # F1 nella barra
            assert b"Menu comandi (MC)" in session.output
            session.key(END)
            assert b"Comando numero 25" in session.output
            session.key(ENTER)
            assert (work / "comando-25").read_text() == "done"
            session.key(ENTER)
            session.key(b"\x1b[11~")  # variante CSI di F1
            session.resize(35)
            session.key(b"\x1b[H")
            session.key(DOWN)
            session.mouse(0, 8, 24)  # Esegui nella finestra stretta
            assert (work / "comando-1").read_text() == "done"
            session.key(ENTER)
        finally:
            session.key(b"\x1b")
            session.close()


def test_directory_remembers_cursor_after_reentry():
    for cols in (80, 120):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            child = root / "cartella"
            child.mkdir()
            for i in range(30):
                (child / f"file-{i:02}.txt").write_text(str(i))
            session = Session(child, cols=cols)
            try:
                session.key(END)
                session.key(LEFT)
                (child / "000-nuovo.txt").write_text("nuovo")
                session.key(RIGHT)
                session.key(F2)
                session.type("ritrovato.txt")
                session.key(ENTER)
                assert (child / "ritrovato.txt").read_text() == "29"
                assert (child / "file-00.txt").read_text() == "0"
            finally:
                session.close()


def test_directory_remembers_marks_and_drops_missing_files():
    for cols, remove in ((80, False), (120, False), (80, True)):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            child, dest, second = (root / name for name in ("cartella", "dest", "second"))
            for path in (child, dest, second): path.mkdir()
            for name in ("a.txt", "b.txt"): (child / name).write_text(name)
            session = Session(child, cols=cols)
            try:
                session.key(F3)
                session.key(F3)
                session.key(LEFT)
                if remove:
                    (child / "b.txt").unlink()
                    (child / "nuovo.txt").write_text("nuovo")
                session.key(RIGHT)
                if cols >= 100: session.resize(80)
                session.key(F5)
                session.type(str(dest))
                session.key(ENTER)
                assert (dest / "a.txt").read_text() == "a.txt"
                assert (dest / "b.txt").exists() == (not remove)
                assert not (dest / "nuovo.txt").exists()
                # Una copia completata azzera i segni: non devono riapparire dal ricordo.
                session.key(LEFT)
                session.key(RIGHT)
                session.key(F5)
                session.type(str(second))
                session.key(ENTER)
                assert (second / "a.txt").exists()
                assert not (second / "b.txt").exists()
            finally:
                session.close()


def test_directory_memory_is_independent_between_panes():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        child, left_dest, right_dest = (root / name for name in ("cartella", "dest-left", "dest-right"))
        for path in (child, left_dest, right_dest): path.mkdir()
        for name in ("a.txt", "b.txt"): (child / name).write_text(name)
        session = Session(child, cols=120)
        try:
            session.key(F3)  # a a sinistra
            session.key(LEFT)
            session.key(b"\t")
            session.key(DOWN)
            session.key(F3)  # b a destra
            session.key(LEFT)
            session.key(b"\t")
            session.key(RIGHT)
            session.resize(80)
            session.key(F5)
            session.type(str(left_dest))
            session.key(ENTER)
            assert (left_dest / "a.txt").exists()
            assert not (left_dest / "b.txt").exists()
            session.resize(120)
            session.key(b"\t")
            session.key(RIGHT)
            session.resize(80)
            session.key(F5)
            session.type(str(right_dest))
            session.key(ENTER)
            assert (right_dest / "b.txt").exists()
            assert not (right_dest / "a.txt").exists()
        finally:
            session.close()


def test_single_pane_transfer_uses_marked_absolute_source():
    for move in (False, True):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source, dest = root / "A", root / "B"
            source.mkdir(); dest.mkdir()
            out = root / "out"
            out.mkdir()
            (source / "a-non-marcato.txt").write_text("altro")
            (source / "scelto.txt").write_text("origine")
            (dest / "altro.txt").write_text("destinazione")
            session = Session(source, cols=80)
            try:
                session.key(END)
                session.key(F3)
                session.key(LEFT)
                session.key(DOWN)
                session.key(RIGHT)
                session.key(F6 if move else F5)
                session.key(ENTER)  # destinazione: cartella corrente B
                assert (dest / "scelto.txt").read_text() == "origine"
                assert (source / "scelto.txt").exists() == (not move)
                assert (dest / "altro.txt").read_text() == "destinazione"
                session.key(LEFT)
                session.key(UP)
                session.key(RIGHT)
                session.key(b"\x1b[H")
                session.key(DOWN)  # a-non-marcato.txt
                session.key(F5)
                session.type(str(out))
                session.key(ENTER)
                assert (out / "a-non-marcato.txt").read_text() == "altro"
                assert not (out / "scelto.txt").exists(), "Marcatura consumata riapparsa"
            finally:
                session.key(b"\x1b")
                session.close()


def test_pending_transfer_does_not_fall_back_when_source_disappears():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        source, dest, out = (root / name for name in ("A", "B", "out"))
        for path in (source, dest, out): path.mkdir()
        file = source / "scelto.txt"
        file.write_text("origine")
        (dest / "altro.txt").write_text("destinazione")
        session = Session(source)
        try:
            session.key(F3)
            session.key(LEFT)
            session.key(DOWN)
            session.key(RIGHT)
            file.unlink()
            session.key(F5)
            session.type(str(out))
            session.key(ENTER)
            assert not list(out.iterdir()), "Copiato il file della destinazione al posto della sorgente"
            assert b"Origine non disponibile" in session.output
        finally:
            session.close()


def test_connections_menu_above_root_and_local_return():
    with tempfile.TemporaryDirectory() as tmp:
        for cols in (80, 120):
            session = Session(pathlib.Path("/"), cols=cols, env={"XDG_CONFIG_HOME": tmp})
            try:
                session.key(LEFT)
                for label in (b"Questo PC", b"SSH", b"FTP"):
                    assert label in session.output, label
                start = len(session.output)
                session.key(F2)
                assert b"Nome attuale:" not in session.output[start:]
                session.key(b"\x1b[H")
                session.key(ENTER)
                session.key(b"\x1b[H")
                session.key(ENTER)  # /.. dalla root riapre Connessioni
                assert b"Connessioni" in session.output[-12000:]
            finally:
                session.close()

def test_remote_connection_dialog_password_hidden_and_cancel():
    with tempfile.TemporaryDirectory() as tmp:
        config = pathlib.Path(tmp) / "config"
        session = Session(pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.key(LEFT)
            session.key(DOWN)
            session.key(ENTER)
            assert b"Connessione SSH" in session.output
            assert b"portachiavi" in session.output
            session.type("user@example.invalid")
            session.key(b"\t")
            session.type("password-segreta")
            assert b"password-segreta" not in session.output
            session.key(b"\x1b")
            session.drain(.2)
            assert not (config / "fm" / "last-ssh").exists()
            session.key(DOWN)
            session.key(ENTER)
            assert b"Connessione FTP" in session.output
            session.key(b"\x1b")
            session.drain(.2)
        finally:
            session.key(b"\x1b")
            session.close()


def saved_connection_fixture(config, protocol="ssh", address="user@example.invalid", label="Server prova"):
    import hashlib

    identifier = hashlib.sha256(f"{protocol}\0{address}".encode()).hexdigest()
    directory = config / "fm" / "connections"
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / identifier
    file.write_text(f"{protocol}\n{address}\n{label}\n")
    file.chmod(0o600)
    return file


def test_saved_connections_rename_delete_and_restart():
    with tempfile.TemporaryDirectory() as tmp:
        config = pathlib.Path(tmp) / "config"
        file = saved_connection_fixture(config)
        session = Session(pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.key(LEFT)
            assert b"Server prova" in session.output
            session.key(END)
            session.key(F2)
            session.type("NAS di casa")
            session.key(ENTER)
            assert file.read_text().splitlines() == ["ssh", "user@example.invalid", "NAS di casa"]
        finally:
            session.close()
        session = Session(pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.key(LEFT)
            assert b"NAS di casa" in session.output
            session.key(END)
            session.key(F8)
            session.type("n")
            session.key(ENTER)
            assert file.exists()
            session.key(F8)
            session.type("s")
            session.key(ENTER)
            assert not file.exists()
            session.key(b"\x1b[H")
            start = len(session.output)
            session.key(F8)
            assert b"Eliminare" not in session.output[start:], "Voce Questo PC eliminabile"
        finally:
            session.close()


def test_saved_connection_opens_prefilled_dialog_without_password():
    for protocol in ("ssh", "ftp"):
        with tempfile.TemporaryDirectory() as tmp:
            config = pathlib.Path(tmp) / "config"
            file = saved_connection_fixture(config, protocol=protocol)
            session = Session(pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
            try:
                session.key(LEFT)
                session.mouse(0, 10, 7)
                session.mouse(0, 10, 7)
                assert f"Connessione {protocol.upper()}".encode() in session.output
                assert b"user@example.invalid" in session.output
                session.type("other@example.invalid")  # cambia solo il dialog, poi annulla
                session.key(b"\x1b")
                session.drain(.2)
                assert file.read_text().splitlines()[1] == "user@example.invalid"
            finally:
                session.key(b"\x1b")
                session.close()


def test_saved_connections_import_only_once():
    with tempfile.TemporaryDirectory() as tmp:
        config = pathlib.Path(tmp)
        directory = config / "fm"
        directory.mkdir()
        for protocol in ("ssh", "ftp"):
            (directory / f"last-{protocol}").write_text("user@example.invalid\n")
        session = Session(pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.key(LEFT)
            assert len(list((directory / "connections").iterdir())) == 2
            for _ in range(2):
                session.key(END)
                session.key(F8)
                session.type("s")
                session.key(ENTER)
            assert not list((directory / "connections").iterdir())
        finally:
            session.close()
        session = Session(pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
        try:
            session.key(LEFT)
            assert not list((directory / "connections").iterdir()), "Connessioni eliminate ricreate"
        finally:
            session.close()


def test_selected_symlink_target_in_status_line():
    for cols in (80, 120):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "target.txt").write_text("target")
            (root / "link.txt").symlink_to("target.txt")
            (root / "broken.txt").symlink_to("missing-target.txt")
            session = Session(root, cols=cols)
            try:
                session.key(b"\x1b[H")
                session.key(DOWN)  # broken.txt
                assert b"Link -> missing-target.txt" in session.output[-5000:]
                start = len(session.output)
                session.key(DOWN)  # link.txt
                assert b"Link -> target.txt" in session.output[start:]
                start = len(session.output)
                session.key(DOWN)  # file normale: ripristina l'aiuto
                assert b"Link ->" not in session.output[start:]
                assert b"Ctrl+F" in session.output[start:]
                if cols == 120:
                    session.key(b"\t")
                    session.key(b"\x1b[H")
                    session.key(DOWN)
                    assert b"Link -> missing-target.txt" in session.output[-5000:]
            finally:
                session.close()


def test_copy_multiple():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        s = Session(src)
        s.key(F3)        # tree/ (prima directory)
        # F3 avanza ad alpha.txt
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
            assert b"\x1b[38;5;144;48;5;237m" in s.output, "Palette classica MC mancante"
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
            s.mouse(0, 40, 25)
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
            s.mouse(0, 21, 25)
            s.type("small-window")
            s.key(ENTER)
            assert (root / "small-window").is_dir(), "F7 non cliccabile su finestra stretta"
            for _ in range(28):
                s.mouse(65, 10, 10)
            assert b"d25" in s.output[-2500:], "Rotella non porta ai file piu' in basso"
        finally:
            s.close()



def test_size_and_modification_columns():
    import re

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        file = root / ("long-name-" * 8 + ".txt")
        file.write_bytes(b"x" * 12345)
        stamp = 1700000000
        os.utime(file, (stamp, stamp))
        expected_date = time.strftime("%d/%m/%Y %H:%M", time.localtime(stamp))
        for cols in (35, 80, 100, 121):
            s = Session(root, cols=cols)
            try:
                plain = re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]", b"", bytes(s.output)).decode()
                assert "Dimensione" in plain and "Ultima modifica" in plain
                assert f"     12345│{expected_date}" in plain
                assert "UP--DIR" in plain
                for row in plain.split("\r\n"):
                    if "12345│" in row:
                        assert len(row.rstrip("\r")) <= cols, (cols, row)
                s.key(DOWN)
                assert b"12345" in s.output
            finally:
                s.close()


def test_reference_palette_and_highlighting():
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
            assert b"\x1b[38;5;144;48;5;237m" in out, "Sfondo grigio scuro e testo giallo mancanti"
            assert b"\x1b[38;5;252;48;5;23m" in out, "Selezione petrolio mancante"
            assert b"\x1b[1;38;5;144;48;5;237m" in out, "Directory gialle mancanti"
            assert b"\x1b[38;5;120;48;5;237m" in out, "Eseguibili verdi mancanti"
            assert b"\x1b[38;5;117;48;5;237m" in out, "Link ciano mancanti"
            assert b"\x1b[38;5;210;48;5;237m" in out, "Link interrotti rossi mancanti"
            assert b"\x1b[38;5;254;48;5;236m" in out, "Barra nera comandi mancante"
            s.key(F3)
            s.key(UP)  # torna sulla riga marcata dopo l'avanzamento automatico
            assert b"\x1b[1;38;5;228;48;5;23m" in s.output, "Selezione marcata gialla mancante"
        finally:
            s.close()


def test_no_color_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        s = Session(pathlib.Path(tmp), env={"ABFM_NO_COLOR": "1"})
        try:
            assert b"\x1b[38;5;144;48;5;237m" not in s.output
            assert b"\x1b[38;5;252;48;5;23m" not in s.output
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


def test_attributes_sudo_retry_and_cancel():
    for command, cancel, denied in (("chmod", False, True), ("chown", False, True),
                                     ("chmod", True, True), ("chmod", "interrupt", True),
                                     ("chown", False, False)):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            work = root / "work"
            work.mkdir()
            file = work / "owned.txt"
            file.write_text("conserva")
            file.chmod(0o644)
            tools = root / "bin"
            tools.mkdir()
            error = "Operation not permitted" if denied else "invalid user"
            mock = tools / command
            mock.write_text(f"#!/bin/sh\nprintf '%s\\n' '{command}: {error}' >&2\nexit 1\n")
            mock.chmod(0o755)
            log = root / "sudo.log"
            sudo = tools / "sudo"
            sudo.write_text("""#!/bin/sh
printf '%s\n' "$*" >> "$FM_TEST_SUDO_LOG"
printf 'Password sudo: ' > /dev/tty
stty -echo < /dev/tty
IFS= read -r answer < /dev/tty
stty echo < /dev/tty
printf '\n' > /dev/tty
[ "$FM_TEST_SUDO_CANCEL" = 1 ] && exit 1
shift
command=$1
shift
exec "/usr/bin/$command" "$@"
""")
            sudo.chmod(0o755)
            session = Session(work, env={"PATH": f"{tools}:{os.environ['PATH']}",
                                        "FM_TEST_SUDO_LOG": str(log),
                                        "FM_TEST_SUDO_CANCEL": str(int(bool(cancel)))})
            try:
                session.key(b"\x18c")
                if command == "chmod":
                    session.type("600")
                else:
                    session.key(b"\t")
                    session.type(f"{os.getuid()}:{os.getgid()}")
                session.key(ENTER)
                if denied:
                    assert b"Password sudo:" in session.output
                    session.key(b"\x03" if cancel == "interrupt" else b"password-di-prova\n")
                    session.drain(0.2)
                    assert "-- " + command + " -- " in log.read_text()
                    assert b"password-di-prova" not in session.output, "Password mostrata a schermo"
                    assert ("Non riusciti: 1" if cancel else "Non riusciti: 0").encode() in session.output
                    if command == "chmod":
                        assert file.stat().st_mode & 0o777 == (0o644 if cancel else 0o600)
                else:
                    assert not log.exists(), "sudo usato per un errore diverso dai permessi"
                    assert b"invalid user" in session.output
                assert file.read_text() == "conserva"
                session.key(b"\x18c")
                assert b"Permessi e proprietario" in session.output[-15000:]
                session.key(b"\x1b")
                session.drain(0.2)
            finally:
                session.key(b"\x1b")
                session.close()


def test_ctrl_x_unified_dialog():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        file = root / "mode.txt"
        file.write_text("data")
        file.chmod(0o644)
        session = Session(root)
        try:
            session.key(b"\x18")
            assert b"Permessi e proprietario" not in session.output
            session.key(b"c")
            assert b"Permessi e proprietario" in session.output
            assert b"Utenti" in session.output and b"Gruppi" in session.output
            session.type("600")
            session.key(b"\t")
            session.type(f"{os.getuid()}:{os.getgid()}")
            session.key(ENTER)
            assert file.stat().st_mode & 0o777 == 0o600
            assert f"chown {os.getuid()}:{os.getgid()}: modificati 1".encode() in session.output
            assert b"chmod 600: modificati 1" in session.output
            session.key(b"\x18o")
            assert b"Ctrl+X: C per attributi" in session.output
        finally:
            session.key(b"\x1b")
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
            session.key(b"\x18s")
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
            session.key(b"\x18c\t")
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
            assert b"Permessi e proprietario" in session.output
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
            session.key(b"\x18c\t")
            assert b"Permessi e proprietario" in session.output
            session.type(str(os.getuid()))
            session.key(b"\t")
            session.type(str(os.getgid()))
            session.key(ENTER)
            assert f.stat().st_uid == os.getuid()
            assert f.stat().st_gid == os.getgid()
            assert f"chown {os.getuid()}:{os.getgid()}: modificati 1".encode() in session.output
        finally:
            session.close()




def test_permission_dialog_mouse_buttons_and_resize():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        file = root / "mode.txt"
        file.write_text("data")
        file.chmod(0o644)
        session = Session(root)
        try:
            session.key(b"\x18c")
            session.mouse(0, 30, 8)  # scrittura gruppo
            session.mouse(0, 38, 24)  # Imposta
            assert file.stat().st_mode & 0o777 == 0o664
            session.key(b"\x18c")
            session.type("777")
            session.key(b"\t\t\t\t")  # Annulla
            session.key(ENTER)
            assert file.stat().st_mode & 0o777 == 0o664
            session.key(b"\x18c\t")
            session.type(f"{os.getuid()}:{os.getgid()}")
            session.mouse(0, 38, 24)
            assert f"chown {os.getuid()}:{os.getgid()}: modificati 1".encode() in session.output
            session.key(b"\x18c")
            session.resize(35)
            session.key(b"\t")
            assert b"Gruppi" in session.output[-6000:]
            session.key(b"\x1b")
            session.drain(0.2)
            assert b"Modifica attributi" in session.output
        finally:
            session.key(b"\x1b")
            session.close()



def test_chown_mc_lists_and_cancel():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        file = root / "owned.txt"
        file.write_text("data")
        session = Session(root)
        try:
            session.key(b"\x18c\t")
            for label in (b"Utenti", b"Gruppi", b"File", b"Imposta", b"Annulla"):
                assert label in session.output[-12000:], label
            session.key(DOWN)
            session.key(b"\t")
            session.key(DOWN)
            session.key(b"\t")
            session.key(b"\t")  # Annulla
            session.key(ENTER)
            assert b"Modifica attributi annullata" in session.output
            assert file.stat().st_uid == os.getuid()
            session.key(b"\x18c\t")
            session.type(f"{os.getuid()}:{os.getgid()}")
            session.key(ENTER)
            assert f"chown {os.getuid()}:{os.getgid()}: modificati 1".encode() in session.output
            session.key(b"\x18c\t")
            session.key(UP)
            session.key(DOWN)
            session.key(b"\t")
            session.key(UP)
            session.key(DOWN)
            session.key(ENTER)
            import pwd
            import grp
            spec = f"{pwd.getpwuid(os.getuid()).pw_name}:{grp.getgrgid(os.getgid()).gr_name}"
            assert f"chown {spec}: modificati 1".encode() in session.output
        finally:
            session.close()


def test_file_operations_retry_with_sudo():
    for operation, command in (("rename", "mv"), ("copy", "cp"), ("move", "mv"),
                               ("mkdir", "mkdir"), ("delete", "rm"), ("link", "ln")):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            work, dest, tools = (root / name for name in ("work", "dest", "bin"))
            for path in (work, dest, tools):
                path.mkdir()
            source = work / "originale.txt"
            source.write_text("conserva")
            mock = tools / command
            mock.write_text("#!/bin/sh\nprintf 'Permission denied\\n' >&2\nexit 1\n")
            mock.chmod(0o755)
            log = root / "sudo.log"
            sudo = tools / "sudo"
            sudo.write_text("""#!/bin/sh
printf '%s\n' "$*" >> "$FM_TEST_SUDO_LOG"
printf 'Password sudo: ' > /dev/tty
stty -echo < /dev/tty
IFS= read -r answer < /dev/tty
stty echo < /dev/tty
printf '\n' > /dev/tty
shift
command=$1
shift
exec "/usr/bin/$command" "$@"
""")
            sudo.chmod(0o755)
            session = Session(work, env={"PATH": f"{tools}:{os.environ['PATH']}", "FM_TEST_SUDO_LOG": str(log)})
            try:
                if operation == "rename":
                    session.key(F2)
                    session.type("rinominato.txt")
                    session.key(ENTER)
                elif operation in ("copy", "move"):
                    session.key(F5 if operation == "copy" else F6)
                    session.type(str(dest))
                    session.key(ENTER)
                elif operation == "mkdir":
                    session.key(F7)
                    session.type("nuova")
                    session.key(ENTER)
                elif operation == "delete":
                    session.key(F8)
                    assert not log.exists(), "sudo prima della conferma di eliminazione"
                    session.type("s")
                    session.key(ENTER)
                else:
                    session.key(b"\x18s")
                assert b"Password sudo:" in session.output, operation
                session.key(b"password-di-prova\n")
                session.drain(.15)
                assert log.read_text().startswith(f"-- {command} ")
                assert b"password-di-prova" not in session.output
                if operation == "rename": assert (work / "rinominato.txt").read_text() == "conserva"
                elif operation in ("copy", "move"):
                    assert (dest / source.name).read_text() == "conserva"
                    assert source.exists() == (operation == "copy")
                elif operation == "mkdir": assert (work / "nuova").is_dir()
                elif operation == "delete": assert not source.exists()
                else: assert (work / "originale.txt.lnk").is_symlink()
            finally:
                session.key(b"\x1b")
                session.close()


def test_rename_dialog_edit_cancel_and_mouse():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        file = root / "originale.txt"
        file.write_text("conserva")
        session = Session(root)
        try:
            session.key(F2)
            assert b"Nome attuale:" in session.output and b"Nuovo nome:" in session.output
            session.type("annullato.txt")
            session.key(b"\t\t")
            session.key(ENTER)
            assert file.read_text() == "conserva"
            assert not (root / "annullato.txt").exists()
            session.key(F2)
            session.key(END)
            session.key(BACK)
            session.type("T")
            session.key(ENTER)
            edited = root / "originale.txT"
            assert edited.read_text() == "conserva"
            session.key(F2)
            session.type("rinominato.txt")
            session.mouse(0, 39, 18)  # pulsante Rinomina
            assert (root / "rinominato.txt").read_text() == "conserva"
        finally:
            session.key(b"\x1b")
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
            session.mouse(0, 15, 25)  # F2 nella barra estesa
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
            session.key(F3)  # tree, poi avanza ad alpha.txt
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



def test_live_filter_and_enter_opens_or_runs():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "altro").mkdir()
        (root / "cartella").mkdir()
        (root / "cartella" / "inside.txt").write_text("dentro")
        runner = root / "esegui.sh"
        runner.write_text('#!/bin/sh\nprintf eseguito > risultato\n')
        runner.chmod(0o755)
        session = Session(root)
        try:
            session.key(b"\x06")
            start = len(session.output)
            session.type("car")
            screen = session.output[start:]
            assert b"/cartella" in screen
            assert b"/altro" not in screen, "Filtro non aggiornato prima di Invio"
            session.key(ENTER)
            session.key(F7)
            session.type("nuova")
            session.key(ENTER)
            assert (root / "cartella" / "nuova").is_dir()
            session.key(BACK)
            session.key(b"\x06")
            session.type("esegui")
            session.key(ENTER)
            assert (root / "risultato").read_text() == "eseguito"
            session.key(ENTER)  # ritorna dall'eseguibile
            session.key(b"\x06")
            session.type("inesistente")
            session.key(ENTER)
            assert b"Nessuna corrispondenza" in session.output
            session.key(b"\x1b")
            session.drain(.2)
        finally:
            session.key(b"\x1b")
            session.close()


def test_parent_reselects_departed_directory():
    for cols in (80, 120):
        for back in (LEFT, BACK, b"parent-row"):
            with tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                for i in range(30):
                    (root / f"dir-{i:02}").mkdir()
                session = Session(root, cols=cols)
                try:
                    session.key(END)
                    session.key(ENTER)
                    if back == b"parent-row":
                        session.key(b"\x1b[H")
                        session.key(ENTER)
                    else:
                        session.key(back)
                    session.key(F2)
                    session.type("ritrovata")
                    session.key(ENTER)
                    assert not (root / "dir-29").exists()
                    assert (root / "ritrovata").is_dir()
                finally:
                    session.close()


def test_live_filter_spaces_backspace_and_escape():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in ("alfa uno.txt", "alfa due.txt", "beta.txt"):
            (root / name).write_text(name)
        session = Session(root)
        try:
            session.key(b"\x06")
            session.type("alfa ")
            start = len(session.output)
            session.type("u")
            assert b"alfa uno.txt" in session.output[start:]
            assert b"alfa due.txt" not in session.output[start:]
            start = len(session.output)
            session.key(BACK)
            assert b"alfa due.txt" in session.output[start:]
            assert b"alfa uno.txt" in session.output[start:]
            session.type("u")
            session.key(b"\x1b")
            session.drain(.2)
            session.key(F2)
            session.type("scelto.txt")
            session.key(ENTER)
            assert (root / "scelto.txt").read_text() == "alfa uno.txt"
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
            session.type("alph")
            start = len(session.output)
            session.type("a")
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


def test_dual_move_directory_and_failure_reasons():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        session = Session(src, cols=120)
        try:
            session.key(F6)
            assert b"Stessa cartella" in session.output
            assert (src / "tree" / "deep.txt").exists()
            session.key(b"\t")
            session.key(LEFT)
            session.key(UP)  # il padre evidenzia src; dest e' la voce precedente
            session.key(ENTER)
            session.key(b"\t")
            session.key(F6)
            assert (dst / "tree" / "deep.txt").read_text() == "profondo"
            assert not (src / "tree").exists()
            (src / "tree").mkdir()
            (src / "tree" / "keep.txt").write_text("conserva")
            session.key(b"r")
            session.key(F6)
            assert b"Nome gia' presente" in session.output
            assert (src / "tree" / "keep.txt").read_text() == "conserva"
            assert (dst / "tree" / "deep.txt").read_text() == "profondo"
        finally:
            session.close()


def test_dual_copy_move_and_independent_selection():
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = fixture(pathlib.Path(tmp))
        session = Session(src, cols=120)
        try:
            session.key(F3)  # seleziona tree a sinistra e avanza
            session.key(F3)  # seleziona alpha
            session.key(b"\t")
            session.key(LEFT)
            session.key(UP)  # il padre evidenzia src; dest e' la voce precedente
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
            session.key(UP)  # il padre evidenzia src; dest e' la voce precedente
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
            session.key(UP)  # il padre evidenzia src; dest e' la voce precedente
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



def test_filter_clears_on_choice_and_keeps_current_file():
    for choice in (F3, ENTER, "mouse"):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "alpha.txt").write_text("intatto")
            (root / "target.txt").write_text("scelto")
            session = Session(root)
            try:
                session.key(b"\x06")
                session.type("target")
                start = len(session.output)
                if choice == "mouse":
                    session.mouse(0, 10, 5)
                else:
                    session.key(choice)
                assert b"alpha.txt" in session.output[start:], "Filtro non azzerato"
                session.key(F2)
                session.type("scelto.txt")
                session.key(ENTER)
                assert (root / "scelto.txt").read_text() == "scelto"
                assert (root / "alpha.txt").read_text() == "intatto"
            finally:
                session.close()


def test_filter_clears_on_directory_open_and_double_click():
    for mouse in (False, True):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "a-other").mkdir()
            (root / "target").mkdir()
            (root / "target" / "inside.txt").write_text("visibile")
            session = Session(root)
            try:
                session.key(b"\x06")
                session.type("target")
                if mouse:
                    session.mouse(0, 10, 5)
                    session.mouse(0, 10, 5)
                else:
                    session.key(ENTER)
                assert b"inside.txt" in session.output[-6000:]
                session.key(F7)
                session.type("created")
                session.key(ENTER)
                assert (root / "target" / "created").is_dir()
            finally:
                session.close()


if __name__ == "__main__":
    tests = [test_scrolling_redraws_only_active_list, test_queued_navigation_keeps_following_command_responsive, test_escape_digit_and_insert_decoding, test_selection_keys_advance_and_stop_at_last_entry, test_escape_then_digit_with_typing_delay, test_selected_symlink_target_in_status_line, test_saved_connections_import_only_once, test_saved_connections_rename_delete_and_restart, test_saved_connection_opens_prefilled_dialog_without_password, test_connections_menu_above_root_and_local_return, test_remote_connection_dialog_password_hidden_and_cancel, test_single_pane_transfer_uses_marked_absolute_source, test_pending_transfer_does_not_fall_back_when_source_disappears, test_directory_memory_is_independent_between_panes, test_directory_remembers_cursor_after_reentry, test_directory_remembers_marks_and_drops_missing_files, test_f1_menu_mouse_scroll_and_resize, test_f1_mc_menu_context_macros_and_prompt, test_f1_mc_menu_tagged_and_opposite_directory, test_file_operations_retry_with_sudo, test_rename_dialog_edit_cancel_and_mouse, test_column_separators_continue_through_empty_rows, test_q_does_not_quit, test_live_filter_spaces_backspace_and_escape, test_live_filter_and_enter_opens_or_runs, test_parent_reselects_departed_directory, test_attributes_sudo_retry_and_cancel, test_ctrl_x_unified_dialog, test_permission_dialog_mouse_buttons_and_resize, test_chown_mc_lists_and_cancel, test_dual_move_directory_and_failure_reasons, test_size_and_modification_columns, test_filter_clears_on_choice_and_keeps_current_file,
             test_filter_clears_on_directory_open_and_double_click, test_ctrl_h_hidden_files_and_filter, test_ctrl_h_independent_panes_and_resize,
             test_resize_preserves_panes_and_selection, test_dual_no_overwrite_and_literal_filter,
             test_filter_names_and_reset, test_dual_copy_move_and_independent_selection,
             test_dual_filter_and_mouse_focus, test_editor_fallback_and_arguments, test_mouse_rename_directory_wide_bar,
             test_move_multiple_relative_destination, test_f2_rename_and_no_overwrite, test_f4_editor_interactive,
             test_move_no_overwrite_and_cancel, test_copy_multiple, test_cut_move, test_mkdir_and_delete, test_no_overwrite,
             test_filename_with_spaces, test_delete_cancelled, test_no_copy_into_self,
             test_mouse_double_click_opens_folder, test_mouse_button_mkdir,
             test_mouse_prompt_ignores_click, test_mouse_mark_copy,
             test_mouse_compact_bar_and_wheel, test_reference_palette_and_highlighting,
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
