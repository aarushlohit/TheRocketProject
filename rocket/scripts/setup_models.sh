#!/bin/bash
# Model Setup Script
# Downloads and prepares AI models for Whisper and OCR

set -e

echo "🎯 Rocket Models Setup"
echo "====================="
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

models_dir="$HOME/.rocket/models"
mkdir -p "$models_dir"

echo "Models directory: $models_dir"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

# Whisper Model
echo "Whisper Model Setup"
echo "-------------------"
echo
echo "Whisper is the speech-to-text model."
echo "Choose model size (larger = more accurate but slower):"
echo "  tiny     - 39MB, fastest, suitable for low-resource devices"
echo "  base     - 140MB, recommended (Phase 0)"
echo "  small    - 466MB, better accuracy"
echo "  medium   - 1.5GB, good accuracy"
echo "  large    - 2.9GB, best accuracy"
echo

read -p "Enter model size [base]: " whisper_model
whisper_model=${whisper_model:-base}

if [ "$whisper_model" != "tiny" ] && [ "$whisper_model" != "base" ] && \
   [ "$whisper_model" != "small" ] && [ "$whisper_model" != "medium" ] && \
   [ "$whisper_model" != "large" ]; then
    echo -e "${YELLOW}Invalid model size. Using 'base'${NC}"
    whisper_model="base"
fi

echo "Downloading Whisper model: $whisper_model"
echo "(This may take a few minutes depending on model size)"

# Try to download Whisper model
if python3 -c "import whisper" 2>/dev/null; then
    python3 -c "
import whisper
print('Downloading model...')
model = whisper.load_model('$whisper_model', download_root='$models_dir')
print('Model loaded successfully')
"
    echo -e "${GREEN}✓${NC} Whisper model downloaded"
else
    echo -e "${YELLOW}⚠${NC}  Whisper not installed. To use local STT, run:"
    echo "    pip install openai-whisper"
fi

echo

# OCR Model (Tesseract)
echo "OCR Model Setup (Optional)"
echo "--------------------------"
echo "Tesseract is used for OCR in future phases."
echo
read -p "Install/check Tesseract? [y/N]: " install_tesseract

if [ "$install_tesseract" = "y" ] || [ "$install_tesseract" = "Y" ]; then
    if command -v tesseract &> /dev/null; then
        echo -e "${GREEN}✓${NC} Tesseract is installed"
        tesseract --version | head -1
    else
        echo -e "${YELLOW}⚠${NC}  Tesseract not found"
        echo "To install on your system:"
        echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
        echo "  macOS: brew install tesseract"
        echo "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
    fi
fi

echo
echo -e "${GREEN}✓${NC} Models setup complete!"
echo
echo "Configuration saved in: ~/.rocket/config.yaml"
echo "Models stored in: $models_dir"
echo
