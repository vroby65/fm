"""Navigazione archivi con GVfs/FUSE su bus privato, senza estrazione su disco."""
import hashlib
import io
import os
import pathlib
import runpy
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile

if "--session" not in sys.argv:
    with tempfile.TemporaryDirectory(prefix="fm-archives-") as tmp:
        root = pathlib.Path(tmp)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        temporary = root / "temporary"
        temporary.mkdir(mode=0o700)
        env = dict(os.environ, HOME=tmp, TMPDIR=str(temporary), XDG_RUNTIME_DIR=str(runtime),
                   XDG_DATA_HOME=str(root / "data"), XDG_CONFIG_HOME=str(root / "config"),
                   XDG_CACHE_HOME=str(root / "cache"), FM_ARCHIVE_TEST_ROOT=tmp)
        services = root / "data" / "dbus-1" / "services"
        services.mkdir(parents=True)
        for name in ("org.gnome.keyring", "org.freedesktop.secrets"):
            (services / (name + ".service")).write_text(
                f"[D-BUS Service]\nName={name}\nExec=/bin/false\n"
            )
        try:
            subprocess.run(["dbus-run-session", "--", sys.executable, __file__, "--session"],
                           env=env, check=True, timeout=150)
        finally:
            subprocess.run(["fusermount3", "-uz", str(runtime / "gvfs")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sys.exit()

root = pathlib.Path(os.environ["FM_ARCHIVE_TEST_ROOT"])
m = runpy.run_path(str(pathlib.Path(__file__).with_name("smoke.py")))
formats = [("zip", None), ("tar", "w"), ("tar.gz", "w:gz"),
           ("tar.bz2", "w:bz2"), ("tar.xz", "w:xz")]
if shutil.which("7z"):
    formats.append(("7z", "7z"))
for suffix, mode in formats:
    source = root / suffix
    source.mkdir()
    out = source / "out"
    out.mkdir()
    archive = source / ("pacchetto prova." + suffix)
    content = b"contenuto archivio"
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as file:
        file.writestr("interno.txt", b"archivio annidato")
    payload = {"cartella/file.txt": content, "annidato.zip": nested.getvalue()}
    outside = root / (suffix + "-esterno")
    outside.mkdir()
    (outside / "privato.txt").write_text("non seguire link esterni")
    if mode is None:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as file:
            for name, data in payload.items():
                file.writestr(name, data)
            info = zipfile.ZipInfo("esterno")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            file.writestr(info, str(outside))
    elif mode == "7z":
        fixture = root / "7z-payload"
        fixture.mkdir()
        for name, data in payload.items():
            target = fixture / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (fixture / "esterno").symlink_to(outside)
        subprocess.run(["7z", "a", "-snl", str(archive), "."], cwd=fixture,
                       stdout=subprocess.DEVNULL, check=True)
    else:
        with tarfile.open(archive, mode) as file:
            for name, data in payload.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                file.addfile(info, io.BytesIO(data))
            info = tarfile.TarInfo("esterno")
            info.type = tarfile.SYMTYPE
            info.linkname = str(outside)
            file.addfile(info)
    before = hashlib.sha256(archive.read_bytes()).digest()
    session = m["Session"](source)
    try:
        session.key(m["END"])
        session.key(m["ENTER"])
        deadline = time.monotonic() + 15
        while b"cartella" not in session.output[-12000:] and time.monotonic() < deadline:
            session.drain(.1)
            if b"Apertura archivio non riuscita" in session.output[-3000:]:
                break
        if suffix == "7z" and b"does not support seeking" in session.output:
            assert hashlib.sha256(archive.read_bytes()).digest() == before
            print("PASS 7z unsupported seeking reported without changing original", flush=True)
            continue
        if b"cartella" not in session.output[-12000:]:
            import re
            print(re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", bytes(session.output)).decode(errors="replace"), flush=True)
            subprocess.run(["gio", "mount", "-l"])
        assert b"cartella" in session.output[-12000:]
        assert b"!/" in session.output[-12000:], "Percorso archivio non leggibile"
        session.key(b"\x1b[H")
        session.key(m["DOWN"])
        session.key(m["RIGHT"])
        assert b"file.txt" in session.output[-12000:]
        session.key(m["F5"])
        session.type(str(out))
        session.key(m["ENTER"])
        assert (out / "file.txt").read_bytes() == content
        session.key(m["F6"])
        assert b"sola lettura" in session.output[-5000:]
        session.key(m["F8"])
        assert b"sola lettura" in session.output[-5000:]
        session.key(m["LEFT"])
        if suffix != "7z":
            session.key(b"\x06")
            session.type("esterno")
            session.key(m["ENTER"])
            assert b"privato.txt" not in session.output[-5000:], "Seguito link esterno"
            session.key(m["F7"])
            assert b"sola lettura" in session.output[-5000:], "Uscita dalla radice archivio tramite link"
        session.key(b"\x06")
        session.type("annidato")
        session.key(m["ENTER"])
        deadline = time.monotonic() + 15
        while b"interno.txt" not in session.output[-12000:] and time.monotonic() < deadline:
            session.drain(.1)
            if b"Apertura archivio non riuscita" in session.output[-3000:]:
                break
        if b"interno.txt" not in session.output[-12000:]:
            import re
            print(re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", bytes(session.output)).decode(errors="replace"), flush=True)
        assert b"interno.txt" in session.output[-12000:], "Archivio annidato non aperto"
        session.key(m["LEFT"])
        session.key(m["LEFT"])
        assert str(source).encode() in session.output[-12000:]
        session.key(m["RIGHT"])  # torna sul file archivio appena lasciato
        session.drain(.3)
        assert b"!/" in session.output[-10000:]
        assert hashlib.sha256(archive.read_bytes()).digest() == before
        print("PASS", suffix, "navigation/copy/read-only/nested/return", flush=True)
    finally:
        session.close()
        assert not list(pathlib.Path(os.environ["TMPDIR"]).glob("fm-archive.*")), "Cache archivio non rimossa"

    if suffix == "zip":
        session = m["Session"](out, cols=120)
        try:
            session.key(b"\t")
            session.key(m["LEFT"])
            session.key(m["END"])
            session.key(m["ENTER"])
            deadline = time.monotonic() + 10
            while b"!/" not in session.output[-12000:] and time.monotonic() < deadline:
                session.drain(.1)
            session.key(b"\t")
            session.key(m["F5"])
            assert b"destinazione in sola lettura" in session.output[-5000:]
            session.key(b"\t")
            session.key(b"\x1b[H")
            session.key(m["DOWN"])
            session.key(m["F5"])
            assert (out / "cartella" / "file.txt").read_bytes() == content
            print("PASS dual pane archive copy and read-only destination", flush=True)
        finally:
            session.close()

invalid = root / "invalid"
invalid.mkdir()
(invalid / "rotto.zip").write_text("Questo non e' uno ZIP")
session = m["Session"](invalid)
try:
    session.key(m["ENTER"])
    deadline = time.monotonic() + 10
    while b"Apertura archivio non riuscita" not in session.output and time.monotonic() < deadline:
        session.drain(.1)
    assert b"Apertura archivio non riuscita" in session.output
    assert (invalid / "rotto.zip").read_text() == "Questo non e' uno ZIP"
    print("PASS corrupt archive error and original preservation", flush=True)
finally:
    session.close()
