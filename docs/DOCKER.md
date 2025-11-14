# Docker Deployment Guide

This guide explains how to deploy the Video2MD project using Docker.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+ (optional, for docker-compose method)
- At least 4GB available disk space
- Configured `.env` file with necessary API keys

## 🚀 Quick Start

### Method 1: Using Docker Compose (Recommended)

This is the simplest deployment method:

```bash
# 1. Ensure .env file exists and is configured
cp .env.example .env
# Edit .env file and add your API keys

# 2. Start container
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Access application
# Open browser and visit http://localhost:7860
```

**Stop and cleanup:**

```bash
# Stop container
docker-compose down

# Stop and remove all data (use with caution!)
docker-compose down -v
```

### Method 2: Using Docker Commands

If you're not using Docker Compose:

```bash
# 1. Build image
docker build -t video2md .

# 2. Run container
docker run -d \
  --name video2md \
  -p 7860:7860 \
  -v $(pwd):/app/data \
  -e TZ=Australia/Sydney \
  --restart unless-stopped \
  video2md

# 3. View logs
docker logs -f video2md

# 4. Stop container
docker stop video2md
docker rm video2md
```

## 📁 Data Persistence

The container uses a single volume mount to persist all data:

| Container Path | Host Path                | Purpose                                                    |
| -------------- | ------------------------ | ---------------------------------------------------------- |
| `/app/data`    | `./` (current directory) | Parent directory containing input/, output/, models/, .env |

The container automatically creates symbolic links on startup:

- `/app/input` → `/app/data/input`
- `/app/output` → `/app/data/output`
- `/app/models` → `/app/data/models`
- `/app/.env` → `/app/data/.env`

**Why use a single mount point?**

Benefits of using a single parent directory mount:

1. ✅ **Allows file movement between input and output** (same filesystem)
2. ✅ **Simplified configuration** (only one `-v` parameter needed)
3. ✅ **Avoids cross-device link errors** (EXDEV error)

**Important:** Ensure these directories are created before first run:

```bash
mkdir -p input output models
```

## ⚙️ Environment Configuration

### Required Environment Variables

Configure the following variables in `.env` file:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-proj-your-key-here

# Serper API Key (required for web search)
SERPER_API_KEY=your-serper-key-here
```

### Optional Environment Variables

Can be configured in `docker-compose.yml` or Docker command:

```yaml
environment:
  - TZ=Australia/Sydney # Timezone setting
  - GRADIO_SERVER_NAME=0.0.0.0 # Gradio server address
  - GRADIO_SERVER_PORT=7860 # Gradio port
  - RESEARCH_TOOL_SESSION_TIMEOUT_SECONDS=10 # Research timeout
```

## 🔧 Custom Configuration

### Modify Port

**Docker Compose method:**

Edit `docker-compose.yml` file:

```yaml
ports:
  - '8080:7860' # Change host port to 8080
```

**Docker command method:**

```bash
docker run -p 8080:7860 ...  # Use port 8080
```

### Modify Timezone

**Docker Compose method:**

Edit `docker-compose.yml`:

```yaml
environment:
  - TZ=America/New_York # Change to your timezone
```

**Docker command method:**

```bash
docker run -e TZ=Australia/Sydney ...
```

## 🐛 Troubleshooting

### Container Fails to Start

```bash
# View container logs
docker logs video2md

# Check container status
docker ps -a | grep video2md

# Check if .env file exists
ls -la .env
```

### API Key Errors

Ensure `.env` file format is correct:

```bash
# View .env content (hide sensitive info)
cat .env | sed 's/=.*/=***/'
```

### Port Conflicts

If port 7860 is already in use:

```bash
# Check port usage
lsof -i :7860

# Use different port (e.g., 8080)
docker run -p 8080:7860 ...
```

### Permission Issues

Ensure mounted directories have correct permissions:

```bash
# Grant read/write permissions
chmod -R 755 input output models
```

### Out of Memory

If running out of memory when processing large files:

```bash
docker run --memory=4g --memory-swap=4g ...
```

## 🔄 Updating the Application

### Using Docker Compose

```bash
# 1. Stop current container
docker-compose down

# 2. Pull latest code
git pull

# 3. Rebuild and start
docker-compose up -d --build
```

### Using Docker Commands

```bash
# 1. Stop and remove old container
docker stop video2md
docker rm video2md

# 2. Remove old image
docker rmi video2md

# 3. Rebuild
docker build -t video2md .

# 4. Start new container
docker run -d ...
```

## 📊 Monitoring and Maintenance

### View Container Status

```bash
# View running status
docker ps | grep video2md

# View resource usage
docker stats video2md

# View container details
docker inspect video2md
```

### Clean Up Old Data

```bash
# Clean unused Docker resources
docker system prune

# Clean unused images
docker image prune

# Clean old output files (use with caution!)
rm -rf output/*
```

## 🚢 Production Deployment Recommendations

### 1. Use Reverse Proxy

Use Nginx or Traefik as reverse proxy:

**Nginx configuration example:**

```nginx
server {
    listen 80;
    server_name video2md.example.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Enable HTTPS

Configure SSL using Let's Encrypt:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d video2md.example.com
```

### 3. Configure Automatic Backups

Create cron job to backup important data:

```bash
# Add to crontab
0 2 * * * tar -czf /backup/video2md-$(date +\%Y\%m\%d).tar.gz /path/to/video2md/output
```

### 4. Monitoring and Logging

Use log management tools:

```bash
# Use journalctl to view logs (if using systemd)
journalctl -u docker -f | grep video2md

# Or configure Docker log driver
docker run --log-driver=syslog ...
```

## 🔐 Security Recommendations

1. **Never commit `.env` file to version control**
2. **Regularly update Docker images and base images**
3. **Configure file permissions with least privilege principle**
4. **Use HTTPS in production environment**
5. **Regularly backup important data**

## 📝 CI/CD Integration

This project includes Jenkins configuration file `ci/Jenkinsfile` for automated build and deployment.

See Jenkins configuration:

```groovy
// See ci/Jenkinsfile
```

## ❓ FAQ

**Q: Why can't I access the application after container starts?**

A: Check firewall settings and ensure port 7860 is open.

**Q: How to use GPU in container?**

A: Install NVIDIA Container Toolkit and add `--gpus all` parameter when running. See GPU support documentation for details.

**Q: Data lost after container restart?**

A: Ensure volume mounts are correctly configured. Data should be stored in mounted directories.

**Q: How to view detailed processing logs?**

A: Use `docker logs -f video2md` to view real-time log output.

## 📚 Related Documentation

- [README.md](../README.md) - Project overview
- [SETUP.md](../SETUP.md) - Local development setup
- [docs/GPU_SUPPORT.md](GPU_SUPPORT.md) - GPU acceleration configuration
- [docs/ENVIRONMENT_CONFIG.md](ENVIRONMENT_CONFIG.md) - Environment variables reference

## 💬 Getting Help

If you encounter issues:

1. Check container logs
2. Review [GitHub Issues](https://github.com/your-username/video2md/issues)
3. Submit new Issue with detailed error information
