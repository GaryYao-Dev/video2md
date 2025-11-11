# Environment Configuration Guide

This document describes all environment variables supported by video2md.

## Whisper Configuration

Configure the local Whisper transcription client:

```bash
# Model Configuration
WHISPER_MODEL_SIZE=base                # Model size: tiny, base, small, medium, large-v1, large-v2, large-v3
                                       # Default: base
                                       # Larger models = better accuracy but slower

WHISPER_MODEL_DIR=./models/whisper     # Directory to store downloaded models
                                       # Default: ./models/whisper
                                       # Models are ~150MB (base) to ~3GB (large-v3)

# Device Configuration
WHISPER_DEVICE=auto                    # Compute device: auto, cpu, cuda
                                       # Default: auto (uses CUDA if available)
                                       # auto: Auto-detect GPU/CPU
                                       # cuda: Force GPU (falls back to CPU if unavailable)
                                       # cpu: Force CPU-only mode

WHISPER_COMPUTE_TYPE=                  # Compute precision type
                                       # Default: auto (float16 for GPU, int8 for CPU)
                                       # Options:
                                       #   - float16: Best for GPU
                                       #   - int8: Best for CPU (uses ~50% less memory)
                                       #   - int8_float16: Mixed precision

WHISPER_CPU_THREADS=4                  # Number of CPU threads to use
                                       # Default: 4
                                       # Increase for faster CPU processing (if available)
```

## Legacy Remote Whisper Server (Backup)

These settings were used for the old remote Whisper server (now replaced by local client):

```bash
WHISPER_API_URL=http://localhost:8000  # Remote Whisper server URL
                                       # Note: Local client is now default
```

## Model Size Guide

Choose the appropriate model size based on your needs:

| Model    | Size    | Memory | Speed   | Accuracy | Use Case                 |
| -------- | ------- | ------ | ------- | -------- | ------------------------ |
| tiny     | ~75 MB  | ~1 GB  | Fastest | Lower    | Real-time, quick drafts  |
| base     | ~150 MB | ~1 GB  | Fast    | Good     | General purpose, default |
| small    | ~500 MB | ~2 GB  | Medium  | Better   | Balanced accuracy/speed  |
| medium   | ~1.5 GB | ~5 GB  | Slower  | Great    | High accuracy needed     |
| large-v3 | ~3 GB   | ~10 GB | Slowest | Best     | Maximum accuracy         |

## Example .env File

Create a `.env` file in your project root:

```bash
# Whisper Local Client Configuration
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=float16
WHISPER_MODEL_DIR=./models/whisper
WHISPER_CPU_THREADS=4

# For GPU users: Enable CUDA
# Make sure to install PyTorch with CUDA support first
# See docs/GPU_SUPPORT.md for details

# For CPU users: Optimize for CPU
# WHISPER_DEVICE=cpu
# WHISPER_COMPUTE_TYPE=int8
# WHISPER_CPU_THREADS=8
```

## Loading Environment Variables

### In Python

```python
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Access variables
model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
device = os.getenv("WHISPER_DEVICE", "auto")
```

### In Command Line

```bash
# Export variables
export WHISPER_MODEL_SIZE=medium
export WHISPER_DEVICE=cuda

# Or load from .env file
source .env  # bash/zsh
```

### In WhisperClient

The `WhisperClient` automatically reads environment variables:

```python
from video2md.clients.whisper_client import WhisperClient

# Uses environment variables by default
client = WhisperClient()

# Or override with explicit parameters
client = WhisperClient(
    model_size="medium",
    device="cuda",
    compute_type="float16"
)
```

## Priority Order

When configuration values are provided in multiple ways, the priority order is:

1. **Explicit parameters** (highest priority)

   ```python
   client = WhisperClient(model_size="large-v3")
   ```

2. **Environment variables**

   ```bash
   export WHISPER_MODEL_SIZE=medium
   ```

3. **Default values** (lowest priority)
   - model_size: `base`
   - device: `auto`
   - compute_type: `float16` (GPU) or `int8` (CPU)
   - cpu_threads: `4`

## Directory Structure

By default, video2md creates the following structure:

```
project-root/
├── .env                      # Your environment configuration
├── models/
│   └── whisper/             # Downloaded Whisper models
│       ├── whisper-base/
│       ├── whisper-medium/
│       └── whisper-large-v3/
└── output/                  # Transcription outputs
```

## Best Practices

1. **Use .env file for local development**

   - Keep it in `.gitignore` to avoid committing secrets
   - Create `.env.example` with dummy values for team members

2. **Use environment variables in production**

   - Set variables in your deployment environment
   - Don't commit actual values to version control

3. **Choose model size wisely**

   - Start with `base` for general use
   - Use `medium` or `large-v3` only when accuracy is critical
   - Consider GPU memory limits

4. **Optimize for your hardware**
   - GPU users: Use `float16` compute type
   - CPU users: Use `int8` and increase thread count
   - Limited memory: Use smaller models

## Migration from Remote Server

If you were using the old remote Whisper server:

**Old way (remote server):**

```python
from video2md.clients.backup.whisper_client_remote import transcribe_media

result = transcribe_media(
    "audio.mp3",
    server_url="http://localhost:8000"
)
```

**New way (local client):**

```python
from video2md.clients.whisper_client import WhisperClient

client = WhisperClient()
result = client.transcribe("audio.mp3")
```

The new local client:

- ✅ No need for a separate server
- ✅ Automatic model management
- ✅ Better performance with local processing
- ✅ Structured output with segments
- ✅ GPU acceleration support

## See Also

- [GPU Support Guide](GPU_SUPPORT.md) - How to enable GPU acceleration
- [README.md](../README.md) - Project overview and quick start
