#!/usr/bin/env python3
"""
Kill process occupying a specified port.

Usage:
    python3 kill_port_occupation.py <port>
    python3 kill_port_occupation.py <port1> <port2> ...
    python3 kill_port_occupation.py 3000
    python3 kill_port_occupation.py 3000 5177

Examples:
    python3 kill_port_occupation.py 3000      # Kill process on port 3000
    python3 kill_port_occupation.py 3000 5177 # Kill processes on both ports
"""

import subprocess
import sys
import os


def find_process_on_port(port: int) -> int | None:
    """Find the PID of the process occupying the specified port."""
    try:
        # Use lsof to find the process on the specified port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            return [int(pid) for pid in pids if pid.isdigit()]
        return []
    except Exception as e:
        print(f"❌ Error finding process on port {port}: {e}")
        return []


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill the specified process."""
    try:
        # Get process info before killing
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True
            )
            process_name = result.stdout.strip() or "unknown"
        except Exception:
            process_name = "unknown"

        # Kill the process
        cmd = ["kill", "-9", str(pid)] if force else ["kill", str(pid)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Killed process {pid} ({process_name})")
            return True
        else:
            print(f"❌ Failed to kill process {pid}: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Error killing process {pid}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Error: Please specify at least one port number.")
        print("Example: python3 kill_port_occupation.py 3000")
        sys.exit(1)

    ports = []
    for arg in sys.argv[1:]:
        try:
            port = int(arg)
            if 1 <= port <= 65535:
                ports.append(port)
            else:
                print(f"⚠️  Invalid port number: {arg} (must be 1-65535)")
        except ValueError:
            print(f"⚠️  Invalid port number: {arg}")

    if not ports:
        print("Error: No valid port numbers provided.")
        sys.exit(1)

    print(f"🔍 Scanning ports: {', '.join(map(str, ports))}")
    print("-" * 50)

    killed_count = 0
    for port in ports:
        print(f"\nPort {port}:")
        pids = find_process_on_port(port)

        if not pids:
            print(f"  ℹ️  No process found on port {port}")
            continue

        print(f"  Found {len(pids)} process(es): {pids}")

        for pid in pids:
            if kill_process(pid):
                killed_count += 1

    print("-" * 50)
    print(f"\n✅ Summary: Killed {killed_count} process(es)")

    return 0 if killed_count == len(ports) else 1


if __name__ == "__main__":
    sys.exit(main())
