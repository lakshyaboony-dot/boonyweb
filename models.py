from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from sqlalchemy import types


class UUIDOrString(types.TypeDecorator):
    """Use PostgreSQL UUID when available, else fallback to CHAR(36) for SQLite."""
    impl = types.CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(types.CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            # PostgreSQL me UUID object allow hai, SQLite me string chahiye
            return value if dialect.name == 'postgresql' else str(value)
        try:
            u = uuid.UUID(str(value))
            return u if dialect.name == 'postgresql' else str(u)
        except Exception:
            # agar value galat ho to naya UUID generate karo
            u = uuid.uuid4()
            return u if dialect.name == 'postgresql' else str(u)


    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    # Supabase-aligned primary key
    user_id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)

    # Web login/display fields
    username = db.Column(db.String(150), unique=True)
    email = db.Column(db.String(150), unique=True)
    full_name = db.Column(db.String(150))

    # Optional local auth (if using Flask login locally)
    password_hash = db.Column(db.String(255))

    mobile = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    state = db.Column(db.String(100))
    city = db.Column(db.String(100))

    gender = db.Column(db.String(20), default="Male")
    voice  = db.Column(db.String(20), default="Male")
    language = db.Column(db.String(20), default="hinglish")
    photo = db.Column(db.String(255))  # Store uploaded photo filename

    created_at = db.Column(db.DateTime, server_default=func.now())

    progresses = db.relationship("Progress", backref="user", lazy=True, cascade="all, delete-orphan")
    surveys = db.relationship("UserSurvey", backref="user", lazy=True, cascade="all, delete-orphan")

    def get_id(self):
        # Flask-Login uses this; return as string
        return str(self.user_id)

    def __repr__(self):
        return f"<User {self.username or self.email or self.full_name}>"


class Progress(db.Model):
    __tablename__ = "progress"

    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUIDOrString, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    day = db.Column(db.String(50), nullable=False)
    listen = db.Column(db.Integer, default=0)
    speak = db.Column(db.Integer, default=0)
    vocabulary = db.Column(db.Integer, default=0)
    revision = db.Column(db.Integer, default=0)
    karaoke = db.Column(db.Integer, default=10)
    topic_speaker = db.Column(db.Integer, default=10)
    vocabulary_forest = db.Column(db.Integer, default=0)  # <-- New column

    listen_test_passed = db.Column(db.Boolean, default=False)
    pronunciation_score = db.Column(db.Integer, default=0)
    last_stage = db.Column(db.String(50), default="")
    last_statement = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())



class UserSurvey(db.Model):
    __tablename__ = "user_survey"

    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUIDOrString, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    question = db.Column(db.Text, nullable=True)
    answer = db.Column(db.Text, nullable=True)

    # Backward-compat support with existing code if any
    question_no = db.Column(db.Integer)
    question_text = db.Column(db.Text)
    answer_text = db.Column(db.Text)

    def __repr__(self):
        return f"<Survey for User {self.user_id}>"


# PreGeneratedImage model removed - no longer using image generation


class Poem(db.Model):
    __tablename__ = "poems"

    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    poem_name = db.Column(db.String(200), nullable=False)  # Name of the poem
    poem_content = db.Column(db.Text, nullable=False)  # Full poem text
    poem_tune = db.Column(db.String(500))  # Background music file or tune info
    difficulty_level = db.Column(db.String(50), nullable=False)  # nursery, beginner, intermediate
    day = db.Column(db.Integer, nullable=False)  # Day number (1-15)
    poem_order = db.Column(db.Integer, nullable=False)  # Order within the day (1-3)
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<Poem Day-{self.day}: {self.poem_name}>"


class Syllabus(db.Model):
    __tablename__ = "syllabus"

    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    day = db.Column(db.String(50), nullable=False)  # e.g., "Day-1"
    topic = db.Column(db.String(200), nullable=False)  # e.g., "Daily Routine"
    sr_no = db.Column(db.Float)  # Serial number from Excel
    listen_speak_statement = db.Column(db.Text, nullable=False)  # Main statement to practice
    pronounciation = db.Column(db.String(500))  # Pronunciation guide
    hindi_meaning = db.Column(db.Text)  # Hindi translation/meaning
    vocab = db.Column(db.String(200))  # Key vocabulary word
    grammar_note = db.Column(db.Text)  # Grammar explanation
    practice_question = db.Column(db.Text)  # Practice question for the statement
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<Syllabus {self.day} - {self.topic}>"


class WordCategory(db.Model):
    __tablename__ = "word_categories"
    
    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), nullable=False, unique=True)  # noun, verb, adjective, etc.
    display_name = db.Column(db.String(100), nullable=False)  # Noun, Verb, Adjective, etc.
    description = db.Column(db.Text)  # Description of the category
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<WordCategory {self.name}>"

class UserLevel(db.Model):
    __tablename__ = "user_levels"
    
    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUIDOrString, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    current_level = db.Column(db.Integer, default=1)  # 1 = basic game, 2 = category game
    selected_category = db.Column(db.String(50))  # Current selected category
    category_progress = db.Column(db.JSON, default=dict)  # Progress per category
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserLevel user_id={self.user_id} level={self.current_level}>"

class VocabularyWord(db.Model):
    __tablename__ = "vocabulary_words"

    id = db.Column(UUIDOrString, primary_key=True, default=uuid.uuid4)
    word = db.Column(db.String(100), nullable=False, unique=True)  # The vocabulary word
    image_path = db.Column(db.String(500), nullable=False)  # Path to the image file
    category = db.Column(db.String(100))  # Category like noun, verb, adjective, etc.
    word_type = db.Column(db.String(50))  # Grammar type: noun, verb, adjective, etc.
    difficulty_level = db.Column(db.String(20), default="beginner")  # beginner, intermediate, advanced
    is_used = db.Column(db.Boolean, default=False)  # Track if image has been used in current game session
    usage_count = db.Column(db.Integer, default=0)  # Total times this word has been used
    hindi_meaning = db.Column(db.Text)  # Added Hindi meaning field
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<VocabularyWord {self.word}>"

    def mark_as_used(self):
        """Mark this word as used in current session"""
        self.is_used = True
        self.usage_count += 1
        db.session.commit()

    def reset_usage(self):
        """Reset usage status for new game session"""
        self.is_used = False
        db.session.commit()

    @classmethod
    def get_unused_words(cls, limit=None, word_type=None):
        """Get words that haven't been used in current session"""
        query = cls.query.filter_by(is_used=False)
        if word_type:
            query = query.filter_by(word_type=word_type)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_random_unused(cls, word_type=None):
        """Get a random unused word for the game"""
        import random
        query = cls.query.filter_by(is_used=False)
        if word_type:
            query = query.filter_by(word_type=word_type)
        unused_words = query.all()
        if unused_words:
            return random.choice(unused_words)
        return None
    
    @classmethod
    def get_words_by_category(cls, word_type, limit=None):
        """Get words by category/word_type"""
        query = cls.query.filter_by(word_type=word_type)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def reset_all_usage(cls):
        """Reset all words usage status for new game session"""
        cls.query.update({cls.is_used: False})
        db.session.commit()
