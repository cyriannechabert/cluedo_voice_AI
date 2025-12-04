# Detective Game - Sound Mystery

A detective game where players solve mysteries by questioning AI-generated witnesses using voice or text.

## Features

- **Dynamic Case Generation**: Each case is AI-generated with unique characters and mysteries
- **AI Characters**: Each witness has personality, memory, and unique testimony
- **Voice Support**: Optional text-to-speech using 11 Labs API
- **Minimal UI**: Focus on immersive audio storytelling
- **Console Logging**: All case information is printed to console for debugging

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask app:
```bash
python app.py
```

3. Open your browser to `http://localhost:5000`

## How to Play

1. Click "Generate New Case" to start
2. Select a character to question
3. Type your questions and press Enter
4. Listen for contradictions and clues
5. Name the suspect when you're ready

## API Keys

The API keys are already configured in `app.py`. The game uses:
- **Gemini API** for case generation and character conversations
- **11 Labs API** for text-to-speech

