"""
Douyin video downloader using yt-dlp.
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

# Lazy import
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
                "yt-dlp is required for Douyin downloads. "
                "Install with: pip install yt-dlp"
            ) from e
    return _yt_dlp


class DouyinDownloader(Downloader):
    """
    Douyin video downloader using yt-dlp.
    """
    
    @property
    def platform(self) -> Platform:
        return Platform.DOUYIN
    
    @property
    def name(self) -> str:
        return "Douyin"
        
    @property
    def requires_cookie(self) -> bool:
        return True
    
    def supports(self, url: str) -> bool:
        return "douyin.com" in url or "iesdouyin.com" in url
    
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
        import httpx
        from video2md.downloaders.douyin_api.client import DouyinAPI, LinkExtractor
        
        output_dir = self.validate_output_dir(output_dir)
        
        # Check for cookie in env if not provided
        if not cookie:
            cookie = os.environ.get("DOUYIN_COOKIE")
            
        # Extract ID
        video_id = LinkExtractor.get_id(url)
        if not video_id:
            # Fallback for standard URLs if regex didn't catch earlier
            # e.g. https://www.douyin.com/video/742...
            match = re.search(r"/video/(\d+)", url)
            if match:
                video_id = match.group(1)
            else:
                raise DownloadFailedError(url, "Could not extract video ID")

        try:
            async with DouyinAPI(cookie=cookie) as api:
                # Initialize cookies if needed
                await api.initialize()
                
                # Fetch metadata
                logger.info(f"Fetching metadata for ID: {video_id}")
                detail = await api.get_video_data(video_id)
                
                if not detail:
                    raise DownloadFailedError(url, "Failed to fetch video metadata")
                
                # Get video URL (prefer 720p or highest available)
                # Structure: detail['video']['play_addr']['url_list']
                video_info = detail.get("video", {})
                play_addr = video_info.get("play_addr", {})
                url_list = play_addr.get("url_list", [])
                
                if not url_list:
                    raise DownloadFailedError(url, "No video URL found in metadata")
                
                # Use the last URL usually (better quality or CDN) or first
                video_url = url_list[-1] 
                
                # Filename
                title = detail.get("desc", video_id)
                # Sanitize filename
                safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:50] # Limit length
                filename = f"{safe_title}_{video_id}.mp4"
                file_path = output_dir / filename
                
                if file_path.exists():
                    logger.info(f"File already exists: {file_path}")
                else:
                    logger.info(f"Downloading video from {video_url}")
                    async with api.client.stream("GET", video_url) as response:
                        response.raise_for_status()
                        total_size = int(response.headers.get("Content-Length", 0))
                        downloaded = 0
                        
                        with open(file_path, "wb") as f:
                            async for chunk in response.aiter_bytes(chunk_size=1024*1024):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if progress_hook and total_size > 0:
                                    # Simple progress report (could be improved)
                                    status = {
                                        'status': 'downloading',
                                        'downloaded_bytes': downloaded,
                                        'total_bytes': total_size,
                                        'filename': filename
                                    }
                                    # Adaptation for yt-dlp style hook if needed, or custom
                                    # Since our UI expects simple prints or direct hook:
                                    # We can try to format a yt-dlp like dict but for now we just log
                                    pass

                return DownloadResult(
                    file_path=file_path,
                    title=title,
                    video_id=video_id,
                    platform=Platform.DOUYIN,
                    duration=video_info.get("duration", 0) / 1000, # duration is usually in ms
                    cover_url=video_info.get("cover", {}).get("url_list", [None])[0],
                    raw_info=detail
                )

        except Exception as e:
            logger.error(f"Failed to download Douyin video: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise DownloadFailedError(url, str(e)) from e

    def _extract_and_download(self, yt_dlp: Any, url: str, opts: dict) -> dict:
        # Deprecated/Unused in new implementation
        pass

