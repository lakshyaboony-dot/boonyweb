# services/pronunciation.py
"""
Phoneme-level pronunciation analysis using CMU Pronouncing Dictionary.
Supports all English words.
"""

import difflib
import nltk

# Download CMU dictionary if not already
nltk.download('cmudict', quiet=True)
from nltk.corpus import cmudict

# Load CMU dictionary
CMU_DICT = cmudict.dict()

def get_phonemes(word):
    """
    Return the list of phonemes for a word from CMU dictionary.
    Fallback: use letters if not found.
    """
    word = word.lower()
    if word in CMU_DICT:
        return CMU_DICT[word][0]  # first pronunciation variant
    else:
        return list(word)  # fallback to letters

def word_pronunciation_similarity(expected_word, transcribed_word):
    """
    Calculate similarity between expected and transcribed word at phoneme level.
    Returns ratio 0..1
    """
    expected_ph = get_phonemes(expected_word)
    transcribed_ph = get_phonemes(transcribed_word)
    return difflib.SequenceMatcher(None, expected_ph, transcribed_ph).ratio()

def detect_mispronounced_words(transcribed_text: str, target_sentence: str) -> dict:
    """
    Detect mispronounced words in a sentence.
    """
    if not target_sentence.strip():
        return {"status": "silent", "mispronounced": []}

    if not transcribed_text or transcribed_text in ["[No speech detected]", "[Transcription error]", "[Low volume or unclear speech detected]"]:
        return {"status": "silent", "mispronounced": []}

    expected_words = target_sentence.lower().strip().split()
    user_words = transcribed_text.lower().strip().split()

    if not user_words:
        return {"status": "silent", "mispronounced": []}

    # Overall sentence similarity
    sentence_similarity = difflib.SequenceMatcher(None, target_sentence.lower(), transcribed_text.lower()).ratio()

    # Check each word for phoneme-level similarity
    mispronounced = []
    for i, expected_word in enumerate(expected_words):
        if i < len(user_words):
            similarity = word_pronunciation_similarity(expected_word, user_words[i])
            if similarity < 0.8:
                mispronounced.append(user_words[i])
        else:
            mispronounced.append("[missing]")

    if not mispronounced:
        return {"status": "ok", "mispronounced": []}
    elif sentence_similarity >= 0.5:
        return {"status": "different", "mispronounced": mispronounced}
    else:
        return {"status": "mispronounced", "mispronounced": mispronounced}


def get_pronunciation_corrections(transcribed_text: str, expected_text: str) -> list:
    """
    Provide detailed corrections for mispronounced words using phoneme-level similarity.
    """
    corrections = []
    if not transcribed_text or not expected_text:
        return corrections

    expected_words = expected_text.lower().strip().split()
    transcribed_words = transcribed_text.lower().strip().split()

    max_len = max(len(expected_words), len(transcribed_words))
    for i in range(max_len):
        if i < len(expected_words):
            expected_word = expected_words[i]
            if i < len(transcribed_words):
                transcribed_word = transcribed_words[i]
                similarity = word_pronunciation_similarity(expected_word, transcribed_word)
                if similarity < 0.8:
                    corrections.append({
                        "position": i + 1,
                        "expected_word": expected_word,
                        "transcribed_word": transcribed_word,
                        "similarity_score": round(similarity * 100, 2),
                        "correction_type": get_correction_type(expected_word, transcribed_word),
                        "pronunciation_tip": get_pronunciation_tip(expected_word, transcribed_word),
                        "phonetic_guide": get_phonetic_guide(expected_word),
                        "audio_tip": get_pronunciation_audio_text(expected_word)  # <-- new field
                    })
            else:
                corrections.append({
                    "position": i + 1,
                    "expected_word": expected_word,
                    "transcribed_word": "[missing]",
                    "similarity_score": 0,
                    "correction_type": "missing_word",
                    "pronunciation_tip": f"You missed the word '{expected_word}'. Try to pronounce it clearly.",
                    "phonetic_guide": get_phonetic_guide(expected_word),
                    "audio_tip": get_pronunciation_audio_text(expected_word)  # <-- new field
                })

    # Extra words
    if len(transcribed_words) > len(expected_words):
        for i in range(len(expected_words), len(transcribed_words)):
            corrections.append({
                "position": i + 1,
                "expected_word": "[none]",
                "transcribed_word": transcribed_words[i],
                "similarity_score": 0,
                "correction_type": "extra_word",
                "pronunciation_tip": f"You added an extra word '{transcribed_words[i]}'. Stick to the original sentence.",
                "phonetic_guide": ""
            })
    return corrections


def get_correction_type(expected_word: str, transcribed_word: str) -> str:
    if len(expected_word) == len(transcribed_word):
        return "substitution"
    elif len(transcribed_word) < len(expected_word):
        return "deletion"
    elif len(transcribed_word) > len(expected_word):
        return "insertion"
    else:
        return "mispronunciation"


def get_pronunciation_tip(expected_word: str, transcribed_word: str) -> str:
    """
    Generic tips based on phonemes.
    """
    tips = {
        "the": "Pronounce as 'thuh' or 'thee', tongue between teeth for 'th'",
        "this": "Start with 'th' sound (tongue between teeth), then 'is'",
        "that": "'Th' sound followed by 'at', tongue between teeth",
        "with": "End with 'th' sound",
    }
    if expected_word in tips:
        return tips[expected_word]
    elif expected_word.startswith('th'):
        return f"Place tongue between teeth for '{expected_word}'"
    elif 'r' in expected_word and 'r' not in transcribed_word:
        return f"Make sure to pronounce the 'r' sound in '{expected_word}'"
    elif expected_word.endswith('ed'):
        return f"Pronounce the '-ed' ending clearly in '{expected_word}'"
    else:
        return f"Practice pronouncing '{expected_word}' slowly, focusing on each syllable"

def get_pronunciation_audio_text(word: str) -> str:
    """
    Return Hinglish-friendly audio explanation for the correct pronunciation of a word.
    Example: 'this' -> "Word 'this' ko bolo: th - is (जैसे 'थ' + 'इस')."
    """
    word = word.lower()
    if word in CMU_DICT:
        phonemes = CMU_DICT[word][0]

        # Basic Hinglish mapping
        mapping = {
            "TH": "थ",
            "IH": "इ",
            "IY": "ई",
            "AE": "ऐ",
            "AH": "अ",
            "AA": "आ",
            "UH": "उ",
            "UW": "ऊ",
            "ER": "र",
            "OW": "ओ",
            "AW": "औ"
        }

        phonetic_parts = []
        for ph in phonemes:
            ph_clean = ''.join([c for c in ph if not c.isdigit()])
            phonetic_parts.append(mapping.get(ph_clean, ph_clean))

        phonetic_hinglish = " - ".join(phonetic_parts)
        return f"Word '{word}' ko bolo: {phonetic_hinglish}. Dheere se repeat karo."
    else:
        return f"Word '{word}' ko clearly bolo: " + " ".join(list(word))


def get_phonetic_guide(word: str) -> str:
    """
    Return CMU phonemes if available.
    """
    word = word.lower()
    if word in CMU_DICT:
        return " ".join(CMU_DICT[word][0])
    else:
        return f"/{word}/"
