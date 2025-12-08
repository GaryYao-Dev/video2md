"""
OpenAI Transcription Client using whisper-1 model
Provides similar interface to WhisperClient for compatibility
"""
import os
from pathlib import Path
from typing import Optional
import logging

from dotenv import load_dotenv
import openai

from video2md.models.transcription_models import TranscriptSegment, TranscriptResult

# Load environment variables
load_dotenv(override=True)

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class OpenAITranscribeClient:
    """
    OpenAI Transcription client using whisper-1 model
    
    Features:
    - Uses OpenAI's Whisper API (whisper-1 model)
    - Automatic language detection
    - Structured output with timestamps
    """
    
    def __init__(
        self,
        model: str = "whisper-1",
        api_key: Optional[str] = None,
    ):
        """
        Initialize OpenAI transcription client
        
        Args:
            model: OpenAI model to use (default: whisper-1)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        logger.info(f"Initialized OpenAI transcription client with model: {self.model}")
    
    def transcribe(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """
        Transcribe audio file using OpenAI API
        
        Args:
            audio_file_path: Path to audio file
            language: Language code (e.g., 'zh', 'en'). None for auto-detection
            prompt: Optional prompt to guide transcription
        
        Returns:
            TranscriptResult with language, full text, and segments
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If transcription fails
        """
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        logger.info(f"Transcribing with OpenAI: {audio_path.name}")
        logger.info(f"Language: {language or 'auto-detect'}")
        
        try:
            with open(audio_path, "rb") as f:
                transcribe_params = {
                    "model": self.model,
                    "file": f,
                    "response_format": "verbose_json",  # Get timestamps
                    "timestamp_granularities": ["segment"],
                }
                
                if language:
                    transcribe_params["language"] = language
                
                if prompt:
                    transcribe_params["prompt"] = prompt
                
                response = self.client.audio.transcriptions.create(**transcribe_params)
            
            # Process response
            segments = []
            for seg in getattr(response, 'segments', []):
                # OpenAI returns TranscriptionSegment objects with attributes, not dicts
                segments.append(TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip()
                ))
            
            # If no segments, create one from full text
            if not segments and hasattr(response, 'text'):
                segments.append(TranscriptSegment(
                    start=0.0,
                    end=0.0,
                    text=response.text.strip()
                ))
            
            full_text = response.text if hasattr(response, 'text') else " ".join(s.text for s in segments)
            detected_language = getattr(response, 'language', language or 'unknown')
            
            result = TranscriptResult(
                language=detected_language,
                full_text=full_text.strip(),
                segments=segments,
                raw={
                    "language": detected_language,
                    "duration": getattr(response, 'duration', 0.0),
                    "provider": "openai",
                    "model": self.model,
                }
            )
            
            logger.info(f"Transcription completed: {len(segments)} segments")
            logger.info(f"Detected language: {detected_language}")
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            raise
    
    def transcribe_with_video(
        self,
        video_file_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """
        Transcribe video file (extracts audio first, then transcribes)
        
        Args:
            video_file_path: Path to video file
            language: Language code (e.g., 'zh', 'en'). None for auto-detection
            prompt: Optional prompt to guide transcription
        
        Returns:
            TranscriptResult with language, full text, and segments
        """
        from video2md.utils.video_converter import VideoConverter
        import tempfile
        
        video_path = Path(video_file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_file_path}")
        
        converter = VideoConverter()
        
        # Check if it's a video file
        if not converter.is_video_file(video_path):
            # If it's already an audio file, just transcribe directly
            if converter.is_audio_file(video_path):
                logger.info("File is already audio, transcribing directly")
                return self.transcribe(
                    audio_file_path=str(video_path),
                    language=language,
                    prompt=prompt,
                )
            else:
                raise ValueError(f"Unsupported file format: {video_path.suffix}")
        
        logger.info(f"Extracting audio from video: {video_path.name}")
        
        # Convert video to audio
        temp_dir = tempfile.gettempdir()
        audio_file = converter.video_to_audio(
            input_path=video_path,
            output_dir=temp_dir,
            audio_format='mp3',  # OpenAI accepts mp3
            sample_rate=16000,
            channels=1
        )
        
        try:
            # Transcribe the extracted audio
            result = self.transcribe(
                audio_file_path=audio_file,
                language=language,
                prompt=prompt,
            )
            return result
            
        finally:
            # Clean up temporary audio file
            try:
                os.unlink(audio_file)
                logger.info(f"Cleaned up temporary audio file")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")


def main():
    """Command-line interface for OpenAI transcription client"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OpenAI transcription client using whisper-1 model"
    )
    parser.add_argument("input_file", type=str, help="Audio or video file to transcribe")
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., zh, en). Auto-detect if not specified"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Optional prompt to guide transcription"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (optional)"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="txt",
        choices=["txt", "json"],
        help="Output format (default: txt)"
    )
    
    args = parser.parse_args()
    
    # Initialize client
    client = OpenAITranscribeClient()
    
    # Transcribe
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {args.input_file}")
        return 1
    
    # Check if it's video or audio
    from video2md.utils.video_converter import VideoConverter
    converter = VideoConverter()
    
    if converter.is_video_file(input_path):
        result = client.transcribe_with_video(
            video_file_path=str(input_path),
            language=args.language,
            prompt=args.prompt,
        )
    else:
        result = client.transcribe(
            audio_file_path=str(input_path),
            language=args.language,
            prompt=args.prompt,
        )
    
    # Output results
    if args.format == "json":
        import json
        from dataclasses import asdict
        output = json.dumps(asdict(result), ensure_ascii=False, indent=2)
    else:
        output = result.full_text
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Results saved to: {args.output}")
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    exit(main())
