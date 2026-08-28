/* MindBloom adapted for the intervention module. Original work: David W Mpangala (MIT). */
"use strict";

const MAX_FLOWERS = 24;
const WINNING_FLOWERS = 20;
const palettes = [
  ["#ff6b9d", "#c2185b", "#880e4f"], ["#ff9a3c", "#e65100", "#bf360c"],
  ["#ffe14d", "#f9a825", "#e65100"], ["#a78bfa", "#5b21b6", "#3730a3"],
  ["#38bdf8", "#0369a1", "#01579b"], ["#4ade80", "#15803d", "#064e3b"],
  ["#fb7185", "#be123c", "#881337"], ["#f472b6", "#9d174d", "#701a75"],
];
const playerTwoPalettes = [["#f472b6", "#9d174d", "#701a75"], ["#e879f9", "#7e22ce", "#581c87"], ["#f9a8d4", "#be185d", "#9d174d"]];

const dom = {
  garden: document.querySelector("#garden"), empty: document.querySelector("#garden-empty"), input: document.querySelector("#word-input"),
  chars: document.querySelector("#char-count"), message: document.querySelector("#message"), solo: document.querySelector("#solo-button"),
  two: document.querySelector("#two-player-button"), turn: document.querySelector("#turn-banner"), turnText: document.querySelector("#turn-text"),
  turnDot: document.querySelector(".turn-dot"), playerOneLabel: document.querySelector("#player-one-label"), p1: document.querySelector("#player-one-score"),
  p2: document.querySelector("#player-two-score"), p2Card: document.querySelector("#player-two-card"), flowers: document.querySelector("#flower-count"),
  sound: document.querySelector("#sound-button"), help: document.querySelector("#help-modal"), winner: document.querySelector("#winner-modal"),
  winnerTitle: document.querySelector("#winner-title"), winnerText: document.querySelector("#winner-text"), sky: document.querySelector("#sky"),
};

let mode = 1;
let currentPlayer = 1;
let scores = [0, 0];
let flowerCount = 0;
let lastFlower = null;
let soundEnabled = true;
let messageTimer;
const usedWords = new Set();

function characterCount(value) { return Array.from(value).length; }
function normaliseWord(value) {
  return value.trim().toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
}
function scoreFor(word) {
  const length = characterCount(word);
  if (length <= 3) return 1;
  if (length <= 5) return 2;
  if (length <= 7) return 3;
  if (length <= 10) return 4;
  return 5;
}
function dimensionsFor(word) {
  const length = characterCount(word);
  if (length <= 3) return { stem: 43, radius: 14, petals: 5 };
  if (length <= 5) return { stem: 58, radius: 18, petals: 6 };
  if (length <= 7) return { stem: 74, radius: 23, petals: 7 };
  if (length <= 10) return { stem: 90, radius: 28, petals: 8 };
  return { stem: 108, radius: 34, petals: 10 };
}
function showMessage(text, color = "#237a3d") {
  dom.message.textContent = text;
  dom.message.style.color = color;
  window.clearTimeout(messageTimer);
  messageTimer = window.setTimeout(() => { dom.message.textContent = ""; }, 3200);
}
function updateScores() {
  const previous = [Number(dom.p1.textContent), Number(dom.p2.textContent)];
  dom.p1.textContent = String(scores[0]);
  dom.p2.textContent = String(scores[1]);
  dom.flowers.textContent = String(flowerCount);
  [dom.p1, dom.p2].forEach((element, index) => {
    if (scores[index] !== previous[index]) {
      element.classList.remove("is-bumping");
      void element.offsetWidth;
      element.classList.add("is-bumping");
    }
  });
}
function updateTurn() {
  const second = currentPlayer === 2;
  dom.turnText.textContent = second ? "玩家 2 的回合" : "玩家 1 的回合";
  dom.turn.style.borderColor = second ? "#d94f8d" : "#3f9a58";
  dom.turn.style.color = second ? "#bd266d" : "#20703a";
  dom.turnDot.style.background = second ? "#d94f8d" : "#3f9a58";
}
function createFlowerHead(radius, petals, palette, points) {
  const size = radius * 3.6;
  const center = size / 2;
  const petalRadius = radius * .62;
  const orbit = radius * .72;
  const shapes = [];
  for (let index = 0; index < petals; index += 1) {
    const angle = (360 / petals) * index - 90;
    const radians = angle * Math.PI / 180;
    const x = center + Math.cos(radians) * orbit;
    const y = center + Math.sin(radians) * orbit;
    shapes.push(`<ellipse cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" rx="${petalRadius.toFixed(1)}" ry="${(petalRadius * .68).toFixed(1)}" fill="${palette[0]}" transform="rotate(${angle + 90} ${x.toFixed(1)} ${y.toFixed(1)})"/>`);
  }
  const centerRadius = radius * .45;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.ceil(size)}" height="${Math.ceil(size)}" viewBox="0 0 ${size} ${size}" aria-hidden="true">${shapes.join("")}<circle cx="${center}" cy="${center}" r="${centerRadius}" fill="${palette[2]}"/><circle cx="${center}" cy="${center - centerRadius * .25}" r="${centerRadius * .55}" fill="${palette[1]}" opacity=".4"/><text x="${center}" y="${center + 4}" text-anchor="middle" font-family="sans-serif" font-size="${Math.max(8, Math.round(centerRadius * .7))}" font-weight="700" fill="white">${points}</text></svg>`;
}
function createFlower(raw, clean, points) {
  const dimensions = dimensionsFor(clean);
  const collection = mode === 2 && currentPlayer === 2 ? playerTwoPalettes : palettes;
  const palette = collection[Math.floor(Math.random() * collection.length)];
  const flower = document.createElement("div");
  flower.className = "flower";
  flower.dataset.word = clean;
  flower.dataset.player = String(currentPlayer);
  flower.title = `“${raw}” · ${points} 分`;
  flower.style.setProperty("--sway", `${(2.5 + Math.random() * 2).toFixed(1)}s`);
  flower.style.setProperty("--delay", `${(Math.random() * 2).toFixed(1)}s`);

  const pointBadge = document.createElement("span");
  pointBadge.className = "flower__points";
  pointBadge.textContent = `${points} 分`;
  const head = document.createElement("div");
  head.className = "flower__head";
  head.innerHTML = createFlowerHead(dimensions.radius, dimensions.petals, palette, points);
  const stem = document.createElement("div");
  stem.className = "flower__stem";
  stem.style.width = `${Math.max(4, Math.round(dimensions.radius * .18))}px`;
  stem.style.height = `${dimensions.stem}px`;
  const label = document.createElement("span");
  label.className = "flower__word";
  label.textContent = characterCount(raw) > 10 ? `${Array.from(raw).slice(0, 9).join("")}…` : raw;
  flower.append(pointBadge, head, stem, label);
  return flower;
}
function playSound(points) {
  if (!soundEnabled) return;
  try {
    const context = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.connect(gain).connect(context.destination);
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime([261, 294, 329, 392, 523][points - 1], context.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(600, context.currentTime + .16);
    gain.gain.setValueAtTime(.14, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(.001, context.currentTime + .4);
    oscillator.start(); oscillator.stop(context.currentTime + .4);
  } catch (_) { /* Audio is an optional enhancement. */ }
}
function spawnParticles(points) {
  const icons = ["🌸", "✨", "🌺", "⭐", "🌼"];
  for (let index = 0; index <= points; index += 1) {
    const particle = document.createElement("span");
    particle.className = "particle";
    particle.textContent = icons[Math.floor(Math.random() * icons.length)];
    particle.style.left = `${32 + Math.random() * 36}%`;
    particle.style.top = `${42 + Math.random() * 15}%`;
    particle.style.animationDelay = `${index * .07}s`;
    document.body.append(particle);
    window.setTimeout(() => particle.remove(), 1500);
  }
}
function reportProgress(points) {
  if (window.parent !== window) {
    window.parent.postMessage({ type: "intervention-game-progress", payload: { flowers: flowerCount, scores: [...scores], points_awarded: points, mode: mode === 1 ? "solo" : "two_player" } }, window.location.origin);
  }
}
function plantWord() {
  const raw = dom.input.value.trim();
  const clean = normaliseWord(raw);
  if (!clean) return showMessage("请输入词语、汉字或数字。", "#b33b3b");
  if (characterCount(clean) < 2) return showMessage("至少输入两个字符，再试试看。", "#b33b3b");
  if (usedWords.has(clean)) return showMessage("这个词已经种下了，换一个试试吧！", "#b87818");
  if (flowerCount >= MAX_FLOWERS) return showMessage("花园已经开满啦，清空后可以重新种花。", "#b87818");

  const points = scoreFor(clean);
  const flower = createFlower(raw, clean, points);
  usedWords.add(clean);
  flowerCount += 1;
  dom.empty.style.display = "none";
  dom.garden.append(flower);
  lastFlower = flower;
  scores[currentPlayer - 1] += points;
  updateScores();
  spawnParticles(points);
  playSound(points);
  reportProgress(points);
  showMessage(`${["真好看！", "开花啦！", "很棒！", "温暖的词语！"][Math.floor(Math.random() * 4)]} +${points} 分`);

  if (mode === 2) {
    currentPlayer = currentPlayer === 1 ? 2 : 1;
    updateTurn();
    if (flowerCount >= WINNING_FLOWERS) window.setTimeout(showWinner, 350);
  }
  dom.input.value = "";
  dom.chars.textContent = "0";
  dom.input.focus();
}
function resetGarden() {
  scores = [0, 0];
  usedWords.clear();
  flowerCount = 0;
  currentPlayer = 1;
  lastFlower = null;
  [...dom.garden.querySelectorAll(".flower")].forEach((flower) => flower.remove());
  dom.empty.style.display = "block";
  updateScores();
  updateTurn();
}
function setMode(nextMode) {
  mode = nextMode;
  dom.solo.classList.toggle("is-active", mode === 1);
  dom.two.classList.toggle("is-active", mode === 2);
  dom.p2Card.classList.toggle("is-hidden", mode === 1);
  dom.turn.classList.toggle("is-visible", mode === 2);
  dom.playerOneLabel.textContent = mode === 1 ? "🌿 我的花园" : "🌿 玩家 1";
  resetGarden();
  showMessage(mode === 1 ? "慢慢种下属于你的花吧。" : "轮流输入词语，看看谁的花园更繁盛！");
  dom.input.focus();
}
function undoLast() {
  if (!lastFlower || !lastFlower.isConnected) return showMessage("还没有可以撤销的花朵。", "#777");
  const word = lastFlower.dataset.word;
  const player = Number(lastFlower.dataset.player);
  scores[player - 1] -= scoreFor(word);
  usedWords.delete(word);
  flowerCount -= 1;
  if (mode === 2) { currentPlayer = currentPlayer === 1 ? 2 : 1; updateTurn(); }
  const removed = lastFlower;
  lastFlower = null;
  removed.style.opacity = "0";
  removed.style.transform = "scaleY(0)";
  window.setTimeout(() => removed.remove(), 280);
  if (flowerCount === 0) dom.empty.style.display = "block";
  updateScores();
  showMessage("已撤销最后一朵花。", "#b87818");
}
function clearGarden() {
  if (!flowerCount) return showMessage("花园现在还是空的。", "#777");
  if (window.confirm("清空这座花园，重新开始吗？")) { resetGarden(); showMessage("花园已清空，随时可以种下新的词语。 "); }
}
function showWinner() {
  const [first, second] = scores;
  dom.winnerTitle.textContent = first === second ? "你们平分秋色！" : first > second ? "玩家 1 的花园胜出！" : "玩家 2 的花园胜出！";
  dom.winnerText.textContent = `一共种下了 ${flowerCount} 朵花 · ${first} 分比 ${second} 分`;
  dom.winner.hidden = false;
}
function drawSky() {
  const canvas = dom.sky;
  const context = canvas.getContext("2d");
  const scale = window.devicePixelRatio || 1;
  const width = canvas.offsetWidth;
  const height = canvas.offsetHeight;
  canvas.width = width * scale; canvas.height = height * scale;
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#ffe165"; context.beginPath(); context.arc(width - 50, 42, 21, 0, Math.PI * 2); context.fill();
  context.fillStyle = "rgba(255,255,255,.72)";
  [[32, 34, 1], [width * .4, 28, .8], [width * .68, 44, .65]].forEach(([x, y, size]) => {
    context.beginPath(); context.arc(x, y, 18 * size, 0, Math.PI * 2); context.arc(x + 22 * size, y - 8 * size, 22 * size, 0, Math.PI * 2); context.arc(x + 46 * size, y, 16 * size, 0, Math.PI * 2); context.fill();
  });
}

dom.input.addEventListener("input", () => { dom.chars.textContent = String(characterCount(dom.input.value)); });
dom.input.addEventListener("keydown", (event) => { if (event.key === "Enter") plantWord(); });
document.querySelector("#plant-button").addEventListener("click", plantWord);
dom.solo.addEventListener("click", () => setMode(1));
dom.two.addEventListener("click", () => setMode(2));
document.querySelector("#undo-button").addEventListener("click", undoLast);
document.querySelector("#clear-button").addEventListener("click", clearGarden);
dom.sound.addEventListener("click", () => { soundEnabled = !soundEnabled; dom.sound.textContent = soundEnabled ? "♪" : "♩̶"; dom.sound.setAttribute("aria-label", soundEnabled ? "关闭音效" : "开启音效"); showMessage(soundEnabled ? "音效已开启。" : "音效已关闭。", "#777"); });
document.querySelector("#how-to-button").addEventListener("click", () => { dom.help.hidden = false; });
document.querySelector("#close-help").addEventListener("click", () => { dom.help.hidden = true; dom.input.focus(); });
document.querySelector("#start-button").addEventListener("click", () => { dom.help.hidden = true; dom.input.focus(); });
dom.help.addEventListener("click", (event) => { if (event.target === dom.help) dom.help.hidden = true; });
document.querySelector("#play-again-button").addEventListener("click", () => { dom.winner.hidden = true; setMode(mode); });
window.addEventListener("resize", drawSky);
window.addEventListener("load", () => { drawSky(); window.setTimeout(() => { dom.help.hidden = false; }, 350); });
