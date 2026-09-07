(function () {
  "use strict";
  const poem = window.MODERN_POETRY;
  const recitation = document.getElementById("recitation-audio");
  const music = document.getElementById("music-audio");
  const video = document.getElementById("background-video");
  const track = document.getElementById("scroll-track");
  const viewport = document.getElementById("scroll-viewport");
  const startOverlay = document.getElementById("start-overlay");
  const endOverlay = document.getElementById("end-overlay");
  const startButton = document.getElementById("start-button");
  const replayButton = document.getElementById("replay-button");
  const playButton = document.getElementById("play-button");
  const soundButton = document.getElementById("sound-button");
  const exitButton = document.getElementById("exit-button");
  const endExitButton = document.getElementById("end-exit-button");
  const pauseHint = document.getElementById("pause-hint");
  const duration = poem.duration;
  let started = false;
  let activeIndex = -2;
  let completionSent = false;

  // Keep the recitation in front while making the pastoral music clearly audible.
  music.volume = .30;

  poem.lines.forEach((line, index) => {
    const node = document.createElement("p");
    node.className = "poem-line";
    node.dataset.index = String(index);
    node.textContent = line.text;
    track.appendChild(node);
  });

  function postEvent(action, extra) {
    if (!window.parent || window.parent === window) return;
    window.parent.postMessage({ type: "intervention-story-event", story: "modern-poetry", action, elapsedTime: Number(recitation.currentTime.toFixed(2)), duration, ...extra }, window.location.origin);
  }

  function syncLoopedMedia(media, time) {
    if (!Number.isFinite(media.duration) || media.duration <= 0) return;
    const target = Math.max(0, time % media.duration);
    if (Math.abs(media.currentTime - target) > .18) media.currentTime = target;
  }

  function playCompanions() {
    syncLoopedMedia(music, recitation.currentTime);
    syncLoopedMedia(video, recitation.currentTime);
    music.play().catch(() => {});
    video.play().catch(() => {});
  }

  function pauseCompanions() { music.pause(); video.pause(); }

  function updateText(time, force) {
    const nextIndex = poem.getLineIndex(time);
    if (!force && nextIndex === activeIndex) return;
    activeIndex = nextIndex;
    const nodes = Array.from(track.children);
    nodes.forEach((node, index) => node.classList.toggle("is-read", index < nextIndex));
    nodes.forEach((node, index) => node.classList.toggle("is-active", index === nextIndex));
    const focusIndex = Math.max(0, nextIndex);
    const focusNode = nodes[focusIndex];
    if (focusNode) {
      const offset = viewport.clientHeight / 2 - focusNode.offsetTop - focusNode.offsetHeight / 2;
      track.style.transform = `translateY(${offset}px)`;
    }
  }

  function showHint(text) {
    pauseHint.textContent = text;
    pauseHint.classList.add("is-visible");
    window.clearTimeout(showHint.timer);
    showHint.timer = window.setTimeout(() => pauseHint.classList.remove("is-visible"), 900);
  }

  async function startPlayback(restart) {
    try {
      if (restart) {
        recitation.currentTime = 0;
        music.currentTime = 0;
        video.currentTime = 0;
      }
      await recitation.play();
      playCompanions();
      started = true;
      completionSent = false;
      startOverlay.classList.remove("is-visible");
      endOverlay.classList.remove("is-visible");
      playButton.textContent = "停";
      playButton.setAttribute("aria-label", "暂停");
      postEvent(restart ? "restarted" : "started");
    } catch (error) {
      console.error("无法播放朗诵音频：", error);
      showHint("请再次轻触开始");
    }
  }

  function togglePlayback() {
    if (!started) return startPlayback(false);
    if (recitation.paused) {
      recitation.play().then(() => { playCompanions(); playButton.textContent = "停"; playButton.setAttribute("aria-label", "暂停"); showHint("继续"); postEvent("resumed"); }).catch(console.error);
    } else {
      recitation.pause(); pauseCompanions(); playButton.textContent = "播"; playButton.setAttribute("aria-label", "继续播放"); showHint("已暂停"); postEvent("paused");
    }
  }

  function toggleMute() {
    recitation.muted = !recitation.muted;
    music.muted = recitation.muted;
    soundButton.textContent = recitation.muted ? "静" : "音";
    soundButton.setAttribute("aria-label", recitation.muted ? "取消静音" : "静音");
    postEvent(recitation.muted ? "muted" : "unmuted");
  }

  function exitExperience() {
    postEvent("exited", { progress: Number((recitation.currentTime / duration).toFixed(4)) });
    recitation.pause(); pauseCompanions();
    if (window.parent && window.parent !== window) return window.parent.postMessage({ type: "intervention-exit" }, window.location.origin);
    window.location.href = "/intervention";
  }

  function returnToPoetrySelection() {
    recitation.pause();
    pauseCompanions();
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "intervention-return-to-poetry-selection" }, window.location.origin);
      return;
    }
    window.location.href = "/intervention/story";
  }

  function finish() {
    pauseCompanions();
    playButton.textContent = "播";
    endOverlay.classList.add("is-visible");
    if (!completionSent) { completionSent = true; postEvent("completed", { progress: 1 }); }
  }

  function tick() {
    const time = Number.isFinite(recitation.currentTime) ? recitation.currentTime : 0;
    updateText(time, false);
    requestAnimationFrame(tick);
  }

  startButton.addEventListener("click", () => startPlayback(false));
  playButton.addEventListener("click", togglePlayback);
  replayButton.addEventListener("click", () => startPlayback(true));
  soundButton.addEventListener("click", toggleMute);
  exitButton.addEventListener("click", returnToPoetrySelection);
  endExitButton.addEventListener("click", returnToPoetrySelection);
  recitation.addEventListener("ended", finish);
  recitation.addEventListener("error", () => showHint("朗诵音频加载失败"));
  music.addEventListener("loadedmetadata", () => syncLoopedMedia(music, recitation.currentTime));
  video.addEventListener("loadedmetadata", () => syncLoopedMedia(video, recitation.currentTime));
  document.addEventListener("keydown", event => { if (event.code === "Space") { event.preventDefault(); togglePlayback(); } if (event.key === "Escape") exitExperience(); if (event.key.toLowerCase() === "m") toggleMute(); });
  document.addEventListener("visibilitychange", () => { if (document.hidden && started && !recitation.paused) { recitation.pause(); pauseCompanions(); playButton.textContent = "播"; } });
  window.addEventListener("resize", () => updateText(recitation.currentTime, true));

  updateText(0, true);
  requestAnimationFrame(tick);
})();
