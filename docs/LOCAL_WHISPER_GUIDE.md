# Local Whisper Implementation - Migration Guide

## Overview

This guide covers the migration from the remote Whisper server to the new local Whisper implementation using `faster-whisper` with Hugging Face models.

## What's New

✨ **Key Features:**

- 🚀 Local processing with `faster-whisper` (4-8x faster than original Whisper)
- 🤗 Hugging Face model support (e.g., `Systran/faster-whisper-medium`)
- 🎯 Structured output with `TranscriptResult` and `TranscriptSegment`
- 💾 Automatic model download and caching
- ⚡ GPU acceleration support (optional)
- 🔄 Multiple output formats (SRT, VTT, TXT, JSON)
- 📦 No separate server required

## Installation

### Basic Installation (CPU only)

```bash
# Install the package with local Whisper support using uv
uv pip install -e .

# Or sync from pyproject.toml
uv sync

# This will install faster-whisper automatically
```

### GPU Installation (Optional)

For GPU acceleration (7-8x speedup):

```bash
# Install PyTorch with CUDA support first using uv
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Then install video2md
uv pip install -e .
```

See [docs/GPU_SUPPORT.md](../docs/GPU_SUPPORT.md) for detailed GPU setup.

## Quick Start

### Python API

```python
from video2md.clients.whisper_client import WhisperClient
from video2md.utils.transcript_converter import save_transcript

# Initialize client (downloads model on first run)
client = WhisperClient(model_size="base")

# Transcribe audio or video
result = client.transcribe("audio.mp3")

# Access results
print(f"Language: {result.language}")
print(f"Text: {result.full_text}")
print(f"Segments: {len(result.segments)}")

# Save in different formats
save_transcript(result, "output.srt", format="srt")
save_transcript(result, "output.txt", format="txt")
save_transcript(result, "output.json", format="json")
```

### Command Line

```bash
# Transcribe a file using uv
uv run video2md-whisper-client input.mp4 --model-size base --output output.txt

# Transcribe with specific language
uv run video2md-whisper-client audio.mp3 --language zh --output chinese.txt

# Use GPU acceleration
uv run video2md-whisper-client video.mp4 --device cuda --model-size medium

# Output as JSON
uv run video2md-whisper-client audio.wav --format json --output result.json
```

### Convert Formats

```bash
# Convert JSON transcript to other formats using uv
uv run video2md-transcript-converter result.json output.srt --format srt
uv run video2md-transcript-converter result.json output.vtt --format vtt
uv run video2md-transcript-converter result.json output.txt --format txt --include-timestamps
```

## Migration from Remote Server

### Before (Remote Server)

```python
from video2md.clients.backup.whisper_client_remote import transcribe_media

# Required separate Whisper server running
result = transcribe_media(
    "audio.mp3",
    server_url="http://localhost:8000",
    output_format="srt"
)
# Result was a string (SRT content)
```

### After (Local Client)

```python
from video2md.clients.whisper_client import WhisperClient
from video2md.utils.transcript_converter import transcript_to_srt

# No server needed!
client = WhisperClient()
result = client.transcribe("audio.mp3")

# Result is structured data
print(result.language)      # Detected language
print(result.full_text)     # Complete text
print(result.segments)      # List of segments with timestamps

# Convert to SRT if needed
srt_content = transcript_to_srt(result)
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# Model configuration
WHISPER_MODEL_SIZE=base                # tiny, base, small, medium, large-v3
WHISPER_MODEL_DIR=./models/whisper     # Where to store models

# Device configuration
WHISPER_DEVICE=auto                    # auto, cpu, cuda
WHISPER_COMPUTE_TYPE=float16           # float16 (GPU), int8 (CPU)
WHISPER_CPU_THREADS=4                  # Number of CPU threads
```

See [docs/ENVIRONMENT_CONFIG.md](../docs/ENVIRONMENT_CONFIG.md) for complete configuration guide.

### Model Selection

| Model    | Size   | Memory | Speed   | Accuracy | Best For                  |
| -------- | ------ | ------ | ------- | -------- | ------------------------- |
| tiny     | 75 MB  | ~1 GB  | Fastest | Lower    | Quick drafts              |
| base     | 150 MB | ~1 GB  | Fast    | Good     | **General use (default)** |
| small    | 500 MB | ~2 GB  | Medium  | Better   | Balanced                  |
| medium   | 1.5 GB | ~5 GB  | Slower  | Great    | High accuracy             |
| large-v3 | 3 GB   | ~10 GB | Slowest | Best     | Maximum accuracy          |

## Data Models

### TranscriptSegment

```python
@dataclass
class TranscriptSegment:
    start: float      # Start time in seconds
    end: float        # End time in seconds
    text: str         # Transcribed text
```

### TranscriptResult

```python
@dataclass
class TranscriptResult:
    language: Optional[str]                # Detected language code
    full_text: str                         # Complete merged text
    segments: List[TranscriptSegment]      # Timestamped segments
    raw: Optional[dict] = None             # Raw metadata
```

## Output Formats

### SRT (SubRip)

```srt
1
00:00:00,000 --> 00:00:02,500
Hello world

2
00:00:02,500 --> 00:00:05,000
This is a test
```

### VTT (WebVTT)

```vtt
WEBVTT

00:00:00.000 --> 00:00:02.500
Hello world

00:00:02.500 --> 00:00:05.000
This is a test
```

### TXT (Plain Text)

```txt
Hello world This is a test
```

Or with timestamps:

```txt
[0.00s - 2.50s] Hello world
[2.50s - 5.00s] This is a test
```

### JSON

```json
{
  "language": "en",
  "full_text": "Hello world This is a test",
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Hello world"
    },
    {
      "start": 2.5,
      "end": 5.0,
      "text": "This is a test"
    }
  ],
  "raw": {
    "language_probability": 0.98,
    "duration": 5.0
  }
}
```

## Advanced Usage

### Video Processing

```python
# Automatically extracts audio from video
result = client.transcribe_with_video("video.mp4")
```

### Custom Parameters

```python
result = client.transcribe(
    audio_file_path="audio.mp3",
    language="zh",              # Force Chinese
    task="transcribe",          # or "translate" to English
    initial_prompt="专业术语",   # Guide the model
    word_timestamps=True,       # Get word-level timestamps
    vad_filter=True,           # Voice activity detection
)
```

### Batch Processing

```python
from pathlib import Path

client = WhisperClient(model_size="base")

for audio_file in Path("input").glob("*.mp3"):
    result = client.transcribe(str(audio_file))

    output_path = Path("output") / f"{audio_file.stem}.srt"
    save_transcript(result, output_path, format="srt")
```

## Testing

Run the test suite to verify your installation:

```bash
# Run all tests using uv
uv run python test_local_whisper.py

# Or run directly
uv run ./test_local_whisper.py

# The test will:
# 1. Initialize Whisper client
# 2. Test data models
# 3. Test format conversions
# 4. Test file operations
# 5. Test real transcription (if audio files available)
# 6. Check CUDA availability
# 7. Check environment variables
```

### Test with Sample Audio

1. Place audio/video files in `./input/` directory
2. Run: `uv run python test_local_whisper.py`
3. Check results in `./test_output/`

## Performance Tips

### CPU Optimization

```bash
# Use smaller model
WHISPER_MODEL_SIZE=tiny

# Use int8 quantization (50% memory reduction)
WHISPER_COMPUTE_TYPE=int8

# Increase CPU threads
WHISPER_CPU_THREADS=8
```

### GPU Optimization

```bash
# Use larger model on GPU
WHISPER_MODEL_SIZE=medium

# Use float16 for best GPU performance
WHISPER_COMPUTE_TYPE=float16
WHISPER_DEVICE=cuda
```

## Troubleshooting

### Model Download Issues

If model download fails:

```python
# Models are downloaded from Hugging Face automatically
# Default models use Systran repositories:
# - Systran/faster-whisper-base
# - Systran/faster-whisper-medium
# - Systran/faster-whisper-large-v3

# Check your internet connection and firewall settings
```

### Memory Issues

```bash
# Use smaller model
WHISPER_MODEL_SIZE=tiny

# Or use int8 quantization
WHISPER_COMPUTE_TYPE=int8
```

### CUDA Issues

```bash
# Check CUDA availability
uv run python -c "import torch; print(torch.cuda.is_available())"

# If False, install PyTorch with CUDA:
uv pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## File Locations

```
video2md/
├── src/video2md/
│   ├── clients/
│   │   ├── whisper_client.py           # ✨ New local client
│   │   └── backup/
│   │       └── whisper_client_remote.py # Old remote client (backup)
│   ├── models/
│   │   ├── __init__.py
│   │   └── transcription_models.py      # Data models
│   └── utils/
│       └── transcript_converter.py      # Format converters
├── models/
│   └── whisper/                         # Downloaded models (auto-created)
├── docs/
│   ├── GPU_SUPPORT.md                   # GPU setup guide
│   └── ENVIRONMENT_CONFIG.md            # Configuration guide
├── test_local_whisper.py                # Test suite
└── .env.example                         # Example configuration
```

## API Reference

### WhisperClient

**Constructor:**

```python
WhisperClient(
    model_size: str = "base",
    device: str = None,           # None = auto-detect
    compute_type: str = None,     # None = auto (float16/int8)
    cpu_threads: int = 4,
    model_dir: str = None,        # None = ./models/whisper
)
```

**Methods:**

```python
# Transcribe audio file
transcribe(
    audio_file_path: str,
    language: str = None,         # None = auto-detect
    task: str = "transcribe",     # or "translate"
    initial_prompt: str = None,
    word_timestamps: bool = False,
    vad_filter: bool = False,
) -> TranscriptResult

# Transcribe video file (extracts audio)
transcribe_with_video(
    video_file_path: str,
    language: str = None,
    task: str = "transcribe",
    initial_prompt: str = None,
    word_timestamps: bool = False,
    vad_filter: bool = False,
) -> TranscriptResult
```

### Conversion Utilities

```python
from video2md.utils.transcript_converter import (
    transcript_to_srt,      # Convert to SRT
    transcript_to_vtt,      # Convert to VTT
    transcript_to_txt,      # Convert to TXT
    transcript_to_json,     # Convert to JSON
    save_transcript,        # Save to file
    load_transcript_from_json,  # Load from JSON
)
```

## Support

- 📖 Documentation: See `docs/` folder
- 🐛 Issues: GitHub Issues
- 💬 Questions: GitHub Discussions

## See Also

- [GPU Support Guide](../docs/GPU_SUPPORT.md)
- [Environment Configuration](../docs/ENVIRONMENT_CONFIG.md)
- [BiliNote Whisper Integration Guide](../extra/BiliNote/WHISPER_INTEGRATION_GUIDE.md)
