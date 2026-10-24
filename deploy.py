"""Incremental deploy: upload only changed files, rebuild image, restart container.

Usage:
    python deploy.py                # incremental (default)
    python deploy.py --full         # re-upload everything
    python deploy.py --upload-only  # upload changed files, skip docker build/run/restart
"""

import json
import os
import posixpath
import sys
import time

import paramiko

LOCAL_ROOT = os.path.dirname(os.path.abspath(__file__))

EXCLUDE_DIRS = {".venv", ".git", "__pycache__", ".claude", "DATA", ".pytest_cache", ".idea", ".vscode"}
EXCLUDE_FILES = {".env", "server.json", "tatwir.backup", "deploy.py"}

CONTAINER = "supervisor_backend"
COMPOSE_ROOT = "/root/projects"


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name in EXCLUDE_FILES or name.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            yield full, rel


def run(client, cmd, quiet=False):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=900)
    out = stdout.read().decode(errors="replace")
    if not quiet:
        print(out.rstrip())
    return out


def main():
    full = "--full" in sys.argv
    upload_only = "--upload-only" in sys.argv
    started = time.time()

    with open(os.path.join(LOCAL_ROOT, "server.json")) as f:
        cfg = json.load(f)
    remote_root = cfg["project_path"]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(cfg["server_ip"], username="root", password=cfg["server_password"], timeout=20)
    sftp = client.open_sftp()

    # One listing of the remote tree beats a stat() round-trip per file.
    remote_meta = {}
    if not full:
        listing = run(client, f"cd {remote_root} && find . -type f -printf '%P\\t%s\\t%T@\\n' 2>/dev/null", quiet=True)
        for line in listing.splitlines():
            parts = line.strip().split("\t")
            if len(parts) == 3:
                try:
                    remote_meta[parts[0]] = (int(parts[1]), float(parts[2]))
                except ValueError:
                    pass

    made_dirs = set()
    uploaded = skipped = 0
    for local_path, rel in iter_files(LOCAL_ROOT):
        stat = os.stat(local_path)
        if not full and rel in remote_meta:
            r_size, r_mtime = remote_meta[rel]
            if r_size == stat.st_size and r_mtime >= stat.st_mtime - 1:
                skipped += 1
                continue

        remote_path = posixpath.join(remote_root, rel)
        remote_dir = posixpath.dirname(remote_path)
        if remote_dir not in made_dirs:
            run(client, f"mkdir -p '{remote_dir}'", quiet=True)
            made_dirs.add(remote_dir)
        sftp.put(local_path, remote_path)
        os.utime(local_path, (stat.st_atime, stat.st_mtime))
        sftp.utime(remote_path, (stat.st_atime, stat.st_mtime))
        uploaded += 1

    sftp.close()
    print(f"[upload] {uploaded} changed, {skipped} unchanged ({time.time() - started:.1f}s)")

    if upload_only:
        print("[upload-only] skipping docker build/run - restart the container manually")
        client.close()
        return

    if uploaded == 0 and not full:
        print("[build] nothing changed - skipping rebuild")
        client.close()
        return

    run(client, f"cd {COMPOSE_ROOT} && docker compose down {CONTAINER} 2>&1 | tail -10")
    run(client, f"cd {COMPOSE_ROOT} && docker compose up -d --build {CONTAINER} 2>&1 | tail -25")
    run(client, f"sleep 3 && docker ps --filter name={CONTAINER} --format '{{{{.Names}}}}\\t{{{{.Status}}}}'")
    run(client, f"docker logs --tail 15 {CONTAINER} 2>&1")

    print(f"[done] {time.time() - started:.1f}s")
    client.close()


if __name__ == "__main__":
    main()
