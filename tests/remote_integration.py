"""Integrazione FTP/SFTP reale su loopback, con bus D-Bus e credenziali temporanei.

Opzionale: richiede paramiko, pyftpdlib e lo stack GIO/GVfs/FUSE installato.
Non usa server, configurazioni SSH o portachiavi personali.
"""

import sys, os, pathlib, tempfile, subprocess, threading, socket, errno, time, runpy, logging
import paramiko
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

logging.getLogger("paramiko").setLevel(logging.CRITICAL)
from pyftpdlib.log import config_logging

config_logging(level=logging.ERROR)
SCRIPT = str(pathlib.Path(__file__).resolve().parents[1])


class SFTP(paramiko.SFTPServerInterface):
    root = None

    def path(self, p):
        target = (self.root / p.lstrip("/")).resolve()
        if target != self.root and self.root not in target.parents:
            raise PermissionError(errno.EACCES, "Denied")
        return str(target)

    def canonicalize(self, p):
        return "/" + os.path.normpath("/" + p).lstrip("/")

    def stat(self, p):
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(self.path(p)))
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    lstat = stat

    def list_folder(self, p):
        try:
            result = []
            for f in pathlib.Path(self.path(p)).iterdir():
                a = paramiko.SFTPAttributes.from_stat(f.stat())
                a.filename = f.name
                result.append(a)
            return result
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def open(self, p, flags, attr):
        try:
            fd = os.open(self.path(p), flags, 0o600)
            f = os.fdopen(fd, "wb" if flags & (os.O_WRONLY | os.O_RDWR) else "rb")
            h = paramiko.SFTPHandle(flags)
            h.readfile = f
            h.writefile = f
            return h
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def mkdir(self, p, attr):
        try:
            os.mkdir(self.path(p))
            return paramiko.SFTP_OK
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def rmdir(self, p):
        try:
            os.rmdir(self.path(p))
            return paramiko.SFTP_OK
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def remove(self, p):
        try:
            os.unlink(self.path(p))
            return paramiko.SFTP_OK
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def rename(self, a, b):
        try:
            os.rename(self.path(a), self.path(b))
            return paramiko.SFTP_OK
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def chattr(self, p, attr):
        try:
            if attr.st_mode is not None:
                os.chmod(self.path(p), attr.st_mode)
            if attr.st_atime is not None:
                os.utime(self.path(p), (attr.st_atime, attr.st_mtime))
            return paramiko.SFTP_OK
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)


class Auth(paramiko.ServerInterface):
    key = None
    kind = "password"

    def check_auth_password(self, user, password):
        return (
            paramiko.AUTH_SUCCESSFUL
            if self.kind == "password"
            and user == "fmtest"
            and password == "test-secret"
            else paramiko.AUTH_FAILED
        )

    def check_auth_publickey(self, user, key):
        return (
            paramiko.AUTH_SUCCESSFUL
            if self.kind == "key" and user == "fmtest" and key == self.key
            else paramiko.AUTH_FAILED
        )

    def get_allowed_auths(self, user):
        return "publickey,password"

    def check_channel_request(self, kind, chanid):
        return (
            paramiko.OPEN_SUCCEEDED
            if kind == "session"
            else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        )


def ssh_server(root, key, kind):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    host_key = paramiko.RSAKey.generate(2048)
    auth = type("TestAuth", (Auth,), {"key": key, "kind": kind})
    sftp = type("TestSFTP", (SFTP,), {"root": root})

    def serve():
        while True:
            try:
                client, _ = sock.accept()
            except OSError:
                return
            t = paramiko.Transport(client)
            t.add_server_key(host_key)
            t.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp)
            try:
                t.start_server(server=auth())
            except Exception:
                t.close()

    threading.Thread(target=serve, daemon=True).start()
    return sock, port, host_key


if "--session" not in sys.argv:
    with tempfile.TemporaryDirectory(prefix="fm-remote-") as tmp:
        root = pathlib.Path(tmp)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        env = os.environ.copy()
        env.update(
            XDG_RUNTIME_DIR=str(runtime),
            XDG_DATA_HOME=str(root / "data"),
            FM_REMOTE_TEST_ROOT=tmp,
        )
        services = root / "data" / "dbus-1" / "services"
        services.mkdir(parents=True)
        for name in ("org.gnome.keyring", "org.freedesktop.secrets"):
            (services / (name + ".service")).write_text(
                f"[D-BUS Service]\nName={name}\nExec=/bin/false\n"
            )
        try:
            subprocess.run(
                ["dbus-run-session", "--", sys.executable, __file__, "--session"],
                env=env,
                check=True,
                timeout=150,
            )
        finally:
            # Solo il mount FUSE privato del test, anche se il bus e' gia' terminato.
            subprocess.run(
                ["fusermount3", "-uz", str(runtime / "gvfs")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    sys.exit()

root = pathlib.Path(os.environ["FM_REMOTE_TEST_ROOT"])
config = root / "config"
config.mkdir()
os.environ["XDG_CONFIG_HOME"] = str(config)
bin_dir = root / "bin"
bin_dir.mkdir()
ssh_config = root / "ssh_config"
ssh_config.write_text(
    f"Host *\n  UserKnownHostsFile {root}/known_hosts\n  StrictHostKeyChecking yes\n  IdentityFile {root}/id_rsa\n  IdentitiesOnly yes\n"
)
wrapper = bin_dir / "ssh"
wrapper.write_text(f'#!/bin/sh\nexec /usr/bin/ssh -F "{ssh_config}" "$@"\n')
wrapper.chmod(0o755)
os.environ["PATH"] = str(bin_dir) + ":" + os.environ["PATH"]
key = paramiko.RSAKey.generate(2048)
key.write_private_key_file(str(root / "id_rsa"))
(root / "id_rsa").chmod(0o600)
ports = []
known = []
stops = []
for kind in ("password", "key"):
    remote = root / f"ssh-{kind}"
    remote.mkdir()
    (remote / "hello.txt").write_text("SSH " + kind)
    sock, port, host_key = ssh_server(remote, key, kind)
    stops.append(sock)
    known.append(f"[127.0.0.1]:{port} {host_key.get_name()} {host_key.get_base64()}\n")
    ports.append(("ssh", kind, port, remote))
(root / "known_hosts").write_text("".join(known))
ftp_root = root / "ftp"
ftp_root.mkdir()
(ftp_root / "hello.txt").write_text("FTP password")
a = DummyAuthorizer()
a.add_user("fmtest", "test-secret", str(ftp_root), perm="elradfmwMT")
handler = type("TestFTP", (FTPHandler,), {"authorizer": a})
ftp = FTPServer(("127.0.0.1", 0), handler)
ftp_port = ftp.socket.getsockname()[1]
threading.Thread(target=ftp.serve_forever, kwargs={"timeout": 0.1}, daemon=True).start()
ports.append(("ftp", "password", ftp_port, ftp_root))
subprocess.run(
    ["dbus-update-activation-environment", "PATH", "XDG_CONFIG_HOME"], check=True
)
m = runpy.run_path(SCRIPT + "/tests/smoke.py")
try:
    for protocol, kind, port, remote in ports:
        print("TEST", protocol, kind, port, flush=True)
        out = root / f"out-{protocol}-{kind}"
        out.mkdir()
        upload = root / f"upload-{protocol}-{kind}"
        upload.mkdir()
        (upload / "upload.txt").write_text("upload " + protocol)
        s = m["Session"](
            pathlib.Path("/"), cols=96, env={"XDG_CONFIG_HOME": str(config)}
        )
        try:
            s.key(m["LEFT"])
            s.key(m["DOWN"])
            if protocol == "ftp":
                s.key(m["DOWN"])
            s.key(m["ENTER"])
            s.type(f"fmtest@127.0.0.1:{port}")
            s.key(b"\t")
            if kind == "password":
                s.type("test-secret")
            s.key(m["ENTER"])
            deadline = time.monotonic() + 40
            while b"hello.txt" not in s.output and time.monotonic() < deadline:
                s.drain(0.15)
                if b"Connessione non riuscita:" in s.output:
                    break
            if b"hello.txt" not in s.output:
                print(bytes(s.output[-3000:]).decode(errors="replace"), flush=True)
            assert b"hello.txt" in s.output, "Remote listing failed"
            assert b"test-secret" not in s.output
            s.key(m["F7"])
            s.type("nuova")
            s.key(m["ENTER"])
            deadline = time.monotonic() + 5
            while not (remote / "nuova").is_dir() and time.monotonic() < deadline:
                s.drain(0.15)
            if not (remote / "nuova").is_dir():
                print(bytes(s.output[-2200:]).decode(errors="replace"), flush=True)
            assert (remote / "nuova").is_dir()
            s.key(b"\x1b[H")
            s.key(m["DOWN"])  # nuova e' una directory, hello e' il file
            s.key(m["END"])
            s.key(m["F5"])
            s.type(str(out))
            s.key(m["ENTER"])
            deadline = time.monotonic() + 5
            while not (out / "hello.txt").exists() and time.monotonic() < deadline:
                s.drain(0.15)
            assert (
                (out / "hello.txt")
                .read_text()
                .startswith(protocol.upper() if protocol == "ftp" else "SSH")
            )
            s.key(m["LEFT"])
            s.drain(0.2)
            assert b"Connessioni" in s.output[-12000:]
            if protocol == "ssh" and kind == "password":
                s.key(m["END"])
                s.key(m["F2"])
                s.type("Server laboratorio")
                s.key(m["ENTER"])
                profiles = list((config / "fm" / "connections").iterdir())
                assert len(profiles) == 1
                assert profiles[0].read_text().splitlines()[2] == "Server laboratorio"
            print("PASS listing/mkdir/download", protocol, kind, flush=True)
        finally:
            s.close()
        s = m["Session"](upload, cols=120, env={"XDG_CONFIG_HOME": str(config)})
        try:
            s.key(b"\t")
            for _ in range(len(upload.parts)):
                s.key(m["LEFT"])
            if protocol == "ssh" and kind == "password":
                s.key(m["END"])  # riapre la connessione salvata e rinominata
            else:
                s.key(m["DOWN"])
                if protocol == "ftp":
                    s.key(m["DOWN"])
            s.key(m["ENTER"])
            assert f"fmtest@127.0.0.1:{port}".encode() in s.output[-12000:]
            s.key(b"\t")
            start = len(s.output)
            s.key(m["ENTER"])
            deadline = time.monotonic() + 10
            while b"hello.txt" not in s.output[start:] and time.monotonic() < deadline:
                s.drain(0.15)
            s.key(b"\t")
            start = len(s.output)
            s.key(m["F5"])
            deadline = time.monotonic() + 5
            while not (remote / "upload.txt").exists() and time.monotonic() < deadline:
                s.drain(0.15)
            deadline = time.monotonic() + 8
            while (
                b"Operazione completata:" not in s.output[start:]
                and time.monotonic() < deadline
            ):
                s.drain(0.15)
            if b"Operazione completata: 1." not in s.output[-8000:]:
                print(bytes(s.output[-2200:]).decode(errors="replace"), flush=True)
            assert b"Operazione completata: 1." in s.output[start:]
            assert (remote / "upload.txt").read_text() == "upload " + protocol
            (upload / "move.txt").write_text("move " + protocol)
            s.key(b"r")
            s.key(b"\x1b[H")
            s.key(m["DOWN"])
            start = len(s.output)
            s.key(m["F6"])
            deadline = time.monotonic() + 8
            while (
                b"Operazione completata:" not in s.output[start:]
                and time.monotonic() < deadline
            ):
                s.drain(0.15)
            assert b"Operazione completata: 1." in s.output[start:]
            assert (remote / "move.txt").read_text() == "move " + protocol
            assert not (upload / "move.txt").exists()
            print("PASS upload/move and remembered address", protocol, kind, flush=True)
        finally:
            s.close()
        if kind == "password":
            scheme = "sftp" if protocol == "ssh" else "ftp"
            subprocess.run(
                ["gio", "mount", "-u", f"{scheme}://fmtest@127.0.0.1:{port}/"],
                check=True,
            )
            s = m["Session"](pathlib.Path("/"), env={"XDG_CONFIG_HOME": str(config)})
            try:
                s.key(m["LEFT"])
                s.key(m["DOWN"])
                if protocol == "ftp":
                    s.key(m["DOWN"])
                s.key(m["ENTER"])
                s.key(b"\t")
                s.type("wrong-password")
                s.key(m["ENTER"])
                deadline = time.monotonic() + 35
                while (
                    b"Connessione non riuscita:" not in s.output
                    and time.monotonic() < deadline
                ):
                    s.drain(0.15)
                assert b"Connessione non riuscita:" in s.output
                assert b"wrong-password" not in s.output
                assert b"Autenticazione non riuscita" in s.output
                print("PASS authentication failure", protocol, flush=True)
            finally:
                s.close()
    profiles = list((config / "fm" / "connections").iterdir())
    assert len(profiles) == 3, "Connessioni duplicate o mancanti"
    assert sum(f.read_text().splitlines()[2] == "Server laboratorio" for f in profiles) == 1
    print("PASS saved connections, rename and duplicate prevention", flush=True)
    for file in (config / "fm").rglob("*"):
        if not file.is_file():
            continue
        assert "test-secret" not in file.read_text()
        assert "wrong-password" not in file.read_text()
        assert file.stat().st_mode & 0o777 == 0o600
finally:
    ftp.close_all()
    for sock in stops:
        sock.close()
