(function () {
  const audio = document.getElementById("audio-player");
  const canvas = document.getElementById("visualizer");
  if (!audio || !canvas) return;

  const playBtn = document.getElementById("play-btn");
  const iconPlay = document.getElementById("icon-play");
  const iconPause = document.getElementById("icon-pause");
  const seekBar = document.getElementById("seek-bar");
  const timeCurrent = document.getElementById("time-current");
  const timeTotal = document.getElementById("time-total");
  const expandBtn = document.getElementById("expand-player-btn");
  const playerSection = document.getElementById("player-section");
  const iconExpand = document.getElementById("icon-expand");
  const iconCollapse = document.getElementById("icon-collapse");
  const playerStatus = document.getElementById("player-status");
  const lyricsScroll = document.getElementById("lyrics-scroll");
  const lyricLines = lyricsScroll ? Array.from(lyricsScroll.querySelectorAll(".lyric-line")) : [];
  const volumeBar = document.getElementById("volume-bar");
  const muteBtn = document.getElementById("mute-btn");
  const iconVolume = document.getElementById("icon-volume");
  const iconMuted = document.getElementById("icon-muted");
  const skipZones = Array.from(document.querySelectorAll(".visualizer-skip-zone"));

  function formatTime(sec) {
    if (!isFinite(sec)) return "0:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  function setVolumeUi(isMuted) {
    if (!iconVolume || !iconMuted) return;
    if (isMuted) {
      iconVolume.style.display = "none";
      iconMuted.style.display = "block";
    } else {
      iconVolume.style.display = "block";
      iconMuted.style.display = "none";
    }
    if (muteBtn) {
      muteBtn.setAttribute("aria-pressed", isMuted ? "true" : "false");
    }
  }

  function setVolumeFill() {
    if (!volumeBar) return;
    const fill = volumeBar.querySelector(".volume-bar-fill");
    const thumb = volumeBar.querySelector(".volume-bar-thumb");
    const level = audio.muted ? 0 : Math.max(0, Math.min(1, audio.volume || 0));
    const percent = Math.round(level * 100);
    if (fill) {
      fill.style.height = `${percent}%`;
    }
    if (thumb) {
      thumb.style.bottom = `calc(${percent}% - 6px)`;
    }
    volumeBar.setAttribute("aria-valuenow", percent);
  }

  function setExpandedState(isExpanded) {
    if (!playerSection) return;
    playerSection.classList.toggle("is-expanded", isExpanded);
    document.body.classList.toggle("player-expanded-open", isExpanded);
    if (expandBtn) {
      expandBtn.setAttribute("aria-pressed", isExpanded ? "true" : "false");
      expandBtn.setAttribute("aria-label", isExpanded ? "خروج از حالت بزرگنمایی" : "بزرگنمایی بخش پخش");
    }
    if (iconExpand && iconCollapse) {
      iconExpand.style.display = isExpanded ? "none" : "block";
      iconCollapse.style.display = isExpanded ? "block" : "none";
    }
  }

  if (expandBtn) {
    expandBtn.addEventListener("click", () => {
      const expanded = !playerSection.classList.contains("is-expanded");
      setExpandedState(expanded);
      if (expanded) {
        window.scrollTo({ top: playerSection.offsetTop - 24, behavior: "smooth" });
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && playerSection && playerSection.classList.contains("is-expanded")) {
      setExpandedState(false);
    }
  });

  if (volumeBar) {
    audio.volume = 0.75;
    setVolumeFill();

    let isDragging = false;
    const updateVolumeFromPointer = (clientY) => {
      const rect = volumeBar.getBoundingClientRect();
      const ratio = 1 - ((clientY - rect.top) / rect.height);
      const percent = Math.max(0, Math.min(100, Math.round(ratio * 100)));
      audio.volume = percent / 100;
      audio.muted = audio.volume === 0;
      setVolumeFill();
      setVolumeUi(audio.muted);
    };

    volumeBar.addEventListener("pointerdown", (event) => {
      isDragging = true;
      volumeBar.setPointerCapture(event.pointerId);
      updateVolumeFromPointer(event.clientY);
    });

    volumeBar.addEventListener("pointermove", (event) => {
      if (!isDragging) return;
      updateVolumeFromPointer(event.clientY);
    });

    const endDrag = () => {
      isDragging = false;
    };
    volumeBar.addEventListener("pointerup", endDrag);
    volumeBar.addEventListener("pointerleave", endDrag);
    volumeBar.addEventListener("pointercancel", endDrag);

    volumeBar.addEventListener("keydown", (event) => {
      if (event.key === "ArrowUp" || event.key === "ArrowRight") {
        event.preventDefault();
        audio.volume = Math.min(1, audio.volume + 0.05);
        setVolumeFill();
        setVolumeUi(audio.muted);
      } else if (event.key === "ArrowDown" || event.key === "ArrowLeft") {
        event.preventDefault();
        audio.volume = Math.max(0, audio.volume - 0.05);
        setVolumeFill();
        setVolumeUi(audio.muted);
      }
    });
  }

  function updatePlayState() {
    const ready = audio.readyState >= 2;
    playBtn.disabled = !ready;
    playBtn.style.opacity = ready ? "1" : "0.65";
    playBtn.style.cursor = ready ? "pointer" : "not-allowed";
    if (playerStatus) {
      if (audio.paused && !ready) {
        playerStatus.textContent = "در حال آماده‌سازی...";
      } else if (audio.paused && ready) {
        playerStatus.textContent = "آماده برای پخش";
      } else if (!audio.paused) {
        playerStatus.textContent = "در حال پخش";
      }
    }
  }

  // ---------- پخش/توقف ----------
  playBtn.addEventListener("click", () => {
    if (playBtn.disabled) return;
    if (audio.paused) {
      audio.play();
    } else {
      audio.pause();
    }
  });
  audio.addEventListener("canplay", updatePlayState);
  audio.addEventListener("loadeddata", updatePlayState);
  audio.addEventListener("loadedmetadata", updatePlayState);
  audio.addEventListener("progress", updatePlayState);
  audio.addEventListener("playing", updatePlayState);
  audio.addEventListener("ended", updatePlayState);
  audio.addEventListener("play", () => {
    iconPlay.style.display = "none";
    iconPause.style.display = "block";
  });
  audio.addEventListener("pause", () => {
    iconPlay.style.display = "block";
    iconPause.style.display = "none";
  });
  audio.addEventListener("waiting", () => {
    playBtn.disabled = true;
    playBtn.style.opacity = "0.65";
    playBtn.style.cursor = "not-allowed";
  });
  updatePlayState();

  audio.addEventListener("loadedmetadata", () => {
    seekBar.max = Number.isFinite(audio.duration) ? audio.duration : 100;
    seekBar.value = 0;
    timeTotal.textContent = formatTime(audio.duration);
  });

  audio.addEventListener("timeupdate", () => {
    if (!Number.isFinite(audio.duration)) return;
    seekBar.value = audio.currentTime;
    timeCurrent.textContent = formatTime(audio.currentTime);
    updateActiveLyric(audio.currentTime);
  });

  seekBar.addEventListener("input", () => {
    if (!Number.isFinite(audio.duration)) return;
    audio.currentTime = parseFloat(seekBar.value);
    timeCurrent.textContent = formatTime(audio.currentTime);
  });

  seekBar.addEventListener("change", () => {
    if (!Number.isFinite(audio.duration)) return;
    audio.currentTime = parseFloat(seekBar.value);
    timeCurrent.textContent = formatTime(audio.currentTime);
  });

  skipZones.forEach((zone) => {
    zone.addEventListener("click", () => {
      if (!Number.isFinite(audio.duration)) return;
      const delta = parseInt(zone.dataset.skip, 10);
      const nextTime = Math.min(audio.duration, Math.max(0, audio.currentTime + delta));
      audio.currentTime = nextTime;
      timeCurrent.textContent = formatTime(audio.currentTime);
      seekBar.value = nextTime;
    });
  });

  if (volumeBar) {
    audio.volume = 0.75;
    audio.muted = audio.volume === 0;
    setVolumeUi(audio.muted);
    setVolumeFill();
  }

  if (muteBtn) {
    muteBtn.addEventListener("click", () => {
      if (audio.muted) {
        audio.muted = false;
        if (audio.volume === 0) {
          audio.volume = 0.75;
        }
      } else {
        audio.muted = true;
      }
      if (volumeBar) {
        volumeBar.value = audio.muted ? 0 : audio.volume;
      }
      setVolumeUi(audio.muted);
      setVolumeFill();
    });
  }

  audio.addEventListener("volumechange", () => {
    setVolumeUi(audio.muted);
    setVolumeFill();
  });

  // ---------- سینک متن آهنگ ----------
  let activeLineIndex = -1;
  function updateActiveLyric(currentTime) {
    if (!lyricLines.length) return;
    let newIndex = -1;
    for (let i = 0; i < lyricLines.length; i++) {
      const t = parseFloat(lyricLines[i].dataset.time);
      if (currentTime >= t) newIndex = i;
      else break;
    }
    if (newIndex !== activeLineIndex) {
      if (activeLineIndex >= 0) lyricLines[activeLineIndex].classList.remove("active");
      if (newIndex >= 0) {
        lyricLines[newIndex].classList.add("active");
        lyricLines[newIndex].scrollIntoView({ behavior: "smooth", block: "center" });
      }
      activeLineIndex = newIndex;
    }
  }

  // کلیک روی یک خط از متن آهنگ → پرش پخش به همان لحظه
  lyricLines.forEach((line) => {
    line.addEventListener("click", () => {
      audio.currentTime = parseFloat(line.dataset.time);
      audio.play();
    });
  });

  // ---------- ویژوالایزر (Web Audio API) ----------
  const ctx2d = canvas.getContext("2d");
  let audioCtx, analyser, source, dataArray, bufferLength;
  let rafId = null;

  function resizeCanvas() {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    ctx2d.setTransform(ratio, 0, 0, ratio, 0, 0);
  }
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  function setupAudioGraph() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);

    source = audioCtx.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(audioCtx.destination);
  }

  function drawIdle() {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    ctx2d.clearRect(0, 0, width, height);

    const bgGradient = ctx2d.createRadialGradient(width * 0.5, height * 0.9, 0, width * 0.5, height * 0.9, width * 0.8);
    bgGradient.addColorStop(0, "rgba(216,180,106,0.16)");
    bgGradient.addColorStop(0.45, "rgba(216,180,106,0.06)");
    bgGradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx2d.fillStyle = bgGradient;
    ctx2d.fillRect(0, 0, width, height);

    ctx2d.strokeStyle = "rgba(216,180,106,0.26)";
    ctx2d.lineWidth = 2;
    ctx2d.beginPath();
    const midY = height * 0.48;
    for (let i = 0; i <= 90; i++) {
      const x = (i / 90) * width;
      const y = midY + Math.sin(i / 12) * 8 + Math.cos(i / 23) * 4;
      if (i === 0) {
        ctx2d.moveTo(x, y);
      } else {
        ctx2d.lineTo(x, y);
      }
    }
    ctx2d.stroke();
  }

  function drawBars() {
    rafId = requestAnimationFrame(drawBars);
    if (!analyser) return;

    analyser.getByteFrequencyData(dataArray);

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    ctx2d.clearRect(0, 0, width, height);

    const bgGradient = ctx2d.createRadialGradient(width * 0.5, height * 0.9, 0, width * 0.5, height * 0.9, width * 0.8);
    bgGradient.addColorStop(0, "rgba(216,180,106,0.16)");
    bgGradient.addColorStop(0.45, "rgba(216,180,106,0.08)");
    bgGradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx2d.fillStyle = bgGradient;
    ctx2d.fillRect(0, 0, width, height);

    const barCount = Math.min(72, bufferLength);
    const gap = 4;
    const barWidth = (width - gap * (barCount - 1)) / barCount;
    const maxHeight = height * 0.52;
    const midY = height * 0.5;

    for (let i = 0; i < barCount; i++) {
      const value = dataArray[i] / 255;
      const barHeight = Math.max(6, value * maxHeight);
      const x = i * (barWidth + gap);
      const y = midY - barHeight / 2;

      const gradient = ctx2d.createLinearGradient(0, y + barHeight, 0, y);
      gradient.addColorStop(0, "rgba(255,243,211,0.95)");
      gradient.addColorStop(0.5, "rgba(216,180,106,0.95)");
      gradient.addColorStop(1, "rgba(124,94,36,0.95)");
      ctx2d.fillStyle = gradient;
      ctx2d.fillRect(x, y, barWidth, barHeight);
    }

    ctx2d.strokeStyle = "rgba(255,243,211,0.7)";
    ctx2d.lineWidth = 2;
    ctx2d.beginPath();
    for (let i = 0; i <= barCount; i++) {
      const x = (i / barCount) * width;
      const value = dataArray[Math.min(i, barCount - 1)] / 255;
      const y = midY + Math.sin(i / 4 + performance.now() / 750) * (8 + value * 14);
      if (i === 0) {
        ctx2d.moveTo(x, y);
      } else {
        ctx2d.lineTo(x, y);
      }
    }
    ctx2d.stroke();
  }

  drawIdle();

  audio.addEventListener("play", () => {
    setupAudioGraph();
    if (audioCtx.state === "suspended") audioCtx.resume();
    if (!rafId) drawBars();
  });
  audio.addEventListener("pause", () => {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
      drawIdle();
    }
  });
  audio.addEventListener("ended", () => {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
      drawIdle();
    }
  });
})();
