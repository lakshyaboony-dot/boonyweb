var currentDay = document.body.getAttribute("data-day");
var vocabularyWords = [];
var currentWordIndex = 0;
var voices = [];
var credits = 0;
let recognition = null;
let isRecording = false;

// ===========================
// Load Voices
// ===========================
function loadVoices() { voices = speechSynthesis.getVoices(); }
speechSynthesis.onvoiceschanged = loadVoices;

// ===========================
// Speak Text
// ===========================
function speakText(text, callback) {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();

    let utter = new SpeechSynthesisUtterance(text);
    let lang = "{{ ui_lang|default('english') }}";
    utter.lang = (lang === "hinglish") ? "hi-IN" : "en-US";

    let genderPref = "{{ session.get('voice_gender','male') }}";
    if (voices.length > 0) {
        let chosen = voices.find(v =>
            (genderPref === "male" && v.name.toLowerCase().includes("male")) ||
            (genderPref === "female" && v.name.toLowerCase().includes("female"))
        );
        if (chosen) utter.voice = chosen;
    }
    utter.rate = 0.9;
    utter.onend = () => { if (callback) callback(); };
    speechSynthesis.speak(utter);
}

// ===========================
// Toggle Recording
// ===========================
function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("SpeechRecognition not supported");
        return null;
    }
    recognition = new SpeechRecognition();
    recognition.lang = ("{{ ui_lang|default('english') }}" === "hinglish") ? "hi-IN" : "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
        let transcript = event.results[0][0].transcript;
        showTranscript(transcript);
    };

    recognition.onerror = (event) => {
        console.error("Recognition error:", event.error);
        alert("⚠️ Could not recognize. Try again!");
        isRecording = false;
        updateRecordButton();
    };

    recognition.onend = () => {
        isRecording = false;
        updateRecordButton();
    };
}

function toggleRecording() {
    if (!recognition) initRecognition();
    if (!recognition) return;

    if (!isRecording) {
        recognition.start();
        isRecording = true;
        document.getElementById("practice-instruction").textContent = "🎤 Listening... Speak your sentence!";
    } else {
        recognition.stop();
        isRecording = false;
    }
    updateRecordButton();
}

function updateRecordButton() {
    const btn = document.getElementById("record-btn");
    btn.textContent = isRecording ? "Stop Recording" : "Start Recording";
    btn.disabled = (document.getElementById("current-word").textContent === "");
}

// ===========================
// Play Word Step-by-Step
// ===========================
function playWord(index) {
    currentWordIndex = index;
    const wordObj = vocabularyWords[index];

    // Reset
    document.getElementById("practice-result").style.display = "none";
    document.getElementById("transcribed-text").innerHTML = "";
    document.getElementById("ai-feedback").innerHTML = "";
    document.getElementById("score-display").innerHTML = "";
    document.getElementById("next-word-btn").style.display = "none";
    isRecording = false;
    updateRecordButton();

    ["word-meaning", "word-antonyms", "word-synonyms", "word-example"].forEach(id => {
        document.getElementById(id).style.display = "none";
    });

    document.getElementById("current-word").textContent = wordObj.word;

    // Step 1: Meaning
    document.getElementById("word-meaning").style.display = "block";
    let meaningText = "Meaning: " + (wordObj.meaning || "N/A");
    if (wordObj.hindi_meaning) {
        meaningText += " (Hindi: " + wordObj.hindi_meaning + ")";
    }
    document.getElementById("word-meaning").textContent = meaningText;
    
    let speakMeaning = `Meaning of ${wordObj.word} is ${wordObj.meaning}`;
    if (wordObj.hindi_meaning) {
        speakMeaning += `. In Hindi it means ${wordObj.hindi_meaning}`;
    }
    
    speakText(speakMeaning, () => {

        // Step 2: Antonyms
        document.getElementById("word-antonyms").style.display = "block";
        document.getElementById("word-antonyms").textContent = "Antonyms: " + (wordObj.antonyms || "N/A");
        speakText(`Antonyms of ${wordObj.word} are ${wordObj.antonyms}`, () => {

            // Step 3: Synonyms
            document.getElementById("word-synonyms").style.display = "block";
            document.getElementById("word-synonyms").textContent = "Synonyms: " + (wordObj.synonyms || "N/A");
            speakText(`Synonyms of ${wordObj.word} are ${wordObj.synonyms}`, () => {

                // Step 4: Example
                document.getElementById("word-example").style.display = "block";
                document.getElementById("word-example").textContent = "Example: " + (wordObj.example || "N/A");
                speakText(`Example: ${wordObj.example}`, () => {
                    // Enable recording after explanation
                    updateRecordButton();
                });
            });
        });
    });
}

// ===========================
// Transcript + Analysis
// ===========================
function showTranscript(transcript) {
    let wordObj = vocabularyWords[currentWordIndex];
    let highlighted = transcript.replace(new RegExp(wordObj.word, "gi"), `<mark>${wordObj.word}</mark>`);
    document.getElementById("transcribed-text").innerHTML = highlighted;
    analyzeSentence(transcript, wordObj);
}

function analyzeSentence(transcript, wordObj) {
    fetch("/api/check-vocab-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_answer: transcript,
            word: wordObj.word,
            correct_answer: wordObj.example
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("ai-feedback").textContent = data.feedback;
        document.getElementById("corrected-sentence").textContent = "Corrected: " + data.corrected_sentence;

        speakText("Feedback: " + data.feedback);

        document.getElementById("practice-result").style.display = "block";
        if (currentWordIndex + 1 < vocabularyWords.length)
            document.getElementById("next-word-btn").style.display = "inline-block";

        credits++;
        document.getElementById("vocab-credits").textContent = credits;
        let percent = ((currentWordIndex + 1) / vocabularyWords.length) * 100;
        document.getElementById("progress-fill").style.width = percent + "%";
    })
    .catch(err => console.error("Error analyzing:", err));
}
// ===========================
// Word List
// ===========================
function populateWordList() {
    const list = document.getElementById("word-list");
    list.innerHTML = "";

    vocabularyWords.forEach((w, index) => {
        const li = document.createElement("li");
        li.innerHTML = `<span class="play-icon">▶</span> ${w.word}`;
        li.addEventListener("click", () => {
            playWord(index);
            highlightActiveWord();
        });
        list.appendChild(li);
    });
    highlightActiveWord();
}

function highlightActiveWord() {
    const items = document.querySelectorAll("#word-list li");
    items.forEach((li, idx) => {
        li.classList.toggle("active", idx === currentWordIndex);
    });
}

// ===========================
// Load Vocabulary
// ===========================
function loadVocabularyWords() {
    fetch(`/api/vocabulary/random`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.word) {
                vocabularyWords = [data.word]; // Single word from API
                currentWordIndex = 0;
                populateWordList();
                playWord(0);
            } else {
                // Fallback data
                vocabularyWords = [
                    { word: "Amazing", meaning: "Very impressive", hindi_meaning: "अद्भुत", synonyms: "Wonderful", antonyms: "Boring", example: "The view was amazing." }
                ];
                currentWordIndex = 0;
                populateWordList();
                playWord(0);
            }
        })
        .catch(err => {
            console.error("Error fetching vocabulary:", err);
            // Fallback data
            vocabularyWords = [
                { word: "Amazing", meaning: "Very impressive", hindi_meaning: "अद्भुत", synonyms: "Wonderful", antonyms: "Boring", example: "The view was amazing." }
            ];
            currentWordIndex = 0;
            populateWordList();
            playWord(0);
        });
}

// ===========================
// DOM Ready
// ===========================
document.addEventListener("DOMContentLoaded", function () {
    loadVoices();
    loadVocabularyWords();
    document.getElementById("record-btn").addEventListener("click", toggleRecording);
    document.getElementById("next-word-btn").addEventListener("click", function () {
        if (currentWordIndex + 1 < vocabularyWords.length) {
            currentWordIndex++;
            populateWordList();
            playWord(currentWordIndex);
        }
    });
});
