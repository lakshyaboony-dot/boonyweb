# services/ai_guide.py
import openai
import random
from services.load_config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

# Predefined messages for better performance and consistency
WELCOME_MESSAGES = {
    "english": [
        "🎉 Welcome to Boony! Let's start your English speaking journey together!",
        "✨ Hello there! Ready to become confident in English? I'm here to guide you!",
        "🌟 Welcome aboard! Your English fluency adventure begins now!",
        "👋 Hi! I'm Boony, your AI guide. Let's make English speaking fun and easy!"
    ],
    "hinglish": [
        "🎉 Boony mein aapka swagat hai! Chalo English bolna sikhte hain saath mein!",
        "✨ Namaste! English mein confident banne ke liye ready hain? Main aapki madad karunga!",
        "🌟 Welcome! Aapka English fluency ka safar ab shuru hota hai!",
        "👋 Hi! Main Boony hun, aapka AI guide. English bolna aasan aur mazedaar banate hain!"
    ]
}

CONGRATULATION_MESSAGES = {
    "english": {
        "signup_complete": [
            "🎊 Fantastic! Your account is ready. Time to start speaking!",
            "✅ Excellent! Welcome to the Boony family. Let's begin your journey!",
            "🌟 Amazing! You're all set. Ready for your first English lesson?"
        ],
        "lesson_complete": [
            "🎉 Well done! You completed another lesson. Keep it up!",
            "👏 Excellent progress! You're getting better every day!",
            "⭐ Great job! Your English is improving with each practice!"
        ],
        "milestone": [
            "🏆 Congratulations! You've reached a new milestone!",
            "🎯 Amazing achievement! You're becoming more fluent!",
            "💪 Superb! Your dedication is paying off!"
        ]
    },
    "hinglish": {
        "signup_complete": [
            "🎊 Zabardast! Aapka account ready hai. Ab bolna shuru karte hain!",
            "✅ Excellent! Boony family mein aapka swagat hai. Safar shuru karte hain!",
            "🌟 Amazing! Sab set hai. Pehle English lesson ke liye ready hain?"
        ],
        "lesson_complete": [
            "🎉 Bahut badhiya! Ek aur lesson complete kiya. Keep it up!",
            "👏 Excellent progress! Aap roz better ho rahe hain!",
            "⭐ Great job! Har practice se aapki English improve ho rahi hai!"
        ],
        "milestone": [
            "🏆 Congratulations! Aapne naya milestone achieve kiya!",
            "🎯 Amazing achievement! Aap fluent bante ja rahe hain!",
            "💪 Superb! Aapki mehnat rang la rahi hai!"
        ]
    }
}

GUIDANCE_MESSAGES = {
    "english": {
        "login": "Enter your credentials to continue your English learning journey!",
        "signup": "Let's create your account and start speaking English confidently!",
        "dashboard": "Welcome back! Choose a lesson or practice session to continue learning.",
        "lesson": "Listen carefully, repeat after me, and don't worry about mistakes!",
        "practice": "Practice makes perfect! Speak clearly and I'll give you feedback.",
        "profile": "Update your preferences to personalize your learning experience."
    },
    "hinglish": {
        "login": "Apne credentials enter karke English learning journey continue karein!",
        "signup": "Account banate hain aur confident English bolna shuru karte hain!",
        "dashboard": "Welcome back! Koi lesson ya practice session choose karke learning continue karein.",
        "lesson": "Dhyan se suniye, mere saath repeat kariye, aur galtiyon ki chinta na kariye!",
        "practice": "Practice se perfect hota hai! Saaf boliye, main feedback dunga.",
        "profile": "Apni preferences update karke learning experience personalize kariye."
    }
}

def get_welcome_message(language="hinglish"):
    """Get a random welcome message in specified language"""
    lang = language.lower()
    if lang not in WELCOME_MESSAGES:
        lang = "hinglish"
    return random.choice(WELCOME_MESSAGES[lang])

def get_congratulation_message(message_type="lesson_complete", language="hinglish"):
    """Get a congratulation message for specific achievement"""
    lang = language.lower()
    if lang not in CONGRATULATION_MESSAGES:
        lang = "hinglish"
    
    if message_type not in CONGRATULATION_MESSAGES[lang]:
        message_type = "lesson_complete"
    
    return random.choice(CONGRATULATION_MESSAGES[lang][message_type])

def get_guidance_message(section="dashboard", language="hinglish"):
    """Get contextual guidance for different app sections"""
    lang = language.lower()
    if lang not in GUIDANCE_MESSAGES:
        lang = "hinglish"
    
    if section not in GUIDANCE_MESSAGES[lang]:
        section = "dashboard"
    
    return GUIDANCE_MESSAGES[lang][section]

def generate_signup_guide(step, user_context=None, language="hinglish"):
    """Generate dynamic signup guidance using AI"""
    context_text = ""
    if user_context:
        context_text = "User has entered: " + ", ".join(f"{k}={v}" for k,v in user_context.items())

    # Language-specific prompts
    if language.lower() == "english":
        system_prompt = "You are Boony, a friendly AI English tutor. Give encouraging, short guidance in English only."
        user_prompt = f"""
        You are guiding a user through signup step {step}.
        {context_text}
        Give a short, encouraging instruction (20-40 words max) in English.
        Be friendly, supportive, and motivating.
        """
    else:
        system_prompt = "You are Boony, a friendly AI English tutor. Give encouraging, short guidance in Hinglish (Hindi + English mix)."
        user_prompt = f"""
        You are guiding a user through signup step {step}.
        {context_text}
        Give a short, encouraging instruction (20-40 words max) in Hinglish.
        Be friendly, supportive, and motivating. Use Hindi-English mix naturally.
        """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        guide_text = response.choices[0].message["content"].strip()
        return guide_text
    except Exception as e:
        print("⚠️ AI guide error:", e)
        # Fallback messages
        fallback = {
            "english": "Please follow the instructions on screen. You're doing great!",
            "hinglish": "Screen par instructions follow kariye. Aap bahut accha kar rahe hain!"
        }
        return fallback.get(language.lower(), fallback["hinglish"])
