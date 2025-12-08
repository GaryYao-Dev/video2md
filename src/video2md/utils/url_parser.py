"""
URL parsing utilities for video downloaders.

This module provides utilities for:
- Resolving short URLs to their full form
- Extracting video IDs from various platform URLs
- Validating and normalizing video URLs
"""

from __future__ import annotations

import re
from typing import Final, Optional
from urllib.parse import parse_qs, urlparse

from video2md.downloaders.base import Platform


# Compiled regex patterns for video ID extraction
_PATTERNS: Final[dict[Platform, re.Pattern[str]]] = {
    Platform.BILIBILI: re.compile(r"(BV[A-Za-z0-9]+)"),
    Platform.YOUTUBE: re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|v/)([A-Za-z0-9_-]{11})"),
}


async def resolve_short_url(short_url: str, *, timeout: float = 10.0) -> str:
    """
    Resolve a short URL to its full form by following redirects.
    
    Supports:
    - Bilibili short links (b23.tv)
    - Douyin short links (v.douyin.com)
    - TikTok short links (vm.tiktok.com)
    
    Args:
        short_url: Short URL to resolve
        timeout: Request timeout in seconds
    
    Returns:
        Resolved full URL, or original URL if resolution fails
    
    Example:
        >>> await resolve_short_url("https://b23.tv/xxxxxx")
        "https://www.bilibili.com/video/BV1xxxxxxx"
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head(short_url)
            return str(response.url)
    except Exception:
        # Return original URL if resolution fails
        return short_url


def is_short_url(url: str) -> bool:
    """
    Check if URL is a short link that needs resolution.
    
    Args:
        url: URL to check
    
    Returns:
        True if URL is a known short link format
    """
    short_domains = [
        "b23.tv",
    ]
    
    try:
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in short_domains)
    except Exception:
        return False


def extract_video_id(url: str, platform: Platform) -> Optional[str]:
    """
    Extract video ID from a URL for the specified platform.
    
    Args:
        url: Video URL
        platform: Target platform
    
    Returns:
        Video ID string, or None if extraction fails
    
    Examples:
        >>> extract_video_id("https://www.bilibili.com/video/BV1xxx", Platform.BILIBILI)
        "BV1xxx"
        >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ", Platform.YOUTUBE)
        "dQw4w9WgXcQ"
    """
    if pattern := _PATTERNS.get(platform):
        if match := pattern.search(url):
            return match.group(1)
    
    # Special handling for YouTube query parameter
    if platform == Platform.YOUTUBE:
        try:
            parsed = urlparse(url)
            if 'v' in parse_qs(parsed.query):
                return parse_qs(parsed.query)['v'][0]
        except Exception:
            pass
    
    return None


def normalize_url(url: str) -> str:
    """
    Normalize a video URL by stripping unnecessary parts.
    
    - Removes query parameters that aren't needed
    - Ensures proper URL scheme
    - Trims whitespace
    
    Args:
        url: URL to normalize
    
    Returns:
        Normalized URL
    """
    url = url.strip()
    
    # Ensure URL has a scheme
    if not url.startswith(('http://', 'https://', '/')):
        # Check if it looks like a domain
        if '.' in url.split('/')[0]:
            url = 'https://' + url
    
    return url


def build_video_url(video_id: str, platform: Platform) -> str:
    """
    Build a canonical video URL from a video ID.
    
    Useful for generating consistent URLs from extracted IDs.
    
    Args:
        video_id: Platform-specific video ID
        platform: Target platform
    
    Returns:
        Canonical video URL
    
    Raises:
        ValueError: If platform is not supported for URL building
    """
    url_templates: dict[Platform, str] = {
        Platform.BILIBILI: "https://www.bilibili.com/video/{video_id}",
        Platform.YOUTUBE: "https://www.youtube.com/watch?v={video_id}",
    }
    
    if platform == Platform.LOCAL:
        raise ValueError("Cannot build URL for local files")
    
    if template := url_templates.get(platform):
        return template.format(video_id=video_id)
    
    raise ValueError(f"URL building not supported for platform: {platform}")


def get_video_page_url(video_id: str, platform: Platform) -> Optional[str]:
    """
    Get the canonical video page URL for embedding in markdown.
    
    This returns a user-friendly URL that can be used as a reference
    in the generated markdown documentation.
    
    Args:
        video_id: Platform-specific video ID
        platform: Target platform
    
    Returns:
        Canonical video page URL, or None for local files
    """
    if platform == Platform.LOCAL:
        return None
    
    try:
        return build_video_url(video_id, platform)
    except ValueError:
        return None
