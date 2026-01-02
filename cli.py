"""CLI entry point for ALIP - Re-exports from alip.cli for backward compatibility.

This file maintains backward compatibility for direct execution:
    python cli.py --help

The actual implementation is in alip/cli.py
"""

from alip.cli import main

if __name__ == "__main__":
    main()
