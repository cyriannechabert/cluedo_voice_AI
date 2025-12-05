from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import requests
import json
import os
from dotenv import load_dotenv
import hathora
import io

load_dotenv()

app = Flask(__name__)
CORS(app)

# Serve character images
@app.route('/characters/<path:filename>')
def serve_character_image(filename):
    return send_from_directory('characters', filename)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HATHORA_API_KEY = os.getenv("HATHORA_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Available voices
AVAILABLE_VOICES = [
    {
        "voice_id": "CwhRBWXzGAHq8TQ4Fs17",
        "name": "Roger",
        "description": "Easy going and perfect for casual conversations.",
        "accent": "american",
        "gender": "male",
        "descriptive": "classy",
        "age": "middle_aged"
    },
    {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Sarah",
        "description": "Young adult woman with a confident and warm, mature quality and a reassuring, professional tone.",
        "accent": "american",
        "gender": "female",
        "descriptive": "professional",
        "age": "young"
    },
    {
        "voice_id": "FGY2WhTYpPnrIDTdsKH5",
        "name": "Laura",
        "description": "This young adult female voice delivers sunny enthusiasm with a quirky attitude.",
        "accent": "american",
        "gender": "female",
        "descriptive": "sassy",
        "age": "young"
    },
    {
        "voice_id": "IKne3meq5aSn9XLyUdCD",
        "name": "Charlie",
        "description": "A young Australian male with a confident and energetic voice.",
        "accent": "australian",
        "gender": "male",
        "descriptive": "hyped",
        "age": "young"
    },
    {
        "voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "name": "George",
        "description": "Warm resonance that instantly captivates listeners.",
        "accent": "british",
        "gender": "male",
        "descriptive": "mature",
        "age": "middle_aged"
    },
    {
        "voice_id": "N2lVS1w4EtoT3dr4eOWO",
        "name": "Callum",
        "description": "Deceptively gravelly, yet unsettling edge.",
        "accent": "american",
        "gender": "male",
        "descriptive": None,
        "age": "middle_aged"
    },
    {
        "voice_id": "SAz9YHcvj6GT2YYXdXww",
        "name": "River",
        "description": "A relaxed, neutral voice ready for narrations or conversational projects.",
        "accent": "american",
        "gender": "neutral",
        "descriptive": "calm",
        "age": "middle_aged"
    },
    {
        "voice_id": "SOYHLrjzK2X1ezoPC6cr",
        "name": "Harry",
        "description": "An animated warrior ready to charge forward.",
        "accent": "american",
        "gender": "male",
        "descriptive": "rough",
        "age": "young"
    },
    {
        "voice_id": "TX3LPaxmHKxFdv7VOQHJ",
        "name": "Liam",
        "description": "A young adult with energy and warmth - suitable for reels and shorts.",
        "accent": "american",
        "gender": "male",
        "descriptive": "confident",
        "age": "young"
    },
    {
        "voice_id": "Xb7hH8MSUJpSbSDYk0k2",
        "name": "Alice",
        "description": "Clear and engaging, friendly woman with a British accent suitable for e-learning.",
        "accent": "british",
        "gender": "female",
        "descriptive": "professional",
        "age": "middle_aged"
    }
]

# Game state
game_state = {
    'case': None,
    'characters': [],
    'suspect': None,
    'conversations': {}
}

def select_voice_for_character(character_name, character_role, personality_traits, character_gender=None):
    """Select an appropriate voice for a character based on name, role, personality, and gender"""
    import random
    
    gender = character_gender
    
    # If gender not provided, try to infer from name (simple heuristic)
    if not gender:
        name_lower = character_name.lower()
        
        # Common female name patterns
        female_indicators = ['sarah', 'emma', 'laura', 'alice', 'mary', 'anna', 'sophia', 'olivia', 
                            'emily', 'jessica', 'lisa', 'amy', 'diana', 'elizabeth', 'jennifer', 'eleanor']
        # Common male name patterns  
        male_indicators = ['mike', 'john', 'david', 'james', 'robert', 'william', 'richard', 'thomas',
                           'charles', 'daniel', 'matthew', 'mark', 'paul', 'steven', 'andrew', 'bartholomew', 'barty']
        
        if any(indicator in name_lower for indicator in female_indicators):
            gender = 'female'
        elif any(indicator in name_lower for indicator in male_indicators):
            gender = 'male'
    
    # If we still can't determine from name, try to infer from role
    if not gender:
        role_lower = character_role.lower()
        if any(word in role_lower for word in ['lady', 'woman', 'miss', 'mrs', 'ms', 'mother', 'wife', 'sister', 'daughter']):
            gender = 'female'
        elif any(word in role_lower for word in ['mr', 'sir', 'lord', 'father', 'husband', 'brother', 'man', 'son']):
            gender = 'male'
    
    # Normalize gender
    if gender:
        gender = gender.lower()
        if gender not in ['male', 'female', 'neutral']:
            gender = None
    
    # Filter voices by gender
    if gender:
        matching_voices = [v for v in AVAILABLE_VOICES if v['gender'] == gender]
    else:
        # If we can't determine gender, use neutral or all voices
        matching_voices = [v for v in AVAILABLE_VOICES if v['gender'] == 'neutral'] or AVAILABLE_VOICES
    
    if not matching_voices:
        matching_voices = AVAILABLE_VOICES
    
    # Select a random voice from matching voices
    selected_voice = random.choice(matching_voices)
    
    print(f"Selected voice '{selected_voice['name']}' ({selected_voice['gender']}, {selected_voice['accent']}) for character '{character_name}' ({gender or 'unknown'})")
    
    return selected_voice['voice_id']

def generate_case():
    """Generate a detective case with 3-4 characters"""
    prompt = """Generate a simple detective mystery case with the following structure:

1. A brief case description (1-2 sentences)
2. A list of 4 characters (witnesses and one suspect):
   - Name
   - Role/Relationship
   - Gender (male, female, or other)
   - Age (approximate age as a number, e.g., 25, 35, 60)
   - Personality traits (2-3 traits)
   - Their testimony/alibi (what they claim happened)
   - A contradiction or clue in their story (something that doesn't add up)

3. The actual suspect (who committed the crime)
4. The truth (what really happened)

Format as JSON with this structure:
{
  "case_description": "...",
  "characters": [
    {
      "name": "...",
      "role": "...",
      "gender": "male" or "female",
      "age": 25,
      "personality": ["trait1", "trait2"],
      "testimony": "...",
      "contradiction": "..."
    }
  ],
  "suspect": "character_name",
  "truth": "..."
}

Keep it simple - a theft, a missing item, or a small mystery. Make sure one character is clearly the suspect with a contradiction in their story. Include gender and age for each character."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Extract JSON from response (might have markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        case_data = json.loads(text)
        return case_data
    except Exception as e:
        print(f"Error generating case: {e}")
        # Fallback case
        return {
            "case_description": "A valuable painting was stolen from the art gallery last night.",
            "characters": [
                {
                    "name": "Sarah",
                    "role": "Gallery Manager",
                    "gender": "female",
                    "age": 35,
                    "personality": ["nervous", "defensive"],
                    "testimony": "I was in my office all night doing paperwork. I didn't see anything suspicious.",
                    "contradiction": "Claims to be in office but security footage shows her near the gallery at 2 AM"
                },
                {
                    "name": "Mike",
                    "role": "Security Guard",
                    "gender": "male",
                    "age": 35,
                    "personality": ["calm", "observant"],
                    "testimony": "I did my rounds every hour. Everything seemed normal until I found the painting missing at 6 AM.",
                    "contradiction": "None - his story is consistent"
                },
                {
                    "name": "Emma",
                    "role": "Art Dealer",
                    "gender": "female",
                    "age": 30,
                    "personality": ["suspicious", "evasive"],
                    "testimony": "I was at home sleeping. I have no idea who could have done this.",
                    "contradiction": "None - but she was the last person seen near the painting before it disappeared"
                }
            ],
            "suspect": "Sarah",
            "truth": "Sarah stole the painting to pay off her debts. She used her key to access the gallery after hours and took the painting, then tried to cover it up by claiming she was in her office."
        }

def get_character_conversation_prompt(character, case_description, player_message):
    """Generate a prompt for character conversation"""
    return f"""You are {character['name']}, a {character['role']} in a detective mystery.

Case: {case_description}

Your personality: {', '.join(character['personality'])}
Your testimony: {character['testimony']}

You are being questioned by a detective. Respond naturally based on your personality and testimony. 
If you are the suspect, be evasive and try to avoid revealing the contradiction: {character.get('contradiction', 'None')}
If you are not the suspect, be helpful but stick to what you know.

Keep responses brief (1-2 sentences). Stay in character.

IMPORTANT: Add emotion tags to your response when appropriate to convey feelings and tone. Use these tags:
- [happy] - for happy or positive emotions
- [excited] - for excitement or enthusiasm
- [sad] - for sadness or disappointment
- [angry] - for anger or frustration
- [nervous] - for nervousness or anxiety
- [curious] - for curiosity or questioning
- [mischievously] - for mischievous or sly behavior
- [laughs] - for laughter
- [sighs] - for sighs
- [whispers] - for whispering or speaking quietly

Example: "[nervous] Well, I... I'm not sure what to say. [sighs] I was at home that night."

Use emotion tags naturally and only when they add to the character's response. Don't overuse them. You can use multiple tags in one response if it fits the emotional flow.

Detective asks: "{player_message}"

Your response:"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-case', methods=['POST'])
def generate_case_route():
    """Generate a new case"""
    case = generate_case()
    
    # Assign voice IDs to each character
    for char in case['characters']:
        voice_id = select_voice_for_character(
            char['name'],
            char['role'],
            char.get('personality', []),
            char.get('gender')  # Use gender from AI if provided
        )
        char['voice_id'] = voice_id
    
    game_state['case'] = case
    game_state['characters'] = case['characters']
    game_state['suspect'] = case['suspect']
    game_state['conversations'] = {char['name']: [] for char in case['characters']}
    
    # Print case info to console
    print("\n" + "="*60)
    print("NEW CASE GENERATED")
    print("="*60)
    print(f"\nCase: {case['case_description']}")
    print(f"\nSuspect: {case['suspect']}")
    print(f"\nTruth: {case['truth']}")
    print("\nCharacters:")
    for char in case['characters']:
        print(f"\n  {char['name']} ({char['role']})")
        print(f"    Personality: {', '.join(char['personality'])}")
        print(f"    Testimony: {char['testimony']}")
        print(f"    Contradiction: {char.get('contradiction', 'None')}")
        print(f"    Voice ID: {char.get('voice_id', 'Not assigned')}")
    print("="*60 + "\n")
    
    return jsonify({
        'success': True,
        'case': case
    })

@app.route('/api/characters', methods=['GET'])
def get_characters():
    """Get list of characters"""
    if not game_state['characters']:
        return jsonify({'error': 'No case generated yet'}), 400
    return jsonify({
        'characters': game_state['characters']
    })

@app.route('/api/converse', methods=['POST'])
def converse():
    """Handle conversation with a character"""
    data = request.json
    character_name = data.get('character')
    message = data.get('message')
    
    if not character_name or not message:
        return jsonify({'error': 'Missing character or message'}), 400
    
    if not game_state['characters']:
        return jsonify({'error': 'No case generated yet'}), 400
    
    # Find character (case-insensitive)
    character = None
    for char in game_state['characters']:
        if char['name'].lower() == character_name.lower():
            character = char
            break
    
    if not character:
        available = [c['name'] for c in game_state['characters']]
        print(f"Character not found: '{character_name}'. Available: {available}")
        return jsonify({
            'error': 'Character not found',
            'requested': character_name,
            'available': available
        }), 404
    
    # Generate response
    prompt = get_character_conversation_prompt(
        character,
        game_state['case']['case_description'],
        message
    )
    
    try:
        response = model.generate_content(prompt)
        character_response = response.text.strip()
        
        # Store conversation
        if character_name not in game_state['conversations']:
            game_state['conversations'][character_name] = []
        
        game_state['conversations'][character_name].append({
            'player': message,
            'character': character_response
        })
        
        print(f"\n[{character_name}] Detective: {message}")
        print(f"[{character_name}] {character['name']}: {character_response}\n")
        
        return jsonify({
            'success': True,
            'response': character_response,
            'character': character_name
        })
    except Exception as e:
        print(f"Error in conversation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using Hathora SDK"""
    data = request.json
    text = data.get('text')
    character_name = data.get('character', 'default')

    if not text:
        return jsonify({'error': 'Missing text'}), 400

    # Find the character and get their gender for voice selection
    character_gender = None

    if character_name and game_state['characters']:
        for char in game_state['characters']:
            if char['name'].lower() == character_name.lower():
                character_gender = char.get('gender', 'female')
                break

    # Select kokoro voice based on gender
    # Male voices: am_adam, am_michael
    # Female voices: af_bella, af_sarah, af_nicole
    if character_gender == 'male':
        kokoro_voice = "am_adam"
    else:
        kokoro_voice = "af_bella"

    print(f"\n{'='*60}")
    print(f"Hathora TTS Request")
    print(f"Character: {character_name} ({character_gender or 'unknown'})")
    print(f"Kokoro voice: {kokoro_voice}")
    print(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")
    print(f"Text length: {len(text)} chars")
    print(f"API Key set: {'Yes' if HATHORA_API_KEY else 'No'}")
    print(f"{'='*60}\n")

    try:
        # Initialize Hathora client
        client = hathora.Hathora(api_key=HATHORA_API_KEY)

        # Use kokoro model with gender-appropriate voice
        print(f"Using kokoro model with {kokoro_voice} voice...")

        response = client.text_to_speech.convert(
            "kokoro",
            text,
            voice=kokoro_voice
        )

        # Save to temporary file and read back (like test_hathora_simple.py)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name

        response.save(temp_filename)

        # Read the audio file
        with open(temp_filename, 'rb') as f:
            audio_data = f.read()

        # Clean up temp file
        os.remove(temp_filename)

        print(f"[OK] Audio generated successfully ({len(audio_data)} bytes)")

        return audio_data, 200, {'Content-Type': 'audio/wav'}

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Hathora SDK Error")
        print(f"Error: {str(e)}")
        print(f"Character: {character_name}")
        print(f"{'='*60}\n")

        import traceback
        traceback.print_exc()

        return jsonify({
            'error': f'Hathora TTS error: {str(e)}',
            'details': 'Check server logs for details.'
        }), 500

@app.route('/api/test-tts-key', methods=['GET'])
def test_tts_key():
    """Test Hathora API key by checking API access"""
    try:
        # Test with a simple request to Hathora Models API
        # Adjust endpoint based on Hathora's actual API documentation
        url = "https://models.hathora.dev/v1/models"
        headers = {
            "Authorization": f"Bearer {HATHORA_API_KEY}"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            models = response.json()
            return jsonify({
                'success': True,
                'message': 'Hathora API key is valid',
                'details': models
            })
        else:
            error_msg = response.text
            return jsonify({
                'success': False,
                'error': f'API key test failed: {response.status_code}',
                'details': error_msg
            }), response.status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submit-suspect', methods=['POST'])
def submit_suspect():
    """Submit suspect guess"""
    data = request.json
    guessed_suspect = data.get('suspect')
    
    if not guessed_suspect:
        return jsonify({'error': 'Missing suspect name'}), 400
    
    correct = guessed_suspect.lower() == game_state['suspect'].lower()
    
    result = {
        'correct': correct,
        'guessed': guessed_suspect,
        'actual_suspect': game_state['suspect'],
        'truth': game_state['case']['truth'] if correct else None
    }
    
    if correct:
        print(f"\n✓ CORRECT! The suspect was {game_state['suspect']}")
        print(f"Truth: {game_state['case']['truth']}\n")
    else:
        print(f"\n✗ WRONG! You guessed {guessed_suspect}, but the actual suspect was {game_state['suspect']}\n")
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

