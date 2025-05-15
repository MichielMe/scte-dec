#!/usr/bin/env python3
"""
Main entry point for the SCTE decoder.

This module provides a simple interface for running the SCTE decoder from the command line.
"""
import sys

from src.cli.mxf_decoder_cli import main

if __name__ == "__main__":
    # Ensure we use padding=2 by default
    if (
        len(sys.argv) > 1
        and "--html" in sys.argv
        and "--padding" not in sys.argv
        and "-p" not in sys.argv
    ):
        sys.argv.extend(["--padding", "2"])

    sys.exit(main())
