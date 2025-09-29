import json
import os
from openai import OpenAI
from .resource_helper import resource_path  # ensures correct path in exe or script

# Load API key from core/config.json
try:
    config_path = resource_path("core/config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    OPENAI_API_KEY = config.get("openai_api_key", "").strip()
except Exception as e:
    raise RuntimeError(f"⚠️ Could not read OpenAI API key from config.json: {e}")

if not OPENAI_API_KEY:
    raise RuntimeError("⚠️ openai_api_key missing in core/config.json")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def get_openai_client():
    """
    Returns the configured OpenAI client instance
    """
    return client

def call_openai(
    messages,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 1000
):
    """
    Sends messages to OpenAI and returns the completion text.

    Args:
        messages (list): Chat messages as a list of dicts.
        model (str): Model to use (default = gpt-4o-mini)
        temperature (float): Randomness in response
        max_tokens (int): Maximum tokens in output

    Returns:
        str: AI response text
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ call_openai failed: {e}")
        return "No response from AI."


# ===========================
# 🔹 10 Ready-made Tutor Prompts
# ===========================

ENGLISH_TUTOR_PROMPTS = {
    # =====================
    # 🔹 Beginner (20 Topics)
    # =====================
    "beginner_greetings": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Teach basic greetings like 'Hello, how are you?', 'Good morning'. Correct common mistakes."}
    ],
    "beginner_self_intro": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Help students introduce themselves with name, age, city. Example: 'I am Ramesh. I am 12 years old. I live in Delhi'."}
    ],
    "beginner_family": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Create a conversation about family members. Example: 'This is my father. He is a teacher'."}
    ],
    "beginner_school": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Make a conversation about school life: subjects, teachers, friends."}
    ],
    "beginner_daily_routine": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Guide students to speak about daily routine. Example: 'I wake up at 7 am. I go to school at 8 am'."}
    ],
    "beginner_food": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Conversation about food: favorite dish, asking 'What do you like to eat?'."}
    ],
    "beginner_colors": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Teach colors through conversation. Example: 'What is your favorite color?' → 'My favorite color is blue'."}
    ],
    "beginner_numbers": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Simple conversation about numbers and counting. Example: 'How many pens do you have?' → 'I have three pens'."}
    ],
    "beginner_weather": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Make conversation about weather. Example: 'It is sunny today'."}
    ],
    "beginner_shopping": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Create a simple shopping role-play. 'How much is this?' → 'It is 50 rupees'."}
    ],
    "beginner_transport": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Conversation about bus, train, or cycle. Example: 'I go to school by bus'."}
    ],
    "beginner_animals": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Conversation about animals. Example: 'Do you like dogs?' → 'Yes, I like dogs'."}
    ],
    "beginner_friends": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Role-play about making friends. 'What is your name?' → 'My name is Anu'."}
    ],
    "beginner_games": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Talk about games: 'Do you play cricket?' → 'Yes, I play cricket'."}
    ],
    "beginner_hobbies": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Conversation about hobbies. Example: 'I like singing'."}
    ],
    "beginner_body_parts": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Talk about body parts. 'This is my hand. These are my eyes'."}
    ],
    "beginner_classroom": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Conversation inside classroom. 'May I come in?' 'Yes, please sit down'."}
    ],
    "beginner_fruits": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Talk about fruits. 'Do you like apples?' → 'Yes, I like apples'."}
    ],
    "beginner_festivals": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Simple talk about festivals. Example: 'Diwali is the festival of lights'."}
    ],
    "beginner_polite_words": [
        {"role": "system", "content": "You are a friendly English Spoken Tutor."},
        {"role": "user", "content": "Teach polite words like Please, Thank you, Sorry in conversations."}
    ],

    # =====================
    # 🔹 Intermediate (20 Topics)
    # =====================
    "intermediate_travel": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about planning a trip: booking tickets, asking directions."}
    ],
    "intermediate_restaurant": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Role-play ordering food in a restaurant: 'Can I have a pizza, please?'."}
    ],
    "intermediate_doctor": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation with doctor: 'I have a fever'. Doctor gives advice."}
    ],
    "intermediate_bank": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Simple conversation in a bank: opening an account, depositing money."}
    ],
    "intermediate_market": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Role-play buying vegetables in the market. Bargaining practice."}
    ],
    "intermediate_cinema": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about buying movie tickets and discussing films."}
    ],
    "intermediate_post_office": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about posting a letter or parcel."}
    ],
    "intermediate_phone_call": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Practice making a phone call to a friend or office."}
    ],
    "intermediate_invitation": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about inviting a friend to a birthday party."}
    ],
    "intermediate_sharing_opinion": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Practice expressing opinions: 'I think…', 'In my opinion…'."}
    ],
    "intermediate_trains": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Role-play buying a train ticket and asking about timings."}
    ],
    "intermediate_airport": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation at airport: check-in, boarding."}
    ],
    "intermediate_directions": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Practice asking and giving directions on the street."}
    ],
    "intermediate_holiday_plan": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about planning holidays with friends."}
    ],
    "intermediate_library": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation in a library: asking for books, issuing books."}
    ],
    "intermediate_sports": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Talk about sports matches, favorite players."}
    ],
    "intermediate_sharing_experience": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about a past trip or festival experience."}
    ],
    "intermediate_room_booking": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Practice booking a hotel room: 'I need a single room for two nights'."}
    ],
    "intermediate_social_media": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Talk about using WhatsApp, Instagram, or Facebook."}
    ],
    "intermediate_future_plan": [
        {"role": "system", "content": "You are a supportive English Tutor."},
        {"role": "user", "content": "Conversation about future dreams: 'I want to become a doctor'."}
    ],

    # =====================
    # 🔹 Advanced (20 Topics)
    # =====================
    "advanced_interview": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Role-play for a job interview: self-introduction, strengths, weaknesses."}
    ],
    "advanced_group_discussion": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Conversation practice for group discussion: education system, technology."}
    ],
    "advanced_debate": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Debate on topics like 'Mobile phones are useful or harmful'."}
    ],
    "advanced_storytelling": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Narrate a story in English. Encourage use of past tense and descriptive words."}
    ],
    "advanced_presentation": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Practice giving a short presentation on environment, health, or education."}
    ],
    "advanced_technology": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Conversation about AI, internet, and modern technology impact."}
    ],
    "advanced_environment": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Talk about global warming, pollution, and solutions."}
    ],
    "advanced_career_plan": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Discuss career plans: 'I want to work in IT sector because…'."}
    ],
    "advanced_healthcare": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Conversation on healthcare system, importance of fitness."}
    ],
    "advanced_travel_abroad": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Talk about traveling abroad, visa, culture differences."}
    ],
    "advanced_public_speaking": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Practice public speaking on stage with confidence tips."}
    ],
    "advanced_ethics": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Conversation about ethics, honesty, moral values."}
    ],
    "advanced_science_fiction": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Create a conversation about future robots and space travel."}
    ],
    "advanced_business_meeting": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Role-play a business meeting: sharing ideas, making decisions."}
    ],
    "advanced_social_issues": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Discuss social issues: poverty, gender equality."}
    ],
    "advanced_media": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Conversation about role of media in society."}
    ],
    "advanced_future_goals": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Discuss long-term goals and ambitions in life."}
    ],
    "advanced_culture_exchange": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Talk about Indian culture vs western culture exchange."}
    ],
    "advanced_globalization": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Discuss globalization, trade, and world economy impact."}
    ],
    "advanced_inspiration": [
        {"role": "system", "content": "You are an advanced English Mentor."},
        {"role": "user", "content": "Conversation about inspirational people and role models."}
    ]
}

