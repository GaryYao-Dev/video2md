# Video2MD

🎬 **Transform your videos into structured markdown summaries with AI**

Video2MD is an intelligent toolkit that automatically converts video content into comprehensive, searchable markdown documents. Using advanced AI agents, it transcribes audio, researches context, and generates structured summaries - perfect for content creators, researchers, and knowledge workers.

## ✨ What Video2MD Does

### Input: Any Video File

- Drop in MP4, AVI, MOV, or any common video format
- Supports batch processing of multiple files
- Works with audio files too (MP3, WAV, FLAC, etc.)

### Output: Rich Markdown Documents

For each video `example.mp4`, you get a complete folder `output/example/` containing:

- 📄 **`example.md`** - Structured summary with embedded video player
- 🎬 **`example.mp4`** - Original media file (organized)
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

2. **Setup and Launch**:

   ```bash
   git clone https://github.com/your-username/video2md.git
   cd video2md
   uv sync
   uv run python ui/app.py
   ```

3. **Use the Web Interface**:
   - Open your browser to the displayed URL (usually http://localhost:7860)
   - Upload videos or select existing files
   - Click "Go" to process
   - Preview results instantly in the browser

### Option 2: Command Line

For automation and batch processing:

```bash
# Setup (one time)
uv sync

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

- Converts video/audio to accurate text using OpenAI Whisper
- Handles multiple languages and accents
- Generates both clean text and timestamped subtitles
- Supports Chinese simplified/traditional conversion

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
# Transcribe videos directly
uv run video2md-whisper-client your-video.mp4

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

### Configuration & Environment

Set up API keys and customize behavior:

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys (see details below)
```

#### Environment Configuration

Copy `.env.example` to `.env` and configure the following variables:

```bash
cp .env.example .env
```

Then edit the `.env` file with your specific configuration:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `WHISPER_API_URL` | URL for Whisper transcription server | `http://localhost:8000` | Yes |
| `OPENAI_API_KEY` | OpenAI API key for AI processing | `sk-proj-...` | Yes |
| `SERPER_API_KEY` | Serper API key for web search | `your_serper_key_here` | Yes |

**Example `.env` file:**

```bash
# Whisper API server configuration
WHISPER_API_URL=http://localhost:8000

# OpenAI API key for transcription and summarization
OPENAI_API_KEY=sk-proj-your-actual-openai-key-here

# Serper API key for web search during research phase
SERPER_API_KEY=your-actual-serper-key-here
```

**Getting API Keys:**

- **OpenAI API Key**: Sign up at [OpenAI Platform](https://platform.openai.com/) and create an API key
- **Serper API Key**: Register at [Serper](https://serper.dev/) for web search functionality
- **Whisper API URL**: This should point to your Whisper server (default: `http://localhost:8000`)

## 📋 Requirements

- **Python 3.11+** (required for modern AI libraries)
- **uv** package manager (handles dependencies automatically)
- **FFmpeg** (for video/audio processing) - install via:

  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt install ffmpeg

  # Windows (via chocolatey)
  choco install ffmpeg
  ```

### Optional Dependencies

For enhanced functionality, Video2MD can use:

- **Node.js** (for additional MCP servers)
- **OpenAI API key** (for transcription and summarization)
- **Web search APIs** (Brave, Serper) for enhanced research

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
- **`src/video2md/`** - Core processing engine
  - `agents/` - The three AI agents (Whisper, Research, Summary)
  - `clients/` - Communication with external services
  - `tools/` - Individual command-line utilities
  - `utils/` - Helper functions for video/text processing
- **`ui/`** - Web interface code

## 🔧 Troubleshooting

### Common Issues

**"No module named 'video2md'"**: Run `uv sync` to install dependencies

**"FFmpeg not found"**: Install FFmpeg using the commands above

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

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository** and clone your fork
2. **Set up development environment**: `uv sync`
3. **Make your changes** and test thoroughly
4. **Update documentation** if needed
5. **Submit a pull request** with a clear description

### Development Setup

```bash
git clone https://github.com/your-username/video2md.git
cd video2md
uv sync --extra dev  # Install with development dependencies
uv run pytest       # Run tests
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/video2md/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/video2md/discussions)

---

**Made with ❤️ for the open source community**
