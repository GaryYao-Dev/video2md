"""
TikTok video downloader using yt-dlp.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Final, Optional

from video2md.downloaders.base import (
    Downloader,
    DownloadFailedError,
    DownloadResult,
    Platform,
)

logger = logging.getLogger(__name__)

_yt_dlp: Any = None


def _get_yt_dlp() -> Any:
    global _yt_dlp
    if _yt_dlp is None:
        try:
            import yt_dlp
            _yt_dlp = yt_dlp
        except ImportError as e:
            raise ImportError(
                "yt-dlp is required for TikTok downloads. "
                "Install with: pip install yt-dlp"
            ) from e
    return _yt_dlp


class TiktokDownloader(Downloader):
    """
    TikTok video downloader using yt-dlp.
    """
    
    @property
    def platform(self) -> Platform:
        return Platform.TIKTOK
    
    @property
    def name(self) -> str:
        return "TikTok"

    @property
    def requires_cookie(self) -> bool:
        return True
    
    def supports(self, url: str) -> bool:
        return "tiktok.com" in url
    
    async def download(
        self,
        url: str,
        output_dir: Path,
        *,
        download_video: bool = True,
        download_audio: bool = False,
        progress_hook: Optional[callable] = None,
        cookie: Optional[str] = None,
    ) -> DownloadResult:
        import asyncio
        
        yt_dlp = _get_yt_dlp()
        output_dir = self.validate_output_dir(output_dir)
        
        if not cookie:
            cookie = os.environ.get("TIKTOK_COOKIE")
            
        ydl_opts = {
            'outtmpl': str(output_dir / "%(id)s.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
        }
        
        if cookie:
            ydl_opts['http_headers'] = {'Cookie': cookie}
            
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_and_download(yt_dlp, url, ydl_opts)
            )
            
            video_id = info.get('id', 'unknown')
            video_ext = info.get('ext', 'mp4')
            
            file_path = output_dir / f"{video_id}.{video_ext}"
            
            if not file_path.exists():
                 found = list(output_dir.glob(f"{video_id}.*"))
                 if found:
                     file_path = found[0]
            
            if not file_path.exists():
                raise DownloadFailedError(url, "Downloaded file not found")
                
            return DownloadResult(
                file_path=file_path,
                title=info.get('title', video_id),
                video_id=video_id,
                platform=Platform.TIKTOK,
                duration=info.get('duration'),
                cover_url=info.get('thumbnail'),
                raw_info=info
            )
            
        except Exception as e:
            logger.error(f"Failed to download TikTok video: {e}")
            raise DownloadFailedError(url, str(e)) from e

    def _extract_and_download(self, yt_dlp: Any, url: str, opts: dict) -> dict:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=True)
