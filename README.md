# Video2MD

🎬 **Transform your videos into structured markdown summaries with AI**

Video2MD is an intelligent toolkit that automatically converts video content into comprehensive, searchable markdown documents. Using advanced AI agents, it transcribes audio, researches context, and generates structured summaries - perfect for content creators, researchers, and knowledge workers.

## 💡 Why Video2MD?

Every day we come across excellent videos and short clips introducing projects, tutorials, or valuable insights. We bookmark them with good intentions, but they often end up buried and forgotten in our collections.

**Video2MD solves this problem** by:

- 📝 **Extracting the core content** from videos automatically
- 🗂️ **Making information organized** and easily searchable
- 🔍 **Enabling quick retrieval** when you need that knowledge later
- 💾 **Preserving knowledge** in a format that's easy to reference and share

Transform your video bookmarks from a digital graveyard into a searchable knowledge base.

## ✨ What Video2MD Does

### Input: Any Video File

- Drop in MP4, AVI, MOV, or any common video format
- Supports batch processing of multiple files
- Works with audio files too (MP3, WAV, FLAC, etc.)

### Output: Rich Markdown Documents

For each video `example.mp4`, you get a complete folder `output/example/` containing:

- 📄 **`example.md`** - Structured summary with embedded video player
- 📝 **`example.txt`** - Clean transcript text
- 🎞️ **`example.srt`** - Subtitle file with timestamps

### Sample Output Preview

```markdown
# My Video Title

## Media

<video src="./my-video.mp4" controls style="width:100%;max-width:100%;"></video>

## Summary

This video discusses three key concepts:

1. **Main Topic**: Detailed explanation with context
2. **Key Insights**: Research-backed information
3. **Actionable Steps**: What viewers should do next

## Transcript

[00:00:01] Hello everyone, welcome to today's discussion about...
```

## 🚀 Quick Start

### Option 1: Web Interface (Recommended)

The easiest way to use Video2MD is through the web interface:

1. **Install uv** (Python package manager):

   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Setup**:

   ```bash
   # Clone and install dependencies
   git clone https://github.com/your-username/video2md.git
   cd video2md
   uv sync

   # Optional: Install GPU support for faster transcription (NVIDIA GPU required)
   # Windows:
   .\install_gpu.ps1
   # Linux/macOS:
   bash install_gpu.sh
   ```

3. **Configure Environment Variables**:

   Copy `.env.example` to `.env` and configure your API keys:

   ```bash
   cp .env.example .env
   ```

   Then edit the `.env` file with your specific configuration:

   | Variable         | Description                      | Example                | Required |
   | ---------------- | -------------------------------- | ---------------------- | -------- |
   | `OPENAI_API_KEY` | OpenAI API key for AI processing | `sk-proj-...`          | Yes      |
   | `SERPER_API_KEY` | Serper API key for web search    | `your_serper_key_here` | Yes      |

   **Example `.env` file:**

   ```bash
   # OpenAI API key for transcription and summarization
   OPENAI_API_KEY=sk-proj-your-actual-openai-key-here

   # Serper API key for web search during research phase
   SERPER_API_KEY=your-actual-serper-key-here
   ```

   **Getting API Keys:**

   - **OpenAI API Key**: Sign up at [OpenAI Platform](https://platform.openai.com/) and create an API key
     - Required for AI agents and OpenAI transcription method
   - **Serper API Key**: Register at [Serper](https://serper.dev/) for web search functionality

4. **Launch**:

   ```bash
   uv run python ui/app.py

   # run the following command to enable MCP logger output on Windows
   uv run python ui/app.py 2>&1
   ```

5. **Use the Web Interface**:

   - Open your browser to the displayed URL (usually http://localhost:7860)
   - Upload videos or select existing files
   - **Choose transcription method** (Local Whisper or OpenAI Transcription)
   - Click "Go" to process
   - Preview results instantly in the browser

### Option 2: Command Line

For automation and batch processing:

```bash
# Setup (one time)
uv sync

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see environment configuration above)

# Add videos to the input folder
mkdir -p input
cp your-video.mp4 input/

# Run processing
uv run python main.py

# Results appear in output/your-video/
```

## 🤖 How It Works: The AI Agent Pipeline

Video2MD uses three specialized AI agents working together:

### 1. 🎧 Whisper Agent - Transcription

- Supports **two transcription methods**:
  - **Local Whisper** - Free, runs on your hardware using faster-whisper
  - **OpenAI Transcription** - Cloud-based using gpt-4o-transcribe model
- Converts video/audio to accurate text
- Handles multiple languages and accents
- Generates both clean text and timestamped subtitles
- Supports Chinese simplified/traditional conversion
- **Group ID tracing** - All agent operations for the same media file are grouped together for easy tracking

### 2. 🔍 Research Agent - Context Enhancement

- Searches the web for related information and context
- Finds relevant articles, documentation, and references
- Enriches the content with external knowledge
- Handles timeouts gracefully for blocked/slow sites

### 3. ✍️ Summary Agent - Intelligent Structuring

- Combines transcript and research into coherent summaries
- Creates proper markdown structure with headings and sections
- Embeds the original video for reference
- Maintains context and key insights

### Processing Flow

```
📹 Video File → 🎧 Whisper Agent → 🔍 Research Agent → ✍️ Summary Agent → 📄 Markdown
```

Each agent runs independently and can handle multiple files in parallel for efficient batch processing.

## 🛠️ Advanced Usage

### Individual Command-Line Tools

Video2MD includes standalone tools for specific tasks:

```bash
# Transcribe videos with local Whisper
uv run video2md-whisper-client your-video.mp4

# Transcribe videos with OpenAI API
uv run video2md-openai-transcribe-client your-video.mp4 --language zh

# Convert video to audio (useful for audio-only processing)
uv run video2md-video-converter --format wav your-video.mp4

# Convert Chinese text between simplified/traditional
uv run video2md-chinese-converter --to simplified transcript.txt
```

### Batch Processing

Process multiple videos at once:

```bash
# Add multiple videos to input/
cp *.mp4 input/

# Run batch processing
uv run python main.py

# Or use the web interface for visual progress tracking
```

### Additional Configuration Options

## 📋 Requirements

- **Python 3.11+** (required for modern AI libraries)
- **uv** package manager (handles dependencies automatically)
- **FFmpeg** (for video/audio processing) - **REQUIRED**
- **Node.js** (for MCP servers) - **REQUIRED**

### Installing Required Dependencies

Video2MD will automatically check for required dependencies on startup. If any are missing, you'll see clear installation instructions.

**FFmpeg Installation:**

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (via chocolatey)
choco install ffmpeg

# Windows (via winget)
winget install ffmpeg
```

**Node.js Installation:**

```bash
# macOS
brew install node

# Ubuntu/Debian
sudo apt install nodejs npm

# Windows
# Download from https://nodejs.org/
# Or use package manager:
choco install nodejs
winget install OpenJS.NodeJS
```

### Verifying Dependencies

You can manually check if all dependencies are installed:

```bash
# Check FFmpeg
ffmpeg -version

# Check Node.js
node --version

# Or use the built-in dependency checker
uv run python -c "from video2md.utils import DependencyChecker; DependencyChecker.validate_or_exit()"
```

### Optional Dependencies

For enhanced functionality, Video2MD can use:

- **OpenAI API key** (for transcription and summarization)
- **Web search APIs** (Brave, Serper) for enhanced research
- **GPU Support** (NVIDIA GPU with CUDA) - See GPU Installation below

### GPU Installation (Optional, Recommended for Speed)

For **7-8x faster transcription**, install GPU support if you have an NVIDIA GPU:

**Automated Installation:**

```bash
# Windows
.\install_gpu.ps1

# Linux/macOS
bash install_gpu.sh
```

**Manual Installation:**

```bash
# Check CUDA version
nvcc --version

# Install PyTorch with CUDA 12.x
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Verify GPU support
uv run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

⚠️ **Important for repo cloners**: `uv sync` alone won't install GPU support. You must run the installation script or manual commands above after cloning.

See [`docs/GPU_SUPPORT.md`](docs/GPU_SUPPORT.md) for detailed GPU setup instructions.

## 🎯 Use Cases

- **📚 Educational Content**: Convert lectures and tutorials into searchable notes
- **🎙️ Podcast Summaries**: Transform audio content into readable articles
- **📊 Meeting Records**: Turn recorded meetings into structured minutes
- **🎬 Content Creation**: Generate blog posts from video content
- **🔬 Research**: Create transcripts and summaries for interviews or presentations

## 📁 Project Structure

Understanding the organization:

- **`input/`** - Drop your video files here
- **`output/`** - Processed results appear here (one folder per video)
- **`prompts/`** - AI prompt templates (customize behavior here)
- **`docs/`** - Documentation
  - `GPU_SUPPORT.md` - GPU setup instructions
  - `ENVIRONMENT_CONFIG.md` - Environment variables reference
- **`src/video2md/`** - Core processing engine
  - `agents/` - The three AI agents (Whisper, Research, Summary)
  - `clients/` - Communication with external services (Whisper, OpenAI)
  - `tools/` - Individual command-line utilities
  - `utils/` - Helper functions for video/text processing
- **`ui/`** - Web interface code

## 🔧 Troubleshooting

### Common Issues

**"No module named 'video2md'"**: Run `uv sync` to install dependencies

**"FFmpeg not found" or "Node.js not found"**: The application will automatically detect missing dependencies on startup and show installation instructions. Install the missing dependencies and try again.

**Application hangs or crashes on startup**: This is usually caused by missing FFmpeg or Node.js. Check the startup logs for dependency check results.

**Slow processing**: The Research agent may timeout on slow websites (this is normal and won't break processing)

**API errors**: Check your `.env` file for correct API keys

### Performance Tips

- **Preinstall MCP servers** to avoid on-demand installation delays:

  ```bash
  uv sync --extra mcp-servers
  npm install -g @modelcontextprotocol/server-filesystem
  ```

- **Adjust research timeout** for faster processing:

  ```bash
  export RESEARCH_TOOL_SESSION_TIMEOUT_SECONDS=10
  ```
