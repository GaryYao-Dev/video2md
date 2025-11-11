# GPU Setup Script for video2md
# This script installs PyTorch with CUDA support for GPU acceleration

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "video2md GPU Setup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check if CUDA is available
Write-Host "Checking for NVIDIA GPU and CUDA..." -ForegroundColor Yellow

try {
    $nvccOutput = nvcc --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ CUDA detected" -ForegroundColor Green
        Write-Host $nvccOutput
        
        # Determine CUDA version
        if ($nvccOutput -match "release (\d+)\.(\d+)") {
            $cudaMajor = [int]$matches[1]
            $cudaMinor = [int]$matches[2]
            
            Write-Host ""
            Write-Host "CUDA Version: $cudaMajor.$cudaMinor" -ForegroundColor Cyan
            
            # Recommend PyTorch CUDA version
            if ($cudaMajor -ge 12) {
                $torchCuda = "cu124"
                Write-Host "Recommended PyTorch: CUDA 12.4 build" -ForegroundColor Green
            } elseif ($cudaMajor -eq 11) {
                $torchCuda = "cu118"
                Write-Host "Recommended PyTorch: CUDA 11.8 build" -ForegroundColor Green
            } else {
                Write-Host "⚠ Unsupported CUDA version. Defaulting to CPU mode." -ForegroundColor Yellow
                $torchCuda = "cpu"
            }
        }
    }
} catch {
    Write-Host "✗ CUDA not detected. Will use CPU mode." -ForegroundColor Yellow
    $torchCuda = "cpu"
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan

# Ask user for confirmation
if ($torchCuda -ne "cpu") {
    $response = Read-Host "Install PyTorch with GPU support ($torchCuda)? [Y/n]"
    if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
        Write-Host ""
        Write-Host "Installing PyTorch with CUDA support..." -ForegroundColor Yellow
        Write-Host "This may take several minutes (PyTorch is ~2GB)..." -ForegroundColor Yellow
        Write-Host ""
        
        $indexUrl = "https://download.pytorch.org/whl/$torchCuda"
        uv pip install torch torchvision torchaudio --index-url $indexUrl
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ PyTorch installed successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Verifying GPU support..." -ForegroundColor Yellow
            
            uv run python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
        } else {
            Write-Host ""
            Write-Host "✗ Installation failed!" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Installation cancelled." -ForegroundColor Yellow
    }
} else {
    Write-Host "CPU mode will be used (GPU support not available)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Cyan
