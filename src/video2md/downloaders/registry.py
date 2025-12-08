"""
Platform registry and downloader factory.

This module provides:
- Platform detection from URLs
- Downloader factory to get appropriate downloader for a URL
- Registration of all available downloaders
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final, Optional

from video2md.downloaders.base import (
    Downloader,
    Platform,
    PlatformNotSupportedError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


# URL patterns for platform detection
# Each pattern maps to a Platform enum value
_PLATFORM_PATTERNS: Final[dict[Platform, tuple[re.Pattern[str], ...]]] = {
    Platform.BILIBILI: (
        re.compile(r"bilibili\.com/video/", re.IGNORECASE),
        re.compile(r"b23\.tv/", re.IGNORECASE),
    ),
    Platform.YOUTUBE: (
        re.compile(r"youtube\.com/watch", re.IGNORECASE),
        re.compile(r"youtu\.be/", re.IGNORECASE),
        re.compile(r"youtube\.com/shorts/", re.IGNORECASE),
    ),
    Platform.LOCAL: (
        re.compile(r"^/"),           # Unix absolute path
        re.compile(r"^[A-Za-z]:\\"),  # Windows absolute path
        re.compile(r"^\./"),          # Relative path
        re.compile(r"^\.\./"),        # Parent relative path
    ),
}

# Human-readable platform names
SUPPORTED_PLATFORMS: Final[dict[Platform, str]] = {
    Platform.BILIBILI: "哔哩哔哩 (Bilibili)",
    Platform.YOUTUBE: "YouTube",
    Platform.LOCAL: "本地文件 (Local)",
}


def detect_platform(url: str) -> Optional[Platform]:
    """
    Detect the platform from a video URL.
    
    Args:
        url: Video URL or file path to analyze
    
    Returns:
        Platform enum if detected, None otherwise
    
    Example:
        >>> detect_platform("https://www.bilibili.com/video/BV1xxx")
        Platform.BILIBILI
        >>> detect_platform("https://unknown.com/video")
        None
    """
    if not url:
        return None
    
    url = url.strip()
    
    for platform, patterns in _PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(url):
                return platform
    
    return None


def is_supported_url(url: str) -> bool:
    """
    Check if a URL is from a supported platform.
    
    Args:
        url: URL to check
    
    Returns:
        True if URL is supported
    """
    return detect_platform(url) is not None


# Lazy-loaded downloader instances
# Using late binding to avoid circular imports and allow optional dependencies
_downloaders: dict[Platform, Downloader] = {}
_downloaders_initialized: bool = False


def _initialize_downloaders() -> None:
    """
    Initialize all available downloaders.
    
    This is called lazily on first access to avoid import-time side effects.
    Downloaders that fail to initialize (e.g., missing dependencies) are skipped.
    """
    global _downloaders_initialized
    
    if _downloaders_initialized:
        return
    
    # Import and register downloaders
    # Each import is wrapped in try-except to handle missing dependencies gracefully
    
    try:
        from video2md.downloaders.bilibili import BilibiliDownloader
        _downloaders[Platform.BILIBILI] = BilibiliDownloader()
    except ImportError as e:
        import logging
        logging.getLogger(__name__).warning(f"BilibiliDownloader not available: {e}")
    
    try:
        from video2md.downloaders.youtube import YoutubeDownloader
        _downloaders[Platform.YOUTUBE] = YoutubeDownloader()
    except ImportError as e:
        import logging
        logging.getLogger(__name__).warning(f"YoutubeDownloader not available: {e}")
    
    try:
        from video2md.downloaders.local import LocalDownloader
        _downloaders[Platform.LOCAL] = LocalDownloader()
    except ImportError as e:
        import logging
        logging.getLogger(__name__).warning(f"LocalDownloader not available: {e}")
    
    _downloaders_initialized = True


def get_downloader(url: str) -> Downloader:
    """
    Get the appropriate downloader for a URL.
    
    Args:
        url: Video URL to download
    
    Returns:
        Downloader instance that can handle this URL
    
    Raises:
        PlatformNotSupportedError: If no downloader supports this URL
    
    Example:
        >>> downloader = get_downloader("https://www.bilibili.com/video/BV1xxx")
        >>> result = await downloader.download(url, output_dir)
    """
    _initialize_downloaders()
    
    platform = detect_platform(url)
    if platform is None:
        raise PlatformNotSupportedError(url)
    
    downloader = _downloaders.get(platform)
    if downloader is None:
        raise PlatformNotSupportedError(url)
    
    return downloader


def get_downloader_for_platform(platform: Platform) -> Optional[Downloader]:
    """
    Get the downloader for a specific platform.
    
    Args:
        platform: Platform enum value
    
    Returns:
        Downloader instance or None if not available
    """
    _initialize_downloaders()
    return _downloaders.get(platform)


def get_all_downloaders() -> Sequence[Downloader]:
    """
    Get all available downloaders.
    
    Returns:
        Sequence of all registered downloader instances
    """
    _initialize_downloaders()
    # Return unique downloaders (DouyinTikTok is registered twice)
    return list(dict.fromkeys(_downloaders.values()))


def get_available_platforms() -> list[Platform]:
    """
    Get list of platforms with available downloaders.
    
    Returns:
        List of Platform enum values that have working downloaders
    """
    _initialize_downloaders()
    return list(_downloaders.keys())
