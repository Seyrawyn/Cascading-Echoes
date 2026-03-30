#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  WATERFALL CODE — Generative Art for Live Projection        ║
║                                                              ║
║  Animated waterfall with embedded scrolling source code.     ║
║  The water reacts to the text with ripples and turbulence.   ║
║                                                              ║
║  Controls:                                                   ║
║    F / F11  — Toggle fullscreen                              ║
║    ESC / Q  — Quit                                           ║
║    R        — Restart animation                              ║
║    N        — Next code file                                 ║
║    P        — Previous code file                             ║
║    1-5      — Switch color palette                           ║
║    SPACE    — Pause / resume scrolling                       ║
║    UP/DOWN  — Adjust scroll speed                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app import WaterfallApp


def main():
    config = Config()

    # Override defaults via environment variables if desired
    if os.environ.get("WATERFALL_FULLSCREEN"):
        config.fullscreen = True
    if os.environ.get("WATERFALL_PALETTE"):
        try:
            config.active_palette = int(os.environ["WATERFALL_PALETTE"])
        except ValueError:
            pass

    app = WaterfallApp(config)
    app.run()


if __name__ == "__main__":
    main()
