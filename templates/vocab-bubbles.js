const words = [
    { word: "apple", image: "/static/images/apple.png" },
    { word: "dog", image: "/static/images/dog.png" },
    { word: "cat", image: "/static/images/cat.png" },
    { word: "ball", image: "/static/images/ball.png" },
    { word: "book", image: "/static/images/book.png" },
    { word: "car", image: "/static/images/car.png" },
    { word: "banana", image: "/static/images/banana.png" },
    { word: "tree", image: "/static/images/tree.png" },
    { word: "chair", image: "/static/images/chair.png" },
    { word: "house", image: "/static/images/house.png" }
];

let score = 0;
let shownBubbles = 0;
const scoreEl = document.getElementById("score");
const npcPrompt = document.getElementById("npc-prompt");
const bubbleArea = document.getElementById("bubble-area");

// Setup Speech Recognition
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'en-US';
recognition.interimResults = false;

function speakText(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);
}

function addBubble(wordObj) {
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.style.left = Math.random() * (bubbleArea.clientWidth - 100) + "px";
    bubble.style.top = Math.random() * (bubbleArea.clientHeight - 100) + "px";

    const img = document.createElement("img");
    img.src = wordObj.image;
    bubble.appendChild(img);

    bubbleArea.appendChild(bubble);

    bubble.addEventListener("click", () => {
        npcPrompt.textContent = "🎤 Say the word!";
        recognition.start();
        recognition.onresult = (event) => {
            const userAnswer = event.results[0][0].transcript.toLowerCase();
            if (userAnswer === wordObj.word.toLowerCase()) {
                score += 10;
                scoreEl.textContent = "⭐ Score: " + score;
                npcPrompt.textContent = "✅ Correct! +" + 10;
                bubble.classList.add("pop");
                setTimeout(() => bubble.remove(), 500);
            } else {
                npcPrompt.textContent = "❌ Oops! That was " + userAnswer;
            }
        };
    });
}

function startGame() {
    // start with 4 bubbles
    for (let i = 0; i < 4; i++) {
        if (shownBubbles < words.length) addBubble(words[shownBubbles++]);
    }

    // add a new bubble every 10 sec
    const bubbleTimer = setInterval(() => {
        if (shownBubbles >= words.length) {
            clearInterval(bubbleTimer);
            npcPrompt.textContent = "🎉 Game Over! Final Score: " + score;
            speakText("Congratulations! Your final score is " + score);
            return;
        }
        addBubble(words[shownBubbles++]);
    }, 10000);
}

startGame();
