#!/bin/bash
# GPU Setup Script for video2md (Linux/macOS)
# This script installs PyTorch with CUDA support for GPU acceleration

echo "======================================="
echo "video2md GPU Setup"
echo "======================================="
echo ""

# Check if CUDA is available
echo "Checking for NVIDIA GPU and CUDA..."

if command -v nvcc &> /dev/null; then
    echo "✓ CUDA detected"
    nvcc --version
    
    # Determine CUDA version
    CUDA_VERSION=$(nvcc --version | grep "release" | sed -n 's/.*release \([0-9]*\.[0-9]*\).*/\1/p')
    CUDA_MAJOR=$(echo $CUDA_VERSION | cut -d. -f1)
    
    echo ""
    echo "CUDA Version: $CUDA_VERSION"
    
    # Recommend PyTorch CUDA version
    if [ "$CUDA_MAJOR" -ge 12 ]; then
        TORCH_CUDA="cu124"
        echo "Recommended PyTorch: CUDA 12.4 build"
    elif [ "$CUDA_MAJOR" -eq 11 ]; then
        TORCH_CUDA="cu118"
        echo "Recommended PyTorch: CUDA 11.8 build"
    else
        echo "⚠ Unsupported CUDA version. Defaulting to CPU mode."
        TORCH_CUDA="cpu"
    fi
else
    echo "✗ CUDA not detected. Will use CPU mode."
    TORCH_CUDA="cpu"
fi

echo ""
echo "======================================="

# Ask user for confirmation
if [ "$TORCH_CUDA" != "cpu" ]; then
    read -p "Install PyTorch with GPU support ($TORCH_CUDA)? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        echo ""
        echo "Installing PyTorch with CUDA support..."
        echo "This may take several minutes (PyTorch is ~2GB)..."
        echo ""
        
        INDEX_URL="https://download.pytorch.org/whl/$TORCH_CUDA"
        uv pip install torch torchvision torchaudio --index-url $INDEX_URL
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✓ PyTorch installed successfully!"
            echo ""
            echo "Verifying GPU support..."
            
            uv run python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
        else
            echo ""
            echo "✗ Installation failed!"
            exit 1
        fi
    else
        echo "Installation cancelled."
    fi
else
    echo "CPU mode will be used (GPU support not available)."
fi

echo ""
echo "======================================="
echo "Setup complete!"
echo "======================================="
