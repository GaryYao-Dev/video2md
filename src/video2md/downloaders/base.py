"""
Base classes and interfaces for video downloaders.

This module defines the core abstractions for the downloader system:
- Downloader: Abstract base class for all platform-specific downloaders
- DownloadResult: Data class containing download result metadata
- Custom exceptions for error handling
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class Platform(str, Enum):
    """Supported video platforms."""
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    DOUYIN = "douyin"
    TIKTOK = "tiktok"
    LOCAL = "local"


class DownloadError(Exception):
    """Base exception for download errors."""
    pass


class PlatformNotSupportedError(DownloadError):
    """Raised when the URL platform is not supported."""
    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"No downloader supports this URL: {url}")


class DownloadFailedError(DownloadError):
    """Raised when download fails after attempting."""
    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to download {url}: {reason}")


class CookieRequiredError(DownloadError):
    """Raised when platform requires cookie but not configured."""
    def __init__(self, platform: Platform) -> None:
        self.platform = platform
        super().__init__(
            f"Platform {platform.value} requires valid cookie configuration. "
            f"Please configure the cookie and try again."
        )


@dataclass(frozen=True)
class DownloadResult:
    """
    Immutable result of a successful video download.
    
    Attributes:
        file_path: Path to the downloaded video file
        title: Video title extracted from source
        video_id: Platform-specific video identifier
        platform: Source platform name
        duration: Video duration in seconds (if available)
        cover_url: URL to video thumbnail (if available)
        raw_info: Original metadata from the source API
    """
    file_path: Path
    title: str
    video_id: str
    platform: Platform
    duration: Optional[int] = None
    cover_url: Optional[str] = None
    raw_info: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.file_path.exists():
            raise ValueError(f"Downloaded file does not exist: {self.file_path}")
        if not self.title:
            object.__setattr__(self, 'title', self.video_id)


class Downloader(ABC):
    """
    Abstract base class for video downloaders.
    
    Each platform-specific downloader must implement:
    - download(): Downloads video to specified directory
    - supports(): Checks if URL is supported by this downloader
    
    Single Responsibility: Each implementation handles one platform.
    Open/Closed: New platforms extend this class without modifying existing code.
    Liskov Substitution: All implementations are interchangeable.
    Interface Segregation: Minimal interface with only essential methods.
    Dependency Inversion: High-level code depends on this abstraction.
    """
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform this downloader handles."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this downloader."""
        ...
    
    @property
    def requires_cookie(self) -> bool:
        """Whether this platform requires cookie configuration."""
        return False
    
    @abstractmethod
    async def download(
        self,
        url: str,
        output_dir: Path,
        *,
        download_video: bool = True,
        download_audio: bool = False,
        progress_hook: Optional[callable] = None,
    ) -> DownloadResult:
        """
        Download video from URL to the specified directory.
        
        Args:
            url: Video URL to download
            output_dir: Directory to save the downloaded file
            download_video: Whether to download video (default: True)
            download_audio: Whether to download audio only (default: False)
        
        Returns:
            DownloadResult with file path and metadata
        
        Raises:
            DownloadFailedError: If download fails
            CookieRequiredError: If cookie is required but not configured
        """
        ...
    
    @abstractmethod
    def supports(self, url: str) -> bool:
        """
        Check if this downloader can handle the given URL.
        
        Args:
            url: URL to check
        
        Returns:
            True if this downloader supports the URL
        """
        ...
    
    def validate_output_dir(self, output_dir: Path) -> Path:
        """
        Ensure output directory exists and is writable.
        
        Args:
            output_dir: Directory path to validate
        
        Returns:
            Validated Path object
        
        Raises:
            ValueError: If directory cannot be created or is not writable
        """
        output_dir = Path(output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Cannot create output directory: {output_dir}") from e
        
        if not output_dir.is_dir():
            raise ValueError(f"Output path is not a directory: {output_dir}")
        
        return output_dir
