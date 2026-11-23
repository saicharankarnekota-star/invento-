#!/usr/bin/env python3
"""INVENTO AI Server Stopper.
Safely terminates any local development server running on ports 5001, 5050, or 5000.
"""
import os
import sys
import subprocess
import signal

PORTS = [5001, 5050]

def stop_server():
    print("=" * 55)
    print("  🛑 INVENTO AI — Stopping Local Server...")
    print("=" * 55)
    stopped_any = False

    for port in PORTS:
        try:
            cmd = ["lsof", "-ti", f":{port}"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            if output:
                pids = [int(p) for p in output.split() if p.isdigit()]
                for pid in pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"  ✓ Stopped process {pid} on port {port}")
                        stopped_any = True
                    except OSError:
                        pass
        except Exception:
            pass

    if stopped_any:
        print("\n  ✅ Server stopped successfully! Port 5001 is now free.")
    else:
        print("\n  ℹ️ No running server found on port 5001 or 5050.")
        print("  Port is already completely free and ready.")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    stop_server()
