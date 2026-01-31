#!/bin/zsh
cd "$(dirname "$0")"

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Set OpenAI API Key (vervang met jouw key!)
export OPENAI_API_KEY= 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

# Check if API key is set
if [ "$OPENAI_API_KEY" = "sk-jouw-api-key-hier" ]; then
    echo ""
    echo "⚠️  BELANGRIJK: Vervang 'sk-jouw-api-key-hier' met je echte OpenAI API key!"
    echo "   Edit dit bestand (run.command) en zet je API key op regel 18"
    echo ""
    read -p "Druk op Enter om toch door te gaan..."
fi

# Run the app
echo "Starting Oekraïense AI Leraar..."
streamlit run app.py
