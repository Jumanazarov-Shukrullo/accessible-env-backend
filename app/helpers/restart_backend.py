#!/usr/bin/env python3
import os
import subprocess
import time


def restart_backend():
    print("🔄 Restarting backend server...")

    # Kill existing uvicorn processes
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], check=False)
        time.sleep(2)
    except Exception:
        pass

    # Change to backend directory
    os.chdir("backend")

    # Start the backend server
    subprocess.run(
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ]
    )


if __name__ == "__main__":
    restart_backend()
