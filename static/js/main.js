// ---------------- Preferences Helper ----------------
// ---------------- Preferences Helper ----------------
function getCurrentPrefs() {
    const prefs = window.getPrefs ? window.getPrefs() : {};
    return {
        voice: prefs.voice || 'female',      // default 'female'
        accent: prefs.accent || 'hi-IN',     // default Indian accent
        lang: prefs.lang || 'hi-IN',         // default Indian language
        mode: prefs.mode || 'online'         // default mode online
    };
}

function getCurrentGender() {
    const prefs = getCurrentPrefs();
    return prefs.voice === 'female' ? 'Female' : 'Male';
}

// ---------------- Centralized Gender Update ----------------
function updateGender(newGender) {
    if (!window.getPrefs) window.getPrefs = {};
    window.getPrefs().voice = newGender.toLowerCase(); // 'male' or 'female'

    const avatar = document.querySelector("#avatar-img");
    if (avatar) avatar.dataset.gender = newGender;

    // Refresh avatar to reflect new gender
    showIdle();
}


// ---------------- Enhanced Recording (Speak page integration) ----------------
let mediaRecorder, chunks = [], resolveStopPromise = null;
let audioContext, analyser, audioMonitorInterval;
let mainRecordingStartTime = null;
const minimumRecordingDuration = 1000; // 1 second minimum

async function startRecording() {
    try {
        console.log('Starting recording...');
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                volume: 1.0
            }
        });

        chunks = [];
        mainRecordingStartTime = Date.now();
        showSpeaking(); // Avatar starts speaking

        // Setup audio monitoring
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        source.connect(analyser);

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        mediaRecorder.ondataavailable = (e) => { 
            if (e.data && e.data.size > 0) {
                chunks.push(e.data);
                console.log('Audio chunk received:', e.data.size, 'bytes');
            }
        };

        mediaRecorder.onstop = () => {
            console.log('MediaRecorder stopped, chunks:', chunks.length);
            stopAudioMonitoring();
            showIdle(); // Avatar idle after recording

            try {
                const recordingDuration = mainRecordingStartTime ? Date.now() - mainRecordingStartTime : 0;
                if (recordingDuration < minimumRecordingDuration) {
                    console.error('Recording too short:', recordingDuration, 'ms');
                    if (typeof resolveStopPromise === 'function') resolveStopPromise(null);
                    return;
                }
                
                if (chunks.length === 0) {
                    console.error('No audio chunks recorded');
                    if (typeof resolveStopPromise === 'function') resolveStopPromise(null);
                    return;
                }
                
                const blob = new Blob(chunks, { type: 'audio/webm' });
                if (blob.size < 1000) {
                    console.error('Audio blob too small:', blob.size, 'bytes');
                    if (typeof resolveStopPromise === 'function') resolveStopPromise(null);
                    return;
                }
                
                if (typeof resolveStopPromise === 'function') resolveStopPromise(blob);
            } catch (e) {
                console.error('Error creating audio blob:', e);
                if (typeof resolveStopPromise === 'function') resolveStopPromise(null);
            } finally {
                resolveStopPromise = null;
            }
        };

        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
            stopAudioMonitoring();
            showIdle();
            if (typeof resolveStopPromise === 'function') resolveStopPromise(null);
        };

        mediaRecorder.start(100); // Collect data every 100ms
        startAudioMonitoring();
        console.log('Recording started successfully');
    } catch (error) {
        console.error('Error starting recording:', error);
        showIdle();
        throw error;
    }
}

function startAudioMonitoring() {
    if (!analyser) return;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    audioMonitorInterval = setInterval(() => {
        analyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        let max = 0;
        for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
            max = Math.max(max, dataArray[i]);
        }
        
        const avgLevel = sum / bufferLength;
        const volume = Math.round((avgLevel / 255) * 100);

        if (volume > 5) {
            console.log(`Audio detected - Volume: ${volume}%`);
        }
    }, 100);
}

function stopAudioMonitoring() {
    if (audioMonitorInterval) {
        clearInterval(audioMonitorInterval);
        audioMonitorInterval = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
}

function stopRecording() {
    return new Promise((resolve) => {
        resolveStopPromise = resolve;
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            try { 
                mediaRecorder.stop();
            } catch (e) { 
                console.error('Error stopping recorder:', e);
                stopAudioMonitoring();
                showIdle();
                resolve(null); 
            }
        } else {
            stopAudioMonitoring();
            showIdle();
            resolve(null);
        }
    });
}

// ---------------- Avatar Animation ----------------
function showSpeaking() {
    const img = document.querySelector("#avatar-img");
    if (!img) return;
    const gender = getCurrentGender();
    img.src = `/static/avatars/boony_${gender.toLowerCase()}_speaking.gif`;
}

function showIdle() {
    const img = document.querySelector("#avatar-img");
    if (!img) return;
    const gender = getCurrentGender();
    img.src = `/static/avatars/boony_${gender.toLowerCase()}_idle.png`;
}

// ---------------- Browser TTS ----------------
function speak(text) {
    showSpeaking();
    const prefs = getCurrentPrefs();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = prefs.lang;

    const voices = speechSynthesis.getVoices();
    const matchedVoice = voices.find(v => {
        const name = v.name.toLowerCase();
        return prefs.voice === 'female' ? name.includes('female') : name.includes('male');
    });
    if (matchedVoice) utterance.voice = matchedVoice;

    utterance.onend = () => showIdle();
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
}

// ---------------- Congratulatory TTS ----------------
function speakCongratulations(message) {
    if (!message) return;
    const cleanMessage = message.replace(/[🎉👏⭐🏆🎯💪🌟✨🎊✅]/g, '');
    const prefs = getCurrentPrefs();

    if (window.getPrefs && typeof window.Audio !== 'undefined') {
        const isMuted = (localStorage.getItem('boony.muted') === 'true');

        function mapToMsVoice(p) { 
            if (p.accent === 'en-US') return p.voice === 'female' ? 'en-US-JennyNeural' : 'en-US-GuyNeural'; 
            return p.voice === 'female' ? 'en-IN-KavyaNeural' : 'hi-IN-PrabhatNeural'; 
        }

        function getTTSEndpoint(text) { 
            const qs = new URLSearchParams({
                text, 
                voice: prefs.voice, 
                accent: prefs.accent, 
                lang: prefs.lang, 
                voice_name: mapToMsVoice(prefs), 
                mode: prefs.mode
            }); 
            return `/tts?${qs.toString()}`; 
        }
        
        if (!isMuted) {
            try {
                const audio = new Audio(getTTSEndpoint(cleanMessage));
                showSpeaking();
                audio.play().catch(e => console.log('TTS Error:', e));
                audio.onended = showIdle;
            } catch (e) {
                console.log('TTS Error:', e);
                speak(cleanMessage); // fallback
            }
        }
    } else {
        speak(cleanMessage);
    }
}

// ---------------- Expose globally ----------------
window.startRecording = startRecording;
window.stopRecording = stopRecording;
window.showSpeaking = showSpeaking;
window.showIdle = showIdle;
window.speak = speak;
window.speakCongratulations = speakCongratulations;
window.updateGender = updateGender; // Add centralized gender update
