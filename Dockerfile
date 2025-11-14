# Use Python 3.11 slim as base image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - ffmpeg: required for video/audio processing
# - curl: for downloading files
# - nodejs & npm: required for MCP servers
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Create necessary directories (only for code, not data directories)
# Note: input, output, models will be created as symlinks by entrypoint script
RUN mkdir -p prompts src ui docs

# Install Python dependencies using uv
RUN uv sync --no-dev

# Optionally preinstall MCP servers to avoid runtime delays
RUN uv sync --extra mcp-servers || true
RUN npm install -g @modelcontextprotocol/server-filesystem 2>/dev/null || true

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/
COPY prompts/ ./prompts/
COPY docs/ ./docs/
COPY main.py ./
COPY .env.example ./
COPY docker-entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Copy environment configuration template
# Users should mount their own .env file when running the container
COPY .env.example ./.env

# Create volume mount points for persistent data
VOLUME ["/app/data"]

# Expose Gradio default port
EXPOSE 7860

# Set environment variables for Gradio
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Set entrypoint to setup script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command: run the web UI
CMD ["uv", "run", "python", "ui/app.py"]
