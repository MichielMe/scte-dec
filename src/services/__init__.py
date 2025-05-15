"""
Services package.

This package provides services for interacting with external systems.
"""

from .ffmpeg_service import (
    FFMPEGFrameData,
    FFMPEGResult,
    FFMPEGService,
    FFProbeResult,
    Packet,
)

__all__ = [
    "FFMPEGService",
    "FFMPEGResult",
    "FFProbeResult",
    "Packet",
    "FFMPEGFrameData",
]
