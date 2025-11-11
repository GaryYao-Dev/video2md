# GPU Support for video2md

This document explains how to enable GPU acceleration for faster Whisper transcription.

## Overview

The `faster-whisper` library supports GPU acceleration through CUDA, which can provide **7-8x speedup** compared to CPU processing.

## Requirements

- NVIDIA GPU with CUDA support
- CUDA Toolkit 11.8 or 12.1
- Sufficient GPU memory (varies by model size):
  - tiny: ~1 GB
  - base: ~1 GB
  - small: ~2 GB
  - medium: ~5 GB
  - large-v3: ~10 GB

## Installation

### Step 1: Install CUDA Toolkit

Download and install CUDA Toolkit from:
https://developer.nvidia.com/cuda-downloads

### Step 2: Install PyTorch with CUDA Support

Choose the appropriate command for your CUDA version:

**For CUDA 11.8:**

```bash
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**For CUDA 12.1:**

```bash
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Or install with the optional gpu dependencies:**

```bash
uv pip install -e ".[gpu]"
# Then manually install PyTorch with CUDA
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 3: Verify Installation

```bash
# Check CUDA availability
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
uv run python -c "import torch; print(f'CUDA version: {torch.version.cuda}')"
uv run python -c "import torch; print(f'GPU device: {torch.cuda.get_device_name(0)}')"
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# Whisper Configuration
WHISPER_MODEL_SIZE=base                # Model size: tiny, base, small, medium, large-v1, large-v2, large-v3
WHISPER_DEVICE=auto                    # Device: auto, cpu, cuda
WHISPER_COMPUTE_TYPE=float16           # Compute type: float16 (GPU), int8 (CPU), int8_float16 (mixed)
WHISPER_MODEL_DIR=./models/whisper     # Directory to store models
WHISPER_CPU_THREADS=4                  # Number of CPU threads (for CPU mode)
```

### Device Selection

The Whisper client automatically detects CUDA availability:

- `WHISPER_DEVICE=auto`: Auto-detect (uses CUDA if available, else CPU)
- `WHISPER_DEVICE=cuda`: Force CUDA (falls back to CPU if unavailable)
- `WHISPER_DEVICE=cpu`: Force CPU-only mode

### Compute Type

Choose the appropriate compute type for your device:

- **float16**: Best for GPU (CUDA), provides fastest processing
- **int8**: Best for CPU, reduces memory usage by ~50%
- **int8_float16**: Mixed precision, useful for limited GPU memory

## Usage Examples

### Using GPU in Python

```python
from video2md.clients.whisper_client import WhisperClient

# Auto-detect device (will use GPU if available)
client = WhisperClient(model_size="base")

# Explicitly use GPU
client = WhisperClient(model_size="base", device="cuda")

# Transcribe audio/video
result = client.transcribe("audio.mp3")
print(result.full_text)
```

### Using GPU from Command Line

```bash
# Auto-detect device
uv run video2md-whisper-client input.mp4 --model-size base --device auto

# Force GPU
uv run video2md-whisper-client input.mp4 --model-size medium --device cuda

# Use larger model on GPU
uv run video2md-whisper-client input.mp4 --model-size large-v3 --device cuda
```

## Performance Benchmarks

Processing a 10-minute audio file:

| Configuration  | Model    | Device         | Time  | Speedup |
| -------------- | -------- | -------------- | ----- | ------- |
| CPU (8-core)   | base     | CPU + int8     | ~180s | 1x      |
| GPU (RTX 3060) | base     | CUDA + float16 | ~25s  | 7.2x    |
| CPU (8-core)   | large-v3 | CPU + int8     | ~600s | 1x      |
| GPU (RTX 3060) | large-v3 | CUDA + float16 | ~80s  | 7.5x    |

## Troubleshooting

### CUDA Out of Memory

If you encounter GPU memory errors:

1. **Use a smaller model**:

   ```bash
   WHISPER_MODEL_SIZE=small  # Instead of large-v3
   ```

2. **Use mixed precision**:

   ```bash
   WHISPER_COMPUTE_TYPE=int8_float16
   ```

3. **Process shorter audio segments** (handled automatically by faster-whisper)

### CUDA Not Detected

If PyTorch doesn't detect CUDA:

1. Verify CUDA installation:

   ```bash
   nvidia-smi
   nvcc --version
   ```

2. Reinstall PyTorch with correct CUDA version:

   ```bash
   uv pip uninstall torch torchvision torchaudio
   uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. Check PyTorch CUDA status:
   ```bash
   uv run python -c "import torch; print(torch.cuda.is_available())"
   ```

### Driver Version Mismatch

If you see CUDA driver version errors:

1. Update NVIDIA GPU drivers to the latest version
2. Ensure CUDA Toolkit version matches your driver version

## macOS (Apple Silicon)

For macOS with Apple Silicon (M1/M2/M3), GPU acceleration is not available through CUDA. However, you can use:

- **CPU mode** with int8 quantization for efficient processing
- Consider using `mlx-whisper` (Apple's MLX framework) for Apple Silicon optimization (not currently integrated)

## Docker GPU Support

To use GPU in Docker containers, you need NVIDIA Container Toolkit:

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python and uv
RUN apt-get update && apt-get install -y python3 python3-pip curl
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install PyTorch with CUDA
RUN uv pip install torch --index-url https://download.pytorch.org/whl/cu118

# Install video2md
COPY . /app
WORKDIR /app
RUN uv pip install -e .

CMD ["video2md-whisper-client"]
```

Run with GPU support:

```bash
docker run --gpus all -v ./models:/app/models myimage video2md-whisper-client input.mp4
```

## References

- [faster-whisper Documentation](https://github.com/SYSTRAN/faster-whisper)
- [PyTorch CUDA Installation](https://pytorch.org/get-started/locally/)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
