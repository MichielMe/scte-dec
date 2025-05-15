"""
Command-line interface package.

This package provides command-line interfaces for various tools.
"""

from .mxf_decoder_cli import main as mxf_decoder_main

__all__ = ["mxf_decoder_main"]
