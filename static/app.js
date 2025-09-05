const el = (id) => document.getElementById(id);
const $text = el('text');
const $voice = el('voice');
const $format = el('format');
const $btn = el('speak');
const audio = el("audio");
const $status = el('status');
const playPauseBtn = el("play-pause");
const progress = el("progress");
const currentTimeEl = el("current-time");
const durationEl = el("duration");
const volume = el("volume");

const downloadBtn = document.getElementById("download-link");
const downloadContainer = document.getElementById("download-container");

async function generate() {
    const text = $text.value.trim();
    if (!text) { $status.textContent = 'Please enter some text.'; return; }

    $btn.disabled = true;
    $status.textContent = 'Generating…';

    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice: $voice.value, format: $format.value })
        });

        const data = await res.json();
        if (!res.ok || !data.ok) {
            throw new Error(data.error || 'Unknown error');
        }

        // ✅ Backend gave us a URL, fetch that audio file
        const audioUrl = data.url;
        audio.src = audioUrl;
        await audio.play();

        // Show audio player and set download
        document.querySelector(".audio-player").classList.add("active");
        playPauseBtn.innerHTML = "&#10074;&#10074;";


downloadContainer.style.display = "block";
downloadBtn.href = audioUrl;                     // Correct variable
downloadBtn.download = `tts_audio.${$format.value}`; // Correct template literal

        $status.textContent = 'Ready.';
    } catch (err) {
        console.error(err);
        $status.textContent = 'Error: ' + err.message;
    } finally {
        $btn.disabled = false;
    }
}


// Play/pause toggle
playPauseBtn.addEventListener("click", () => {
    if (audio.paused) {
        audio.play();
        playPauseBtn.innerHTML = "&#10074;&#10074;";
    } else {
        audio.pause();
        playPauseBtn.innerHTML = "&#9658;";
    }
});

// Audio progress & time
audio.addEventListener("timeupdate", () => {
    const progressPercent = (audio.currentTime / audio.duration) * 100;
    progress.value = progressPercent;
    currentTimeEl.textContent = formatTime(audio.currentTime);
    durationEl.textContent = formatTime(audio.duration);
});
progress.addEventListener("input", () => {
    audio.currentTime = (progress.value / 100) * audio.duration;
});
volume.addEventListener("input", () => { audio.volume = volume.value; });

function formatTime(seconds) {
    if (isNaN(seconds)) return "0:00";
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60).toString().padStart(2, "0");
    return `${minutes}:${secs}`;
}
audio.addEventListener("loadedmetadata", () => { durationEl.textContent = formatTime(audio.duration); });
audio.addEventListener("loadeddata", () => { progress.value = 0; currentTimeEl.textContent = "0:00"; });
audio.addEventListener("ended", () => { playPauseBtn.innerHTML = "&#9658;"; });

$btn.addEventListener('click', generate);
