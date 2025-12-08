"""
YouTube video downloader using yt-dlp.

Supports:
- Standard watch URLs: https://www.youtube.com/watch?v=xxxxx
- Short links: https://youtu.be/xxxxx
- Shorts: https://www.youtube.com/shorts/xxxxx
- Embedded URLs: https://www.youtube.com/embed/xxxxx
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Final

from video2md.downloaders.base import (
    Downloader,
    DownloadFailedError,
    DownloadResult,
    Platform,
)

logger = logging.getLogger(__name__)

# Lazy import yt-dlp to handle missing dependency gracefully
_yt_dlp: Any = None


def _get_yt_dlp() -> Any:
    """Lazy load yt-dlp module."""
    global _yt_dlp
    if _yt_dlp is None:
        try:
            import yt_dlp
            _yt_dlp = yt_dlp
        except ImportError as e:
            raise ImportError(
                "yt-dlp is required for YouTube downloads. "
                "Install with: pip install yt-dlp"
            ) from e
    return _yt_dlp


class YoutubeDownloader(Downloader):
    """
    YouTube video downloader using yt-dlp.
    
    Handles video and audio extraction from YouTube.
    Supports various URL formats including shorts and embeds.
    """
    
    # URL patterns this downloader supports
    _PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
        re.compile(r"youtube\.com/watch", re.IGNORECASE),
        re.compile(r"youtu\.be/", re.IGNORECASE),
        re.compile(r"youtube\.com/shorts/", re.IGNORECASE),
        re.compile(r"youtube\.com/embed/", re.IGNORECASE),
        re.compile(r"youtube\.com/v/", re.IGNORECASE),
    )
    
    # Video ID extraction pattern (11 characters)
    _VIDEO_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"(?:v=|youtu\.be/|shorts/|embed/|v/)([A-Za-z0-9_-]{11})"
    )
    
    @property
    def platform(self) -> Platform:
        return Platform.YOUTUBE
    
    @property
    def name(self) -> str:
        return "YouTube"
    
    def supports(self, url: str) -> bool:
        """Check if URL is a YouTube video URL."""
        if not url:
            return False
        return any(pattern.search(url) for pattern in self._PATTERNS)
    
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
        Download video from YouTube.
        
        Args:
            url: YouTube video URL
            output_dir: Directory to save the video
            download_video: Whether to download video (default: True)
            download_audio: Whether to download audio only (default: False)
            progress_hook: Optional callback for progress updates
        
        Returns:
            DownloadResult with file path and metadata
        
        Raises:
            DownloadFailedError: If download fails
        """
        import asyncio
        
        yt_dlp = _get_yt_dlp()
        output_dir = self.validate_output_dir(output_dir)
        
        # Configure yt-dlp options
        output_template = str(output_dir / "%(id)s.%(ext)s")
        
        if download_audio and not download_video:
            # Audio only mode
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': output_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }
            expected_ext = 'mp3'
        else:
            # Video mode (default)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': output_template,
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }
            expected_ext = 'mp4'
            
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            # Run yt-dlp in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_and_download(yt_dlp, url, ydl_opts)
            )
            
            # Determine output file path
            video_id = info.get('id', 'unknown')
            file_path = output_dir / f"{video_id}.{expected_ext}"
            
            # Handle case where yt-dlp uses different extension
            if not file_path.exists():
                # Try to find the actual downloaded file
                possible_files = list(output_dir.glob(f"{video_id}.*"))
                if possible_files:
                    file_path = possible_files[0]
                else:
                    raise DownloadFailedError(url, f"Downloaded file not found: {file_path}")
            
            logger.info(f"Downloaded YouTube video: {file_path}")
            
            return DownloadResult(
                file_path=file_path,
                title=info.get('title', video_id),
                video_id=video_id,
                platform=Platform.YOUTUBE,
                duration=info.get('duration'),
                cover_url=info.get('thumbnail'),
                raw_info={
                    'uploader': info.get('uploader'),
                    'channel': info.get('channel'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'description': info.get('description'),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                },
            )
            
        except Exception as e:
            logger.error(f"Failed to download YouTube video: {e}")
            raise DownloadFailedError(url, str(e)) from e
    
    def _extract_and_download(
        self,
        yt_dlp: Any,
        url: str,
        ydl_opts: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract info and download video using yt-dlp.
        
        This method runs synchronously and should be called from a thread pool.
        """
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info or {}
    
    def extract_video_id(self, url: str) -> str | None:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube video URL
        
        Returns:
            11-character video ID or None if not found
        """
        match = self._VIDEO_ID_PATTERN.search(url)
        return match.group(1) if match else None
