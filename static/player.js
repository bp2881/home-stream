(function () {
  "use strict";
  const video       = document.getElementById("video");
  if (!video) return;
  const container   = document.getElementById("player-container");
  const controls    = document.getElementById("controls");
  const btnPlay     = document.getElementById("btn-play");
  const btnSkipBack = document.getElementById("btn-skip-back");
  const btnSkipFwd  = document.getElementById("btn-skip-fwd");
  const btnMute     = document.getElementById("btn-mute");
  const btnFS       = document.getElementById("btn-fullscreen");
  const btnCC       = document.getElementById("btn-cc");
  const ccPopup     = document.getElementById("cc-popup");
  const progressBar = document.getElementById("progress-bar");
  const progPlayed  = document.getElementById("progress-played");
  const progBuf     = document.getElementById("progress-buffered");
  const progThumb   = document.getElementById("progress-thumb");
  const timeCur     = document.getElementById("time-current");
  const timeTot     = document.getElementById("time-total");
  const volSlider   = document.getElementById("volume-slider");
  const osdEl       = document.getElementById("osd");
  const fsIconPath  = document.getElementById("fs-icon-path");
  const btnSettings = document.getElementById("btn-settings");
  const settingsPopup = document.getElementById("settings-popup");
  const speedOptions = document.getElementById("speed-options");
  const subsizeOptions = document.getElementById("subsize-options");
  function fmt(s) {
    s = Math.floor(s || 0);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
    return h > 0 ? `${h}:${pad(m)}:${pad(ss)}` : `${m}:${pad(ss)}`;
  }
  function pad(n) { return String(n).padStart(2, "0"); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function pct(v, t) { return t ? clamp(v / t * 100, 0, 100) : 0; }
  let osdTimer;
  function osd(txt) {
    if (!osdEl) return;
    osdEl.textContent = txt;
    osdEl.classList.add("osd--visible");
    clearTimeout(osdTimer);
    osdTimer = setTimeout(() => osdEl.classList.remove("osd--visible"), 800);
  }
  let hideTimer;
  function showControls() {
    controls.classList.add("visible");
    container.classList.add("controls-active");
    container.style.cursor = "";
    clearTimeout(hideTimer);
    if (!video.paused) hideTimer = setTimeout(hideControls, 3000);
  }
  function hideControls() {
    if (!video.paused) { 
      controls.classList.remove("visible"); 
      container.classList.remove("controls-active");
      container.style.cursor = "none"; 
    }
  }
  container.addEventListener("mousemove", showControls);
  container.addEventListener("mouseleave", hideControls);
  showControls();
  function togglePlay() { video.paused ? video.play() : video.pause(); }
  function updatePlayBtn() { btnPlay.textContent = video.paused ? "▶" : "⏸"; }
  btnPlay.addEventListener("click", togglePlay);
  container.addEventListener("click", function(e) {
    if (!controls.contains(e.target)) togglePlay();
  });
  video.addEventListener("play",  () => { updatePlayBtn(); showControls(); });
  video.addEventListener("pause", () => { updatePlayBtn(); showControls(); });
  function seekBy(s) {
    video.currentTime = clamp(video.currentTime + s, 0, video.duration || 0);
    osd((s > 0 ? "+" : "") + s + "s");
    showControls();
  }
  if (btnSkipBack) btnSkipBack.addEventListener("click", () => seekBy(-10));
  if (btnSkipFwd)  btnSkipFwd.addEventListener("click",  () => seekBy(10));
  let dragging = false;
  function applySeek(cx) {
    const r = progressBar.getBoundingClientRect();
    video.currentTime = clamp((cx - r.left) / r.width, 0, 1) * (video.duration || 0);
    updateProgress();
  }
  function updateProgress() {
    if (!video.duration) return;
    const p = pct(video.currentTime, video.duration);
    progPlayed.style.width = p + "%";
    progThumb.style.left   = p + "%";
    timeCur.textContent    = fmt(video.currentTime);
    if (video.buffered.length)
      progBuf.style.width = pct(video.buffered.end(video.buffered.length - 1), video.duration) + "%";
  }
  progressBar.addEventListener("mousedown",  e => { dragging = true; applySeek(e.clientX); });
  document.addEventListener("mousemove",     e => { if (dragging) applySeek(e.clientX); });
  document.addEventListener("mouseup",       () => { dragging = false; });
  progressBar.addEventListener("touchstart", e => { dragging = true; applySeek(e.touches[0].clientX); }, { passive: true });
  document.addEventListener("touchmove",     e => { if (dragging) applySeek(e.touches[0].clientX); }, { passive: true });
  document.addEventListener("touchend",      () => { dragging = false; });
  video.addEventListener("timeupdate", () => { if (!dragging) updateProgress(); });
  video.addEventListener("progress",   updateProgress);
  video.addEventListener("loadedmetadata", () => { timeTot.textContent = fmt(video.duration); updateProgress(); });
  function setVol(v) {
    video.volume = clamp(v, 0, 1);
    video.muted  = video.volume === 0;
    if (volSlider) volSlider.value = video.volume;
    updateVolBtn();
  }
  function updateVolBtn() {
    if (!btnMute) return;
    btnMute.textContent = (video.muted || video.volume === 0) ? "🔇"
                        : video.volume < 0.5 ? "🔉" : "🔊";
  }
  if (btnMute)    btnMute.addEventListener("click", () => { video.muted = !video.muted; updateVolBtn(); });
  if (volSlider)  volSlider.addEventListener("input", () => setVol(parseFloat(volSlider.value)));
  video.addEventListener("volumechange", updateVolBtn);
  const FS_ENTER = "M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z";
  const FS_EXIT  = "M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z";
  function toggleFS() {
    document.fullscreenElement ? document.exitFullscreen() : container.requestFullscreen();
  }
  if (btnFS) btnFS.addEventListener("click", toggleFS);
  document.addEventListener("fullscreenchange", () => {
    if (fsIconPath) fsIconPath.setAttribute("d", document.fullscreenElement ? FS_EXIT : FS_ENTER);
  });
  let currentTrack = -1;  
  function setTrack(idx) {
    currentTrack = idx;
    const tracks = video.textTracks;
    for (let i = 0; i < tracks.length; i++) {
      tracks[i].mode = (i === idx) ? "showing" : "hidden";
    }
    if (btnCC) btnCC.classList.toggle("ctrl-btn--cc-on", idx >= 0);
    if (ccPopup) {
      ccPopup.querySelectorAll(".cc-option").forEach(el => {
        el.classList.toggle("cc-option--active", parseInt(el.dataset.idx) === idx);
      });
    }
  }
  function initSubtitleTracks() {
    const tracks = video.textTracks;
    if (!tracks.length) return;
    for (let i = 0; i < tracks.length; i++) tracks[i].mode = "hidden";
    if (window.TRACK_COUNT > 0) setTrack(0);
  }
  video.textTracks.addEventListener("addtrack", function() {
    clearTimeout(window._trackInitTimer);
    window._trackInitTimer = setTimeout(initSubtitleTracks, 50);
  });
  video.addEventListener("loadeddata", initSubtitleTracks);
  if (video.readyState >= 2) initSubtitleTracks();
  if (btnCC && ccPopup) {
    btnCC.addEventListener("click", function(e) {
      e.stopPropagation();
      ccPopup.classList.toggle("cc-popup--open");
    });
    ccPopup.addEventListener("click", function(e) {
      const opt = e.target.closest(".cc-option");
      if (!opt) return;
      setTrack(parseInt(opt.dataset.idx));
      ccPopup.classList.remove("cc-popup--open");
    });
    document.addEventListener("click", () => ccPopup.classList.remove("cc-popup--open"));
  }
  function toggleCC() {
    const tracks = video.textTracks;
    if (!tracks.length) return;
    if (currentTrack >= 0) { setTrack(-1); osd("CC off"); }
    else { setTrack(0); osd("CC on"); }
  }
  if (btnSettings && settingsPopup) {
    btnSettings.addEventListener("click", function(e) {
      e.stopPropagation();
      settingsPopup.classList.toggle("cc-popup--open");
      if (ccPopup) ccPopup.classList.remove("cc-popup--open");
    });
    settingsPopup.addEventListener("click", function(e) {
      e.stopPropagation(); 
    });
    document.addEventListener("click", () => settingsPopup.classList.remove("cc-popup--open"));
  }
  const speedSlider = document.getElementById("speed-slider");
  const speedVal = document.getElementById("speed-val");
  function setSpeed(v) {
    video.playbackRate = v;
    if (speedSlider) speedSlider.value = v;
    if (speedVal) speedVal.textContent = v.toFixed(2) + "x";
    osd(v.toFixed(2) + "x");
  }
  if (speedSlider) {
    speedSlider.addEventListener("input", function() {
      setSpeed(parseFloat(this.value));
    });
  }
  const subsizeSlider = document.getElementById("subsize-slider");
  const subsizeVal = document.getElementById("subsize-val");
  function setSubSize(v) {
    document.documentElement.style.setProperty("--sub-size", v + "%");
    if (subsizeSlider) subsizeSlider.value = v;
    if (subsizeVal) subsizeVal.textContent = v + "%";
  }
  if (subsizeSlider) {
    subsizeSlider.addEventListener("input", function() {
      setSubSize(parseInt(this.value));
    });
  }
  document.addEventListener("keydown", function(e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    switch (e.key) {
      case " ": case "k": e.preventDefault(); togglePlay(); osd(video.paused ? "⏸" : "▶"); break;
      case "j": e.preventDefault(); seekBy(-10); break;
      case "l": e.preventDefault(); seekBy(10); break;
      case "ArrowLeft":  e.preventDefault(); seekBy(-5); break;
      case "ArrowRight": e.preventDefault(); seekBy(5); break;
      case "ArrowUp":    e.preventDefault(); setVol(video.volume + 0.05); osd("🔊 " + Math.round(video.volume * 100) + "%"); showControls(); break;
      case "ArrowDown":  e.preventDefault(); setVol(video.volume - 0.05); osd("🔉 " + Math.round(video.volume * 100) + "%"); showControls(); break;
      case "m": video.muted = !video.muted; osd(video.muted ? "🔇 Muted" : "🔊 Unmuted"); break;
      case "f": toggleFS(); break;
      case "c": toggleCC(); break;
      case ">": 
      case ".": {
        if (!video.paused && e.key === ">" || e.shiftKey) {
          setSpeed(Math.min(3, video.playbackRate + 0.25));
        } else if (e.key === "." && video.paused) {
          video.currentTime = Math.min(video.duration, video.currentTime + 1/30);
        }
        break;
      }
      case "<":
      case ",": {
        if (!video.paused && e.key === "<" || e.shiftKey) {
          setSpeed(Math.max(0.25, video.playbackRate - 0.25));
        } else if (e.key === "," && video.paused) {
          video.currentTime = Math.max(0, video.currentTime - 1/30);
        }
        break;
      }
      default:
        if (e.key >= "0" && e.key <= "9") {
          e.preventDefault();
          video.currentTime = (parseInt(e.key) / 10) * (video.duration || 0);
          osd(e.key + "0%"); showControls();
        }
    }
  });
  updatePlayBtn();
  updateVolBtn();
})();