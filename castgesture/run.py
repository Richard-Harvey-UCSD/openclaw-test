#!/usr/bin/env python3
"""CastGesture — One-command launcher."""

import subprocess
import sys
import webbrowser
import time
import os

def main():
    port = int(os.environ.get("CASTGESTURE_PORT", "7555"))
    host = os.environ.get("CASTGESTURE_HOST", "0.0.0.0")

    print(r"""
   ____          _    ____           _
  / ___|__ _ ___| |_ / ___| ___  ___| |_ _   _ _ __ ___
 | |   / _` / __| __| |  _ / _ \/ __| __| | | | '__/ _ \
 | |__| (_| \__ \ |_| |_| |  __/\__ \ |_| |_| | | |  __/
  \____\__,_|___/\__|\____|\___|_|___/\__|\__,_|_|  \___|
                                    Gesture-powered streaming effects
    """)
    print(f"  🚀 Starting CastGesture server on http://localhost:{port}")
    print(f"  🎮 Control Panel: http://localhost:{port}/panel/")
    print(f"  🖥️  OBS Overlay:   http://localhost:{port}/overlay/")
    print(f"  📄 Landing Page:   http://localhost:{port}/landing/")
    print()

    # Open control panel in browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}/panel/")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Start the server
    try:
        import uvicorn
        uvicorn.run(
            "castgesture.server.app:app",
            host=host,
            port=port,
            reload=False,
            log_level="info",
        )
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
