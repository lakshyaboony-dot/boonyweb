let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let selectedIndex = 0;

// ✅ Select a sentence
// sentence load hone par reset
function selectSentence(index) {
    const li = document.getElementById(`list-item-${index}`);
    if (li.dataset.enabled === "false") return;

    selectedIndex = index;
    const s = SPEAK_STATEMENTS[index];

    document.getElementById("card-no").innerText = `Sentence ${index + 1} / ${SPEAK_STATEMENTS.length}`;
    document.getElementById("sentence-english").innerText = s.text || "";
    document.getElementById("sentence-hindi").innerText = s.hindi || "";
    document.getElementById("card-topic").innerText = s.topic || "";

    document.querySelectorAll(".sentence-item").forEach(li => li.classList.remove("active"));
    li.classList.add("active");

    // reset analysis & progress
    resetAnalysis();

    // ✅ Next button disable on sentence load
    document.getElementById("go-next").disabled = true;
}

// 🎤 Toggle recording
async function toggleRecording() {
    const recordLabel = document.getElementById("record-label");

    if (!isRecording) {
        // start recording
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const formData = new FormData();
            formData.append("audio", audioBlob, "recording.wav");
            formData.append("expected_text", SPEAK_STATEMENTS[selectedIndex].text);

            // processing...
            try {
                const res = await fetch("/api/analyze_speech", { method: "POST", body: formData });
                const data = await res.json();
                if (data.ok) renderAnalysis(data.analysis.word_accuracy, data.analysis.feedback, data.corrections);
            } catch (err) { console.error(err); }
        };

        mediaRecorder.start();
        isRecording = true;
        recordLabel.innerText = "⏹ Stop Recording";

        // ✅ Enable Next button immediately after recording started
        document.getElementById("go-next").disabled = false;

    } else {
        mediaRecorder.stop();
        isRecording = false;
        recordLabel.innerText = "🎙 Start Recording";
    }
}


// 🔄 Reset analysis section
function resetAnalysis() {
    document.getElementById("progress-fill").style.width = "0%";
    document.getElementById("score-value").innerText = "—";
    document.getElementById("feedback-text").innerText = "Record to get feedback";
    document.getElementById("transcription").innerText = "Click record and speak...";
    document.getElementById("mispronounced-chips").innerHTML = "";
}

// 🎤 Toggle recording
async function toggleRecording() {
    const recordBtn = document.getElementById("record-btn");
    const recordLabel = document.getElementById("record-label");
    const nextBtn = document.getElementById("go-next"); // next button

    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                const formData = new FormData();
                formData.append("audio", audioBlob, "recording.wav");
                formData.append("expected_text", SPEAK_STATEMENTS[selectedIndex].text);

                document.getElementById("feedback-text").innerText = "Processing... ⏳";

                try {
                    const res = await fetch("/api/analyze_speech", { method: "POST", body: formData });
                    const data = await res.json();

                    if (data.ok) {
                        document.getElementById("transcription").innerText = data.transcription || "No transcription";
                        renderAnalysis(data.analysis.word_accuracy, data.analysis.feedback, data.corrections);

                        // ✅ Enable Next button after successful recording & analysis
                        nextBtn.disabled = false;
                    } else {
                        document.getElementById("feedback-text").innerText = "❌ Error: " + (data.message || "Unknown");
                    }
                } catch (err) {
                    console.error("Upload failed:", err);
                    document.getElementById("feedback-text").innerText = "❌ Upload failed";
                }
            };

            mediaRecorder.start();
            isRecording = true;
            recordLabel.innerText = "⏹ Stop Recording";
        } catch (err) {
            console.error("Mic access denied:", err);
            document.getElementById("feedback-text").innerText = "❌ Microphone not accessible";
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        recordLabel.innerText = "🎙 Start Recording";
    }
}

// 📝 Render analysis
function renderAnalysis(score, feedback, corrections) {
    document.getElementById("score-value").innerText = `${score}% ${getEmoji(score)}`;
    document.getElementById("feedback-text").innerText = feedback;

    const chipBox = document.getElementById("mispronounced-chips");
    chipBox.innerHTML = "";
    corrections.forEach(c => {
        if (c.correction_type !== "extra_word" && c.expected_word && c.expected_word !== "[missing]" && c.audio_tip) {
            const btn = document.createElement("div");
            btn.className = "chip";
            btn.innerText = `🔊 ${c.transcribed_word || c.expected_word}`;
            btn.onclick = () => playAudioTip(c.audio_tip);
            chipBox.appendChild(btn);
        }
    });
}

// 🔊 Play audio tip
function playAudioTip(audioText) {
    if (!audioText) return;
    const audio = new Audio(`/tts?text=${encodeURIComponent(audioText)}&voice=Male&mode=auto`);
    audio.play();
}

// 🔊 Play sentence
function playSentence(index) {
    const sentenceText = SPEAK_STATEMENTS[index].text;
    const audio = new Audio(`/tts?text=${encodeURIComponent(sentenceText)}&voice=Male&mode=auto`);
    audio.play();
}

// 😀 Emoji feedback
function getEmoji(score) {
    if (score >= 90) return "🌟 Excellent!";
    else if (score >= 75) return "👍 Good!";
    else if (score >= 50) return "🙂 Keep Trying";
    else return "⏳ Try Again Slowly";
}

// 🔄 Next sentence
function goNext() {
    // Stop recording if in progress
    if (isRecording && mediaRecorder) toggleRecording();

    // Current sentence deactivate
    document.getElementById(`list-item-${selectedIndex}`).classList.remove("active");

    // Next index
    let nextIndex = selectedIndex + 1;
    if (nextIndex >= SPEAK_STATEMENTS.length) return; // last sentence

    // Enable next sentence
    const nextLi = document.getElementById(`list-item-${nextIndex}`);
    nextLi.dataset.enabled = "true";

    // Select next sentence automatically
    selectSentence(nextIndex);

    // Add 1 credit
    addCredit();
}

// 🔄 Retry
function tryAgain() {
    resetAnalysis();
}

// 💰 Add credit
function addCredit() {
    let creditsEl = document.getElementById("speak-credits");
    let currentCredits = parseInt(creditsEl.innerText) || 0;
    currentCredits += 1;
    creditsEl.innerText = currentCredits;

    // server update
    fetch("/update_credits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credits: currentCredits, sentence_index: selectedIndex })
    });
}
