(function () {
    "use strict";

    var STREAM_URL = "https://stream.lessthanze.ro/lessthanzero";
    var STATUS_URL = "https://stream.lessthanze.ro/status-json.xsl";
    var ARTWORK_URL = "https://itunes.apple.com/search";
    var POLL_MS = 15000;
    var LIVE_CHECK_MS = 60000;

    var PLAY_ICON = '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l10-5.5z"></path></svg>';
    var PAUSE_ICON = '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="2" width="4" height="12" rx="1"></rect><rect x="9" y="2" width="4" height="12" rx="1"></rect></svg>';

    var audio, nowPlaying, art, artPlaceholder, liveDot, liveLabel;
    var playButtons = [];
    var lastTitle = null;

    function renderButton(btn, isPlaying) {
        var label = btn.getAttribute("data-ltz-play-label");
        if (label) {
            btn.innerHTML = (isPlaying ? PAUSE_ICON : PLAY_ICON) + " " + (isPlaying ? "Listening&hellip;" : label);
        } else {
            btn.innerHTML = isPlaying ? PAUSE_ICON : PLAY_ICON;
        }
        btn.setAttribute("aria-label", isPlaying ? "Pause live stream" : "Play live stream");
    }

    function setPlaying(isPlaying) {
        for (var i = 0; i < playButtons.length; i++) renderButton(playButtons[i], isPlaying);
    }

    function toggle() {
        if (audio.paused) {
            if (!audio.src) audio.src = STREAM_URL;
            audio.play().catch(function () {});
        } else {
            audio.pause();
        }
    }

    function showArt(url) {
        if (url) {
            art.src = url;
            art.hidden = false;
            artPlaceholder.style.display = "none";
        } else {
            art.hidden = true;
            artPlaceholder.style.display = "flex";
        }
    }

    function fetchArtwork(title) {
        var xhr = new XMLHttpRequest();
        var url = ARTWORK_URL + "?term=" + encodeURIComponent(title) +
            "&media=music&entity=song&limit=1";
        xhr.open("GET", url, true);
        xhr.onload = function () {
            if (xhr.status !== 200) { showArt(null); return; }
            try {
                var data = JSON.parse(xhr.responseText);
                var hit = data.results && data.results[0];
                var artwork = hit && hit.artworkUrl100;
                showArt(artwork ? artwork.replace("100x100bb", "300x300bb") : null);
            } catch (e) {
                showArt(null);
            }
        };
        xhr.onerror = function () { showArt(null); };
        xhr.send();
    }

    function pollNowPlaying() {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", STATUS_URL, true);
        xhr.onload = function () {
            if (xhr.status !== 200) return;
            try {
                var data = JSON.parse(xhr.responseText);
                var title = data.icestats && data.icestats.source && data.icestats.source.title;
                nowPlaying.textContent = title ? title : "Less Than Zero";
                if (title && title !== lastTitle) {
                    lastTitle = title;
                    fetchArtwork(title);
                } else if (!title) {
                    lastTitle = null;
                    showArt(null);
                }
            } catch (e) {}
        };
        xhr.send();
    }

    // The show broadcasts live Thursdays 7-9pm UK time; outside that window
    // the stream is the 24/7 archive jukebox, not a live broadcast.
    function isLiveNow() {
        var parts = new Intl.DateTimeFormat("en-GB", {
            timeZone: "Europe/London",
            weekday: "short",
            hour: "2-digit",
            hour12: false
        }).formatToParts(new Date());
        var weekday, hour;
        for (var i = 0; i < parts.length; i++) {
            if (parts[i].type === "weekday") weekday = parts[i].value;
            if (parts[i].type === "hour") hour = parseInt(parts[i].value, 10);
        }
        return weekday === "Thu" && hour >= 19 && hour < 21;
    }

    function updateLiveStatus() {
        if (!liveDot || !liveLabel) return;
        if (isLiveNow()) {
            liveDot.hidden = false;
            liveLabel.textContent = "Live now";
        } else {
            liveDot.hidden = true;
            liveLabel.textContent = "24/7 · archive shuffle";
        }
    }

    function init() {
        audio = document.getElementById("ltz-audio");
        nowPlaying = document.getElementById("ltz-now-playing");
        art = document.getElementById("ltz-art");
        artPlaceholder = document.getElementById("ltz-art-placeholder");
        liveDot = document.getElementById("ltz-live-dot");
        liveLabel = document.getElementById("ltz-live-label");
        playButtons = Array.prototype.slice.call(document.querySelectorAll("[data-ltz-play]"));
        if (!audio || !playButtons.length) return;

        for (var i = 0; i < playButtons.length; i++) {
            playButtons[i].addEventListener("click", toggle);
        }
        audio.addEventListener("play", function () { setPlaying(true); });
        audio.addEventListener("pause", function () { setPlaying(false); });
        setPlaying(false);

        updateLiveStatus();
        setInterval(updateLiveStatus, LIVE_CHECK_MS);

        pollNowPlaying();
        setInterval(pollNowPlaying, POLL_MS);
    }

    window.addEventListener("DOMContentLoaded", init);
})();
