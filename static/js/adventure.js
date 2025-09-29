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
let activeBubbles = [];
let bubbleInterval;
let spawnCount = 0;

const gameArea = document.getElementById("gameArea");
const scoreBoard = document.getElementById("scoreBoard");
const startBtn = document.getElementById("startGameBtn");

// Speech recognition setup
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = "en-US";
recognition.continuous = true;
recognition.interimResults = false;

recognition.onresult = (event) => {
    const spoken = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
    console.log("Heard:", spoken);

    activeBubbles.forEach((bObj) => {
        if (!bObj.popped && spoken.includes(bObj.word.toLowerCase())) {
            popBubble(bObj);
        }
    });
};

function spawnBubble(wordObj) {
    const bubble = document.createElement("div");
    bubble.classList.add("bubble");

    const img = document.createElement("img");
    img.src = wordObj.image;
    bubble.appendChild(img);

    bubble.style.left = Math.random() * (window.innerWidth - 150) + "px";
    gameArea.appendChild(bubble);

    const bubbleData = { bubble, word: wordObj.word, popped: false };
    activeBubbles.push(bubbleData);

    // Auto remove if not answered in 12s
    setTimeout(() => {
        if (bubble.parentNode && !bubbleData.popped) {
            bubble.remove();
            activeBubbles = activeBubbles.filter(b => b !== bubbleData);
        }
    }, 12000);
}

function popBubble(bubbleData) {
    if (bubbleData.popped) return;
    bubbleData.popped = true;
    bubbleData.bubble.classList.add("pop");

    setTimeout(() => {
        if (bubbleData.bubble.parentNode) bubbleData.bubble.remove();
    }, 500);

    score += 10;
    scoreBoard.textContent = "⭐ Score: " + score;
}

function startGame() {
    score = 0;
    scoreBoard.textContent = "⭐ Score: 0";
    gameArea.innerHTML = "";
    activeBubbles = [];
    spawnCount = 0;

    recognition.start();

    // spawn 4 bubbles immediately
    for (let i = 0; i < 4; i++) {
        spawnBubble(vocabWords[spawnCount % vocabWords.length]);
        spawnCount++;
    }

    // spawn new bubble every 5s
    bubbleInterval = setInterval(() => {
        if (spawnCount < vocabWords.length) {
            spawnBubble(vocabWords[spawnCount % vocabWords.length]);
            spawnCount++;
        } else {
            clearInterval(bubbleInterval);
        }
    }, 5000);
}

startBtn.addEventListener("click", startGame);
