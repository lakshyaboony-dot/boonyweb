// Adventure Quest: Vocabulary Forest Game

const vocabWords = [
    { word: "apple", image: "/static/images/apple.png" },
    { word: "dog", image: "/static/images/dog.png" },
    { word: "cat", image: "/static/images/cat.png" },
    { word: "ball", image: "/static/images/ball.png" },
    { word: "book", image: "/static/images/book.png" },
    { word: "car", image: "/static/images/car.png" },
    { word: "chair", image: "/static/images/chair.png" },
    { word: "banana", image: "/static/images/banana.png" },
    { word: "tree", image: "/static/images/tree.png" },
    { word: "house", image: "/static/images/house.png" }
];

let score = 0;
let currentIndex = -1;

const startBtn = document.getElementById("startVocabGameBtn");
const container = document.getElementById("vocabGameContainer");

// TTS helper
function speak(text) {
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-US";
    utter.rate = 1;
    speechSynthesis.speak(utter);
}

// Play sound helper
function playSound(file) {
    const audio = new Audio(file);
    audio.play();
}

// Speech recognition
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = "en-US";
recognition.interimResults = false;

function listen(callback) {
    recognition.start();
    recognition.onresult = (e) => {
        const result = e.results[0][0].transcript;
        callback(result);
    };
    recognition.onerror = () => callback("[Could not understand]");
}

// Build game UI
function buildGameUI() {
    container.innerHTML = `
        <div id="gameUI">
            <p id="prompt">Get ready!</p>
            <img id="gameImage" src="" style="width:150px;height:150px;margin:10px 0;">
            <p>Score: <span id="gameScore">0</span></p>
            <button id="nextWordBtn" disabled class="fun-btn">Next Word</button>
        </div>
    `;

    document.getElementById("nextWordBtn").addEventListener("click", nextWord);
}

// Start game
startBtn.addEventListener("click", () => {
    score = 0;
    currentIndex = -1;
    buildGameUI();
    startBtn.disabled = true;
    nextWord();
});

// Next word function
function nextWord() {
    currentIndex++;
    if (currentIndex >= vocabWords.length) {
        document.getElementById("prompt").innerText = "🎉 Congratulations! You finished!";
        document.getElementById("gameImage").src = "";
        document.getElementById("nextWordBtn").disabled = true;
        startBtn.disabled = false;
        speak("Congratulations! You finished Vocabulary Forest!");
        return;
    }

    const wordObj = vocabWords[currentIndex];
    document.getElementById("gameImage").src = wordObj.image;
    document.getElementById("prompt").innerText = "What is this?";
    speak("What is this?");
    document.getElementById("nextWordBtn").disabled = true;

    listen((userAnswer) => {
        if (userAnswer.toLowerCase() === wordObj.word.toLowerCase()) {
            score += 10;
            document.getElementById("gameScore").innerText = score;
            playSound("/static/sounds/correct.mp3");
            speak("Correct! You earned 10 points.");
        } else {
            playSound("/static/sounds/incorrect.mp3");
            speak(`Oops! The correct answer is ${wordObj.word}`);
        }
        document.getElementById("nextWordBtn").disabled = false;
    });
}
