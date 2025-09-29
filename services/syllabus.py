import os
import pandas as pd

def load_day_statements(xlsx_path, day: str):
    """Load statements for a specific day from the Excel structure"""
    if not os.path.exists(xlsx_path):
        return []
    
    try:
        # Try to load specific day sheet first
        sheet_name = f"Day-{day}"
        try:
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        except:
            # If sheet doesn't exist, try loading from main sheet
            df_all = pd.read_excel(xlsx_path)
            # Filter by day if day column exists
            if "day" in df_all.columns:
                # Try both formats: 'Day-1' and '1'
                day_filter = f"Day-{day}" if not day.startswith('Day-') else day
                df = df_all[df_all["day"].astype(str).str.strip() == day_filter]
                # If no match, try the other format
                if df.empty:
                    alt_day = day.replace('Day-', '') if day.startswith('Day-') else f"Day-{day}"
                    df = df_all[df_all["day"].astype(str).str.strip() == alt_day]
            else:
                df = df_all
            
        if df.empty:
            # Return sample statements for Day-1 if no data found
            if day == "1":
                return generate_sample_day1_statements()
            return []

        results = []
        for _, row in df.iterrows():
            # Extract data from available columns
            text = str(row.get('statement', '')).strip() if not pd.isna(row.get('statement')) else ""
            if not text:
                text = str(row.get('listen_speak_statement', '')).strip() if not pd.isna(row.get('listen_speak_statement')) else ""
            
            # Skip if no text content
            if not text:
                continue
                
            pronunciation = str(row.get('pronounciation', '')).strip() if not pd.isna(row.get('pronounciation')) else ""
            hindi = str(row.get('hindi', '')).strip() if not pd.isna(row.get('hindi')) else ""
            if not hindi:
                hindi = str(row.get('hindi_meaning', '')).strip() if not pd.isna(row.get('hindi_meaning')) else ""
            
            sr_no_val = float(row.get('sr_no', len(results) + 1)) if not pd.isna(row.get('sr_no')) else len(results) + 1
            topic_val = str(row.get('Topic', '')).strip() if not pd.isna(row.get('Topic')) else ""
            if not topic_val:
                topic_val = str(row.get('topic', '')).strip() if not pd.isna(row.get('topic')) else ""

            results.append({
                "sr_no": sr_no_val,
                "text": text,
                "pronunciation": pronunciation,
                "hindi": hindi,
                "topic": topic_val
            })

        # If no valid data found, return sample data for Day-1
        if not results and day == "1":
            return generate_sample_day1_statements()
            
        return results
        
    except Exception as e:
        print(f"Error loading day statements: {e}")
        # Return sample data for Day-1 as fallback
        if day == "1":
            return generate_sample_day1_statements()
        return []

def generate_sample_day1_statements():
    """Generate sample statements for Day-1"""
    return [
        {"sr_no": 1, "text": "I wake up early in the morning.", "pronunciation": "आई वेक अप अर्ली इन द मॉर्निंग", "hindi": "मैं सुबह जल्दी उठता हूँ।", "topic": "Daily Routine"},
        {"sr_no": 2, "text": "I brush my teeth and take a shower.", "pronunciation": "आई ब्रश माई टीथ एंड टेक अ शावर", "hindi": "मैं अपने दांत साफ करता हूँ और नहाता हूँ।", "topic": "Daily Routine"},
        {"sr_no": 3, "text": "I have breakfast with my family.", "pronunciation": "आई हैव ब्रेकफास्ट विद माई फैमिली", "hindi": "मैं अपने परिवार के साथ नाश्ता करता हूँ।", "topic": "Daily Routine"},
        {"sr_no": 4, "text": "I go to work by bus.", "pronunciation": "आई गो टू वर्क बाई बस", "hindi": "मैं बस से काम पर जाता हूँ।", "topic": "Transportation"},
        {"sr_no": 5, "text": "I work in an office building.", "pronunciation": "आई वर्क इन एन ऑफिस बिल्डिंग", "hindi": "मैं एक ऑफिस बिल्डिंग में काम करता हूँ।", "topic": "Work"},
        {"sr_no": 6, "text": "I have lunch at twelve o'clock.", "pronunciation": "आई हैव लंच एट ट्वेल्व ओ'क्लॉक", "hindi": "मैं बारह बजे दोपहर का खाना खाता हूँ।", "topic": "Daily Routine"},
        {"sr_no": 7, "text": "I attend meetings with my colleagues.", "pronunciation": "आई अटेंड मीटिंग्स विद माई कॉलीग्स", "hindi": "मैं अपने सहयोगियों के साथ बैठकों में भाग लेता हूँ।", "topic": "Work"},
        {"sr_no": 8, "text": "I finish work at six in the evening.", "pronunciation": "आई फिनिश वर्क एट सिक्स इन द इवनिंग", "hindi": "मैं शाम छह बजे काम खत्म करता हूँ।", "topic": "Work"},
        {"sr_no": 9, "text": "I go shopping for groceries.", "pronunciation": "आई गो शॉपिंग फॉर ग्रोसरीज", "hindi": "मैं किराने का सामान खरीदने जाता हूँ।", "topic": "Shopping"},
        {"sr_no": 10, "text": "I cook dinner for my family.", "pronunciation": "आई कुक डिनर फॉर माई फैमिली", "hindi": "मैं अपने परिवार के लिए रात का खाना बनाता हूँ।", "topic": "Daily Routine"},
        {"sr_no": 11, "text": "We watch television together.", "pronunciation": "वी वॉच टेलीविजन टुगेदर", "hindi": "हम एक साथ टेलीविजन देखते हैं।", "topic": "Family Time"},
        {"sr_no": 12, "text": "I read a book before sleeping.", "pronunciation": "आई रीड अ बुक बिफोर स्लीपिंग", "hindi": "मैं सोने से पहले किताब पढ़ता हूँ।", "topic": "Daily Routine"},
        {"sr_no": 13, "text": "I exercise three times a week.", "pronunciation": "आई एक्सरसाइज थ्री टाइम्स अ वीक", "hindi": "मैं सप्ताह में तीन बार व्यायाम करता हूँ।", "topic": "Health"},
        {"sr_no": 14, "text": "I visit my friends on weekends.", "pronunciation": "आई विजिट माई फ्रेंड्स ऑन वीकएंड्स", "hindi": "मैं सप्ताहांत में अपने दोस्तों से मिलने जाता हूँ।", "topic": "Social Life"},
        {"sr_no": 15, "text": "I like to listen to music.", "pronunciation": "आई लाइक टू लिसन टू म्यूजिक", "hindi": "मुझे संगीत सुनना पसंद है।", "topic": "Hobbies"},
        {"sr_no": 16, "text": "I play cricket with my friends.", "pronunciation": "आई प्ले क्रिकेट विद माई फ्रेंड्स", "hindi": "मैं अपने दोस्तों के साथ क्रिकेट खेलता हूँ।", "topic": "Sports"},
        {"sr_no": 17, "text": "I help my mother with household work.", "pronunciation": "आई हेल्प माई मदर विद हाउसहोल्ड वर्क", "hindi": "मैं अपनी माँ की घर के काम में मदद करता हूँ।", "topic": "Family"},
        {"sr_no": 18, "text": "I study English every day.", "pronunciation": "आई स्टडी इंग्लिश एवरी डे", "hindi": "मैं रोज अंग्रेजी पढ़ता हूँ।", "topic": "Education"},
        {"sr_no": 19, "text": "I save money for the future.", "pronunciation": "आई सेव मनी फॉर द फ्यूचर", "hindi": "मैं भविष्य के लिए पैसे बचाता हूँ।", "topic": "Finance"},
        {"sr_no": 20, "text": "I go to bed at ten o'clock.", "pronunciation": "आई गो टू बेड एट टेन ओ'क्लॉक", "hindi": "मैं दस बजे सोने जाता हूँ।", "topic": "Daily Routine"}
    ]


def load_day_vocab(xlsx_path, day: str):
    """Load vocabulary for a specific day from the new Excel structure"""
    if not os.path.exists(xlsx_path):
        return []
    
    try:
        # Load the entire Excel file (single sheet structure)
        df_all = pd.read_excel(xlsx_path)
        
        # Filter by day
        if "day" in df_all.columns:
            df = df_all[df_all["day"].astype(str).str.strip() == str(day)]
        else:
            return []
            
        if df.empty:
            return []

        out = []
        for _, row in df.iterrows():
            # Extract vocab data from the vocab column
            vocab_text = str(row.get('vocab', '')).strip() if not pd.isna(row.get('vocab')) else ""
            hindi_meaning = str(row.get('hindi_meaning', '')).strip() if not pd.isna(row.get('hindi_meaning')) else ""
            
            # If vocab column contains word-meaning pairs, parse them
            if vocab_text and hindi_meaning:
                # For now, treat vocab as the word and hindi_meaning as meaning
                # This can be enhanced later if vocab column has specific format
                out.append((vocab_text, hindi_meaning, ""))
                
        return out
        
    except Exception as e:
        print(f"Error loading day vocab: {e}")
        return []
