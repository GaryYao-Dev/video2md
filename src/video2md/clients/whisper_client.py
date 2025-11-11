"""
Local Whisper Client using faster-whisper
Adapted from BiliNote project with Hugging Face model support
"""
import os
from pathlib import Path
from typing import Optional
import logging

from dotenv import load_dotenv
from faster_whisper import WhisperModel

from video2md.models.transcription_models import TranscriptSegment, TranscriptResult

# Load environment variables
load_dotenv(override=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Model name to Hugging Face repository mapping
# Using Systran models as specified
MODEL_MAP = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
}


class WhisperClient:
    """
    Local Whisper transcription client using faster-whisper
    
    Features:
    - Automatic model download from Hugging Face
    - CUDA auto-detection with CPU fallback
    - Configurable model storage directory
    - Structured output with segments and timestamps
    """

    def __init__(
        self,
        model_size: str = None,
        device: str = None,
        compute_type: str = None,
        cpu_threads: int = 4,
        model_dir: str = None,
    ):
        """
        Initialize Whisper client

        Args:
            model_size: Model size (tiny/base/small/medium/large-v1/large-v2/large-v3)
            device: Compute device ('cpu', 'cuda', or None for auto-detect)
            compute_type: Computation precision (None for auto: 'float16' on GPU, 'int8' on CPU)
            cpu_threads: Number of CPU threads to use
            model_dir: Directory to store models (default: ./models/whisper/)
        """
        # Get configuration from environment variables with fallbacks
        # Priority: environment variable > explicit parameter > default value
        # This allows .env to override all scripts
        env_model_size = os.getenv("WHISPER_MODEL_SIZE")
        if env_model_size:
            self.model_size = env_model_size
            if model_size and model_size != env_model_size:
                logger.info(f"Environment variable WHISPER_MODEL_SIZE={env_model_size} overrides parameter model_size={model_size}")
        else:
            self.model_size = model_size or "base"
        
        # Device detection
        if device is None:
            device = os.getenv("WHISPER_DEVICE", "auto")
        
        if device == "auto" or device is None:
            self.device = "cuda" if self._is_cuda_available() else "cpu"
        elif device == "cpu":
            self.device = "cpu"
        else:
            # User requested CUDA, check if available
            self.device = "cuda" if self._is_cuda_available() else "cpu"
            if device == "cuda" and self.device == "cpu":
                logger.warning("CUDA requested but not available, falling back to CPU")

        # Compute type configuration
        # GPU uses float16, CPU uses int8 quantization for efficiency
        if compute_type is None:
            compute_type = os.getenv("WHISPER_COMPUTE_TYPE")
        
        self.compute_type = compute_type or (
            "float16" if self.device == "cuda" else "int8"
        )

        # Model directory setup
        if model_dir is None:
            model_dir = os.getenv("WHISPER_MODEL_DIR", "./models/whisper")
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # CPU threads
        self.cpu_threads = int(os.getenv("WHISPER_CPU_THREADS", cpu_threads))

        # Get model path or Hugging Face repo ID
        model_path = self._get_model_path()

        logger.info(f"Initializing Whisper model: {self.model_size}")
        logger.info(f"Device: {self.device}, Compute type: {self.compute_type}")
        logger.info(f"Model directory: {self.model_dir}")

        # Initialize Whisper model
        # If model_path is a Hugging Face repo ID, faster-whisper will download it automatically
        self.model = WhisperModel(
            model_size_or_path=model_path,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads,
            download_root=str(self.model_dir)
        )

        logger.info("Whisper model initialized successfully")

    @staticmethod
    def _is_cuda_available() -> bool:
        """
        Check if CUDA is available for GPU acceleration
        
        Returns:
            True if CUDA is available, False otherwise
        """
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("✓ CUDA available, using GPU")
                return True
            else:
                logger.info("✗ PyTorch installed but CUDA unavailable, using CPU")
                return False
        except ImportError:
            logger.info("✗ PyTorch not installed, using CPU")
            return False

    def _get_model_path(self) -> str:
        """
        Get model path or Hugging Face repository ID
        
        Returns:
            Local model path if exists, otherwise Hugging Face repo ID
        """
        # Check if model exists in Hugging Face cache format
        # faster-whisper downloads to: {model_dir}/models--Systran--faster-whisper-{model_size}
        if self.model_size in MODEL_MAP:
            repo_id = MODEL_MAP[self.model_size]
            # Convert repo ID to cache directory name: "Systran/faster-whisper-medium" -> "models--Systran--faster-whisper-medium"
            cache_dir_name = repo_id.replace("/", "--")
            cache_dir_name = f"models--{cache_dir_name}"
            local_cache_path = self.model_dir / cache_dir_name
            
            if local_cache_path.exists():
                logger.info(f"Using cached model from: {local_cache_path}")
                # Return the repo ID - faster-whisper will find it in cache
                return repo_id
            else:
                logger.info(f"Model not found in cache, will download from Hugging Face: {repo_id}")
                return repo_id
        else:
            # Unknown model size, try as-is (could be custom path or repo ID)
            logger.warning(f"Unknown model size '{self.model_size}', attempting to use as-is")
            return self.model_size

    def transcribe(
        self,
        audio_file_path: str,
        language: str = None,
        task: str = "transcribe",
        initial_prompt: str = None,
        word_timestamps: bool = False,
        vad_filter: bool = False,
    ) -> TranscriptResult:
        """
        Transcribe audio file to text with timestamps
        
        Args:
            audio_file_path: Path to audio file
            language: Language code (e.g., 'zh', 'en'). None for auto-detection
            task: 'transcribe' or 'translate' (to English)
            initial_prompt: Initial prompt to guide the model
            word_timestamps: Enable word-level timestamps
            vad_filter: Enable voice activity detection filter
            
        Returns:
            TranscriptResult with language, full text, and segments
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If transcription fails
        """
        # Check if file exists
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        logger.info(f"Transcribing: {audio_path.name}")
        logger.info(f"Language: {language or 'auto-detect'}, Task: {task}")

        try:
            # Prepare transcription parameters
            transcribe_params = {
                "language": language,
                "task": task,
            }
            
            if initial_prompt:
                transcribe_params["initial_prompt"] = initial_prompt
            
            if word_timestamps:
                transcribe_params["word_timestamps"] = True
            
            if vad_filter:
                transcribe_params["vad_filter"] = True

            # Perform transcription
            segments_raw, info = self.model.transcribe(
                str(audio_path),
                **transcribe_params
            )

            # Process segments
            segments = []
            full_text = ""

            for seg in segments_raw:
                text = seg.text.strip()
                full_text += text + " "
                segments.append(TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=text
                ))

            # Create result
            result = TranscriptResult(
                language=info.language,
                full_text=full_text.strip(),
                segments=segments,
                raw={
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "duration_after_vad": getattr(info, 'duration_after_vad', None),
                }
            )

            logger.info(f"Transcription completed: {len(segments)} segments")
            logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
            logger.info(f"Duration: {info.duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_with_video(
        self,
        video_file_path: str,
        language: str = None,
        task: str = "transcribe",
        initial_prompt: str = None,
        word_timestamps: bool = False,
        vad_filter: bool = False,
    ) -> TranscriptResult:
        """
        Transcribe video file (extracts audio first, then transcribes)
        
        Args:
            video_file_path: Path to video file
            language: Language code (e.g., 'zh', 'en'). None for auto-detection
            task: 'transcribe' or 'translate' (to English)
            initial_prompt: Initial prompt to guide the model
            word_timestamps: Enable word-level timestamps
            vad_filter: Enable voice activity detection filter
            
        Returns:
            TranscriptResult with language, full text, and segments
        """
        # Import video converter
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
                    task=task,
                    initial_prompt=initial_prompt,
                    word_timestamps=word_timestamps,
                    vad_filter=vad_filter,
                )
            else:
                raise ValueError(f"Unsupported file format: {video_path.suffix}")
        
        logger.info(f"Extracting audio from video: {video_path.name}")
        
        # Convert video to audio
        temp_dir = tempfile.gettempdir()
        audio_file = converter.video_to_audio(
            input_path=video_path,
            output_dir=temp_dir,
            audio_format='wav',
            sample_rate=16000,  # Whisper recommended sample rate
            channels=1          # Mono
        )
        
        try:
            # Transcribe the extracted audio
            result = self.transcribe(
                audio_file_path=audio_file,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                word_timestamps=word_timestamps,
                vad_filter=vad_filter,
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
    """
    Command-line interface for Whisper client
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Local Whisper transcription client")
    parser.add_argument("input_file", type=str, help="Audio or video file to transcribe")
    parser.add_argument(
        "--model-size",
        type=str,
        default="base",
        choices=list(MODEL_MAP.keys()),
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., zh, en). Auto-detect if not specified"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="transcribe",
        choices=["transcribe", "translate"],
        help="Task type (default: transcribe)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Compute device (default: auto)"
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
    client = WhisperClient(
        model_size=args.model_size,
        device=args.device,
    )
    
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
            task=args.task,
        )
    else:
        result = client.transcribe(
            audio_file_path=str(input_path),
            language=args.language,
            task=args.task,
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
