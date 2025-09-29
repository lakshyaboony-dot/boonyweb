from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_
from sqlalchemy.exc import OperationalError, DisconnectionError
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, g,flash
from flask_cors import CORS
import jwt
from functools import wraps
from datetime import datetime, timedelta
import time
from config import Config
from models import db, User, Progress, UserSurvey, Poem, Syllabus, VocabularyWord
from services.syllabus import load_day_statements
from services.stt import transcribe_audio
from services.tts import generate_tts
from flask import session
import os, random, requests
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
import psycopg2
import psycopg2.extras
import pandas as pd
from flask import Flask, send_file, request
from services.ai_guide import generate_signup_guide
from services.tts import generate_tts
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from services.sync import run_full_sync
import tempfile
from core.guide_helper import BoonyGuide
from core.openai_helper import call_openai, ENGLISH_TUTOR_PROMPTS,client
from services.pronunciation import detect_mispronounced_words
from flask import request, redirect, url_for
from flask import send_from_directory
from config import Config

import json
from werkzeug.utils import secure_filename
import base64
import json

# Import enhanced modules
from revios import create_revision_routes, revision_manager
from vocab import create_vocabulary_routes

# PDF/Image processing imports
import PyPDF2
import pytesseract
from PIL import Image
import io
import re
from gtts import gTTS
import tempfile


# ----------------------
# App + Config
# ----------------------
app = Flask(__name__, instance_relative_config=True, static_url_path="/static")
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
# Disable static file caching during development
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.cache = {}

# allowed audio extensions (हम इन्हें चेक करेंगे)
ALLOWED_AUDIO_EXTENSIONS = {"wav", "mp3", "m4a","webm"}
app.config.from_object(Config)
app.secret_key = "super-secret-key"   # change in production

# Enable CORS for mobile app
CORS(app, origins=["*"])
app.config["DATA_SYLLABUS"] = "data/syllabus/english_spoken_syllabus_filled_ai.xlsx"
# Ensure instance + uploads
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

UPLOAD_FOLDER = "user_data"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ----------------------
# DB + Migrate + Auth
# ----------------------
db.init_app(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access - return JSON for API routes, redirect for web routes"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login'))

# Create a separate blueprint for public API endpoints
from flask import Blueprint
public_api = Blueprint('public_api', __name__)

# Move analyze_speech to public blueprint (will be registered later)
@public_api.route("/api/analyze_speech", methods=["POST"])
def public_analyze_speech():
    """
    Enhanced speech analysis endpoint:
    - Converts audio to 16kHz mono WAV
    - Transcribes speech via STT
    - Computes word-level fuzzy accuracy + sentence similarity
    - Returns mispronounced words and user-friendly feedback
    """
    import os, tempfile, traceback
    from difflib import SequenceMatcher
    try:
        from pydub import AudioSegment
        from rapidfuzz import fuzz
    except ImportError:
        return jsonify({"ok": False, "error_code": "DEPENDENCY_MISSING",
                        "message": "pydub and rapidfuzz are required"}), 500

    try:
        # 1️⃣ Request validation
        audio_file = request.files.get("audio")
        if not audio_file:
            return jsonify({"ok": False, "error_code": "NO_AUDIO", "message": "No audio uploaded"}), 400

        expected_text = (request.form.get("expected_text") or "").strip()
        if not expected_text:
            expected_text = ""

        filename = getattr(audio_file, "filename", "")
        if not filename or "." not in filename:
            return jsonify({"ok": False, "error_code": "BAD_FILENAME", "message": "Invalid filename"}), 400
        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in {"wav", "mp3", "m4a"}:
            return jsonify({"ok": False, "error_code": "BAD_FORMAT",
                            "message": "Allowed formats: wav, mp3, m4a"}), 400

        # 2️⃣ Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tf:
            audio_path = tf.name
            audio_file.save(audio_path)

        # 3️⃣ Convert to 16kHz mono WAV
        converted_path = audio_path.rsplit(".", 1)[0] + "_16k.wav"
        try:
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_channels(1).set_frame_rate(16000)
            audio.export(converted_path, format="wav")
        except Exception as e:
            converted_path = audio_path  # fallback to original
        finally:
            try: os.remove(audio_path)
            except: pass

        # 4️⃣ Transcribe
        stt_func = None
        try:
            from services.stt import transcribe_audio_file
            stt_func = transcribe_audio_file
        except ImportError:
            try:
                from services.stt import transcribe_audio
                stt_func = transcribe_audio
            except ImportError:
                return jsonify({"ok": False, "error_code": "NO_STT",
                                "message": "STT function not configured"}), 500

        try:
            user_text = stt_func(converted_path) or ""
        except Exception as e:
            tb = traceback.format_exc()
            return jsonify({"ok": False, "error_code": "TRANSCRIPTION_FAILED",
                            "message": str(e), "trace": tb}), 500
        finally:
            try: os.remove(converted_path)
            except: pass

        if not user_text.strip():
            return jsonify({"ok": False, "error_code": "NO_SPEECH",
                            "message": "No speech detected. Try again."}), 400

        # 5️⃣ Pronunciation analysis
        try:
            from services.pronunciation import detect_mispronounced_words
            pronunciation_result = detect_mispronounced_words(user_text, expected_text)
        except Exception:
            pronunciation_result = {"status": "unknown", "mispronounced": []}

        # 6️⃣ Word-level fuzzy accuracy
        def _clean_words(s):
            return [w.strip(".,!?;:").lower() for w in s.strip().split() if w.strip()]

        expected_words = _clean_words(expected_text)
        user_words = _clean_words(user_text)

        total = len(expected_words) or 1
        correct = 0
        mismatches = []

        for i, w in enumerate(expected_words):
            if i < len(user_words):
                sim = fuzz.ratio(w, user_words[i]) / 100  # fuzzy similarity
                if sim >= 0.7:
                    correct += 1
                else:
                    mismatches.append({"expected": w, "spoken": user_words[i], "similarity": round(sim,2)})
            else:
                mismatches.append({"expected": w, "spoken": "", "similarity": 0.0})

        word_accuracy = round((correct / total) * 100, 1)
        sentence_similarity = round(SequenceMatcher(None, expected_text.lower(), user_text.lower()).ratio() * 100, 1)

        # 7️⃣ Feedback
        if word_accuracy >= 90:
            feedback = "Excellent pronunciation! 👏"
        elif word_accuracy >= 75:
            feedback = "Good attempt. Focus on clarity of a few words."
        elif word_accuracy >= 50:
            feedback = "You missed some words. Try: " + ", ".join([m["expected"] for m in mismatches[:5]])
        else:
            feedback = "Let's slow down and try again. Repeat each word clearly."

        # 8️⃣ Return result
        from services.pronunciation import get_pronunciation_corrections, get_pronunciation_audio_text

        corrections = get_pronunciation_corrections(user_text, expected_text)

        # Add audio tips
        for c in corrections:
            expected_word = c.get("expected_word", "")
            if expected_word not in ["[missing]", "[none]"]:
                c["audio_tip"] = get_pronunciation_audio_text(expected_word)
            else:
                c["audio_tip"] = ""

        return jsonify({
            "ok": True,
            "transcription": user_text,
            "expected_text": expected_text,
            "analysis": {
                "word_accuracy": word_accuracy,
                "sentence_similarity": sentence_similarity,
                "total_words": len(expected_words),
                "correct_words": correct,
                "incorrect_words": len(expected_words) - correct,
                "mismatches": mismatches,
                "pronunciation_status": pronunciation_result.get("status"),
                "pronunciation_mispronounced": pronunciation_result.get("mispronounced", []),
                "feedback": feedback
            },
            "corrections": corrections
        })

    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({"ok": False, "error_code": "SERVER_ERROR",
                        "message": str(e), "trace": tb}), 500

# Blueprint route for detailed mispronounced words analysis
@public_api.route("/api/analyze_mispronounced_words", methods=["POST"])
def analyze_mispronounced_words():
    """Detailed analysis and correction of mispronounced words with audio tips"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No JSON data received"}), 400

        transcribed_text = data.get('transcribed_text', '').strip()
        expected_text = data.get('expected_text', '').strip()

        if not transcribed_text or not expected_text:
            return jsonify({"ok": False, "error": "Both transcribed_text and expected_text are required"}), 400

        # Import pronunciation analysis functions
        from services.pronunciation import (
            detect_mispronounced_words,
            get_pronunciation_corrections,
            get_pronunciation_audio_text  # <-- new helper
        )

        # Analyze mispronounced words
        pronunciation_result = detect_mispronounced_words(transcribed_text, expected_text)

        # Get detailed corrections
        corrections = get_pronunciation_corrections(transcribed_text, expected_text)

        # Add audio_tip for each correction
        for c in corrections:
            expected_word = c.get("expected_word", "")
            if expected_word not in ["[missing]", "[none]"]:
                c["audio_tip"] = get_pronunciation_audio_text(expected_word)
            else:
                c["audio_tip"] = ""

        # Word-level accuracy
        expected_words = expected_text.lower().split()
        transcribed_words = transcribed_text.lower().split()
        correct_words = 0
        total_words = len(expected_words)

        import difflib
        for i, expected_word in enumerate(expected_words):
            if i < len(transcribed_words):
                similarity = difflib.SequenceMatcher(None, expected_word, transcribed_words[i]).ratio()
                if similarity >= 0.8:
                    correct_words += 1

        word_accuracy = (correct_words / total_words * 100) if total_words > 0 else 0
        sentence_similarity = difflib.SequenceMatcher(None, expected_text.lower(), transcribed_text.lower()).ratio() * 100

        return jsonify({
            "ok": True,
            "analysis": {
                "status": pronunciation_result.get("status", "unknown"),
                "mispronounced_words": pronunciation_result.get("mispronounced", []),
                "word_accuracy": round(word_accuracy, 2),
                "sentence_similarity": round(sentence_similarity, 2),
                "total_words": total_words,
                "correct_words": correct_words,
                "incorrect_words": total_words - correct_words
            },
            "corrections": corrections,
            "transcribed_text": transcribed_text,
            "expected_text": expected_text
        })

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return jsonify({"ok": False, "error": f"Analysis failed: {str(e)}", "trace": tb}), 500

@login_manager.user_loader
def load_user(user_id):
    """Load user with database connection error handling and retry"""
    def _load_user():
        return db.session.get(User, user_id)
    
    try:
        return retry_db_operation(_load_user)
    except Exception as e:
        print(f"⚠️ Database connection error in load_user after retries: {e}")
        # Return None to force re-authentication
        return None

# Database Connection Utilities
def retry_db_operation(operation, max_retries=3, delay=1):
    """Retry database operations with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return operation()
        except (OperationalError, DisconnectionError) as e:
            if attempt == max_retries - 1:
                raise e
            print(f"🔄 Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(delay * (2 ** attempt))  # Exponential backoff
            try:
                db.session.rollback()
                db.session.close()
            except:
                pass
    return None

# Database Error Handlers
@app.teardown_appcontext
def close_db_session(error):
    """Close database session on app context teardown"""
    if error:
        try:
            db.session.rollback()
        except:
            pass
    try:
        db.session.close()
    except:
        pass

@app.errorhandler(Exception)
def handle_database_errors(error):
    """Global error handler for database connection issues"""
    if "server closed the connection unexpectedly" in str(error) or "OperationalError" in str(error):
        print(f"🔄 Database connection error detected: {error}")
        try:
            db.session.rollback()
            db.session.close()
        except:
            pass
        # Redirect to login page for authentication errors
        if request.endpoint and not request.endpoint.startswith('static'):
            return redirect(url_for('login', error='connection_lost'))
    return str(error), 500

# Safety net for first boot
with app.app_context():
    db.create_all()
    # Try sync if using SQLite last time and Supabase is now available
    try:
        # run_full_sync()  # Temporarily disabled to debug KeyError
        print("✅ Sync temporarily disabled for debugging")
    except Exception as e:
        print("⚠️ Sync skipped:", e)

# ----------------------
# Register Routes
# ----------------------
# create_vocabulary_routes(app)  # Commented out due to route conflicts

# ----------------------
# JWT Token Authentication for API
# ----------------------
def verify_jwt_token(token):
    """Verify JWT token and return user or None"""
    try:
        # Decode the token using the app's secret key
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if user_id:
            return User.query.get(user_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    return None

def api_login_required(f):
    """Custom decorator for API routes that require JWT token authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401
        
        # Extract token from "Bearer <token>" format
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        # Verify token and get user
        user = verify_jwt_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Set current_user for the request
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

# ----------------------
# Helpers: Thought + Stars
# ----------------------
def get_thought_of_day() -> str:
    """
    Try ZenQuotes 'today'; fallback to local list.
    """
    try:
        res = requests.get("https://zenquotes.io/api/today", timeout=4)
        data = res.json()
        if isinstance(data, list) and data:
            return f"{data[0].get('q','Keep learning, keep growing.')} — {data[0].get('a','')}".strip()
    except Exception:
        pass
    fallback = [
        "Keep learning, keep growing.",
        "Small steps daily → Big progress tomorrow.",
        "Practice makes you confident.",
        "Consistency > Intensity.",
        "You don’t have to be perfect to start."
    ]
    return random.choice(fallback)

def _star_between(start_dt: datetime, end_dt: datetime) -> dict:
    """
    Top performer name and user_id between start_dt (inclusive) and end_dt (exclusive),
    by sum(listen+speak+vocabulary). Requires Progress.updated_at to be present.
    """
    q = (
        db.session.query(
            User.full_name,
            User.user_id,
            func.coalesce(func.sum(Progress.listen + Progress.speak + Progress.vocabulary), 0).label("total")
        )
        .join(Progress, Progress.user_id == User.user_id)  # ✅ FIXED
        .filter(Progress.updated_at >= start_dt, Progress.updated_at < end_dt)
        .group_by(User.user_id)
        .order_by(func.sum(Progress.listen + Progress.speak + Progress.vocabulary).desc())
        .limit(1)
    ).first()
    if q and getattr(q, "total", 0) and q.total > 0:
        return {"name": q.full_name, "user_id": q.user_id}
    else:
        return {"name": "—", "user_id": None}

def get_star_of_day() -> dict:
    today = datetime.now(timezone.utc).date()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    return _star_between(start_dt, end_dt)

def get_star_of_week() -> dict:
    today = datetime.now(timezone.utc).date()
    # Monday as start-of-week
    start_of_week = today - timedelta(days=today.weekday())
    start_dt = datetime.combine(start_of_week, datetime.min.time())
    end_dt = start_dt + timedelta(days=7)
    return _star_between(start_dt, end_dt)

def generate_listen_test_questions(statements, day, question_type="fill_blanks_mcq"):
    """Generate 5 questions based on listen statements using OpenAI"""
    try:
        # Use all statements (not just first 10) so AI can randomly choose from all 20 statements
        statements_text = "\n".join([f"{i+1}. {stmt.get('text', '')} - {stmt.get('hindi', '')}" for i, stmt in enumerate(statements)])
        
        if question_type == "fill_blanks_mcq":
            prompt = f"""Based on these English learning statements from Day {day}, create exactly 5 simple fill-in-the-blank questions. You can randomly choose any statements from the list provided.

Statements:
{statements_text}

For each question:
1. Randomly select any statement from the list above
2. Remove 1 key word and replace with blank (______)
3. Provide 4 simple multiple choice options
4. Keep it simple and clear
5. You can use any statement from the entire list, not just the first few

Format as JSON:
{{
  "questions": [
    {{
      "question": "Good ______ sir!",
      "options": ["morning", "evening", "afternoon", "night"],
      "correct_answer": 0,
      "hindi_meaning": "सुप्रभात सर!",
      "type": "fill_blanks_mcq"
    }}
  ]
}}

Keep questions simple and easy to understand."""
        elif question_type == "fill_blanks":
            prompt = f"""Based on these English learning statements from Day {day}, create exactly 5 fill-in-the-blanks questions to test listening comprehension. Use the exact statements provided.

Statements:
{statements_text}

For each question:
1. Take a statement from the list above
2. Remove 1-2 key words and replace with blanks (______)
3. Provide the correct answer(s)
4. Add Hindi translation for context

Format as JSON:
{{
  "questions": [
    {{
      "question": "Fill in the blanks: Good ______ sir! / रिक्त स्थान भरें",
      "statement_with_blanks": "Good ______ sir!",
      "correct_answers": ["morning"],
      "hindi_meaning": "सुप्रभात सर!",
      "type": "fill_blanks"
    }}
  ]
}}

Make questions in Hinglish (mix of English and Hindi) for better understanding."""
        else:
            prompt = f"""Based on these English learning statements from Day {day}, create exactly 5 multiple choice questions to test listening comprehension. Each question should have 4 options (A, B, C, D) with only one correct answer.

Statements:
{statements_text}

Generate questions about:
1. Meaning/translation
2. Pronunciation 
3. Usage context
4. Grammar structure
5. Vocabulary understanding

Format as JSON:
{{
  "questions": [
    {{
      "question": "Question text in English and Hindi",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": 0,
      "type": "mcq"
    }}
  ]
}}

Make questions in Hinglish (mix of English and Hindi) for better understanding."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an English learning expert who creates engaging questions for Indian students."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("questions", [])
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        # Fallback questions using actual day statements
        if question_type == "fill_blanks_mcq":
            # Create questions from actual statements
            fallback_questions = []
            selected_statements = statements[:5] if len(statements) >= 5 else statements
            
            for i, stmt in enumerate(selected_statements):
                text = stmt.get('text', '')
                hindi = stmt.get('hindi', '')
                
                # Simple word replacement logic for fallback
                if 'wake up' in text.lower():
                    question = text.replace('wake up', '______')
                    options = ['wake up', 'sleep', 'eat', 'work']
                    correct = 0
                elif 'brush' in text.lower():
                    question = text.replace('brush', '______')
                    options = ['brush', 'wash', 'clean', 'wipe']
                    correct = 0
                elif 'shower' in text.lower():
                    question = text.replace('shower', '______')
                    options = ['shower', 'bath', 'wash', 'clean']
                    correct = 0
                elif 'breakfast' in text.lower():
                    question = text.replace('breakfast', '______')
                    options = ['breakfast', 'lunch', 'dinner', 'snack']
                    correct = 0
                elif 'exercise' in text.lower() or 'exercising' in text.lower():
                    question = text.replace('exercise', '______').replace('exercising', '______')
                    options = ['exercise', 'running', 'walking', 'sleeping']
                    correct = 0
                else:
                    # Generic fallback - replace first meaningful word
                    words = text.split()
                    if len(words) > 2:
                        # Find a meaningful word to replace (not I, am, is, are, the, a, an)
                        skip_words = ['i', 'am', 'is', 'are', 'the', 'a', 'an', 'to', 'and', 'or', 'but', 'my', 'in', 'on', 'at', 'with']
                        target_word = None
                        for word in words:
                            clean_word = word.lower().strip('.,!?')
                            if clean_word not in skip_words and len(clean_word) > 2:
                                target_word = word
                                break
                        
                        if target_word:
                            question = text.replace(target_word, '______', 1)
                            clean_target = target_word.strip('.,!?')
                            # Generate better distractors based on word type
                            if clean_target.lower() in ['coffee', 'tea', 'water', 'milk']:
                                options = [clean_target, 'juice', 'soda', 'beer']
                            elif clean_target.lower() in ['emails', 'messages', 'calls', 'texts']:
                                options = [clean_target, 'letters', 'notes', 'reports']
                            elif clean_target.lower() in ['work', 'job', 'office', 'business']:
                                options = [clean_target, 'home', 'school', 'market']
                            elif clean_target.lower() in ['morning', 'evening', 'afternoon', 'night']:
                                options = [clean_target, 'noon', 'midnight', 'dawn']
                            else:
                                # Generic but meaningful distractors
                                common_words = ['have', 'make', 'take', 'get', 'go', 'come', 'see', 'know', 'think', 'feel']
                                options = [clean_target] + [w for w in common_words if w != clean_target.lower()][:3]
                            correct = 0
                        else:
                            question = f"Complete: {text[:30]}... ______"
                            options = ['correctly', 'properly', 'nicely', 'well']
                            correct = 0
                    else:
                        question = f"What does this mean: {text}"
                        options = [hindi, 'अन्य अर्थ', 'गलत अर्थ', 'कोई अर्थ नहीं']
                        correct = 0
                
                # Randomize answer position
                import random
                correct_option = options[correct]
                random.shuffle(options)
                new_correct_index = options.index(correct_option)
                
                fallback_questions.append({
                    "question": question,
                    "options": options,
                    "correct_answer": new_correct_index,
                    "hindi_meaning": hindi,
                    "type": "fill_blanks_mcq"
                })
            
            return fallback_questions
        elif question_type == "fill_blanks":
            return [
                {
                    "question": "Fill in the blanks: Good ______ sir! / रिक्त स्थान भरें",
                    "statement_with_blanks": "Good ______ sir!",
                    "correct_answers": ["morning"],
                    "hindi_meaning": "सुप्रभात सर!",
                    "type": "fill_blanks"
                },
                {
                    "question": "Complete the sentence: Thank ______ very much! / वाक्य पूरा करें",
                    "statement_with_blanks": "Thank ______ very much!",
                    "correct_answers": ["you"],
                    "hindi_meaning": "आपका बहुत धन्यवाद!",
                    "type": "fill_blanks"
                },
                {
                    "question": "Fill in the blanks: How ______ you? / रिक्त स्थान भरें",
                    "statement_with_blanks": "How ______ you?",
                    "correct_answers": ["are"],
                    "hindi_meaning": "आप कैसे हैं?",
                    "type": "fill_blanks"
                },
                {
                    "question": "Complete: ______ help me please! / पूरा करें",
                    "statement_with_blanks": "______ help me please!",
                    "correct_answers": ["Please"],
                    "hindi_meaning": "कृपया मेरी मदद करें!",
                    "type": "fill_blanks"
                },
                {
                    "question": "Fill in the blanks: Nice to ______ you! / रिक्त स्थान भरें",
                    "statement_with_blanks": "Nice to ______ you!",
                    "correct_answers": ["meet"],
                    "hindi_meaning": "आपसे मिलकर खुशी हुई!",
                    "type": "fill_blanks"
                }
            ]
        else:
            return [
                {
                    "question": "What does 'Good morning' mean in Hindi?",
                    "options": ["A) शुभ संध्या", "B) शुभ रात्रि", "C) सुप्रभात", "D) नमस्ते"],
                    "correct_answer": 2,
                    "type": "mcq"
                },
                {
                    "question": "Which is the correct pronunciation of 'Thank you'?",
                    "options": ["A) थैंक यू", "B) धन्यवाद", "C) थैंक्स", "D) All of the above"],
                    "correct_answer": 0,
                    "type": "mcq"
                },
                {
                    "question": "'How are you?' ka jawab kya hoga?",
                    "options": ["A) I am fine", "B) Good morning", "C) Thank you", "D) Goodbye"],
                    "correct_answer": 0,
                    "type": "mcq"
                },
                {
                    "question": "'Please' word ka use kab karte hain?",
                    "options": ["A) Greeting ke liye", "B) Request karne ke liye", "C) Goodbye kehne ke liye", "D) Sorry kehne ke liye"],
                    "correct_answer": 1,
                    "type": "mcq"
                },
                {
                    "question": "English mein 'Namaste' ko kya kehte hain?",
                    "options": ["A) Hello", "B) Goodbye", "C) Thank you", "D) Sorry"],
                    "correct_answer": 0,
                    "type": "mcq"
                }
            ]

@app.context_processor
def inject_globals():
    # Single source of truth for template globals
    star_day_data = get_star_of_day()
    star_week_data = get_star_of_week()
    return dict(
        thought_of_day=get_thought_of_day(),
        star_of_day=star_day_data["name"],
        star_of_week=star_week_data["name"],
        star_of_day_user_id=star_day_data["user_id"],
        star_of_week_user_id=star_week_data["user_id"]
    )

# ----------------------
import time

@app.route("/tts")
def tts_route():
    text = request.args.get("text", "").strip()
    print(f"🔊 TTS Request received: '{text[:50]}{'...' if len(text) > 50 else ''}'")
    
    if not text:
        print("❌ TTS Error: No text provided")
        return "No text", 400

    # Optional params from frontend
    gender = request.args.get("voice", "Male")
    lang = request.args.get("lang", None)
    accent = request.args.get("accent", None)
    voice_name = request.args.get("voice_name", None)
    mode = request.args.get("mode", None)  # online/offline/auto
    
    print(f"🎵 TTS Parameters: gender={gender}, lang={lang}, accent={accent}, voice_name={voice_name}, mode={mode}")

    try:
        file_path = generate_tts(text, gender=gender, lang=lang, accent=accent, voice_name=voice_name, mode=mode)
        
        if not file_path or not os.path.exists(file_path):
            print(f"❌ TTS Error: Failed to generate audio file. Path: {file_path}")
            return jsonify({
                "error": "TTS generation failed",
                "message": "Audio file could not be generated. Please try again or switch to offline mode.",
                "suggested_action": "Try changing voice mode to 'offline' in settings"
            }), 500
            
        print(f"✅ TTS Success: Audio file generated at {file_path}")
        
        # optional: cleanup old files in background
        from services.tts import cleanup_tts
        cleanup_tts(older_than_seconds=3600)  # 1 hour

        # return appropriate mimetype based on file extension
        if file_path.endswith('.wav'):
            return send_file(file_path, mimetype="audio/wav")
        else:
            return send_file(file_path, mimetype="audio/mpeg")
        
    except RuntimeError as e:
        error_msg = str(e)
        print(f"❌ TTS RuntimeError: {error_msg}")
        
        # Provide user-friendly error messages
        if "No TTS methods available" in error_msg:
            return jsonify({
                "error": "No voice available",
                "message": "कोई आवाज़ उपलब्ध नहीं है। कृपया अपना इंटरनेट कनेक्शन जांचें।",
                "suggested_action": "Check internet connection or try offline mode"
            }), 503
        elif "Online TTS requested but not available" in error_msg:
            return jsonify({
                "error": "Online voice unavailable",
                "message": "ऑनलाइन आवाज़ उपलब्ध नहीं है। ऑफलाइन मोड का उपयोग करें।",
                "suggested_action": "Switch to offline mode in settings"
            }), 503
        elif "Offline TTS requested but not available" in error_msg:
            return jsonify({
                "error": "Offline voice unavailable", 
                "message": "ऑफलाइन आवाज़ उपलब्ध नहीं है। ऑनलाइन मोड का उपयोग करें।",
                "suggested_action": "Switch to online mode in settings"
            }), 503
        else:
            return jsonify({
                "error": "Voice generation failed",
                "message": "आवाज़ बनाने में समस्या हुई। कृपया दोबारा कोशिश करें।",
                "suggested_action": "Try again or change voice settings"
            }), 500
            
    except Exception as e:
        print(f"❌ TTS Exception: {str(e)}")
        import traceback
        print(f"❌ TTS Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "Unexpected error",
            "message": "अप्रत्याशित त्रुटि हुई। कृपया दोबारा कोशिश करें।",
            "suggested_action": "Try again or contact support"
        }), 500

# ----------------------
# Routes
# ----------------------
@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("intro"))

@app.route("/intro")
def intro():
    return render_template("intro.html")

@app.route("/questionnaire")
def questionnaire():
    return render_template("questionnaire.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            full_name = (request.form.get("full_name") or "").strip()
            user_id_form = (request.form.get("user_id") or "").strip()
            username = (request.form.get("username") or user_id_form or "").strip()
            password = (request.form.get("password") or "").strip()
            mobile = (request.form.get("mobile") or "").strip()
            dob = (request.form.get("dob") or "").strip()
            email = (request.form.get("email") or "").strip()
            state = (request.form.get("state") or "").strip()
            city = (request.form.get("city") or "").strip()
            gender = (request.form.get("gender") or "Male").strip()
            voice = (request.form.get("voice") or gender or "Male").strip()

            if not username or not password:
                return render_template("signup.html", error="Username/User ID and Password are required.")

            # Uniqueness checks
            if User.query.filter(or_(User.username == username, User.user_id == user_id_form)).first():
                return render_template("signup.html", error="User already exists (username or user id).")
            if email and User.query.filter_by(email=email).first():
                return render_template("signup.html", error="Email already registered.")

            u = User(
                username=username,
                user_id=user_id_form or None,
                full_name=full_name or username,
                password_hash=generate_password_hash(password),
                mobile=mobile or None,
                email=email or None,
                dob=dob or None,
                state=state or None,
                city=city or None,
                gender=gender,
                voice=voice
            )
            db.session.add(u)
            db.session.commit()
            login_user(u)
            return redirect(url_for("dashboard"))
        except Exception as e:
            db.session.rollback()
            print(f"Signup error: {str(e)}")
            return render_template("signup.html", error=f"Registration failed: {str(e)}")

    # Add guide message for signup page
    guide = BoonyGuide()
    guide_message = guide.get_welcome_message("signup")
    return render_template("signup.html", guide_message=guide_message)

@app.route("/login", methods=["GET", "POST"])
def login():
    print(f"Login route accessed with method: {request.method}")
    if request.method == "POST":
        # Debug: Check request details
        print(f"Request content type: {request.content_type}")
        print(f"Request is_json: {request.is_json}")
        print(f"Request data: {request.data}")
        
        # Check if it's a JSON request (from mobile app) or has JSON content type
        if request.is_json or request.content_type == 'application/json':
            print("Processing JSON request")
            data = request.get_json()
            print(f"JSON data: {data}")
            user_field = (data.get("username") or data.get("user_id") or data.get("user") or "").strip()
            password = (data.get("password") or "").strip()

            if not user_field or not password:
                return jsonify({"success": False, "message": "Username and password are required"}), 400

            u = User.query.filter(
                or_(User.username == user_field, User.user_id == user_field, User.email == user_field)
            ).first()

            if not u or not check_password_hash(u.password_hash, password):
                return jsonify({"success": False, "message": "Invalid credentials"}), 401

            # For mobile app, return JSON with JWT token
            token_payload = {
                'user_id': str(u.user_id),
                'username': u.username,
                'exp': datetime.utcnow() + timedelta(days=30)  # Token expires in 30 days
            }
            token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
            
            return jsonify({
                "success": True,
                "message": "Login successful",
                "token": token,
                "user_id": str(u.user_id),
                "username": u.username,
                "full_name": u.full_name
            })
        
        # Handle form-based login (web)
        user_field = (request.form.get("username") or request.form.get("user_id") or request.form.get("user") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not user_field or not password:
            return render_template("login.html", error="Enter username/user id and password.")

        u = User.query.filter(
            or_(User.username == user_field, User.user_id == user_field, User.email == user_field)
        ).first()

        if not u or not check_password_hash(u.password_hash, password):
            return render_template("login.html", error="Invalid credentials.")

        login_user(u)
        return redirect(url_for("dashboard"))

    # Add guide message for login page
    guide = BoonyGuide()
    guide_message = guide.get_welcome_message("login")
    return render_template("login.html", guide_message=guide_message)

# Add mobile login endpoint
@app.route("/api/login", methods=["POST"])
def mobile_login():
    print("Mobile login endpoint accessed")
    data = request.get_json()
    print(f"Mobile login data: {data}")
    
    if not data:
        return jsonify({"success": False, "message": "No JSON data provided"}), 400
    
    user_field = (data.get("username") or data.get("user_id") or data.get("user") or "").strip()
    password = (data.get("password") or "").strip()

    if not user_field or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    u = User.query.filter(
        or_(User.username == user_field, User.user_id == user_field, User.email == user_field)
    ).first()

    if not u or not check_password_hash(u.password_hash, password):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    # Generate JWT token
    token_payload = {
        'user_id': str(u.user_id),
        'username': u.username,
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": {
            "user_id": str(u.user_id),
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "mobile": u.mobile,
            "gender": u.gender,
            "voice": u.voice
        }
    })

@app.route("/api/signup", methods=["POST"])
def mobile_signup():
    print("Mobile signup endpoint accessed")
    data = request.get_json()
    print(f"Mobile signup data: {data}")
    
    if not data:
        return jsonify({"success": False, "message": "No JSON data provided"}), 400
    
    try:
        # Extract data from request
        full_name = (data.get("full_name") or "").strip()
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        password = (data.get("password") or "").strip()
        mobile = (data.get("mobile") or "").strip()
        gender = (data.get("gender") or "Male").strip()
        voice = (data.get("voice") or gender or "Male").strip()
        dob = (data.get("dob") or "").strip()
        state = (data.get("state") or "").strip()
        city = (data.get("city") or "").strip()

        # Validation
        if not username or not password or not email:
            return jsonify({"success": False, "message": "Username, email and password are required"}), 400

        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters long"}), 400

        # Check if user already exists
        existing_user = User.query.filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                return jsonify({"success": False, "message": "Username already exists"}), 409
            if existing_user.email == email:
                return jsonify({"success": False, "message": "Email already registered"}), 409

        # Create new user
        new_user = User(
            username=username,
            full_name=full_name or username,
            password_hash=generate_password_hash(password),
            email=email,
            mobile=mobile or None,
            gender=gender,
            voice=voice,
            dob=dob or None,
            state=state or None,
            city=city or None
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Generate JWT token for the new user
        token_payload = {
            'user_id': str(new_user.user_id),
            'username': new_user.username,
            'exp': datetime.utcnow() + timedelta(days=30)
        }
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "success": True,
            "message": "Signup successful",
            "token": token,
            "user": {
                "user_id": str(new_user.user_id),
                "username": new_user.username,
                "full_name": new_user.full_name,
                "email": new_user.email,
                "mobile": new_user.mobile,
                "gender": new_user.gender,
                "voice": new_user.voice
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Signup error: {str(e)}")
        return jsonify({"success": False, "message": f"Registration failed: {str(e)}"}), 500

@app.route("/api/questionnaire", methods=["POST"])
def save_questionnaire():
    """Save user questionnaire responses in session for later use during signup"""
    print("Questionnaire endpoint accessed")
    data = request.get_json()
    print(f"Questionnaire data: {data}")
    
    if not data:
        return jsonify({"success": False, "message": "No JSON data provided"}), 400
    
    try:
        # Store questionnaire data in session for later use during signup
        session['questionnaire_data'] = {
            'english_level': data.get("english_level"),
            'learning_goal': data.get("learning_goal"),
            'focus_area': data.get("focus_area"),
            'time_availability': data.get("time_availability"),
            'learning_style': data.get("learning_style"),
            'avatar_preference': data.get("avatar_preference", "female")
        }
        
        return jsonify({
            "success": True, 
            "message": "Questionnaire data saved successfully"
        }), 200
        
    except Exception as e:
        print(f"Questionnaire error: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to save questionnaire: {str(e)}"}), 500

# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# API endpoints for mobile app
@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.get_json()
    mobile = data.get("mobile")
    
    if not mobile:
        return jsonify({"ok": False, "error": "Mobile number is required"}), 400
    
    user = User.query.filter_by(mobile=mobile).first()
    if not user:
        return jsonify({"ok": False, "error": "Mobile number not found"}), 404

    # Generate OTP
    otp = random.randint(1000, 9999)
    
    # Store OTP in session or cache (for mobile app, we'll use a simple in-memory store)
    # In production, use Redis or database
    if not hasattr(app, 'mobile_otps'):
        app.mobile_otps = {}
    
    app.mobile_otps[mobile] = {
        'otp': otp,
        'user_id': str(user.user_id),
        'timestamp': datetime.now(timezone.utc)
    }

    # Send OTP via SMS
    resp = send_otp_via_sms(user.mobile, otp)
    print("SMS API Response:", resp)

    # Masked number for response
    masked_mobile = "xxxxxx" + user.mobile[-4:]

    return jsonify({
        "ok": True,
        "message": "OTP sent successfully",
        "masked_mobile": masked_mobile
    })

@app.route("/api/verify-otp", methods=["POST"])
def api_verify_otp():
    data = request.get_json()
    mobile = data.get("mobile")
    entered_otp = data.get("otp")
    
    if not mobile or not entered_otp:
        return jsonify({"ok": False, "error": "Mobile and OTP are required"}), 400
    
    if not hasattr(app, 'mobile_otps') or mobile not in app.mobile_otps:
        return jsonify({"ok": False, "error": "No OTP found for this mobile"}), 404
    
    otp_data = app.mobile_otps[mobile]
    
    # Check OTP expiry (10 minutes)
    if datetime.now(timezone.utc) - otp_data['timestamp'] > timedelta(minutes=10):
        del app.mobile_otps[mobile]
        return jsonify({"ok": False, "error": "OTP expired. Please try again."}), 400
    
    if str(entered_otp) != str(otp_data['otp']):
        return jsonify({"ok": False, "error": "Invalid OTP. Please try again."}), 400
    
    # Mark as verified
    app.mobile_otps[mobile]['verified'] = True
    
    return jsonify({
        "ok": True,
        "message": "OTP verified successfully"
    })

@app.route("/api/reset-password", methods=["POST"])
def api_reset_password():
    data = request.get_json()
    mobile = data.get("mobile")
    new_password = data.get("new_password")
    
    if not mobile or not new_password:
        return jsonify({"ok": False, "error": "Mobile and new password are required"}), 400
    
    if len(new_password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters"}), 400
    
    if not hasattr(app, 'mobile_otps') or mobile not in app.mobile_otps:
        return jsonify({"ok": False, "error": "No OTP session found"}), 404
    
    otp_data = app.mobile_otps[mobile]
    
    if not otp_data.get('verified'):
        return jsonify({"ok": False, "error": "OTP not verified"}), 400
    
    user = User.query.get(otp_data['user_id'])
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 404
    
    # Update password
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    # Clean up OTP data
    del app.mobile_otps[mobile]
    
    return jsonify({
        "ok": True,
        "message": "Password reset successful"
    })

# =========================================================
# STEP 1: Full Name + Mobile + Gender
# =========================================================
@app.route("/signup/step1", methods=["GET", "POST"])
def signup_step1():
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        mobile = (request.form.get("mobile") or "").strip()
        gender = (request.form.get("gender") or "Male").strip()

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not mobile.isdigit() or len(mobile) != 10:
            errors.append("Mobile number must be 10 digits.")

        if errors:
            guide_text = "Please correct the errors before proceeding."
            voice_file = generate_tts(guide_text)
            return render_template("signup_step1.html", errors=errors, voice_file=voice_file)

        # save in session
        session["signup_full_name"] = full_name
        session["signup_mobile"] = mobile
        session["signup_gender"] = gender
        session["signup_voice"] = gender  # default voice same as gender

        return redirect(url_for("signup_step2"))

    guide_text = "Welcome! Please enter your full name, mobile number, and select your gender."
    voice_file = generate_tts(guide_text)
    return render_template("signup_step1.html", voice_file=voice_file)


# =========================================================
# STEP 2: Optional Profile Info (old Step3)
# =========================================================
@app.route("/signup/step2", methods=["GET", "POST"])
def signup_step2():
    if request.method == "POST":
        if "skip" in request.form:
            return redirect(url_for("signup_step3"))

        session["signup_email"] = request.form.get("email") or None
        session["signup_dob"] = request.form.get("dob") or None
        session["signup_state"] = request.form.get("state") or None
        session["signup_city"] = request.form.get("city") or None

        return redirect(url_for("signup_step3"))

    guide_text = "This step is optional. You may enter extra details like email, date of birth, state, and city. Or just skip."
    voice_file = generate_tts(guide_text)
    return render_template("signup_step2.html", voice_file=voice_file)


# =========================================================
# STEP 3: Avatar Selection (old Step4)
# =========================================================
@app.route("/signup/step3", methods=["GET", "POST"])
def signup_step3():
    if request.method == "POST":
        selected_avatar = request.form.get("selected_avatar", "male").strip()
        
        # Save avatar selection in session
        session["signup_voice"] = selected_avatar
        session["signup_avatar"] = selected_avatar
        
        return redirect(url_for("signup_step4"))

    guide_text = "Choose your preferred avatar and voice. Click on any avatar to hear a sample."
    voice_file = generate_tts(guide_text)

    return render_template("signup_step3.html", voice_file=voice_file)


# =========================================================
# STEP 4: Welcome (old Step6)
# =========================================================
@app.route("/signup/step4")
def signup_step4():
    # Check if we have the required session data from previous steps
    if not session.get("signup_full_name"):
        return redirect(url_for("signup_step1"))
    
    # Create a temporary user object for display
    temp_user = type('User', (), {
        'full_name': session.get("signup_full_name"),
        'mobile': session.get("signup_mobile"),
        'gender': session.get("signup_gender")
    })()
    
    # Generate a temporary password for display
    temp_password = "temp_" + str(random.randint(1000, 9999))

    guide_text = f"Welcome {temp_user.full_name}! Your profile has been created successfully. Your temporary password is: {temp_password}"
    voice_file = generate_tts(guide_text)

    return render_template("signup_step4.html", user=temp_user, password=temp_password, guide_text=guide_text, voice_file=voice_file)




# Original analyze_speech endpoint removed - now using public_api blueprint

# =========================================================
# STEP 5: Set Login ID + Password (old Step5)
# =========================================================
@app.route("/signup/step5", methods=["GET", "POST"])
def signup_step5():
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "").strip()

        errors = []
        if not login_id or len(login_id) < 4:
            errors.append("Login ID must be at least 4 characters long.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        existing_user = User.query.filter(User.username == login_id).first()
        if existing_user:
            errors.append("This Login ID is already taken.")

        if not errors:
            try:
                u = User(
                    username=login_id,
                    # user_id will be auto-generated as UUID by default
                    full_name=session.get("signup_full_name"),
                    password_hash=generate_password_hash(password),
                    mobile=session.get("signup_mobile"),
                    email=session.get("signup_email"),
                    dob=session.get("signup_dob"),
                    state=session.get("signup_state"),
                    city=session.get("signup_city"),
                    gender=session.get("signup_gender"),
                    voice=session.get("signup_voice"),
                )
                db.session.add(u)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"User creation error: {str(e)}")
                errors.append(f"Registration failed: {str(e)}")
                guide_text = "Please fix the errors and try again."
                voice_file = generate_tts(guide_text)
                return render_template("signup_step5.html", errors=errors, voice_file=voice_file)
            
            # Login the user immediately after creation
            login_user(u)

            session["created_user_id"] = str(u.user_id)
            session["signup_password"] = password
            
            # Clear signup session data
            for key in list(session.keys()):
                if key.startswith("signup_"):
                    session.pop(key, None)
            
            return render_template("signup_success.html", user=u)  # single success page

        guide_text = "Please fix the errors and try again."
        voice_file = generate_tts(guide_text)
        return render_template("signup_step5.html", errors=errors, voice_file=voice_file)

    guide_text = "Now choose your login ID and set a strong password."
    voice_file = generate_tts(guide_text)
    return render_template("signup_step5.html", voice_file=voice_file)



@app.route("/speak/<day>")
@login_required
def speak_page(day):
    try:
        print(f"\n=== SPEAK PAGE DEBUG START ===")
        print(f"DEBUG: Accessing speak page for day: {day}")
        print(f"DEBUG: User: {current_user.user_id}")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request URL: {request.url}")
        print(f"DEBUG: Syllabus file: {app.config['DATA_SYLLABUS']}")
        
        raw_statements = load_day_statements(app.config["DATA_SYLLABUS"], day) or []
        print(f"DEBUG: Loaded {len(raw_statements)} raw statements for day {day}")
        
        # English + Hindi sentence dicts
        sentences = [
            {"text": stmt.get("text", ""), "hindi": stmt.get("hindi", "")}
            for stmt in raw_statements if "text" in stmt
        ]
        print(f"DEBUG: Processed {len(sentences)} sentences")

        # Get user progress safely
        progress = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
        speak_credits = progress.speak if progress else 0
        print(f"DEBUG: User credits: {speak_credits}")
        print(f"DEBUG: Rendering template with {len(sentences)} sentences")
        print(f"=== SPEAK PAGE DEBUG END ===\n")
        
        return render_template(
            "speak.html",
            day=day,
            statements=sentences,   # 👈 Now a list of dicts: {"text": ..., "hindi": ...}
            gender=current_user.gender,
            voice=current_user.voice,
            lang=getattr(current_user, "language", "english"),  # if you want to pass language
            credits={
                "speak": speak_credits
            }
        )
    except Exception as e:
        print(f"\n=== SPEAK PAGE ERROR ===")
        print(f"ERROR in speak_page for day {day}: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"=== SPEAK PAGE ERROR END ===\n")
        # Return error page or redirect to dashboard
        flash(f"Error loading speak page for {day}: {str(e)}", "error")
        return redirect(url_for('dashboard'))
# ------------------ Listen ------------------
@app.route("/listen/<day>")
@login_required
def listen_page(day):
    # ✅ Load statements for this day
    raw_statements = load_day_statements(app.config["DATA_SYLLABUS"], day) or []

    # Ensure each statement has required keys
    statements = []
    for stmt in raw_statements:
        statements.append({
            "text": stmt.get("text", ""),
            "pronunciation": stmt.get("pronunciation", ""),
            "hindi": stmt.get("hindi", ""),
            "videolink": stmt.get("videolink", "")
        })

    # Fix relative videolinks
    for s in statements:
        v = s["videolink"]
        if v:
            # Agar sirf filename hai, static folder me point karo
            if not v.startswith("http") and not v.startswith("static/"):
                s["videolink"] = f"static/gifs/{v}"

    # ✅ Fetch user's progress
    prog = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
    initial_credits = prog.listen if prog else 0
    is_listen_completed = bool(prog.listen) if prog else False

    return render_template(
        "listen.html",
        day=day,
        topic=f"Day {day}",
        statements=statements,           # list of dicts
        initial_credits=initial_credits,
        is_listen_completed=is_listen_completed
    )

# ------------------ Listen Test ------------------
@app.route("/listen-test/<day>")
@login_required
def listen_test_page(day):
    # Check if user has completed listen stage
    prog = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
    if not prog or not prog.listen:
        flash("Please complete the listening practice first!")
        return redirect(url_for("listen_page", day=day))
    
    # Load all statements for this day
    all_statements = load_day_statements(app.config["DATA_SYLLABUS"], day) or []
    
    if not all_statements:
        flash("इस day के लिए कोई statements नहीं मिले!")
        return redirect(url_for("listen_page", day=day))
    
    # Use all statements from the day for test (randomly choose any 5 from all 20 statements)
    # Generate 5 fill-in-the-blanks questions using AI from all day statements
    questions = generate_listen_test_questions(all_statements, day, question_type="fill_blanks_mcq")
    
    return render_template(
        "listen_test.html",
        day=day,
        questions=questions
    )

@app.route("/api/submit-listen-test", methods=["POST"])
@login_required
def submit_listen_test():
    data = request.get_json(force=True)
    day = data.get("day")
    answers = data.get("answers", [])
    questions_data = data.get("questions", [])  # Get original questions from frontend
    
    # Get user's progress
    prog = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
    if not prog:
        return jsonify({"error": "No progress found"}), 400
    
    # Use original questions if provided, otherwise regenerate
    if questions_data:
        questions = questions_data
    else:
        # Load all statements for this day
        all_statements = load_day_statements(app.config["DATA_SYLLABUS"], day) or []
        # Regenerate questions to get correct answers from all day statements
        questions = generate_listen_test_questions(all_statements, day, question_type="fill_blanks_mcq")
    
    # Calculate score based on question type
    score = 0
    total_questions = len(questions)
    
    for i, question in enumerate(questions):
        if i < len(answers):
            user_answer = answers[i]
            
            if question.get("type") == "fill_blanks_mcq":
                # For fill-in-the-blank MCQ, check if user selected correct option
                correct_answer = question.get("correct_answer", 0)
                if user_answer == correct_answer:
                    score += 1
            elif question.get("type") == "fill_blanks":
                # For fill-in-the-blanks, check if user answer matches any correct answer (case-insensitive)
                correct_answers = question.get("correct_answers", [])
                user_answer_clean = str(user_answer).strip().lower()
                
                # Check if user answer matches any of the correct answers
                is_correct = any(user_answer_clean == correct.strip().lower() for correct in correct_answers)
                if is_correct:
                    score += 1
            else:
                # For MCQ questions (fallback)
                correct_answer = question.get("correct_answer", 0)
                if user_answer == correct_answer:
                    score += 1
    
    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    
    # Update progress if score >= 80%
    if percentage >= 80:
        prog = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
        if prog:
            prog.listen_test_passed = True
            prog.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
    return jsonify({
        "ok": True,
        "score": score,
        "total": total_questions,
        "percentage": percentage,
        "passed": percentage >= 80
    })




# ------------------ Revision ------------------
# Revision routes are now handled by enhanced revision in revios.py
# ----------------------
# APIs
# ----------------------
@app.route("/api/upload-audio", methods=["POST"])
@login_required
def api_upload_audio():
    f = request.files.get("audio")
    if not f:
        return jsonify({"ok": False, "error": "No file"}), 400

    out_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{datetime.now(timezone.utc).timestamp()}_{f.filename}")
    f.save(out_path)
    try:
        text = transcribe_audio(out_path)
        return jsonify({"ok": True, "text": text})
    finally:
        try:
            os.remove(out_path)
        except Exception:
            pass


@app.route("/api/progress", methods=["POST"])
@login_required
def api_progress():
    data = request.get_json(force=True)
    day = data.get("day", "Day-1")
    activity = (data.get("activity", "Speak") or "").lower()
    try:
        value = int(data.get("value", 0))
    except (ValueError, TypeError):
        value = 0
    last_stage = data.get("last_stage", "")
    last_statement = int(data.get("last_statement", 0))

    prog = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
    if not prog:
        prog = Progress(user_id=str(current_user.user_id), day=day)
        db.session.add(prog)

    if activity == "listen":
        prog.listen = (prog.listen or 0) + value
    elif activity == "speak":
        prog.speak = (prog.speak or 0) + value
    elif activity == "vocabulary":
        prog.vocabulary = (prog.vocabulary or 0) + value

    if last_stage:
        prog.last_stage = last_stage
    prog.last_statement = last_statement
    prog.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    
    # Generate congratulatory message for progress
    guide = BoonyGuide()
    user_context = {
        'name': current_user.full_name or current_user.username,
        'activity': activity,
        'day': day,
        'value': value
    }
    
    congratulations = None
    if value > 0:  # Only congratulate on positive progress
        if activity == "listen" and (prog.listen or 0) >= 10:
            congratulations = guide.get_congratulatory_message("listen_complete", user_context)
        elif activity == "speak" and (prog.speak or 0) >= 10:
            congratulations = guide.get_congratulatory_message("speak_complete", user_context)
        elif activity == "vocabulary" and (prog.vocabulary or 0) >= 10:
            congratulations = guide.get_congratulatory_message("vocab_complete", user_context)
        else:
            congratulations = guide.get_congratulatory_message("progress_made", user_context)
    
    return jsonify({
        "ok": True,
        "congratulations": congratulations
    })

@app.route("/api/update-credit", methods=["POST"])
@login_required
def update_credit():
    data = request.get_json(force=True)
    day = data.get("day", "Day-1")
    value = int(data.get("value", 1))
    statement_index = int(data.get("statement_index", 0))

    prog = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
    if not prog:
        prog = Progress(user_id=str(current_user.user_id), day=day)
        db.session.add(prog)

    prog.listen = (prog.listen or 0) + value
    prog.last_stage = "Listen"
    prog.last_statement = statement_index
    prog.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify({"ok": True, "listen": prog.listen})

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        mobile = request.form.get("mobile")
        user = User.query.filter_by(mobile=mobile).first()
        if not user:
            return render_template("forgot_password.html", error="Mobile not found")

        # Generate OTP
        otp = random.randint(1000, 9999)
        session["reset_user_id"] = str(user.user_id)
        session["reset_otp"] = otp

        # Send OTP via SMS
        resp = send_otp_via_sms(user.mobile, otp)
        print("SMS API Response:", resp)  # Debug ke liye

        # Masked number show
        masked_mobile = "xxxxxx" + user.mobile[-4:]

        return render_template(
            "forgot_password.html",
            step="verify",
            masked_mobile=masked_mobile
        )

    # Add guide message for forgot password page
    guide = BoonyGuide()
    guide_message = guide.get_guidance_message("forgot_password")
    return render_template("forgot_password.html", guide_message=guide_message)

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    # must have initiated flow
    if not session.get("reset_user_id") or not session.get("reset_otp"):
        return redirect(url_for("forgot_password"))

    entered = (request.form.get("otp") or "").strip()
    real = str(session.get("reset_otp"))
    sent_at = session.get("reset_otp_time")

    # Optional expiry: 10 minutes
    try:
        if sent_at:
            sent_dt = datetime.fromisoformat(sent_at)
            if datetime.now(timezone.utc) - sent_dt > timedelta(minutes=10):
                session.pop("reset_otp", None)
                session.pop("reset_otp_time", None)
                return render_template("forgot_password.html", step="identify", error="OTP expired. Please try again.")
    except Exception:
        pass

    if not entered or entered != real:
        user = User.query.get(session["reset_user_id"])
        masked = "******" + (user.mobile[-4:] if user else "????")
        return render_template("forgot_password.html", step="verify", masked_mobile=masked, error="Invalid OTP. Please try again.")

    # Mark verified and go to reset
    session["otp_verified"] = True
    return redirect(url_for("reset_password"))

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    # guard
    if not session.get("reset_user_id") or not session.get("otp_verified"):
        return redirect(url_for("forgot_password"))

    if request.method == "GET":
        return render_template("forgot_password.html", step="reset")

    # POST: set new password
    new_pwd = (request.form.get("new_password") or "").strip()
    confirm = (request.form.get("confirm_password") or "").strip()

    if not new_pwd or len(new_pwd) < 6:
        return render_template("forgot_password.html", step="reset", error="Password must be at least 6 characters.")
    if new_pwd != confirm:
        return render_template("forgot_password.html", step="reset", error="Passwords do not match.")

    u = User.query.get(session["reset_user_id"])
    if not u:
        return redirect(url_for("forgot_password"))

    u.password_hash = generate_password_hash(new_pwd)
    db.session.commit()

    # clean session
    for k in ["reset_user_id", "reset_otp", "reset_otp_time", "otp_verified"]:
        session.pop(k, None)

    # go to login
    flash("Password reset successful. Please log in.", "success")
    return redirect(url_for("login"))

from twilio.rest import Client
@app.route("/api/update_progress", methods=["POST"])
@login_required
def api_update_progress():
    data = request.get_json()
    day = data.get("day")
    activity = data.get("activity")

    prog = Progress.query.filter_by(user_id=current_user.user_id, day=day).first()
    if not prog:
        prog = Progress(user_id=current_user.user_id, day=day)
        db.session.add(prog)

    if activity == "listen":
        prog.listen = (prog.listen or 0) + 1   # ✅ increment
    elif activity == "speak":
        prog.speak = (prog.speak or 0) + 1
    elif activity == "vocabulary":
        prog.vocabulary = (prog.vocabulary or 0) + 1

    db.session.commit()
    return jsonify({"status": "ok"})


def send_otp_via_sms(mobile, otp):
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "variables_values": otp,
        "route": "otp",
        "numbers": str(mobile)
    }

    headers = {
        "authorization": os.getenv("FAST2SMS_API_KEY", ""),   # 👈 read from env
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache"
    }
    response = requests.post(url, data=payload, headers=headers)
    return response.json()
@app.route("/signup/ai_voice")
def ai_voice():
    step = request.args.get("step", "step1")
    # Optional: user_context json from frontend
    file_path = generate_tts(generate_signup_guide(step))
    return send_file(file_path, mimetype="audio/mp3")
import pandas as pd
import os
from sqlalchemy import cast, Integer, func
@app.route("/dashboard")
@login_required
def dashboard():
    try:
        user_id = str(current_user.user_id)

        # --- Get day from URL ---
        practice_day = request.args.get("practice_day") or request.args.get("day")

        # --- Safe day parser ---
        import re
        def parse_day(day_value):
            try:
                day_str = str(day_value).strip()
                match = re.search(r'\d+', day_str)
                return int(match.group()) if match else 1
            except:
                return 1

        # --- Determine current day and progress object ---
        if practice_day:
            day = practice_day
            current_day_num = parse_day(day)
            progress_obj = Progress.query.filter_by(user_id=user_id, day=day).first()
        else:
            progress_obj = (
                Progress.query.filter_by(user_id=user_id)
                .order_by(Progress.day.desc())
                .first()
            )
            if progress_obj:
                day = progress_obj.day
                current_day_num = parse_day(day)
            else:
                day = "Day-1"
                current_day_num = 1

        # --- Default credits ---
        credits = {
            "listen": 0,
            "speak": 0,
            "vocabulary": 0,
            "revision": 0,
            "karaoke": 0,
            "topic_speaker": 0,
            "vocabulary_forest": 0,  # NEW
        }

        # --- Update credits and progress flags ---
        if progress_obj:
            credits.update({
                "listen": progress_obj.listen or 0,
                "speak": progress_obj.speak or 0,
                "vocabulary": progress_obj.vocabulary or 0,
                "revision": progress_obj.revision or 0,
                "karaoke": progress_obj.karaoke or 0,
                "topic_speaker": progress_obj.topic_speaker or 0,
                "vocabulary_forest": getattr(progress_obj, "vocabulary_forest", 0),  # NEW
            })
            listen_done = bool(progress_obj.listen)
            speak_done = bool(progress_obj.speak)
            revision_done = bool(progress_obj.revision)
            vocabulary_done = bool(progress_obj.vocabulary)
            vocab_forest_score = getattr(progress_obj, "vocabulary_forest", 0)
        else:
            listen_done = speak_done = revision_done = vocabulary_done = False
            vocab_forest_score = 0

        # --- Activity unlock ---
        listen_active = True
        speak_active = listen_done
        revision_active = speak_done
        vocabulary_active = (current_day_num >= 7) and speak_done

        # --- Fun practice ---
        fun_practice_activities = {
            "Karaoke": credits.get("karaoke", 0),
            "Topic Speaker": credits.get("topic_speaker", 0),
            "Antakshari": 0,
            "Image Puzzle": 0,
            "Vocabulary Forest": vocab_forest_score,  # NEW
            "Revision": credits.get("revision", 0),
        }

        can_progress_to_next_day = revision_done

        # --- Fetch poems safely using Python filter ---
        all_poems = Poem.query.order_by(Poem.poem_order).all()
        def extract_day_number(day_str):
            match = re.search(r'\d+', str(day_str))
            return int(match.group()) if match else 1

        day_poems = [p for p in all_poems if extract_day_number(p.day) == current_day_num]

        # --- Guide messages ---
        guide = BoonyGuide()
        user_context = {
            "name": getattr(current_user, "full_name", None) or getattr(current_user, "username", "Learner"),
            "day": day,
            "listen_done": listen_done,
            "speak_done": speak_done,
            "revision_done": revision_done,
            "vocabulary_done": vocabulary_done,
            "is_practice_mode": bool(practice_day),
        }
        welcome_message = guide.get_welcome_message("dashboard", user_context)
        daily_tip = guide.get_daily_tip()
        encouragement = guide.get_encouragement_message(user_context)
        guide_messages = {"Welcome": welcome_message, "Tip": daily_tip, "Encouragement": encouragement}

        # --- Star info ---
        star_of_day = get_star_of_day() or {}
        star_of_week = get_star_of_week() or {}

        return render_template(
            "dashboard.html",
            current_user=current_user,
            credits=credits,
            gender=getattr(current_user, "gender", ""),
            voice=getattr(current_user, "voice", ""),
            day=day,
            current_day_num=current_day_num,
            listen_active=listen_active,
            speak_active=speak_active,
            revision_active=revision_active,
            vocabulary_active=vocabulary_active,
            fun_practice_activities=fun_practice_activities,
            day_poems=day_poems,
            is_practice_mode=bool(practice_day),
            guide_messages=guide_messages,
            daily_tip=daily_tip,
            encouragement=encouragement,
            can_progress_to_next_day=can_progress_to_next_day,
            star_of_day_user_id=star_of_day.get("user_id"),
            star_of_week_user_id=star_of_week.get("user_id"),
            thought_of_day=get_thought_of_day(),
            actions=[],
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Dashboard error: {str(e)}", 500
@app.route("/vocabulary_forest")
@login_required
def vocabulary_forest():
    return render_template("vocabulary_forest.html")

@app.route("/api/vocabulary/random", methods=["GET"])
@login_required
def get_random_vocabulary():
    """Get a random unused vocabulary word, optionally filtered by category"""
    try:
        word_type = request.args.get('word_type')
        
        # Get a random unused word, optionally filtered by category
        if word_type:
            unused_word = VocabularyWord.query.filter_by(category=word_type, is_used=False).order_by(func.random()).first()
        else:
            unused_word = VocabularyWord.get_random_unused()
            
        if unused_word:
            # Get Hindi meaning using AI if not available in database
            hindi_meaning = unused_word.hindi_meaning
            if not hindi_meaning:
                from core.ai_feedback import get_vocab_meaning
                hindi_meaning = get_vocab_meaning(unused_word.word)
                # Update database with Hindi meaning
                unused_word.hindi_meaning = hindi_meaning
                db.session.commit()
            
            return jsonify({
                "success": True,
                "word": {
                    "id": unused_word.id,
                    "word": unused_word.word,
                    "image_path": unused_word.image_path,
                    "category": unused_word.category,
                    "difficulty": unused_word.difficulty_level,
                    "hindi_meaning": hindi_meaning
                }
            })
        else:
            # If no unused words, reset all and get one
            if word_type:
                VocabularyWord.query.filter_by(category=word_type).update({"is_used": False})
                db.session.commit()
                unused_word = VocabularyWord.query.filter_by(category=word_type, is_used=False).order_by(func.random()).first()
            else:
                VocabularyWord.reset_all_usage()
                unused_word = VocabularyWord.get_random_unused()
                
            if unused_word:
                # Get Hindi meaning using AI if not available in database
                hindi_meaning = unused_word.hindi_meaning
                if not hindi_meaning:
                    from core.ai_feedback import get_vocab_meaning
                    hindi_meaning = get_vocab_meaning(unused_word.word)
                    # Update database with Hindi meaning
                    unused_word.hindi_meaning = hindi_meaning
                    db.session.commit()
                
                return jsonify({
                    "success": True,
                    "word": {
                        "id": unused_word.id,
                        "word": unused_word.word,
                        "image_path": unused_word.image_path,
                        "category": unused_word.category,
                        "difficulty": unused_word.difficulty_level,
                        "hindi_meaning": hindi_meaning
                    },
                    "message": "All words completed! Starting fresh cycle."
                })
            else:
                return jsonify({"success": False, "error": "No vocabulary words available"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/vocabulary/mark_used", methods=["POST"])
@login_required
def mark_vocabulary_used():
    """Mark a vocabulary word as used"""
    try:
        data = request.get_json()
        word_id = data.get('word_id')
        
        if not word_id:
            return jsonify({"success": False, "error": "Word ID is required"})
        
        word = VocabularyWord.query.get(word_id)
        if word:
            word.mark_as_used()
            return jsonify({"success": True, "message": "Word marked as used"})
        else:
            return jsonify({"success": False, "error": "Word not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/get-hindi-meaning", methods=["POST"])
@login_required
def get_word_hindi_meaning():
    """Get Hindi meaning for a specific word"""
    try:
        data = request.get_json()
        word = data.get('word')
        
        if not word:
            return jsonify({"success": False, "error": "Word is required"})
        
        # First check if word exists in vocabulary database
        vocab_word = VocabularyWord.query.filter_by(word=word.lower()).first()
        if vocab_word and vocab_word.hindi_meaning:
            return jsonify({
                "success": True,
                "word": word,
                "hindi_meaning": vocab_word.hindi_meaning
            })
        
        # If not in database or no meaning, use AI to get meaning
        from core.ai_feedback import get_vocab_meaning
        hindi_meaning = get_vocab_meaning(word)
        
        # Update database if word exists
        if vocab_word:
            vocab_word.hindi_meaning = hindi_meaning
            db.session.commit()
        
        return jsonify({
            "success": True,
            "word": word,
            "hindi_meaning": hindi_meaning
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
@app.route("/api/vocabulary/stats", methods=["GET"])
@login_required
def get_vocabulary_stats():
    """Get vocabulary usage statistics"""
    try:
        total_words = VocabularyWord.query.count()
        used_words = VocabularyWord.query.filter_by(is_used=True).count()
        unused_words = total_words - used_words
        
        return jsonify({
            "success": True,
            "stats": {
                "total": total_words,
                "used": used_words,
                "unused": unused_words,
                "completion_percentage": round((used_words / total_words) * 100, 1) if total_words > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/vocabulary/reset_game", methods=["POST"])
@login_required
def reset_vocabulary_game():
    """Reset all vocabulary words to unused state for new game session"""
    try:
        VocabularyWord.reset_all_usage()
        return jsonify({
            "success": True,
            "message": "Game session reset successfully. All words are now available again."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/word-categories", methods=["GET"])
@login_required
def get_word_categories():
    """Get all available word categories"""
    try:
        categories = db.session.query(VocabularyWord.category).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]
        return jsonify({
            "success": True,
            "categories": category_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/category-words/<category_name>", methods=["GET"])
@login_required
def get_category_words(category_name):
    """Get all words in a specific category"""
    try:
        words = VocabularyWord.query.filter_by(category=category_name).all()
        word_list = [{
            "id": word.id,
            "word": word.word,
            "image_path": word.image_path,
            "difficulty": word.difficulty_level
        } for word in words]
        return jsonify({
            "success": True,
            "category": category_name,
            "words": word_list,
            "count": len(word_list)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
from flask import request, jsonify
from flask_login import login_required, current_user

@app.route("/save_vocab_score", methods=["POST"])
@login_required
def save_vocab_score():
    try:
        data = request.json
        score = int(data.get("score", 0))
        day = data.get("day", "Day-1")

        progress = Progress.query.filter_by(user_id=str(current_user.user_id), day=day).first()
        if not progress:
            progress = Progress(user_id=str(current_user.user_id), day=day)
            db.session.add(progress)

        progress.vocabulary_forest = score
        db.session.commit()

        return jsonify({"success": True, "score": score})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})


import re, random
from flask import request, jsonify

CATEGORY_WORDS = {
    "Animals": ["Dog","Cat","Elephant","Tiger","Giraffe","Rat","Horse","Horsefly"],
    "Fruits & Vegetables": ["Apple","Mango","Orange","Eggplant","Potato","Tomato"],
    "Countries & Cities": ["India","Italy","Indonesia","Canada","Cairo","Tokyo"],
    "Movies / TV Shows": ["Matrix","Titanic","Friends","Inception"],
    "Foods & Drinks": ["Pizza","Samosa","Coffee","Tea","Biryani"],
    "Sports": ["Football","Cricket","Tennis","Badminton"],
    "Colors": ["Red","Blue","Green","Yellow","Purple"],
    "Occupations": ["Teacher","Doctor","Engineer","Pilot"],
    "Transport": ["Car","Bus","Train","Plane"],
    "Instruments": ["Guitar","Piano","Drums","Violin"]
}

# ---------------- Week-Based Categories (5 per week) ----------------
WEEK_CATEGORIES = {
    1: ["Animals","Fruits & Vegetables","Colors","Transport","Sports"],
    2: ["Countries & Cities","Movies / TV Shows","Foods & Drinks","Instruments","Occupations"],
    3: ["Animals","Movies / TV Shows","Transport","Colors","Fruits & Vegetables"],
    4: ["Countries & Cities","Sports","Instruments","Foods & Drinks","Occupations"]
}

def get_current_week(day:int) -> int:
    """Return current week number given the day number"""
    return ((day - 1) // 7) + 1

def get_categories_for_day(day:int):
    """Return categories for current week"""
    week = get_current_week(day)
    return WEEK_CATEGORIES.get(week, [])

def _first_alpha_char(s: str) -> str:
    m = re.search(r'[a-zA-Z]', s)
    return m.group(0).lower() if m else ''

# ---------------- AI Word Selection ----------------
@app.route("/api/ai_word", methods=["POST"])
def ai_word():
    data = request.json or {}
    category = data.get("category", "")
    used = set(w.lower() for w in data.get("usedWords", []))

    # Local candidates
    candidates = [w for w in CATEGORY_WORDS.get(category, []) if w.lower() not in used]
    if candidates:
        return jsonify({"word": random.choice(candidates)})

    # Fallback AI
    prompt = (
        f"Give me one unique English word from category '{category}' "
        f"not in {sorted(list(used))}. Only the word, no explanation."
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant, reply with one word only."},
        {"role": "user", "content": prompt}
    ]
    try:
        resp_text = call_openai(messages)
        candidate = re.sub(r'[^A-Za-z]', '', (resp_text.split()[0] if resp_text else ""))
        if candidate.lower() not in used:
            return jsonify({"word": candidate})
    except Exception as e:
        print("OpenAI fallback error:", e)
    return jsonify({"word": None})

# ---------------- Word Validation ----------------
@app.route("/api/validate_word", methods=["POST"])
def validate_word():
    data = request.json or {}
    word = (data.get("word") or "").strip().lower()
    category = (data.get("category") or "").strip()
    used = set(w.lower() for w in data.get("usedWords", []))

    if not word or not category:
        return jsonify({"valid": False, "reason": "missing word or category"})
    if word in used:
        return jsonify({"valid": False, "reason": "already used"})
    
    # Local quick check
    if word in [w.lower() for w in CATEGORY_WORDS.get(category, [])]:
        return jsonify({"valid": True})
    
    # AI validation fallback
    prompt = f"Is '{word}' a valid English {category}? Reply ONLY YES or NO."
    messages = [
        {"role": "system", "content": "Reply only YES or NO."},
        {"role": "user", "content": prompt}
    ]
    try:
        resp_text = call_openai(messages)
        if "YES" in resp_text.upper():
            return jsonify({"valid": True})
    except Exception as e:
        print("AI validation error:", e)

    return jsonify({"valid": False, "reason": "not valid for category"})
USER_PROGRESS = {
    "Animals": 0,
    "Fruits & Vegetables": 0,
    "Countries & Cities": 0,
    "Movies / TV Shows": 0,
    "Foods & Drinks": 0
}

# Store total credits
USER_CREDITS = 0

@app.route("/api/submit_word", methods=["POST"])
def submit_word():
    global USER_CREDITS
    data = request.json or {}
    category = data.get("category")
    word = (data.get("word") or "").strip().lower()

    if not category or not word:
        return jsonify({"success": False, "message": "Missing category or word."})

    # Example validation: assume all words valid for simplicity
    # In real app, validate word properly
    USER_PROGRESS[category] += 1
    credit_awarded = 0

    if USER_PROGRESS[category] >= 10:
        USER_CREDITS += 10
        credit_awarded = 10
        USER_PROGRESS[category] = 0  # reset counter for next batch

    return jsonify({
        "success": True,
        "word_count": USER_PROGRESS[category],
        "credits_awarded": credit_awarded,
        "total_credits": USER_CREDITS
    })

_model = None
def get_model(size="base"):
    global _model
    if _model is None:
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def transcribe_audio(path):
    model = get_model()
    try:
        segments, info = model.transcribe(
            path,
            language="en",
            task="transcribe",
            vad_filter=True,
            beam_size=1,
            best_of=1,
            word_timestamps=True,
        )
        result = " ".join([s.text for s in segments]).strip()
        return result or "[No speech detected]"
    except Exception as e:
        print(f"STT error: {e}")
        return "[Transcription error]"

@app.route("/api/recognize_audio", methods=["POST"])
def recognize_audio():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        tmp_name = f"tmp_{uuid.uuid4().hex}.{ext}"
        file.save(tmp_name)
        transcript = transcribe_audio(tmp_name)
        os.remove(tmp_name)
        return jsonify({"transcript": transcript})
    return jsonify({"error": "Invalid file type"}), 400

@app.route("/twinkle-star")
@login_required
def twinkle_star():
    """Interactive Twinkle Twinkle Little Star poem page"""
    # Default to first poem for backward compatibility
    poem = Poem.query.filter_by(day=1, poem_order=1).first()
    if not poem:
        # Fallback if database is not populated
        poem = {
            'poem_name': 'Twinkle Twinkle Little Star',
            'poem_content': 'Twinkle, twinkle, little star, How I wonder what you are! Up above the world so high, Like a diamond in the sky. Twinkle, twinkle, little star, How I wonder what you are!',
            'difficulty_level': 'nursery',
            'day': 1
        }
    return render_template("poem_template.html", poem=poem)

@app.route("/poem/<int:day>/<int:poem_order>")
@login_required
def poem_page(day, poem_order):
    """Dynamic poem page for any day and poem order"""
    poem = Poem.query.filter_by(day=day, poem_order=poem_order).first()
    if not poem:
        return "Poem not found", 404
    return render_template("poem_template.html", poem=poem)

@app.route("/poems/day/<int:day>")
@login_required
def poems_by_day(day):
    """Get all poems for a specific day"""
    poems = Poem.query.filter_by(day=day).order_by(Poem.poem_order).all()
    if not poems:
        return "No poems found for this day", 404
    return render_template("poem_selection.html", poems=poems, day=day)

@app.route("/antakshari")
@login_required
def antakshari_page():
    # मान लो user info session या DB से आ रहा है
    user_gender = session.get("gender", "male")  # default male
    
    if user_gender == "female":
        user_avatar = "/static/avatars/user_female.png"
    else:
        user_avatar = "/static/avatars/user_male.png"

    return render_template("ant_game.html", user_avatar=user_avatar)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload_photo", methods=["POST"])
@login_required
def upload_photo():
    # Check if request is AJAX
    is_ajax = request.headers.get('Content-Type', '').startswith('multipart/form-data')
    
    if "photo" not in request.files:
        if is_ajax:
            return jsonify({"success": False, "error": "No file part"}), 400
        flash("No file part")
        return redirect(url_for("dashboard"))

    file = request.files["photo"]
    if file.filename == "":
        if is_ajax:
            return jsonify({"success": False, "error": "No selected file"}), 400
        flash("No selected file")
        return redirect(url_for("dashboard"))

    if file and allowed_file(file.filename):
        filename = f"user_{current_user.user_id}{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Update user record
        current_user.photo = filename
        db.session.commit()

        if is_ajax:
            return jsonify({"success": True, "filename": filename, "message": "Photo uploaded successfully!"})
        flash("Photo uploaded successfully!")
    else:
        if is_ajax:
            return jsonify({"success": False, "error": "Invalid file type!"}), 400
        flash("Invalid file type!")

    return redirect(url_for("dashboard"))

# 4️⃣ Serve uploaded photo
@app.route("/user_data/<filename>")
def user_photo(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Image API endpoint removed - no longer generating images

@app.route('/api/add_credits', methods=['POST'])
@login_required
def add_credits():
    try:
        data = request.get_json()
        day = data.get('day')
        credits = data.get('credits', 0)
        statement_index = data.get('statement_index')
        activity_type = data.get('activity_type', 'listen')  # Default to listen for backward compatibility
        
        if not day:
            return jsonify({'error': 'Day is required'}), 400
        
        user_id = str(current_user.user_id)
        
        # Find or create progress record
        progress = Progress.query.filter_by(user_id=user_id, day=day).first()
        
        if not progress:
            # Initialize all fields to 0 and set the appropriate activity
            progress = Progress(
                user_id=user_id,
                day=day,
                listen=credits if activity_type == 'listen' else 0,
                speak=credits if activity_type == 'speak' else 0,
                vocabulary=credits if activity_type == 'vocabulary' else 0,
                revision=credits if activity_type == 'revision' else 0,
                karaoke=credits if activity_type == 'karaoke' else 0,
                topic_speaker=credits if activity_type == 'topic_speaker' else 0,
                antakshari_game=credits if activity_type == 'antakshari_game' else 0,
                last_stage=activity_type,
                last_statement=statement_index
            )
            db.session.add(progress)
        else:
            # Add credits to the appropriate activity
            if activity_type == 'listen':
                progress.listen = (progress.listen or 0) + credits
            elif activity_type == 'speak':
                progress.speak = (progress.speak or 0) + credits
            elif activity_type == 'vocabulary':
                progress.vocabulary = (progress.vocabulary or 0) + credits
            elif activity_type == 'revision':
                progress.revision = (progress.revision or 0) + credits
            elif activity_type == 'karaoke':
                progress.karaoke = (progress.karaoke or 0) + credits
            elif activity_type == 'topic_speaker':
                progress.topic_speaker = (progress.topic_speaker or 0) + credits
            
            progress.last_stage = activity_type
            progress.last_statement = statement_index
            progress.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Return the appropriate total credits based on activity type
        total_credits = getattr(progress, activity_type, 0)
        
        return jsonify({
            'success': True,
            'total_credits': total_credits,
            'credits_added': credits,
            'activity_type': activity_type
        })
        
    except Exception as e:
        print(f"Error in add_credits: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_progress')
@login_required
def get_progress():
    try:
        day = request.args.get('day')
        if not day:
            return jsonify({'error': 'Day is required'}), 400
        
        user_id = str(current_user.user_id)
        progress = Progress.query.filter_by(user_id=user_id, day=day).first()
        
        if progress:
            return jsonify({
                'success': True,
                'progress': {
                    'listen': progress.listen,
                    'speak': progress.speak,
                    'vocabulary': progress.vocabulary,
                    'last_stage': progress.last_stage,
                    'last_statement': progress.last_statement
                }
            })
        else:
            return jsonify({
                'success': True,
                'progress': None
            })
            
    except Exception as e:
        print(f"Error in get_progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_language', methods=['POST'])
@login_required
def update_language():
    try:
        data = request.get_json()
        language = data.get('language')
        
        if language not in ['english', 'hinglish']:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400
        
        # Update user's language preference
        current_user.language = language
        db.session.commit()
        
        return jsonify({'success': True, 'language': language})
        
    except Exception as e:
        print(f"Error updating language: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Legacy Image Generation API (kept for backward compatibility)
@app.route("/api/generate_image", methods=["POST"])
def generate_image_api():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # Set OpenAI API key from environment or config
        openai.api_key = os.getenv('OPENAI_API_KEY') or 'your-api-key-here'
        
        if not openai.api_key or openai.api_key == 'your-api-key-here':
            return jsonify({"error": "OpenAI API key not configured"}), 500
            
        # Create a simple prompt for cartoon-style image
        prompt = f"A cute cartoon rabbit character illustration for: {text}. Simple, colorful, child-friendly style with white background."
        
        # Generate image using DALL-E
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        
        return jsonify({
            "success": True,
            "image_url": image_url,
            "prompt": prompt
        })
        
    except Exception as e:
        print(f"Image generation error: {e}")
        return jsonify({"error": str(e)}), 500



# Language switching route
@app.route('/api/set_language', methods=['POST'])
def set_language():
    """Set UI language preference"""
    try:
        data = request.get_json()
        language = data.get('language', 'english')
        
        if language not in ['english', 'hinglish']:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400
        
        session['ui_language'] = language
        
        return jsonify({'success': True, 'language': language})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# Topic Speaker Route
@app.route('/topic-speaker')
@app.route('/topic-speaker/<day>')
@login_required
def topic_speaker(day=None):
    """Topic-based speaking program with Boony Female GIF"""
    if not day:
        # Get current day from user progress
        user_id = str(current_user.user_id)
        progress = Progress.query.filter_by(user_id=user_id).first()
        day = progress.day if progress else 'Day-1'
    
    return render_template('topic_speaker.html', day=day)





@app.route('/js-validator')
def js_validator():
    """JavaScript syntax validator"""
    return render_template('js_validator.html')

@app.route('/minimal-js-test')
@login_required
def minimal_js_test():
    """Minimal JavaScript test with template variables"""
    return render_template('minimal_js_test.html', 
                         day=current_user.current_day,
                         credits=current_user.credits)























@app.route('/test-js-output')
@login_required
def test_js_output():
    """Test JavaScript output with template variables"""
    return render_template('test_js_output.html', 
                         day=current_user.current_day,
                         current_user=current_user,
                         credits=current_user.credits,
                         is_practice_mode=session.get('practice_mode', False))

@app.route('/js-debug-minimal')
@login_required
def js_debug_minimal():
    """Minimal JavaScript debug page to isolate syntax errors"""
    return render_template('js_debug_minimal.html',
                         day=current_user.current_day,
                         current_user=current_user,
                         credits=current_user.credits,
                         star_of_day_user_id=session.get('star_of_day_user_id'),
                         star_of_week_user_id=session.get('star_of_week_user_id'))

@app.route('/test-null-values')
@login_required
def test_null_values():
    """Test null values in JavaScript to identify syntax errors"""
    return render_template('test_null_values.html',
                         current_user=current_user,
                         star_of_day_user_id=get_star_of_day().get('user_id'),
                         star_of_week_user_id=get_star_of_week().get('user_id'))

@app.route('/test-setup-guide-tts')
@login_required
def test_setup_guide_tts():
    """Test setupGuideTTS function"""
    return render_template('test_setup_guide_tts.html')

@app.route('/test-js-syntax')
@login_required
def test_js_syntax():
    """Test JavaScript syntax with template variables"""
    user_id = current_user.user_id
    practice_day = request.args.get('practice_day') or request.args.get('day')
    
    if practice_day:
        practice_progress = Progress.query.filter_by(user_id=user_id, day=practice_day).first()
        if practice_progress:
            credits = {
                "listen": practice_progress.listen or 0,
                "speak": practice_progress.speak or 0,
                "vocabulary": practice_progress.vocabulary or 0,
                "revision": practice_progress.revision or 0,
            }
            day = practice_day
        else:
            credits = {"listen": 0, "speak": 0, "vocabulary": 0, "revision": 0}
            day = practice_day
    else:
        progress = Progress.query.filter_by(user_id=user_id).order_by(Progress.day.desc()).first()
        if not progress:
            credits = {"listen": 0, "speak": 0, "vocabulary": 0, "revision": 0}
            day = "Day-1"
        else:
            credits = {
                "listen": progress.listen or 0,
                "speak": progress.speak or 0,
                "vocabulary": progress.vocabulary or 0,
                "revision": progress.revision or 0,
            }
            day = progress.day or "Day-1"
    
    # Get star information
    star_of_day = get_star_of_day()
    star_of_week = get_star_of_week()
    
    return render_template('test_js_syntax.html',
                         day=day,
                         current_user=current_user,
                         credits=credits,
                         star_of_day_user_id=star_of_day.get('user_id') if star_of_day else None,
                         star_of_week_user_id=star_of_week.get('user_id') if star_of_week else None)

@app.route('/test-dashboard-comprehensive')
@login_required
def test_dashboard_comprehensive():
    """Comprehensive test of dashboard JavaScript"""
    return render_template('test_dashboard_comprehensive.html',
                          day=get_current_day(current_user.user_id),
                          current_user=current_user,
                          credits=get_user_credits(current_user.user_id),
                          star_of_day_user_id=get_star_of_day().get('user_id'),
                          star_of_week_user_id=get_star_of_week().get('user_id'),
                          is_practice_mode=request.args.get('practice_day') is not None)

@app.route('/test-with-external-scripts')
@login_required
def test_with_external_scripts():
    """Test dashboard with external scripts"""
    return render_template('test_with_external_scripts.html',
                          day=get_current_day(current_user.user_id),
                          current_user=current_user,
                          credits=get_user_credits(current_user.user_id),
                          star_of_day_user_id=get_star_of_day().get('user_id'),
                          star_of_week_user_id=get_star_of_week().get('user_id'),
                          is_practice_mode=request.args.get('practice_day') is not None)

@app.route('/test-syntax-debug')
@login_required
def test_syntax_debug():
    """Debug JavaScript syntax issues"""
    return render_template('test_syntax_debug.html',
                          day=get_current_day(current_user.user_id),
                          current_user=current_user,
                          credits=get_user_credits(current_user.user_id),
                          star_of_day_user_id=get_star_of_day().get('user_id'),
                          star_of_week_user_id=get_star_of_week().get('user_id'),
                          is_practice_mode=request.args.get('practice_day') is not None)

@app.route('/test-null-values-debug')
@login_required
def test_null_values_debug():
    """Test null values in JavaScript template"""
    return render_template('test_null_values_debug.html',
                          day=get_current_day(current_user.user_id),
                          current_user=current_user,
                          credits=get_user_credits(current_user.user_id),
                          star_of_day_user_id=None,  # Force None to test
                          star_of_week_user_id=None,  # Force None to test
                          is_practice_mode=request.args.get('practice_day') is not None)

@app.route('/test-exact-dashboard-js')
@login_required
def test_exact_dashboard_js():
    """Test exact dashboard JavaScript structure"""
    return render_template('test_exact_dashboard_js.html',
                          day=get_current_day(current_user.user_id),
                          current_user=current_user,
                          credits=get_user_credits(current_user.user_id),
                          star_of_day_user_id=get_star_of_day().get('user_id'),
                          star_of_week_user_id=get_star_of_week().get('user_id'),
                          is_practice_mode=request.args.get('practice_day') is not None)



@app.route('/test-dashboard-minimal')
@login_required
def test_dashboard_minimal():
    """Test minimal dashboard JavaScript"""
    # Get the same data as dashboard
    user_id = current_user.user_id
    practice_day = request.args.get('practice_day')
    
    if practice_day:
        practice_progress = Progress.query.filter_by(user_id=user_id, day=practice_day).first()
        if practice_progress:
            credits = {
                "listen": practice_progress.listen or 0,
                "speak": practice_progress.speak or 0,
                "vocabulary": practice_progress.vocabulary or 0,
                "revision": practice_progress.revision or 0,
            }
            day = practice_day
        else:
            credits = {"listen": 0, "speak": 0, "vocabulary": 0, "revision": 0}
            day = practice_day
    else:
        progress = Progress.query.filter_by(user_id=user_id).order_by(Progress.day.desc()).first()
        if not progress:
            credits = {"listen": 0, "speak": 0, "vocabulary": 0, "revision": 0}
            day = "Day-1"
        else:
            credits = {
                "listen": progress.listen or 0,
                "speak": progress.speak or 0,
                "vocabulary": progress.vocabulary or 0,
                "revision": progress.revision or 0,
            }
            day = progress.day or "Day-1"
    
    return render_template('test_dashboard_minimal.html',
                         day=day,
                         current_user=current_user,
                         credits=credits,
                         star_of_day_user_id=get_star_of_day().get('user_id'),
                         star_of_week_user_id=get_star_of_week().get('user_id'),
                         is_practice_mode=bool(practice_day))

@app.route('/js-syntax-isolate')
@login_required
def js_syntax_isolate():
    """Isolate JavaScript syntax errors step by step"""
    # Get the same data as dashboard
    user_id = current_user.user_id
    practice_day = request.args.get('practice_day')
    
    if practice_day:
        practice_progress = Progress.query.filter_by(user_id=user_id, day=practice_day).first()
        if practice_progress:
            credits = {
                "listen": practice_progress.listen or 0,
                "speak": practice_progress.speak or 0,
                "vocabulary": practice_progress.vocabulary or 0,
                "revision": practice_progress.revision or 0,
            }
            day = practice_day
        else:
            credits = {"listen": 0, "speak": 0, "vocabulary": 0, "revision": 0}
            day = practice_day
    else:
        progress = Progress.query.filter_by(user_id=user_id).order_by(Progress.day.desc()).first()
        if not progress:
            credits = {"listen": 0, "speak": 0, "vocabulary": 0, "revision": 0}
            day = "Day-1"
        else:
            credits = {
                "listen": progress.listen or 0,
                "speak": progress.speak or 0,
                "vocabulary": progress.vocabulary or 0,
                "revision": progress.revision or 0,
            }
            day = progress.day or "Day-1"
    
    return render_template('js_syntax_isolate.html',
                         day=day,
                         current_user=current_user,
                         credits=credits,
                         star_of_day_user_id=get_star_of_day().get('user_id'),
                         star_of_week_user_id=get_star_of_week().get('user_id'))

@app.route("/api/get_current_session")
@login_required
def get_current_session():
    """Get current user session info including day"""
    try:
        # Get user's latest progress to determine current day
        progress = (
            Progress.query.filter_by(user_id=str(current_user.user_id))
            .order_by(Progress.day.desc())
            .first()
        )
        
        current_day = progress.day if progress else "Day-1"
        
        return jsonify({
            "success": True,
            "day": current_day,
            "user_id": str(current_user.user_id)
        })
    except Exception as e:
        print(f"Error getting current session: {e}")
        return jsonify({
            "success": False,
            "day": "Day-1",
            "error": str(e)
        })

@app.route("/api/progress_to_next_day", methods=["POST"])
@login_required
def progress_to_next_day():
    """Progress user to the next day"""
    try:
        # Get user's current progress
        progress = (
            Progress.query.filter_by(user_id=str(current_user.user_id))
            .order_by(Progress.day.desc())
            .first()
        )
        
        if not progress:
            return jsonify({"success": False, "error": "No progress found"}), 400
        
        # Extract current day number and increment
        current_day_num = int(progress.day.split("-")[1])
        next_day_num = current_day_num + 1
        next_day = f"Day-{next_day_num}"
        
        # Create new progress record for next day
        new_progress = Progress(
            user_id=str(current_user.user_id),
            day=next_day,
            listen=0,
            speak=0,
            vocabulary=0,
            revision=0,
            karaoke=10,
            topic_speaker=0,
            last_stage="",
            last_statement=0,
            updated_at=datetime.now(timezone.utc)
        )
        
        db.session.add(new_progress)
        db.session.commit()
        
        # Generate congratulatory message for day completion
        guide = BoonyGuide()
        user_context = {
            'name': current_user.full_name or current_user.username,
            'completed_day': progress.day,
            'new_day': next_day,
            'day_number': current_day_num
        }
        
        congratulations = guide.get_congratulatory_message("day_complete", user_context)
        
        return jsonify({
            "success": True,
            "new_day": next_day,
            "message": f"Successfully progressed to {next_day}!",
            "congratulations": congratulations
        })
        
    except Exception as e:
        print(f"Error progressing to next day: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/get_completed_days")
@login_required
def get_completed_days():
    """Get list of days user has made progress on (excluding current day for practice)"""
    try:
        # Get user's current day
        current_progress = (
            Progress.query.filter_by(user_id=str(current_user.user_id))
            .order_by(Progress.day.desc())
            .first()
        )
        current_day = current_progress.day if current_progress else "Day-1"
        
        # Get all progress records for user
        progress_records = (
            Progress.query.filter_by(user_id=str(current_user.user_id))
            .order_by(Progress.day.asc())
            .all()
        )
        
        completed_days = []
        for prog in progress_records:
            # Consider a day completed if user has any credits
            total_credits = (prog.listen or 0) + (prog.speak or 0) + (prog.vocabulary or 0)
            # Only include days that are not the current day (for practice purposes)
            if total_credits > 0 and prog.day != current_day:
                completed_days.append(prog.day)
        
        return jsonify({
            "success": True,
            "completed_days": completed_days,
            "current_day": current_day
        })
        
    except Exception as e:
        print(f"Error getting completed days: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/get_day_topic")
@login_required
def get_day_topic():
    """Get topic and content for a specific day from syllabus"""
    try:
        day = request.args.get('day', 'Day-1')
        
        # Extract day number from day string (e.g., "Day-1" -> "1")
        day_num = day.replace('Day-', '') if day.startswith('Day-') else day
        
        # Get syllabus data for the day
        from models import Syllabus
        syllabus_entries = Syllabus.query.filter_by(day=day).all()
        
        if syllabus_entries:
            # Get the topic from first entry (all entries for same day should have same topic)
            topic = syllabus_entries[0].topic
            
            # Prepare content from all statements for the day
            content = []
            for entry in syllabus_entries:
                content.append({
                    "text": entry.listen_speak_statement,
                    "hindi": entry.hindi_meaning or "",
                    "pronunciation": entry.pronounciation or "",
                    "vocab": entry.vocab or ""
                })
            
            return jsonify({
                "success": True,
                "topic": topic,
                "content": content,
                "day": day
            })
        else:
            # Fallback: try to load from syllabus service - first try the main syllabus file
            statements = load_day_statements('data/syllabus/english_spoken_syllabus_filled_ai.xlsx', day_num)
            
            # If not found in main file, try the backup file
            if not statements:
                statements = load_day_statements('data/syllabus/data.xlsx', day_num)
            
            if statements:
                # Extract topic from first statement or use default
                topic = statements[0].get('topic', 'Daily Routine') if statements else 'Daily Routine'
                
                content = []
                for stmt in statements:
                    content.append({
                        "text": stmt.get('text', ''),
                        "hindi": stmt.get('hindi', ''),
                        "pronunciation": stmt.get('pronunciation', ''),
                        "topic": stmt.get('topic', '')
                    })
                
                return jsonify({
                    "success": True,
                    "topic": topic,
                    "content": content,
                    "day": day
                })
            else:
                # Default fallback
                return jsonify({
                    "success": True,
                    "topic": "Daily Routine",
                    "content": [{
                        "text": "I wake up early in the morning.",
                        "hindi": "मैं सुबह जल्दी उठता हूँ।",
                        "pronunciation": "आई वेक अप अर्ली इन द मॉर्निंग",
                        "topic": "Daily Routine"
                    }],
                    "day": day
                })
                
    except Exception as e:
        print(f"Error getting day topic: {e}")
        return jsonify({
            "success": False,
            "topic": "Daily Routine",
            "content": [],
            "error": str(e)
        })

# Enhanced routes are now handled by imported route functions from revios.py and vocab.py

# Register enhanced routes
create_revision_routes(app)
create_vocabulary_routes(app)

@app.route('/api/get-guide-message', methods=['POST'])
@login_required
def get_guide_message():
    """API endpoint to get dynamic guide messages"""
    try:
        data = request.get_json()
        message_type = data.get('type', 'general')
        context = data.get('context', {})
        
        guide = BoonyGuide()
        
        if message_type == 'welcome':
            section = context.get('section', 'general')
            message = guide.get_welcome_message(section, context)
        elif message_type == 'congratulations':
            achievement = context.get('achievement', 'task_completion')
            message = guide.get_congratulatory_message(achievement, context)
        elif message_type == 'encouragement':
            message = guide.get_encouragement_message(context)
        elif message_type == 'daily_tip':
            message = guide.get_daily_tip()
        elif message_type == 'navigation':
            section = context.get('section', 'dashboard')
            message = guide.get_navigation_help(section)
        elif message_type == 'motivational':
            message = guide.get_motivational_quote()
        else:
            message = guide.get_guidance_message('general')
            
        return jsonify({
            'success': True,
            'message': message,
            'type': message_type
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/use-topic-speaker', methods=['POST'])
@login_required
def use_topic_speaker():
    """Add 10 credits for using topic speaker (listening)"""
    try:
        user_id = str(current_user.user_id)
        
        # Get user's progress
        progress = Progress.query.filter_by(user_id=user_id).first()
        
        if not progress:
            # Create new progress record
            progress = Progress(
                user_id=user_id,
                day='Day-1',  # Default day
                listen=0,
                speak=0,
                vocabulary=0,
                revision=0,
                karaoke=0,
                topic_speaker=10,  # Add 10 credits
                last_stage='topic_speaker',
                last_statement=0
            )
            db.session.add(progress)
        else:
            # Add 10 credits for listening to topic
            current_credits = getattr(progress, 'topic_speaker', 0) or 0
            progress.topic_speaker = current_credits + 10
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'remaining_credits': progress.topic_speaker,
            'message': '10 credits added for topic listening'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-sentence', methods=['POST'])
def analyze_sentence():
    """Analyze user's example sentence using AI"""
    try:
        from core.openai_helper import client
        
        data = request.get_json()
        print(f"DEBUG: Received data: {data}")
        sentence = data.get('sentence', '').strip()
        word = data.get('word', 'example').strip()  # Default word if not provided
        print(f"DEBUG: sentence='{sentence}', word='{word}'")
        
        if not sentence:
            print(f"DEBUG: Missing sentence: '{sentence}'")
            return jsonify({
                'success': False,
                'error': 'Sentence is required'
            }), 400
        
        prompt = f"""Analyze this example sentence for the word '{word}':
Sentence: "{sentence}"

Evaluate:
1. Does the sentence correctly use the word '{word}'?
2. Is the grammar correct?
3. Is the sentence meaningful and contextually appropriate?
4. Rate the sentence quality (1-10)

Provide feedback in this JSON format:
{{
    "score": <number 1-10>,
    "feedback": "<constructive feedback>",
    "category": "<excellent|good|needs_improvement>"
}}"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an English teacher helping students learn vocabulary. Provide constructive feedback on example sentences."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
        except Exception as openai_error:
            print(f"DEBUG: OpenAI API error: {openai_error}")
            return jsonify({
                'success': False,
                'error': f'OpenAI API error: {str(openai_error)}'
            }), 500
        
        # Parse AI response
        ai_response = response.choices[0].message.content.strip()
        
        try:
            # Try to parse as JSON
            result = json.loads(ai_response)
        except json.JSONDecodeError:
            # Fallback if AI doesn't return valid JSON
            score = 7  # Default score
            if 'excellent' in ai_response.lower() or 'perfect' in ai_response.lower():
                score = 9
                category = 'excellent'
            elif 'good' in ai_response.lower() or 'correct' in ai_response.lower():
                score = 7
                category = 'good'
            else:
                score = 5
                category = 'needs_improvement'
            
            result = {
                'score': score,
                'feedback': ai_response,
                'category': category
            }
        
        return jsonify({
            'success': True,
            'analysis': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/pandora_box')
@login_required
def pandora_box():
    """Pandora Box page route - Grammar and Pronunciation Rules"""
    import pandas as pd
    import os
    
    user_id = str(current_user.user_id)
    
    # Get current user's day from progress
    progress = (
        Progress.query.filter_by(user_id=user_id)
        .order_by(Progress.day.desc())
        .first()
    )
    
    # Current day (default to Day-1 if no progress)
    current_day = progress.day if progress else "Day-1"
    
    # Load Pandora Box data from Excel file (Grammar & Pronunciation Rules)
    pandora_items = []
    pandora_file = 'data/syllabus/pandora_box.xlsx'
    
    try:
        if os.path.exists(pandora_file):
            df = pd.read_excel(pandora_file)
            
            # Filter data for current day
            day_data = df[df['day'] == current_day]
            
            # Convert to pandora items format
            for _, row in day_data.iterrows():
                pandora_items.append({
                    "type": "grammar_rule",
                    "title": row.get('topic', 'Grammar Rule'),
                    "content": row.get('english_explenation', 'Grammar explanation'),
                    "difficulty": "intermediate",
                    "day": row.get('day', current_day),
                    "vocab": row.get('vocab', ''),
                    "hindi_meaning": row.get('hinglish_explenation', ''),
                    "pronunciation": row.get('topic', ''),
                    "grammar_note": row.get('grammar_note', ''),
                    "topic": row.get('topic', ''),
                    "english_explanation": row.get('english_explenation', ''),
                    "hinglish_explanation": row.get('hinglish_explenation', ''),
                    "practice_question": row.get('practice_question', '')
                })
        
        # If no data found in Excel, show message
        if not pandora_items:
            pandora_items = [{
                "type": "info",
                "title": f"No grammar rules available for {current_day}",
                "content": "Please check back later or contact support.",
                "difficulty": "beginner",
                "day": current_day
            }]
            
    except Exception as e:
        # Fallback error message
        pandora_items = [{
            "type": "error",
            "title": "Error loading Pandora Box content",
            "content": f"Unable to load grammar rules: {str(e)}",
            "difficulty": "beginner",
            "day": current_day
        }]
    
    # Get user language preference from base.html preferences or fallback to user profile
    user_language = current_user.language or 'hinglish'
    
    # Map database language codes to frontend language codes
    language_mapping = {
        'en': 'english',
        'hi': 'hinglish', 
        'hinglish': 'hinglish',
        'english': 'english'
    }
    
    # Use mapped language or default to hinglish
    mapped_language = language_mapping.get(user_language, 'hinglish')
    
    return render_template('pandora_box.html', 
                         pandora_items=pandora_items,
                         access_denied=False,
                         user_language=mapped_language)

# Chatbot Routes
# ----------------------
from services.chatbot import chatbot

@app.route('/chat')
@login_required
def chat():
    """Live Chat with Boony page"""
    return render_template('chat.html', user_language=current_user.language or 'en')

@app.route('/api/chat/topics', methods=['GET'])
@login_required
def get_chat_topics():
    """Get conversation topic options for user"""
    try:
        user_id = str(current_user.user_id)
        topics = chatbot.get_topic_options(user_id)
        
        return jsonify({
            'success': True,
            'topics': topics,
            'user_level': chatbot.get_user_level(user_id)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoints for Flutter app integration

@app.route('/api/vocabulary', methods=['GET'])
def get_vocabulary_words_api():
    """Get vocabulary words with optional limit and exclusion list for Flutter app"""
    try:
        limit = request.args.get('limit', type=int)
        exclude_words = request.args.get('exclude', '').split(',') if request.args.get('exclude') else []
        
        # Load vocabulary from Excel file
        vocab_file = 'data/syllabus/vocab_database.xlsx'
        if os.path.exists(vocab_file):
            df = pd.read_excel(vocab_file)
            words = []
            
            for _, row in df.iterrows():
                word_data = {
                    'word': str(row.get('word', '')),
                    'meaning': str(row.get('meaning', '')),
                    'example': str(row.get('example', '')),
                    'pronunciation': str(row.get('pronunciation', '')),
                    'difficulty': str(row.get('difficulty', 'beginner'))
                }
                
                # Skip excluded words
                if word_data['word'].lower() not in [w.lower() for w in exclude_words]:
                    words.append(word_data)
            
            # Apply limit if specified
            if limit and limit > 0:
                words = words[:limit]
                
            return jsonify({
                'success': True,
                'words': words,
                'total_count': len(words)
            })
        else:
            # Fallback to hardcoded vocabulary if Excel file not found
            fallback_words = [
                {'word': 'Hello', 'meaning': 'A greeting', 'example': 'Hello, how are you?', 'pronunciation': '/həˈloʊ/', 'difficulty': 'beginner'},
                {'word': 'Beautiful', 'meaning': 'Pleasing to look at', 'example': 'The sunset is beautiful.', 'pronunciation': '/ˈbjuːtɪfəl/', 'difficulty': 'intermediate'},
                {'word': 'Excellent', 'meaning': 'Extremely good', 'example': 'Your performance was excellent!', 'pronunciation': '/ˈeksələnt/', 'difficulty': 'intermediate'}
            ]
            
            # Apply exclusions and limit
            filtered_words = [w for w in fallback_words if w['word'].lower() not in [e.lower() for e in exclude_words]]
            if limit and limit > 0:
                filtered_words = filtered_words[:limit]
                
            return jsonify({
                'success': True,
                'words': filtered_words,
                'total_count': len(filtered_words)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/learning-content/<day>', methods=['GET'])
def get_learning_content_api(day):
    """Get learning content for a specific day from Excel syllabus for Flutter app"""
    try:
        # Read Excel file
        excel_file_path = os.path.join('data', 'syllabus', 'english_spoken_syllabus_filled_ai.xlsx')
        
        if not os.path.exists(excel_file_path):
            return jsonify({
                'success': False,
                'error': 'Syllabus file not found'
            }), 404
        
        df = pd.read_excel(excel_file_path)
        
        # Find content for the specified day
        day_filter = f"Day-{day}" if not day.startswith('Day-') else day
        day_row = df[df['day'].astype(str).str.strip() == day_filter]
        
        if day_row.empty:
            # Try alternative format
            alt_day = day.replace('Day-', '') if day.startswith('Day-') else f"Day-{day}"
            day_row = df[df['day'].astype(str).str.strip() == alt_day]
        
        if day_row.empty:
            return jsonify({
                'success': False,
                'error': f'No content found for {day}'
            }), 404
        
        # Extract content from the row
        row = day_row.iloc[0]
        content = {
            'day': day,
            'topic': str(row.get('topic', '')),
            'listen_speak_statement': str(row.get('listen_speak_statement', '')),
            'vocab': str(row.get('vocab', '')),
            'hindi_meaning': str(row.get('hindi_meaning', '')),
            'grammar_note': str(row.get('grammar_note', '')),
            'english_explanation': str(row.get('english_explenation', '')),
            'hinglish_explanation': str(row.get('hinglish_explenation', '')),
            'practice_question': str(row.get('practice_question', ''))
        }
        
        return jsonify({
            'success': True,
            'content': content
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/daily-topic', methods=['GET'])
def get_daily_topic():
    """Get daily topic from syllabus based on current day"""
    print("DEBUG: Function started - get_daily_topic")
    
    try:
        print("DEBUG: Starting get_daily_topic function")
        
        # Simplified approach - just use Day-1 for now to isolate the issue
        current_day = 'Day-1'
        print(f"DEBUG: Using hardcoded current_day: {current_day}")
        
        # Read Excel file
        excel_file_path = os.path.join('data', 'syllabus', 'english_spoken_syllabus_filled_ai.xlsx')
        
        if not os.path.exists(excel_file_path):
            print(f"DEBUG: Excel file not found at: {excel_file_path}")
            return jsonify({
                'success': False,
                'error': 'Syllabus file not found'
            }), 404
        
        print(f"DEBUG: Reading Excel file from: {excel_file_path}")
        
        # Read Excel file using pandas
        try:
            df = pd.read_excel(excel_file_path)
            print(f"DEBUG: Excel file read successfully")
        except Exception as excel_error:
            print(f"DEBUG: Excel read error: {str(excel_error)}")
            raise excel_error
        
        print(f"DEBUG: Excel columns: {list(df.columns)}")
        print(f"DEBUG: DataFrame shape: {df.shape}")
        print(f"DEBUG: First few rows: {df.head()}")
        
        # Find topic for current day
        print(f"DEBUG: Filtering DataFrame for day: {current_day}")
        try:
            day_row = df[df['day'] == current_day]
            print(f"DEBUG: Filter successful, found {len(day_row)} rows for day {current_day}")
        except Exception as filter_error:
            print(f"DEBUG: Filter error: {str(filter_error)}")
            raise filter_error
        
        if day_row.empty:
            print("DEBUG: No rows found for current day, trying fallback to Day-1")
            # Fallback to Day-1 if current day not found
            day_row = df[df['day'] == 'Day-1']
            print(f"DEBUG: Fallback to Day-1, found {len(day_row)} rows")
        
        if day_row.empty:
            print("DEBUG: No rows found even for Day-1")
            return jsonify({
                'success': False,
                'error': 'No topic found for current day'
            }), 404
        
        print(f"DEBUG: Attempting to extract topic from row")
        try:
            topic = day_row.iloc[0]['topic'] if 'topic' in day_row.columns else 'General Conversation'
            print(f"DEBUG: Topic extraction successful: {topic}")
        except Exception as topic_error:
            print(f"DEBUG: Topic extraction error: {str(topic_error)}")
            raise topic_error
        
        print(f"DEBUG: Selected topic: {topic}")
        
        return jsonify({
            'success': True,
            'topic': topic,
            'current_day': current_day
        })
        
    except KeyError as ke:
        print(f"DEBUG: KeyError in get_daily_topic: {str(ke)}")
        print(f"DEBUG: KeyError type: {type(ke).__name__}")
        import traceback
        print(f"DEBUG: KeyError Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(ke)
        }), 500
    except Exception as e:
        print(f"DEBUG: Exception in get_daily_topic: {str(e)}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test-simple', methods=['GET'])
def test_simple():
    """Simple test endpoint to isolate KeyError issue"""
    print("DEBUG: Simple test endpoint called")
    return jsonify({
        'success': True,
        'message': 'Simple test works'
    })

@app.route('/api/test-no-pandas', methods=['GET'])
def test_no_pandas():
    """Test endpoint without any pandas operations"""
    print("DEBUG: No-pandas test endpoint called")
    try:
        # Just return a simple response without any DataFrame operations
        return jsonify({
            'success': True,
            'message': 'No pandas test works',
            'timestamp': str(datetime.now())
        })
    except Exception as e:
        print(f"DEBUG: Error in test_no_pandas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/start', methods=['POST'])
@login_required
def start_chat():
    """Start new conversation with selected topic"""
    try:
        data = request.get_json()
        selected_topic = data.get('topic')
        
        if not selected_topic:
            return jsonify({
                'success': False,
                'error': 'Topic is required'
            }), 400
        
        user_id = str(current_user.user_id)
        result = chatbot.start_conversation(user_id, selected_topic)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/message', methods=['POST'])
@login_required
def send_chat_message():
    """Send message to chatbot and get response"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        user_id = str(current_user.user_id)
        result = chatbot.process_user_message(user_id, message)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/end', methods=['POST'])
@login_required
def end_chat():
    """End conversation and get summary"""
    try:
        user_id = str(current_user.user_id)
        result = chatbot.end_conversation(user_id)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/correct', methods=['POST'])
@login_required
def get_speech_correction():
    """Get speech correction suggestions for user input"""
    try:
        data = request.get_json()
        user_text = data.get('text', '').strip()
        
        if not user_text:
            return jsonify({
                'success': False,
                'error': 'Text is required'
            }), 400
        
        # Generate correction suggestions using OpenAI
        correction_prompt = f"""
Analyze this sentence and provide helpful corrections or alternative ways to say it:

User said: "{user_text}"

Provide:
1. Grammar corrections (if needed)
2. Alternative ways to express the same idea
3. Pronunciation tips (if applicable)

Format your response as a friendly suggestion, like "You can also say this like..." or "Here's another way to express that..."

Keep it encouraging and helpful, not critical.
"""
        
        try:
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Boony, a friendly English learning assistant. Provide helpful and encouraging speech corrections."},
                    {"role": "user", "content": correction_prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            correction = response.choices[0].message.content.strip()
            
            return jsonify({
                'success': True,
                'correction': correction,
                'original_text': user_text
            })
            
        except Exception as openai_error:
            # Fallback to simple corrections
            fallback_corrections = [
                f"You can also say: '{user_text}' - that sounds great!",
                f"Another way to express that could be: '{user_text}'",
                f"Nice! You could also try saying it like this: '{user_text}'"
            ]
            
            return jsonify({
                'success': True,
                'correction': random.choice(fallback_corrections),
                'original_text': user_text
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_image', methods=['POST'])
@login_required
def get_image():
    """Generate or retrieve image for given text"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Text is required'
            }), 400
        
        # For now, return a placeholder response
        # This can be enhanced later with actual image generation
        return jsonify({
            'success': True,
            'image_url': '/static/images/placeholder.png',
            'source': 'placeholder'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ----------------------
# Beginner to Professional Speaker Routes
# ----------------------
@app.route('/beginner-professional-speaker')
@login_required
def beginner_professional_speaker():
    """Beginner to Professional Speaker feature page"""
    try:
        # Get current day from user progress or default to Day-1
        progress = Progress.query.filter_by(user_id=current_user.id).first()
        current_day = progress.current_day if progress else 'Day-1'
        
        # Get current topic from syllabus
        current_topic = get_daily_topic(current_day)
        
        return render_template('beginner_professional_speaker.html', 
                             day=current_day, 
                             current_topic=current_topic)
    except Exception as e:
        print(f"Error in beginner_professional_speaker: {e}")
        return render_template('beginner_professional_speaker.html', 
                             day='Day-1', 
                             current_topic='Daily Routine')

@app.route('/api/get-daily-topic')
@login_required
def api_get_daily_topic():
    """API to get daily topic from syllabus"""
    try:
        day = request.args.get('day', 'Day-1')
        topic = get_daily_topic(day)
        
        return jsonify({
            'success': True,
            'topic': topic,
            'day': day
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate-speaker-content', methods=['POST'])
@login_required
def api_generate_speaker_content():
    """API to generate beginner and professional level content"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        level = data.get('level')  # 'beginner' or 'professional'
        day = data.get('day', 'Day-1')
        
        if not topic or not level:
            return jsonify({
                'success': False,
                'error': 'Topic and level are required'
            }), 400
        
        # Generate content using OpenAI
        content = generate_speaker_content(topic, level)
        title = f"{level.title()} Level: {topic}"
        
        return jsonify({
            'success': True,
            'content': content,
            'title': title,
            'level': level,
            'topic': topic
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_daily_topic(day):
    """Get topic for a specific day from syllabus"""
    try:
        # Load syllabus data
        df = pd.read_excel(app.config["DATA_SYLLABUS"])
        
        # Filter by day and get unique topic
        day_data = df[df['day'] == day]
        if not day_data.empty:
            return day_data['topic'].iloc[0]
        else:
            return 'Daily Routine'  # Default topic
    except Exception as e:
        print(f"Error getting daily topic: {e}")
        return 'Daily Routine'

def generate_speaker_content(topic, level):
    """Generate content for beginner or professional level using OpenAI"""
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        if level == 'beginner':
            prompt = f"""Create realistic content showing how a beginner Indian English learner would actually speak about '{topic}'. This should sound like a real person learning English.
            
Beginner Speaker Characteristics:
            - Speaks with natural hesitation and thinking pauses
            - Uses simple, everyday vocabulary
            - Includes realistic fillers: 'hmm', 'uh', 'you know', 'actually', 'I mean'
            - Sometimes directly translates from Hindi (like 'I am doing' instead of 'I do')
            - Shows genuine thinking process while speaking
            - Uses present continuous tense more often
            - Asks for confirmation with 'no?', 'right?', 'na?'
            - Sometimes repeats words when thinking
            
Format: Write 4-5 sentences as if recording a real beginner speaking naturally.
            
Example style: "Hmm... so about daily routine, you know... I am waking up at, uh, around 6 o'clock in the morning, no? Then I am... I am brushing my teeth and, uh, taking bath also. After that, I mean, I am having my breakfast with family members. It is... how to say... very important for me, actually."
            
Topic: {topic}
            
Make it sound natural and realistic, not scripted."""
        else:  # professional
            prompt = f"""Create impressive content showing how a highly professional, confident English speaker would discuss '{topic}'. This should demonstrate mastery of the language.
            
Professional Speaker Characteristics:
            - Speaks with complete confidence and authority
            - Uses sophisticated vocabulary and varied sentence structures
            - Employs professional idioms and expressions naturally
            - Shows deep thinking with smooth transitions
            - Uses advanced grammar structures effortlessly
            - Demonstrates cultural awareness and global perspective
            - Speaks with natural rhythm and perfect flow
            - Uses power words and impactful phrases
            - Shows expertise and thoughtful insights
            
Format: Write 4-5 sentences that showcase advanced English proficiency and professional communication.
            
Example style: "When we examine daily routines from a productivity standpoint, I've found that establishing non-negotiable morning rituals fundamentally transforms one's entire trajectory. I personally orchestrate my mornings with precision - beginning at 5:30 AM with mindfulness practices, followed by strategic physical conditioning and nutritional optimization. This systematic approach doesn't just enhance productivity; it cultivates the mental resilience essential for navigating complex professional challenges with clarity and purpose."
            
Topic: {topic}
            
Make it sound impressive, confident, and professionally sophisticated."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert English language instructor who understands the learning journey from beginner to professional level."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating speaker content: {e}")
        # Fallback content
        if level == 'beginner':
            return f"Hmm... so about {topic.lower()}, you know... I am thinking it is, uh, very important topic for us. Actually, let me tell you what I am knowing about this thing. It is... how to say... very much useful for our daily life activities, no? I mean, we are doing this every day, right?"
        else:
            return f"When we delve into the intricacies of {topic.lower()}, it becomes evident that this subject encompasses multifaceted dimensions that significantly impact our personal and professional trajectories. The strategic approach to mastering this area involves cultivating both theoretical understanding and practical implementation. This comprehensive perspective enables us to leverage these insights for sustained excellence and meaningful growth."

@app.route("/api/health", methods=["GET"])
def health_check():
    """Simple health check endpoint for connection testing"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "Server is running"
    }), 200

# PDF/Image to Speech Routes
@app.route('/pdf_to_speech')
@login_required
def pdf_to_speech():
    """PDF/Image to Speech converter page"""
    return render_template('pdf_to_speech.html')

@app.route('/api/extract-text', methods=['POST'])
@login_required
def extract_text_from_files():
    """Extract text from uploaded PDF/Image files"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'success': False, 'error': 'No files selected'})
        
        # Validate file count (max 10)
        if len(files) > 10:
            return jsonify({'success': False, 'error': 'Maximum 10 files allowed'})
        
        extracted_text = ""
        page_count = 0
        
        for file in files:
            if file.filename == '':
                continue
                
            # Check file size (50MB limit)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > 50 * 1024 * 1024:  # 50MB
                return jsonify({'success': False, 'error': f'File {file.filename} is too large (max 50MB)'})
            
            # Process based on file type
            if file.filename.lower().endswith('.pdf'):
                text, pages = extract_text_from_pdf(file)
                page_count += pages
            elif file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                text = extract_text_from_image(file)
                page_count += 1
            else:
                continue
            
            extracted_text += text + "\n\n"
        
        # Check page limit
        if page_count > 10:
            return jsonify({'success': False, 'error': 'Maximum 10 pages/images allowed'})
        
        if not extracted_text.strip():
            return jsonify({'success': False, 'error': 'No text found in uploaded files'})
        
        # Extract important words
        important_words = extract_important_words(extracted_text)
        
        # Generate file previews
        file_previews = []
        for file in files:
            file.seek(0)  # Reset file pointer
            preview_data = generate_file_preview(file)
            if preview_data:
                file_previews.append(preview_data)
        
        return jsonify({
            'success': True,
            'text': extracted_text.strip(),
            'important_words': important_words,
            'page_count': page_count,
            'file_previews': file_previews
        })
        
    except Exception as e:
        print(f"Error extracting text: {e}")
        return jsonify({'success': False, 'error': f'Error processing files: {str(e)}'})

def generate_file_preview(file):
    """Generate preview data for uploaded file"""
    try:
        file_type = file.content_type
        filename = file.filename
        
        if file_type == 'application/pdf':
            return generate_pdf_preview(file, filename)
        elif file_type in ['image/jpeg', 'image/jpg', 'image/png']:
            return generate_image_preview(file, filename)
        
        return None
    except Exception as e:
        print(f"Error generating file preview: {e}")
        return None

def generate_pdf_preview(file, filename):
    """Generate preview for PDF file"""
    try:
        import base64
        
        # Read first few bytes for preview
        file.seek(0)
        preview_bytes = file.read(1024)  # Read first 1KB
        file.seek(0)  # Reset
        
        # Get basic PDF info
        pdf_reader = PyPDF2.PdfReader(file)
        page_count = len(pdf_reader.pages)
        
        # Get first page text preview
        first_page_text = ""
        if page_count > 0:
            first_page_text = pdf_reader.pages[0].extract_text()[:200] + "..."
        
        return {
            'type': 'pdf',
            'filename': filename,
            'page_count': page_count,
            'preview_text': first_page_text,
            'icon': 'fas fa-file-pdf'
        }
    except Exception as e:
        print(f"Error generating PDF preview: {e}")
        return None

def generate_image_preview(file, filename):
    """Generate preview for image file"""
    try:
        import base64
        
        # Read image and convert to base64 for preview
        file.seek(0)
        image_data = file.read()
        file.seek(0)  # Reset
        
        # Convert to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get image info
        image = Image.open(file)
        width, height = image.size
        
        return {
            'type': 'image',
            'filename': filename,
            'width': width,
            'height': height,
            'preview_data': f"data:{file.content_type};base64,{image_base64}",
            'icon': 'fas fa-file-image'
        }
    except Exception as e:
        print(f"Error generating image preview: {e}")
        return None
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        page_count = len(pdf_reader.pages)
        
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text, page_count
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return "", 0

def extract_text_from_image(file):
    """Extract text from image using OCR"""
    try:
        image = Image.open(file)
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use pytesseract for OCR
        text = pytesseract.image_to_string(image, lang='eng')
        return text
    except Exception as e:
        print(f"Error extracting image text: {e}")
        return ""

def extract_important_words(text):
    """Extract important words with pronunciation and Hindi meaning"""
    try:
        # Simple word extraction (can be enhanced with NLP)
        words = re.findall(r'\b[A-Za-z]{4,}\b', text)
        word_freq = {}
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in ['that', 'this', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said']:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
        
        # Get top 20 most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        important_words = []
        for word, freq in sorted_words:
            # Simple pronunciation (can be enhanced with phonetic library)
            pronunciation = get_simple_pronunciation(word)
            hindi_meaning = get_hindi_meaning(word)
            
            important_words.append({
                'english': word.capitalize(),
                'pronunciation': pronunciation,
                'hindi': hindi_meaning,
                'frequency': freq
            })
        
        return important_words
    except Exception as e:
        print(f"Error extracting important words: {e}")
        return []

def get_simple_pronunciation(word):
    """Get simple pronunciation for word"""
    # Basic pronunciation rules (can be enhanced)
    pronunciation_map = {
        'the': 'ðə',
        'and': 'ænd',
        'you': 'juː',
        'that': 'ðæt',
        'have': 'hæv',
        'for': 'fɔːr',
        'not': 'nɒt',
        'with': 'wɪð',
        'this': 'ðɪs',
        'but': 'bʌt',
        'his': 'hɪz',
        'from': 'frɒm',
        'they': 'ðeɪ',
        'she': 'ʃiː',
        'her': 'hɜːr',
        'been': 'biːn',
        'than': 'ðæn',
        'its': 'ɪts',
        'who': 'huː',
        'did': 'dɪd'
    }
    
    return pronunciation_map.get(word.lower(), word.lower())

def get_hindi_meaning(word):
    """Get Hindi meaning for word using static dictionary and AI fallback"""
    # Basic Hindi translations (can be enhanced with translation API)
    hindi_map = {
        'good': 'अच्छा',
        'bad': 'बुरा',
        'big': 'बड़ा',
        'small': 'छोटा',
        'new': 'नया',
        'old': 'पुराना',
        'first': 'पहला',
        'last': 'अंतिम',
        'long': 'लंबा',
        'great': 'महान',
        'little': 'छोटा',
        'own': 'अपना',
        'other': 'अन्य',
        'many': 'कई',
        'right': 'सही',
        'still': 'अभी भी',
        'way': 'रास्ता',
        'even': 'यहां तक कि',
        'back': 'वापस',
        'any': 'कोई',
        'very': 'बहुत',
        'her': 'उसका',
        'all': 'सब',
        'there': 'वहाँ',
        'when': 'कब',
        'much': 'बहुत',
        'some': 'कुछ',
        'what': 'क्या',
        'know': 'जानना',
        'just': 'बस',
        'get': 'पाना',
        'over': 'ऊपर',
        'think': 'सोचना',
        'also': 'भी',
        'your': 'आपका',
        'work': 'काम',
        'life': 'जीवन',
        'only': 'केवल',
        'can': 'सकना',
        'should': 'चाहिए',
        'after': 'बाद',
        'being': 'होना',
        'now': 'अब',
        'made': 'बनाया',
        'before': 'पहले',
        'here': 'यहाँ',
        'through': 'के माध्यम से',
        'where': 'कहाँ',
        'most': 'सबसे',
        'take': 'लेना',
        'than': 'से',
        'important': 'महत्वपूर्ण',
        'document': 'दस्तावेज़',
        'information': 'जानकारी',
        'education': 'शिक्षा',
        'learning': 'सीखना',
        'knowledge': 'ज्ञान',
        'understand': 'समझना',
        'language': 'भाषा',
        'meaning': 'अर्थ',
        'word': 'शब्द',
        'text': 'पाठ'
    }
    
    # Check static dictionary first
    static_meaning = hindi_map.get(word.lower())
    if static_meaning:
        return static_meaning
    
    # Use AI for unknown words
    try:
        prompt = f"Translate the English word '{word}' to Hindi. Provide only the Hindi translation in Devanagari script, nothing else."
        
        response = call_openai(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-3.5-turbo",
            max_tokens=50,
            temperature=0.1
        )
        
        if response and response.strip():
            return response.strip()
        else:
            return 'अर्थ उपलब्ध नहीं'
            
    except Exception as e:
        print(f"Error getting AI Hindi meaning for '{word}': {e}")
        return 'अर्थ उपलब्ध नहीं'

@app.route('/api/text-to-speech', methods=['POST'])
@login_required
def convert_text_to_speech():
    """Convert text to speech audio"""
    temp_file_path = None
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        # Create temporary file for audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file_path = temp_file.name
        temp_file.close()  # Close file handle before gTTS writes to it
        
        # Generate TTS using gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_file_path)
        
        # Read the audio file and return as response
        with open(temp_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass  # Ignore cleanup errors
        
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/mpeg',
            as_attachment=False
        )
        
    except Exception as e:
        print(f"Error converting text to speech: {e}")
        # Clean up temporary file on error
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        return jsonify({'success': False, 'error': f'Error generating audio: {str(e)}'})

@app.route('/api/speak-word', methods=['POST'])
@login_required
def speak_single_word():
    """Convert single word to speech"""
    temp_file_path = None
    try:
        data = request.get_json()
        word = data.get('word', '')
        
        if not word:
            return jsonify({'success': False, 'error': 'No word provided'})
        
        # Create temporary file for audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file_path = temp_file.name
        temp_file.close()  # Close file handle before gTTS writes to it
        
        # Generate TTS for single word
        tts = gTTS(text=word, lang='en', slow=True)  # Slow for pronunciation
        tts.save(temp_file_path)
        
        # Read the audio file and return as response
        with open(temp_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass  # Ignore cleanup errors
        
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/mpeg',
            as_attachment=False
        )
        
    except Exception as e:
        print(f"Error speaking word: {e}")
        # Clean up temporary file on error
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        return jsonify({'success': False, 'error': f'Error generating word audio: {str(e)}'})

# Register the public_api blueprint
import logging
logging.basicConfig(level=logging.INFO)
if 'public_api' not in app.blueprints:
    app.register_blueprint(public_api)
    print("[INFO] public_api blueprint registered ✅")
else:
    print("[WARNING] public_api blueprint already registered ⚠️")

# Register Excel API blueprint
from excel_api import excel_bp
if 'excel' not in app.blueprints:
    app.register_blueprint(excel_bp)
    print("[INFO] excel_api blueprint registered ✅")
else:
    print("[WARNING] excel_api blueprint already registered ⚠️")

# Main
# ----------------------
def main():
    """Main entry point for the application"""
    import argparse

    # Step 1: Parse arguments
    parser = argparse.ArgumentParser(description='Boony English Learning App')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--production', action='store_true', help='Run in production mode')
    
    args = parser.parse_args()

    # Step 2: Determine debug mode
    debug_mode = args.debug and not args.production

    # Step 3: Run Flask app
    print(f"Running on {args.host}:{args.port} | Debug: {debug_mode} | Production: {args.production}")
    app.run(
        host=args.host,
        port=args.port,
        debug=debug_mode
    )

# Entry point
if __name__ == "__main__":
    main()
