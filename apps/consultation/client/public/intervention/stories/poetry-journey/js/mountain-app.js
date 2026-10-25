(function () {
  "use strict";

  const experience = window.MOUNTAIN_POETRY;
  if (!experience) return;

  const $ = (selector) => document.querySelector(selector);
  const recitation = $("#recitation-audio");
  const music = $("#music-audio");
  const video = $("#background-video");
  const stage = $("#poem-stage");
  const title = $("#poem-title");
  const author = $("#poem-author");
  const lines = $("#poem-lines");
  const startOverlay = $("#start-overlay");
  const endOverlay = $("#end-overlay");
  const startButton = $("#start-button");
  const replayButton = $("#replay-button");
  const playButton = $("#play-button");
  const soundButton = $("#sound-button");
  const exitButton = $("#exit-button");
  const endExitButton = $("#end-exit-button");
  const pauseHint = $("#pause-hint");

  let started = false;
  let currentChapter = -1;
  let completed = false;
  let outroStarted = false;
  let outroTimer = 0;

  music.volume = 0.14;
  recitation.volume = 1;

  function postEvent(event, details = {}) {
    window.parent.postMessage({ type: "intervention-story-event", story: "poetry-journey", event, details }, window.location.origin);
  }

  function syncMedia(media, targetTime) {
    if (!Number.isFinite(media.duration) || media.duration <= 0) return;
    const desired = targetTime % media.duration;
    if (Math.abs(media.currentTime - desired) > 0.18) media.currentTime = desired;
  }

  function playCompanions() {
    video.play().catch(() => {});
    music.play().catch(() => {});
  }

  function pauseCompanions() {
    video.pause();
    music.pause();
  }

  function buildChapter(index) {
    const chapter = experience.chapters[index];
    currentChapter = index;
    stage.classList.remove("is-ready", "is-dissolving", "is-outro");
    stage.dataset.chapter = chapter.id;
    stage.classList.toggle("has-many-lines", chapter.lines.length > 6);
    stage.classList.toggle("has-long-lines", chapter.lines.some((line) => line.text.length > 14));
    title.textContent = chapter.title;
    // Keep the ci's tune and subtitle together, with a separate subtitle row in portrait.
    const titleSeparator = chapter.title.indexOf("·");
    if (titleSeparator !== -1) {
      const separator = document.createElement("span");
      separator.className = "poem-title-separator";
      separator.textContent = "·";
      const detail = document.createElement("span");
      detail.className = "poem-title-detail";
      detail.textContent = chapter.title.slice(titleSeparator + 1);
      title.replaceChildren(chapter.title.slice(0, titleSeparator), separator, detail);
    }
    author.textContent = chapter.author;
    lines.replaceChildren(...chapter.lines.map((line) => {
      const element = document.createElement("p");
      element.className = "poem-line is-future";
      element.textContent = line.text;
      return element;
    }));
    void stage.offsetWidth;
    if (started) stage.classList.add("is-ready");
  }

  function updatePoetry(time) {
    const result = experience.getChapter(time);
    if (result.index !== currentChapter) buildChapter(result.index);
    const chapter = result.chapter;
    const lineElements = lines.children;
    chapter.lines.forEach((line, index) => {
      const element = lineElements[index];
      if (!element) return;
      element.classList.toggle("is-future", time < line.start);
      element.classList.toggle("is-active", time >= line.start && time < line.end);
      element.classList.toggle("is-read", time >= line.end);
      element.classList.toggle("is-dissolved", line.end < chapter.dissolveStart && time >= line.end + 1.35);
    });
    stage.classList.toggle("is-dissolving", time >= chapter.dissolveStart && time < chapter.end);
  }

  function showPauseHint() {
    pauseHint.classList.add("is-visible");
    window.setTimeout(() => pauseHint.classList.remove("is-visible"), 1200);
  }

  async function startPlayback(restart) {
    if (restart) {
      window.clearTimeout(outroTimer);
      outroStarted = false;
      recitation.currentTime = 0;
      syncMedia(music, 0);
      syncMedia(video, 0);
      completed = false;
      currentChapter = -1;
      endOverlay.hidden = true;
      endOverlay.classList.remove("is-visible");
    }
    started = true;
    startOverlay.hidden = true;
    stage.classList.add("is-ready");
    await recitation.play().catch(() => {});
    playCompanions();
    playButton.classList.add("is-playing");
    postEvent(restart ? "replay" : "play");
  }

  function togglePlayback() {
    if (!started) {
      startPlayback(false);
      return;
    }
    if (recitation.paused) {
      recitation.play().then(playCompanions).catch(() => {});
      playButton.classList.add("is-playing");
      postEvent("resume");
    } else {
      recitation.pause();
      pauseCompanions();
      playButton.classList.remove("is-playing");
      showPauseHint();
      postEvent("pause");
    }
  }

  function toggleSound() {
    const muted = !(recitation.muted && music.muted);
    recitation.muted = muted;
    music.muted = muted;
    soundButton.classList.toggle("is-muted", muted);
    soundButton.setAttribute("aria-pressed", String(muted));
    postEvent(muted ? "mute" : "unmute");
  }

  function finish() {
    if (completed) return;
    completed = true;
    recitation.pause();
    playButton.classList.remove("is-playing");
    endOverlay.hidden = false;
    endOverlay.classList.add("is-visible");
    postEvent("complete");
  }

  function beginOutro() {
    if (outroStarted || completed) return;
    outroStarted = true;
    recitation.pause();
    stage.classList.remove("is-dissolving");
    stage.classList.add("is-outro");
    outroTimer = window.setTimeout(finish, 2300);
  }

  function exitExperience() {
    window.parent.postMessage({ type: "intervention-exit" }, window.location.origin);
    if (window.parent === window) window.location.assign("/intervention");
  }

  function returnToPoetrySelection() {
    recitation.pause();
    pauseCompanions();
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "intervention-return-to-poetry-selection" }, window.location.origin);
      return;
    }
    window.location.assign("/intervention/story");
  }

  function tick() {
    const time = Math.min(recitation.currentTime, experience.duration);
    updatePoetry(time);
    requestAnimationFrame(tick);
  }

  startButton.addEventListener("click", () => startPlayback(true));
  replayButton.addEventListener("click", () => startPlayback(true));
  playButton.addEventListener("click", togglePlayback);
  soundButton.addEventListener("click", toggleSound);
  exitButton.addEventListener("click", returnToPoetrySelection);
  endExitButton.addEventListener("click", returnToPoetrySelection);

  recitation.addEventListener("timeupdate", () => {
    if (recitation.currentTime >= experience.duration) beginOutro();
  });
  recitation.addEventListener("ended", beginOutro);
  recitation.addEventListener("play", () => playButton.classList.add("is-playing"));
  recitation.addEventListener("pause", () => {
    if (!completed) playButton.classList.remove("is-playing");
  });
  recitation.addEventListener("error", () => { startButton.textContent = "朗诵音频无法加载"; });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && !recitation.paused) {
      recitation.pause();
      pauseCompanions();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.code === "Space" && event.target.tagName !== "INPUT") {
      event.preventDefault();
      togglePlayback();
    }
  });

  buildChapter(0);
  updatePoetry(0);
  requestAnimationFrame(tick);
})();
