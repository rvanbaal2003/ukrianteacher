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

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "⚠️  WAARSCHUWING: OPENAI_API_KEY is niet ingesteld!"
    echo "Zet deze in met: export OPENAI_API_KEY='jouw-api-key'"
    echo ""
    read -p "Druk op Enter om door te gaan..."
fi

# Run the app
echo "Starting Oekraïense AI Leraar..."
python -m streamlit run app.py
