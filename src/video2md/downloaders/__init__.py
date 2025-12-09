"""
Video Downloaders Module

This module provides a unified interface for downloading videos from various platforms.
Supports Bilibili, YouTube, Douyin, TikTok, and local files.

Architecture follows SOLID principles:
- S: Each downloader handles one platform
- O: New platforms can be added via new Downloader implementations
- L: All downloaders are substitutable through the Downloader interface
- I: Minimal interface - just download() and supports()
- D: High-level modules depend on Downloader abstraction

Usage:
    from video2md.downloaders import get_downloader, detect_platform
    
    url = "https://www.bilibili.com/video/BVxxxxx"
    downloader = get_downloader(url)
    if downloader:
        result = await downloader.download(url, output_dir)
"""

from video2md.downloaders.base import (
    Downloader,
    DownloadResult,
    DownloadError,
    PlatformNotSupportedError,
    DownloadFailedError,
    Platform,
)
from video2md.downloaders.registry import (
    get_downloader,
    detect_platform,
    get_all_downloaders,
    SUPPORTED_PLATFORMS,
)

__all__ = [
    # Base classes
    "Downloader",
    "DownloadResult",
    "Platform",
    # Exceptions
    "DownloadError",
    "PlatformNotSupportedError",
    "DownloadFailedError",
    # Registry functions
    "get_downloader",
    "detect_platform",
    "get_all_downloaders",
    "SUPPORTED_PLATFORMS",
]
