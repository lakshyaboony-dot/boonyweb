// -------------------------
// Variables
// -------------------------
let currentIndex = 0;
let statementsEls = document.querySelectorAll(".sentence-item");
let totalStatements = statementsEls.length;
let completed = Array(totalStatements).fill(false);
let isAutoPlaying = false;
let currentUtterance = null;
let isPaused = false;
let playCount = 0;

// -------------------------
// Preferences Helper
// -------------------------
function getCurrentPrefs() {
    const prefs = window.getPrefs ? window.getPrefs() : {};
    return {
        voice: prefs.voice || "female",
        accent: prefs.accent || "hi-IN",
        lang: prefs.lang || "hi-IN",
        mode: prefs.mode || "online"
    };
}

function getCurrentGender() {
    const prefs = getCurrentPrefs();
    return prefs.voice === "female" ? "Female" : "Male";
}

function updateGender(newGender) {
    if (!window.getPrefs) window.getPrefs = {};
    window.getPrefs.voice = newGender.toLowerCase();
    updateListenAvatar();
}

// -------------------------
// Highlight statement
// -------------------------
function highlightStatement(index) {
    statementsEls.forEach((el, i) => {
        el.classList.toggle("active", i === index);
        el.classList.toggle("disabled", i !== index);
    });

    const stmt = LISTEN_STATEMENTS[index];
    document.getElementById("card-no").innerText =
        `Sentence ${index + 1} / ${totalStatements}`;
    document.getElementById("sentence-english").innerText = stmt.text;
    document.getElementById("sentence-hindi").innerText = stmt.hindi || "";
    document.getElementById("sentence-pronunciation").innerText =
        stmt.pronunciation || "";

    updateProgressBar();
}

// -------------------------
// Progress Bar
// -------------------------
function updateProgressBar() {
    const progress =
        (completed.filter(c => c).length / totalStatements) * 100;
    document.getElementById("progress-fill").style.width = progress + "%";
}

// -------------------------
// Avatar update
// -------------------------
function updateListenAvatar() {
    const gender = getCurrentGender().toLowerCase();
    const img = document.querySelector("#avatar-img");
    if (!img) return;
    img.src = `/static/avatars/boony_${gender}_idle.png`;
}

// -------------------------
// Play TTS
// -------------------------
function playAudio(text, index, autoplay = false) {
    if (!text) return;

    if (autoplay) {
        isAutoPlaying = true;
        document.getElementById("pause-resume-btn").disabled = false;
        showStopButton();
    }

    playCount = 0;

    function speakOnce() {
        const prefs = getCurrentPrefs();

        if (playCount >= 2) {
            completed[index] = true;
            addCredits(index);
            if (autoplay && isAutoPlaying) nextSentence();
            return;
        }

        currentUtterance = new SpeechSynthesisUtterance(text);
        currentUtterance.lang = prefs.lang;

        function selectVoice() {
            const voices = speechSynthesis.getVoices();
            return (
                voices.find(v => {
                    const name = v.name.toLowerCase();
                    return prefs.voice === "female"
                        ? name.includes("female")
                        : name.includes("male");
                }) || null
            );
        }

        const voices = speechSynthesis.getVoices();
        if (voices.length === 0) {
            speechSynthesis.onvoiceschanged = () => {
                currentUtterance.voice = selectVoice();
                speechSynthesis.speak(currentUtterance);
            };
        } else {
            currentUtterance.voice = selectVoice();
            speechSynthesis.speak(currentUtterance);
        }

        currentUtterance.onend = () => {
            currentUtterance = null;
            playCount++;
            if (!isPaused) setTimeout(speakOnce, 150);
        };
    }

    speakOnce();
}

// -------------------------
// Next sentence
// -------------------------
function nextSentence() {
    if (currentIndex < totalStatements - 1) {
        currentIndex++;
        highlightStatement(currentIndex);
        playAudio(LISTEN_STATEMENTS[currentIndex].text, currentIndex, true);
    } else {
        isAutoPlaying = false;
        hideStopButton();
        showCompletion();
    }
}

// -------------------------
// Credits
// -------------------------
function addCredits(statementIndex) {
    let creditsEl = document.getElementById("listen-credits");
    let newCredit = parseInt(creditsEl.innerText || 0) + 1;
    creditsEl.innerText = newCredit;

    fetch("/api/update-credit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            day: CURRENT_DAY,
            value: 1,
            statement_index: statementIndex
        })
    });
}

// -------------------------
// Pause / Resume
// -------------------------
function togglePauseResume() {
    if (!currentUtterance && !isPaused) return;

    if (!isPaused) {
        speechSynthesis.pause();
        isPaused = true;
        setPauseResumeBtn("resume");
    } else {
        speechSynthesis.resume();
        isPaused = false;
        setPauseResumeBtn("pause");
    }
}

function setPauseResumeBtn(state) {
    const btn = document.getElementById("pause-resume-btn");
    if (!btn) return;
    btn.innerText = state === "pause" ? "⏸ Pause" : "▶ Resume";
}

// -------------------------
// Stop audio & reset
// -------------------------
function stopAudio() {
    speechSynthesis.cancel();
    isAutoPlaying = false;
    isPaused = false;
    currentIndex = 0;
    completed.fill(false);
    highlightStatement(currentIndex);
    hideStopButton();
    document.getElementById("pause-resume-btn").disabled = true;
}

// -------------------------
// Stop button UI
// -------------------------
function showStopButton() {
    const btn = document.getElementById("stop-autoplay-btn");
    if (btn) btn.style.display = "inline-block";
}
function hideStopButton() {
    const btn = document.getElementById("stop-autoplay-btn");
    if (btn) btn.style.display = "none";
}

// -------------------------
// Completion
// -------------------------
function showCompletion() {
    const msgBox = document.getElementById("completion-msg");
    if (msgBox) msgBox.style.display = "block";
    setTimeout(
        () => (window.location.href = `/listen-test/Day-${CURRENT_DAY}`),
        4000
    );
}

// -------------------------
// Init
// -------------------------
document.addEventListener("DOMContentLoaded", () => {
    highlightStatement(currentIndex);
    updateListenAvatar();

    // Autoplay
    document.getElementById("autoplay-btn")?.addEventListener("click", () => {
        stopAudio();
        const startAutoPlay = () => {
            highlightStatement(currentIndex);
            playAudio(
                LISTEN_STATEMENTS[currentIndex].text,
                currentIndex,
                true
            );
        };

        if (speechSynthesis.getVoices().length === 0) {
            speechSynthesis.onvoiceschanged = () => startAutoPlay();
        } else {
            startAutoPlay();
        }
    });

    // Pause/Resume
    document
        .getElementById("pause-resume-btn")
        ?.addEventListener("click", togglePauseResume);

    // Stop
    document
        .getElementById("stop-autoplay-btn")
        ?.addEventListener("click", stopAudio);

    // Manual click on sentence
    statementsEls.forEach((el, idx) => {
        el.addEventListener("click", () => {
            stopAudio();
            currentIndex = idx;
            highlightStatement(currentIndex);
            playAudio(
                LISTEN_STATEMENTS[currentIndex].text,
                currentIndex,
                false
            );
        });
    });

    // Male/Female dropdown
    document.getElementById("pref-voice")?.addEventListener("change", e => {
        updateGender(e.target.value);
    });

    // Avatar clicks
    document
        .getElementById("navAvatarMale")
        ?.addEventListener("click", () => updateGender("male"));
    document
        .getElementById("navAvatarFemale")
        ?.addEventListener("click", () => updateGender("female"));
});
