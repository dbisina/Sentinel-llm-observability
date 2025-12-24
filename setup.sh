#!/bin/bash
set -e

echo '🚀 Setting up LLM Observability Platform...'
echo ''

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo '❌ Python 3 is required but not found'
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VERSION detected"

# Check if Python version is 3.11+
if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo '✅ Python version is 3.11+'
else
    echo '⚠️  Warning: Python 3.11+ is recommended for best compatibility'
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo '📦 Creating virtual environment...'
    python3 -m venv venv
else
    echo '📦 Virtual environment already exists'
fi

# Activate virtual environment
echo '🔧 Activating virtual environment...'
source venv/bin/activate

# Upgrade pip
echo '⬆️  Upgrading pip...'
pip install --upgrade pip --quiet

# Install dependencies
echo '📥 Installing dependencies...'
pip install -r requirements.txt --quiet

# Create necessary directories
echo '📁 Creating directories...'
mkdir -p data
mkdir -p logs

# Setup environment file
if [ ! -f .env ]; then
    echo '📄 Creating .env from template...'
    cp .env.example .env
    echo ''
    echo '⚠️  IMPORTANT: Please edit .env with your API keys:'
    echo '   - DD_API_KEY: Your Datadog API key'
    echo '   - DD_APP_KEY: Your Datadog Application key'
    echo '   - GOOGLE_PROJECT_ID: Your GCP project ID'
    echo '   - GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON'
    echo ''
else
    echo '📄 .env file already exists'
fi

# Generate baseline data
echo '📊 Generating baseline data...'
python scripts/generate_baseline.py

echo ''
echo '✅ Setup complete!'
echo ''
echo '🎯 Next steps:'
echo '   1. Edit .env with your API keys (if not done)'
echo '   2. Activate the virtual environment:'
echo '      source venv/bin/activate'
echo '   3. Start the server:'
echo '      python main.py'
echo ''
echo '📚 For more information, see README.md'
