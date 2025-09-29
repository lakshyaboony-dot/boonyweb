import random
from services.ai_guide import (
    get_welcome_message, 
    get_congratulation_message, 
    get_guidance_message,
    generate_signup_guide
)

class BoonyGuide:
    """AI Guide system for Boony application"""
    
    def __init__(self, language="hinglish"):
        """Initialize with default language preference"""
        self.language = language.lower()
        
    def set_language(self, language):
        """Update the guide language preference"""
        self.language = language.lower()
        
    def get_welcome_message(self, section="general", context=None):
        """Get welcome message for different sections"""
        if section == "login":
            return get_guidance_message("login", self.language)
        elif section == "signup":
            return get_guidance_message("signup", self.language)
        elif section == "dashboard":
            return get_guidance_message("dashboard", self.language)
        else:
            return get_welcome_message(self.language)
        
    def welcome_user(self, user_name=None, is_returning=False):
        """Generate personalized welcome message"""
        base_message = get_welcome_message(self.language)
        
        if user_name:
            if self.language == "english":
                if is_returning:
                    return f"👋 Welcome back, {user_name}! {base_message}"
                else:
                    return f"🎉 Hello {user_name}! {base_message}"
            else:
                if is_returning:
                    return f"👋 Welcome back, {user_name}! {base_message}"
                else:
                    return f"🎉 Namaste {user_name}! {base_message}"
        
        return base_message
    
    def congratulate_user(self, achievement_type="lesson_complete", details=None):
        """Generate congratulatory message for user achievements"""
        message = get_congratulation_message(achievement_type, self.language)
        
        # Add specific details if provided
        if details:
            if self.language == "english":
                message += f" {details}"
            else:
                message += f" {details}"
                
        return message
    
    def guide_user(self, section="dashboard", context=None):
        """Provide contextual guidance for different app sections"""
        base_guidance = get_guidance_message(section, self.language)
        
        # Add context-specific information
        if context:
            if section == "lesson" and "lesson_name" in context:
                if self.language == "english":
                    base_guidance += f" Today's lesson: {context['lesson_name']}"
                else:
                    base_guidance += f" Aaj ka lesson: {context['lesson_name']}"
                    
            elif section == "practice" and "practice_type" in context:
                if self.language == "english":
                    base_guidance += f" Focus on: {context['practice_type']}"
                else:
                    base_guidance += f" Focus: {context['practice_type']}"
        
        return base_guidance
    
    def get_encouragement(self, situation="general"):
        """Get encouraging messages for different situations"""
        encouragements = {
            "english": {
                "general": [
                    "💪 You're doing great! Keep practicing!",
                    "🌟 Every step forward is progress!",
                    "🚀 You're improving every day!",
                    "⭐ Keep up the excellent work!",
                    "🎯 You're on the right track!"
                ],
                "practice": [
                    "🎤 Great job practicing! Your confidence is growing!",
                    "📈 Each practice session makes you stronger!",
                    "🏆 Practice makes perfect - you're doing amazing!",
                    "🌱 Your speaking skills are blooming!",
                    "💫 Keep practicing, you're getting better!"
                ],
                "progress": [
                    "📊 Amazing progress! You're on fire!",
                    "🚀 Look how far you've come!",
                    "⭐ Your hard work is paying off!",
                    "🏆 Incredible improvement! Keep going!"
                ]
            },
            "hinglish": {
                "general": [
                    "💪 Bahut badhiya! Practice karte rahiye!",
                    "🌟 Har kadam aage progress hai!",
                    "🚀 Aap har din improve kar rahe hain!",
                    "⭐ Excellent work! Continue karte rahiye!",
                    "🎯 Aap bilkul sahi raah par hain!"
                ],
                "practice": [
                    "🎤 Practice mein great job! Confidence badh raha hai!",
                    "📈 Har practice session aapko strong banata hai!",
                    "🏆 Practice se perfect bante hain - amazing kar rahe hain!",
                    "🌱 Aapki speaking skills bloom kar rahi hain!",
                    "💫 Practice karte rahiye, better ho rahe hain!"
                ],
                "mistakes": [
                    "🌱 Galtiyon se seekhna humein strong banata hai!"
                ],
                "progress": [
                    "📈 Amazing progress! Aap fire par hain!",
                    "🚀 Dekho kitna aage aa gaye hain!",
                    "⭐ Aapki mehnat rang la rahi hai!",
                    "🏆 Incredible improvement! Keep going!"
                ]
            }
        }
        
        lang = self.language if self.language in encouragements else "hinglish"
        situation = situation if situation in encouragements[lang] else "general"
        
        return random.choice(encouragements[lang][situation])
    
    def get_tip_of_the_day(self):
        """Get daily English learning tips"""
        tips = {
            "english": [
                "💡 Tip: Practice speaking for just 5 minutes daily!",
                "🎯 Tip: Record yourself speaking and listen back!",
                "📚 Tip: Learn 3 new words every day!",
                "🗣️ Tip: Speak to yourself in English while doing daily tasks!",
                "🎵 Tip: Listen to English songs and try to sing along!",
                "📺 Tip: Watch English videos with subtitles!",
                "🤝 Tip: Find a speaking partner to practice with!"
            ],
            "hinglish": [
                "💡 Tip: Roz sirf 5 minute speaking practice kariye!",
                "🎯 Tip: Apni awaaz record karke wapas suniye!",
                "📚 Tip: Har din 3 naye words seekhiye!",
                "🗣️ Tip: Daily kaam karte waqt English mein baat kariye!",
                "🎵 Tip: English songs suno aur saath mein gaane ki koshish kariye!",
                "📺 Tip: English videos subtitles ke saath dekhiye!",
                "🤝 Tip: Practice ke liye koi speaking partner dhundiye!"
            ]
        }
        
        lang = self.language if self.language in tips else "hinglish"
        return random.choice(tips[lang])
        
    def get_daily_tip(self):
        """Alias for get_tip_of_the_day for backward compatibility"""
        return self.get_tip_of_the_day()
        
    def get_encouragement_message(self, context=None):
        """Get encouragement message based on user context"""
        if context:
            if context.get('listen_done') and context.get('speak_done'):
                return self.get_encouragement('progress')
            elif context.get('is_practice_mode'):
                return self.get_encouragement('practice')
            else:
                return self.get_encouragement('general')
        return self.get_encouragement('general')
        
    def get_congratulatory_message(self, achievement_type="task_completion", context=None):
        """Get congratulatory message for achievements"""
        return self.congratulate_user(achievement_type, context.get('details') if context else None)
        
    def get_guidance_message(self, section="general"):
        """Get guidance message for different sections"""
        return self.guide_user(section)
    
    def get_navigation_help(self, current_page="dashboard"):
        """Provide navigation assistance"""
        nav_help = {
            "english": {
                "dashboard": "🏠 You're on the main dashboard. Choose any lesson or practice session to start!",
                "lesson": "📖 You're in a lesson. Follow the instructions and practice speaking!",
                "practice": "🎯 You're in practice mode. Speak clearly and get instant feedback!",
                "profile": "👤 Update your profile settings and preferences here!",
                "login": "🔐 Enter your login details to access your learning dashboard!",
                "signup": "📝 Fill in your details to create your Boony account!"
            },
            "hinglish": {
                "dashboard": "🏠 Aap main dashboard par hain. Koi bhi lesson ya practice session choose kariye!",
                "lesson": "📖 Aap lesson mein hain. Instructions follow kariye aur speaking practice kariye!",
                "practice": "🎯 Aap practice mode mein hain. Saaf boliye aur instant feedback paiye!",
                "profile": "👤 Yahan apni profile settings aur preferences update kariye!",
                "login": "🔐 Apne login details enter karke learning dashboard access kariye!",
                "signup": "📝 Apni details fill karke Boony account banayiye!"
            }
        }
        
        lang = self.language if self.language in nav_help else "hinglish"
        page = current_page if current_page in nav_help[lang] else "dashboard"
        
        return nav_help[lang][page]
    
    def get_motivational_quote(self):
        """Get motivational quotes for inspiration"""
        quotes = {
            "english": [
                "🌟 'The expert in anything was once a beginner.' - Helen Hayes",
                "🚀 'Success is the sum of small efforts repeated day in and day out.' - Robert Collier",
                "💪 'Don't watch the clock; do what it does. Keep going.' - Sam Levenson",
                "🎯 'The only way to do great work is to love what you do.' - Steve Jobs",
                "⭐ 'Believe you can and you're halfway there.' - Theodore Roosevelt"
            ],
            "hinglish": [
                "🌟 'Har expert kabhi beginner tha.' - Helen Hayes",
                "🚀 'Success choti choti mehnat ka sum hai jo roz repeat hoti hai.' - Robert Collier",
                "💪 'Clock ko dekhna mat; woh jo karta hai woh karo. Chalte raho.' - Sam Levenson",
                "🎯 'Great work ka only way hai jo kaam aap love karte hain.' - Steve Jobs",
                "⭐ 'Believe karo ki aap kar sakte hain aur aap halfway pahunch gaye.' - Theodore Roosevelt"
            ]
        }
        
        lang = self.language if self.language in quotes else "hinglish"
        return random.choice(quotes[lang])

# Global instance
boony_guide = BoonyGuide()

# Helper functions for quick access
def get_boony_guide(language="hinglish"):
    """Get a BoonyGuide instance with specified language"""
    guide = BoonyGuide(language)
    return guide

def quick_welcome(user_name=None, language="hinglish", is_returning=False):
    """Quick welcome message generation"""
    guide = BoonyGuide(language)
    return guide.welcome_user(user_name, is_returning)

def quick_congratulate(achievement="lesson_complete", language="hinglish", details=None):
    """Quick congratulation message generation"""
    guide = BoonyGuide(language)
    return guide.congratulate_user(achievement, details)

def quick_guide(section="dashboard", language="hinglish", context=None):
    """Quick guidance message generation"""
    guide = BoonyGuide(language)
    return guide.guide_user(section, context)