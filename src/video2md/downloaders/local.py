"""
Local file handler for files already on disk.

This module handles "downloading" of local files by copying or
moving them to the output directory. It allows the same processing
pipeline to work with both remote URLs and local files.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Final

from video2md.downloaders.base import (
    Downloader,
    DownloadFailedError,
    DownloadResult,
    Platform,
)

logger = logging.getLogger(__name__)


class LocalDownloader(Downloader):
    """
    Local file handler.
    
    Handles local video files by creating symlinks or copying them
    to the output directory. This allows local files to go through
    the same processing pipeline as downloaded videos.
    """
    
    # Supported video file extensions
    VIDEO_EXTENSIONS: Final[frozenset[str]] = frozenset({
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpeg', '.mpg', '.3gp',
    })
    
    # Supported audio file extensions
    AUDIO_EXTENSIONS: Final[frozenset[str]] = frozenset({
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma',
    })
    
    @property
    def platform(self) -> Platform:
        return Platform.LOCAL
    
    @property
    def name(self) -> str:
        return "本地文件 (Local)"
    
    def supports(self, url: str) -> bool:
        """
        Check if the path is a local file.
        
        Supports:
        - Absolute paths: /path/to/file.mp4
        - Relative paths: ./video.mp4, ../video.mp4
        - Windows paths: C:\\path\\to\\file.mp4
        """
        if not url:
            return False
        
        url = url.strip()
        
        # Check for path-like patterns
        path_patterns = [
            r"^/",            # Unix absolute path
            r"^[A-Za-z]:\\",  # Windows absolute path
            r"^\./",          # Relative path
            r"^\.\./",        # Parent relative path
        ]
        
        for pattern in path_patterns:
            if re.match(pattern, url):
                return True
        
        # Also check if it's a file path without prefix that exists
        path = Path(url)
        if path.exists() and path.is_file():
            return True
        
        return False
    
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
        """
        "Download" a local file by copying it to the output directory.
        
        Args:
            url: Path to the local file
            output_dir: Directory to copy the file to
            download_video: Ignored for local files
            download_audio: Ignored for local files
        
        Returns:
            DownloadResult with copied file path and metadata
        
        Raises:
            DownloadFailedError: If file doesn't exist or can't be copied
        """
        source_path = Path(url).resolve()
        
        # Validate source file exists
        if not source_path.exists():
            raise DownloadFailedError(url, f"File does not exist: {source_path}")
        
        if not source_path.is_file():
            raise DownloadFailedError(url, f"Path is not a file: {source_path}")
        
        # Validate file extension
        extension = source_path.suffix.lower()
        if extension not in self.VIDEO_EXTENSIONS and extension not in self.AUDIO_EXTENSIONS:
            raise DownloadFailedError(
                url, 
                f"Unsupported file type: {extension}. "
                f"Supported: {', '.join(sorted(self.VIDEO_EXTENSIONS | self.AUDIO_EXTENSIONS))}"
            )
        
        output_dir = self.validate_output_dir(output_dir)
        
        # Determine output file path
        video_id = source_path.stem
        dest_path = output_dir / source_path.name
        
        try:
            # If source is already in output dir, just use it
            if source_path.parent.resolve() == output_dir.resolve():
                logger.info(f"File already in output directory: {source_path}")
                dest_path = source_path
            else:
                # Copy file to output directory
                logger.info(f"Copying local file: {source_path} -> {dest_path}")
                shutil.copy2(source_path, dest_path)
            
            # Get file metadata
            stat = dest_path.stat()
            
            return DownloadResult(
                file_path=dest_path,
                title=video_id,
                video_id=video_id,
                platform=Platform.LOCAL,
                duration=None,  # We could use ffprobe here, but keeping it simple
                cover_url=None,
                raw_info={
                    'source_path': str(source_path),
                    'file_size': stat.st_size,
                    'modified_time': stat.st_mtime,
                },
            )
            
        except OSError as e:
            logger.error(f"Failed to copy local file: {e}")
            raise DownloadFailedError(url, f"Failed to copy file: {e}") from e
