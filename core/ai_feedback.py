import openai
import json
import os
from core.resource_helper import resource_path 
from difflib import SequenceMatcher, ndiff
import difflib
import time
import openai
import asyncio
import edge_tts
from playsound import playsound
import re
from faster_whisper import WhisperModel

# Global whisper model variable for lazy loading
_model = None

def get_whisper_model():
    """Get or initialize the Whisper model (lazy loading)"""
    global _model
    if _model is None:
        print("⏳ Loading Whisper model (base) for AI feedback...")
        _model = WhisperModel("base", device="cpu", compute_type="int8")
        print("✅ Whisper model loaded for AI feedback")
    return _model

# Load API key from JSON file
config_path = resource_path("core/config.json")
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
else:
    print("⚠️ core/config.json not found! Using default config.")
    config_data = {}

api_key = config_data.get("openai_api_key", "")

if not api_key:
    print("❌ OpenAI API key missing in config.json!")
else:
    print("✅ OpenAI API key loaded.")
def get_ai_feedback(prompt):
    """Simple AI call for generic text-based feedback."""
    if not api_key:
        return "⚠️ OpenAI not configured."

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful and friendly English tutor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"⚠️ AI feedback error: {e}"

# ---------------------- AI Feedback Functions ----------------------
# core/ai_feedback.py
def get_vocab_synonyms(vocab_word):
    """
    Returns exactly two simple English synonyms for the given vocabulary word.
    """
    try:
        from core.openai_helper import call_openai
        prompt = f"Give exactly two simple English synonyms for the word '{vocab_word}'. Return them separated by a comma."
        response = call_openai(prompt)
        if "," in response:
            parts = [p.strip() for p in response.split(",") if p.strip()]
            # Ensure exactly 2 synonyms
            if len(parts) >= 2:
                return parts[0], parts[1]
            elif len(parts) == 1:
                return parts[0], "-"
        return "-", "-"
    except Exception as e:
        print(f"⚠️ get_vocab_synonyms failed: {e}")
        return "-", "-"

def get_vocab_meaning(vocab_word):
    """
    Returns the meaning of a vocabulary word in simple English.
    """
    try:
        from core.openai_helper import call_openai
        prompt = f"Give a short and simple meaning for the word '{vocab_word}' in English."
        return call_openai(prompt)
    except Exception as e:
        print(f"⚠️ get_vocab_meaning failed: {e}")
        return "Meaning not available."

def get_vocab_usage(vocab_word):
    """
    Returns one simple English sentence using the given vocabulary word.
    """
    try:
        from core.openai_helper import call_openai
        prompt = f"Make one simple English sentence using the word '{vocab_word}'."
        return call_openai(prompt)
    except Exception as e:
        print(f"⚠️ get_vocab_usage failed: {e}")
        return "Sentence not available."

def get_sentence_formation_feedback(user_input):
    if not api_key:
        return "⚠️ OpenAI not configured."

    if user_input == "":
        prompt = f"""You are a spoken English teacher. A user said: "{user_input}" Please provide feedback in english: 1. You can say 2. Encouragement. Keep it short and friendly."""
    else:
        prompt = f"""You are a spoken English teacher. A user said: "{user_input}" Please provide feedback in english: 1. improved version of the sentence 2. Encouragement. Keep it short and friendly."""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly spoken English teacher."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Feedback error: {e}"

def get_corrected_version(audio_path):
    model = get_whisper_model()
    segments, _ = model.transcribe(audio_path)
    transcript = " ".join(segment.text for segment in segments).strip()

    if not transcript:
        return ""

    prompt = (
        "You are a helpful English tutor. The following sentence was spoken by a student. "
        "Correct any pronunciation or punctuation mistakes, but do NOT change the structure too much. "
        f"Sentence: \"{transcript}\" \n\nCorrected version:"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("❌ Correction failed:", e)
        return ""

def detect_mispronounced_words(audio_file_path, original_sentence):
    """
    Return a dict with:
      - status: 'silent' | 'different' | 'ok' | 'mispronounced'
      - mispronounced: list of words expected but missing/mispronounced
      - user_text: transcription string (may be empty)
    Logic:
      - If user silent => 'silent'
      - If sentence is too different => 'different'
      - Else compute word-diff and report missing words as mispronounced
    """
    user_text = get_transcription(audio_file_path)  # existing faster-whisper function
    if not user_text or not user_text.strip():
        return {"status": "silent", "mispronounced": [], "user_text": user_text or ""}

    similarity = SequenceMatcher(None, original_sentence.lower(), user_text.lower()).ratio()
    if similarity < 0.40:
        return {"status": "different", "mispronounced": [], "user_text": user_text}

    # Normalize words (keeps contractions)
    original_words = re.findall(r"\b[\w']+\b", original_sentence.lower())
    user_words = re.findall(r"\b[\w']+\b", user_text.lower())
    diff = list(ndiff(original_words, user_words))

    mispronounced = []
    for token in diff:
        # '- word' means expected word missing or different in user's output
        if token.startswith("- "):
            mispronounced.append(token[2:])

    if not mispronounced:
        return {"status": "ok", "mispronounced": [], "user_text": user_text}

    return {"status": "mispronounced", "mispronounced": mispronounced, "user_text": user_text}


def get_smart_pronunciation_analysis(audio_file_path, original_sentence):
    """
    Enhanced pronunciation analysis that combines technical analysis with friendly feedback.
    This function is more forgiving and always provides constructive guidance.
    """
    # Get the friendly feedback first
    friendly_result = get_friendly_pronunciation_feedback(audio_file_path, original_sentence)
    
    # Also get technical analysis for reference
    technical_result = detect_mispronounced_words(audio_file_path, original_sentence)
    
    # Combine both approaches for better user experience
    return {
        "status": friendly_result["status"],
        "feedback": friendly_result["feedback"],
        "user_text": friendly_result["user_text"],
        "encouragement": friendly_result["encouragement"],
        "technical_status": technical_result["status"],
        "mispronounced": technical_result.get("mispronounced", [])
    }


def is_word_spoken_correct(expected_word, spoken_text, threshold=0.70):
    """
    Quick check if the user's spoken_text contains/corresponds to expected_word.
    Returns True/False.
    Behavior:
      - If expected appears as substring -> True
      - Else use SequenceMatcher ratio >= threshold
    """
    if not expected_word or not spoken_text:
        return False
    e = expected_word.lower().strip()
    s = spoken_text.lower().strip()
    if e in s:
        return True
    score = SequenceMatcher(None, e, s).ratio()
    return score >= threshold

def get_vocab_meaning(word):
    """Get meaning for a vocab word using OpenAI API."""
    from core.openai_helper import call_openai  # तुम्हारे system का AI call function
    prompt = f"Give a short Hindi meaning for the English word '{word}'."
    try:
        return call_openai(prompt)
    except Exception:
        return ""





def get_transcription(audio_file_path):
    """Enhanced CPU transcription using faster-whisper with improved speech detection"""
    try:
        if not os.path.exists(audio_file_path):
            print("❌ Audio file does not exist!")
            return ""
        
        # Get the model instance
        model = get_whisper_model()
        
        # Optimized transcription for faster processing
        segments, info = model.transcribe(
            audio_file_path,
            vad_filter=True,  # Enable Voice Activity Detection
            beam_size=1,  # Faster processing with single beam
            best_of=1,    # Single candidate for speed
            temperature=0.0,  # More deterministic output
            no_speech_threshold=0.6,  # Lower threshold = more sensitive to speech
            condition_on_previous_text=False,  # Don't rely on previous context
        )
        
        # Process segments quickly
        segment_texts = []
        for segment in segments:
            segment_text = segment.text.strip()
            if segment_text:
                segment_texts.append(segment_text)
        
        result = " ".join(segment_texts).strip()
        
        # Additional check: if result is empty but audio file exists and has content
        if not result and os.path.exists(audio_file_path):
            file_size = os.path.getsize(audio_file_path)
            if file_size > 1000:  # If file has reasonable size but no transcription
                print(f"⚠️ Audio file size: {file_size} bytes, but no speech detected")
                print(f"⚠️ Detected language: {info.language if hasattr(info, 'language') else 'unknown'}")
                print(f"⚠️ Language probability: {info.language_probability if hasattr(info, 'language_probability') else 'unknown'}")
        
        return result
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return ""


def get_speaking_activity_feedback(audio_file_path, original_sentence):
    if not api_key:
        return "⚠️ OpenAI not configured."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)  # ✅ Initialize here

        # Step 1: Fast local transcription
        user_text = get_transcription(audio_file_path)

        if not user_text:
            return "🔈 Aapne kuch bola nahi. Kripya bolne ki koshish kijiye taki main aapki madad kar sakoon. 😊"

        # Step 2: Compare similarity (optional but useful)
        similarity = SequenceMatcher(None, original_sentence.lower(), user_text.lower()).ratio()

        # Step 3: Ask GPT to improve sentence
        correction_prompt = f"""
You are a pronunciation corrector.

Original sentence: "{original_sentence}"
Student's version: "{user_text}"

Return only the corrected sentence in American English.
Do not add any explanation.
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an American English pronunciation corrector."},
                {"role": "user", "content": correction_prompt}
            ]
        )
        corrected_sentence = response.choices[0].message.content.strip()

        # Step 4: Speak corrected sentence
        async def speak(text):
            communicate = edge_tts.Communicate(text=text, voice="en-US-AriaNeural")
            await communicate.save("output.mp3")
            playsound("output.mp3")

        asyncio.run(speak(corrected_sentence))



    except Exception as e:
        return f"⚠️ Speaking feedback error: {e}"


from difflib import SequenceMatcher, ndiff

def get_highlighted_mispronunciations(audio_file_path, original_sentence):
    user_text = get_transcription(audio_file_path)

    if not user_text.strip():
        # 🟥 Case 2: User silent
        return (
            "😶 Aapne kuch nahi bola.",
            "Aapne kuch nahi bola. Bindaas boliye, main aapki madad karne ke liye yahan hoon!"
        )

    # Check if user text is too different
    similarity = SequenceMatcher(None, original_sentence.lower(), user_text.lower()).ratio()
    if similarity < 0.4:
        # 🟥 Case 1: Unrelated sentence
        return (
            "🔁 Alag sentence bola.",
            "Aapne kuch alag bola hai. Pehle sentence ko dhyan se suniye, phir usi ko bolne ki koshish kijiye."
        )

    # 🟩 Case 3: Compare words for pronunciation correction
    original_words = original_sentence.lower().split()
    user_words = user_text.lower().split()
    diff = list(ndiff(original_words, user_words))

    mispronounced = []
    for word in diff:
        if word.startswith("- "):  # word expected but not matched
            mispronounced.append(word[2:])

    if not mispronounced:
        return (
            "✅ Bahut badiya! Sab shabd sahi bole.",
            "Shandar! Aapne sab kuch sahi bola."
        )

    # Create spoken correction
    explanation = "Chaliye kuch shabdon ko sahi karte hain: " + ", ".join(mispronounced) + "."
    repeat_line = "Repeat after me: " + ", ".join(mispronounced) + "."
    spoken_guide = explanation + " " + repeat_line

    return (", ".join(mispronounced), spoken_guide)


def get_friendly_pronunciation_feedback(audio_file_path, original_sentence):
    """
    Always gives friendly, encouraging feedback to users.
    Even if analysis is incorrect, it provides positive guidance.
    This function focuses on user encouragement and gentle correction.
    """
    user_text = get_transcription(audio_file_path)
    
    # Case 1: Silent input
    if not user_text or not user_text.strip():
        return {
            "status": "silent",
            "feedback": "🎤 Koi baat nahi! Thoda aur confidence ke saath boliye. Main yahan aapki madad ke liye hun!",
            "user_text": "",
            "encouragement": "Aap bilkul sahi kar rahe hain. Bas ek baar aur try kijiye!"
        }
    
    # Calculate similarity
    similarity = SequenceMatcher(None, original_sentence.lower(), user_text.lower()).ratio()
    
    # Check for key word differences (like day vs night)
    original_words = set(original_sentence.lower().split())
    user_words = set(user_text.lower().split())
    
    # Find important word differences
    missing_words = original_words - user_words
    extra_words = user_words - original_words
    
    # Case 2: Very different sentence
    if similarity < 0.3:
        return {
            "status": "different",
            "feedback": f"🌟 Aapne koshish ki, ye bahut acchi baat hai! Ab iss sentence ko try karte hain: '{original_sentence}'",
            "user_text": user_text,
            "encouragement": "Practice makes perfect! Aap bilkul sahi direction mein hain."
        }
    
    # Case 3: Check for important word substitutions (even with high similarity)
    if missing_words and extra_words:
        # Check if there are meaningful word differences
        important_differences = False
        for missing in missing_words:
            for extra in extra_words:
                # If words are very different (not just pronunciation variants)
                if SequenceMatcher(None, missing, extra).ratio() < 0.5:
                    important_differences = True
                    break
        
        if important_differences:
            return {
                "status": "word_error",
                "feedback": f"👀 Dhyan se suniye! Aapne '{', '.join(extra_words)}' bola hai, lekin sentence mein '{', '.join(missing_words)}' hona chahiye. Ek baar aur try karte hain!",
                "user_text": user_text,
                "encouragement": "Bilkul sahi direction mein hain! Bas thoda dhyan dena hai."
            }
    
    # Case 4: Good attempt but needs improvement
    if similarity < 0.8:
        # Find some words that might need work
        return {
            "status": "improving",
            "feedback": f"👏 Bahut accha! Aapka pronunciation improve ho raha hai. Thoda aur practice karte hain: '{original_sentence}'",
            "user_text": user_text,
            "encouragement": "Aap sahi raah par hain! Keep going!"
        }
    
    # Case 5: Good pronunciation (similarity >= 0.8)
    if similarity >= 0.8:
        encouraging_messages = [
            "🎉 Excellent! Aapka pronunciation bahut accha hai!",
            "✨ Wonderful! Aap bilkul sahi bol rahe hain!",
            "🌟 Perfect! Aapne bahut accha kiya!",
            "👍 Great job! Aapka confidence badh raha hai!",
            "🔥 Amazing! Aap expert ban rahe hain!"
        ]
        
        import random
        selected_message = random.choice(encouraging_messages)
        
        return {
            "status": "excellent",
            "feedback": selected_message,
            "user_text": user_text,
            "encouragement": "Aap bahut accha kar rahe hain! Next sentence ke liye ready?"
        }
    
    # Fallback - Always positive
    return {
        "status": "good_effort",
        "feedback": "💪 Bahut acchi koshish! Aap sahi direction mein hain. Ek baar aur try karte hain!",
        "user_text": user_text,
        "encouragement": "Har koshish aapko better banati hai. Keep it up!"
    }


def get_speaking_activity_feedback1(audio_file_path):
    """
    Analyze a user's spoken recording and give feedback on:
    - Grammar
    - Pronunciation
    - Fluency
    - Sentence formation
    - Suggestions for improvement
    """

    if not api_key:
        return "⚠️ OpenAI not configured."

    try:
        client = openai.OpenAI(api_key=api_key)

        # Step 1: Transcribe audio (use Whisper model)
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",  # or "whisper-1"
                file=audio_file
            )
        user_text = transcription.text.strip()

        # Step 2: Ask GPT to analyze the speech
        prompt = f"""
You are a spoken English teacher evaluating a student's SPEAKING activity.

The student said (transcribed):
"{user_text}"

Provide feedback in English:
Sentence formation (suggest improved sentences)
Grammar errors (list them and fixes)
Pronunciation issues (words, syllables, stress)
Fluency (pauses, speed, naturalness)

Keep it structured, easy to understand, and motivating.
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Better for nuanced feedback
            messages=[
                {"role": "system", "content": "You are a supportive spoken English teacher."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"⚠️ Speaking feedback error: {e}"
def get_pronunciation_feedback(user_input):
    if not api_key:
        return "⚠️ OpenAI not configured."
    prompt = f"""
You are a pronunciation coach. A user said:
"{user_input}"

Give English feedback:
1. Words mispronounced (in quotes)
2. Syllables to improve
3. Encourage the user
"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful English pronunciation coach."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Feedback error: {e}"


def get_grammar_mcqs(topic):
    if not topic or not api_key:
        return []

    prompt = f"""
You are an English grammar teacher.

Create 5 multiple choice questions (MCQs) for the topic: "{topic}".

Each question should include:
1. A question string
2. Four answer options (A, B, C, D)
3. The correct answer letter (A/B/C/D)
4. Return output as a JSON list of dictionaries with keys:
   'question', 'options', and 'answer'

Only return JSON, no extra explanation.
"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful English grammar MCQ generator."},
                {"role": "user", "content": prompt}
            ]
        )
        raw_output = response.choices[0].message.content.strip()

        # Try to extract JSON from the raw response
        try:
            if raw_output.startswith("```json"):
                raw_output = raw_output.split("```json")[1].split("```")[0].strip()
            elif raw_output.startswith("```"):
                raw_output = raw_output.split("```")[1].strip()

            mcqs = json.loads(raw_output)
            return mcqs if isinstance(mcqs, list) else []

        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
            print("⚠️ Raw response was:\n", raw_output)
            return []

    except Exception as e:
        print("❌ OpenAI API call failed:", e)
        return []


def get_grammar_explanation(topic):
    if not api_key:
        return "⚠️ OpenAI not configured."

    prompt = f"""
Explain this grammar question's answer in Hinglish in detail with 7-10 examples and make sentences:
Topic: "{topic}"
Keep it beginner-friendly.
"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a grammar expert who explains topics in Hinglish with examples."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Grammar explanation error: {e}"


def get_vocabulary_feedback(text):
    if not api_key:
        return "⚠️ OpenAI not configured."
    prompt = f"""
The user wrote the following vocabulary response:
"{text}"

Give feedback in English:
1. Spelling errors
2. Correctness of words
3. Number of valid words out of 5
4. Motivational comment
"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an English vocabulary evaluator."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Vocabulary feedback error: {e}"


def get_writing_feedback(text):
    if not api_key:
        return "⚠️ OpenAI not configured."
    prompt = f"""
Analyze this writing assignment:
"{text}"

Give feedback in Hinglish:
1. Grammar
2. Spelling
3. Sentence structure
4. Motivation
"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly writing evaluator."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Writing feedback error: {e}"


def get_listening_feedback(count):
    if count >= 10:
        return "✅ Excellent! You understood the listening passage very well."
    elif count >= 5:
        return "👍 Good attempt! Try focusing more on key details."
    elif count >= 3:
        return "🙂 You caught something, but try to improve your focus."
    else:
        return "⚠️ You should listen more."


def improve_response_for_resume(field_name, user_input, category=None):
    if not api_key:
        return "⚠️ OpenAI not configured."

    prompt = f"""
You are a resume writing assistant.

A user entered this value for the field "{field_name}":
"{user_input}"

1. Convert Hinglish to English if needed.
2. Improve grammar and professionalism for resumes.
3. Capitalize proper nouns (like names, companies).
4. Use full form instead of short informal words.
5. Use full sentences instead of fragments.
6. Ensure clarity and conciseness.
7. Use full forms instead of abbreviations.
8. consider user is an indian and use Indian english conventions.
Give only the improved response, no explanation no field name.
"""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional resume helper."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"⚠️ Resume improvement error: {e}"


def get_professional_examples_for_field(field_name, user_input=None, user_info=None, category=None):
    base_examples = {
        "Job Title": [
            "Software Engineer Intern at XYZ Ltd",
            "Marketing Executive - Digital Campaigns",
            "Primary School Teacher (CBSE)"
        ],
        "Education": [
            "B.Tech in Computer Science, Delhi University (2022)",
            "MBA - Marketing, IIM Bangalore (2023)"
        ],
        "Certifications": [
            "AWS Certified Cloud Practitioner",
            "Google Analytics Certified",
            "IELTS 7.5 Band"
        ],
        "Experience": [
            "Worked as Software Intern at ABC Corp (6 months)",
            "Handled classroom of 40 students (Teaching Assistant)"
        ],
        "Skills": [
            "Python, SQL, Data Analysis",
            "Communication, Leadership, Problem Solving"
        ],
        "Achievements": [
            "Increased sales by 20% within 6 months",
            "Awarded 'Best Employee of the Month'"
        ],
        "Projects": [
            "Developed an E-commerce website using Django",
            "Built a Marketing Strategy Plan for a startup"
        ]
    }

    examples = base_examples.get(field_name, [])

    if category:
        if "IT" in category:
            examples.append("Contributed to open-source Python libraries")
        elif "Teaching" in category:
            examples.append("Designed interactive lesson plans for Grade 8")
        elif "Marketing" in category:
            examples.append("Managed 5-member social media team")

    try:
        prompt = f"""
Suggest 3 concise, professional examples for resume field "{field_name}".
Category: {category or 'General'}.
User context: {user_info or 'N/A'}.
Current input: {user_input or 'N/A'}.
Keep each example max 12 words. Separate by |.
"""
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a resume suggestion generator."},
                {"role": "user", "content": prompt}
            ]
        )
        text = response.choices[0].message.content.strip()
        if text:
            return text
    except Exception:
        pass

    return "|".join(examples if examples else ["No examples found"])


def analyze_tone_and_grammar(text):
    if not api_key:
        return "⚠️ OpenAI not configured."
    if not text.strip():
        return ""

    prompt = f"""
Analyze the following resume text:
"{text}"

Give a one-line feedback:
1. Is the tone professional?
2. Is the grammar correct?
3. If something can be improved, suggest a short fix.

Keep the response short (max 20 words).
"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a resume grammar and tone checker."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Grammar feedback error: {e}"


def get_ai_career_suggestion(user_info, lang="english"):
    if not api_key:
        return "⚠️ OpenAI not configured."

    client = openai.OpenAI(api_key=api_key)

    prompt_parts = []
    for key, val in user_info.items():
        prompt_parts.append(f"{key}: {val.strip()}")

    lang_instruction = {
        "english": "Respond in English only.",
        "hindi": "Answer fully in Hindi only.",
        "french": "Répondez uniquement en français."  # French prompt
    }.get(lang.lower(), "Respond in English only.")

    prompt = (
        "Act like a world-class career coach. Based on the following user details, "
        "give a highly personalized, motivating, and expert-level career suggestion.\n\n"
        "- If user is a fresher: suggest trending roles, required skills, and learning path.\n"
        "- If experienced: recommend job titles, industry trends, upskilling, and motivation.\n"
        "- Avoid repeating generic tips. Provide fresh and creative suggestions.\n"
        f"{lang_instruction}\n\n"
        + "\n".join(prompt_parts)
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a multilingual expert career advisor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI Suggestion Error: {e}")
        return "AI suggestion failed. Please try again."

