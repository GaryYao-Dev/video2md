# Setup Guide for video2md

Complete setup instructions for new users.

## Prerequisites

1. **Python 3.11+** installed
2. **uv** package manager installed
3. **FFmpeg** installed
4. (Optional) **NVIDIA GPU with CUDA** for faster transcription

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/GaryYao-Dev/video2md.git
cd video2md
```

### 2. Install Dependencies

```bash
uv sync
```

This installs all basic dependencies including:

- faster-whisper (CPU version)
- openai, openai-agents
- gradio (web UI)
- All other required packages

### 3. (Optional) Install GPU Support

⚠️ **Important**: `uv sync` does NOT install GPU support automatically because PyTorch requires a special index URL.

If you have an NVIDIA GPU and want **7-8x faster transcription**:

#### Windows (PowerShell):

```powershell
.\install_gpu.ps1
```

#### Linux/macOS (Bash):

```bash
bash install_gpu.sh
```

#### Manual Installation:

```bash
# Check your CUDA version
nvcc --version

# For CUDA 12.x (12.4 and newer)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# For CUDA 11.8
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify installation
uv run python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# - OPENAI_API_KEY (required for AI agents)
# - SERPER_API_KEY (required for web search)
# - WHISPER_MODEL_SIZE (optional, default: base)
# - WHISPER_DEVICE (optional, auto-detected)
```

### 5. Test Installation

```bash
# Test basic functionality
uv run python test_whisper_direct.py

# Test MCP server
uv run python test_whisper_mcp.py --startup-only

# Run full test suite
uv run python test_whisper_full.py
```

### 6. Start Using

#### Web Interface (Recommended):

```bash
uv run python ui/app.py
```

Then open http://localhost:7860 in your browser.

#### Command Line:

```bash
# Add videos to input/
cp your-video.mp4 input/

# Run processing
uv run python main.py

# Results will be in output/your-video/
```

## Verification

### Check GPU Support

```bash
uv run python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

Expected output with GPU:

```
PyTorch: 2.6.0+cu124
CUDA: True
```

Expected output without GPU (CPU mode):

```
PyTorch: (not installed or CPU version)
CUDA: False
```

### Check Whisper Client

```bash
uv run python -c "from video2md.clients.whisper_client import WhisperClient; client = WhisperClient(); print('Device:', client.device)"
```

Expected output:

- With GPU: `Device: cuda`
- Without GPU: `Device: cpu`

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'video2md'"

**Solution**: Run `uv sync` from the project root directory.

### Issue: "FFmpeg not found"

**Solution**: Install FFmpeg:

- Windows: `choco install ffmpeg` or download from https://ffmpeg.org/
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Issue: GPU not detected even after installing PyTorch

**Solutions**:

1. Verify CUDA is installed: `nvcc --version`
2. Check PyTorch installation: `uv pip list | grep torch`
3. Verify correct CUDA version match
4. Reinstall PyTorch with correct index URL

### Issue: "CUDA out of memory"

**Solution**: Use a smaller Whisper model size in `.env`:

```bash
WHISPER_MODEL_SIZE=tiny   # or base, small instead of medium/large
```

## Next Steps

- Read [`README.md`](README.md) for usage examples
- See [`docs/GPU_SUPPORT.md`](docs/GPU_SUPPORT.md) for detailed GPU setup
- Check [`docs/ENVIRONMENT_CONFIG.md`](docs/ENVIRONMENT_CONFIG.md) for configuration options

## Getting Help

If you encounter issues:

1. Check the test scripts output for detailed error messages
2. Review the documentation in the `docs/` folder
3. Open an issue on GitHub with error details and system info
