#!/usr/bin/env python3
import os
import socket
import sys


def _ensure_host_docker_internal():
    try:
        socket.getaddrinfo("host.docker.internal", 80)
        return
    except socket.gaierror:
        pass

    gateway = None
    try:
        with open("/proc/net/route") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1] == "00000000":
                    gw_hex = parts[2]
                    gw_bytes = bytes.fromhex(gw_hex)
                    gateway = ".".join(str(b) for b in reversed(gw_bytes))
                    break
    except (FileNotFoundError, OSError, ValueError):
        pass

    if gateway:
        with open("/etc/hosts", "a") as f:
            f.write(f"{gateway} host.docker.internal\n")


if __name__ == "__main__":
    _ensure_host_docker_internal()

    os.environ["ALEMBIC_STARTUP_CHECK"] = "false"

    os.execvp(sys.argv[1], sys.argv[1:])
