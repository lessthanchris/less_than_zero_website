(function () {
    "use strict";

    var indexData = null;
    var artistsFlat = [];
    var tracksFlat = [];

    function fold(s) {
        if (!s) return "";
        s = s.normalize("NFKD").replace(/[^\x00-\x7F]/g, "");
        s = s.toLowerCase().replace(/[^\w]+/g, " ").trim();
        return s;
    }

    function loadIndex() {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "static/search_index.json", true);
        xhr.onload = function () {
            if (xhr.status === 200) {
                indexData = JSON.parse(xhr.responseText);
                var keys = Object.keys(indexData.artists);
                for (var i = 0; i < keys.length; i++) {
                    var e = indexData.artists[keys[i]];
                    artistsFlat.push({
                        key: keys[i],
                        artist: e.artist,
                        count: e.count,
                        shows: e.shows,
                        samples: e.samples || [],
                        _search: e._search || keys[i]
                    });
                }
                tracksFlat = indexData.tracks || [];
                if (document.getElementById("search_box").value) {
                    search();
                }
            }
        };
        xhr.send();
    }

    function escape(s) {
        if (!s) return "";
        return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function search() {
        var el = document.getElementById("song_list");
        var countEl = document.getElementById("songs_found");
        if (!indexData) {
            countEl.innerText = "loading...";
            if (!el.innerHTML) el.innerHTML = "<p class='text-muted'>Loading...</p>";
            return;
        }

        var q = fold(document.getElementById("search_box").value);
        if (!q) {
            el.innerHTML = "";
            countEl.innerText = "0";
            return;
        }

        var artistHits = [];
        for (var i = 0; i < artistsFlat.length; i++) {
            if (artistsFlat[i]._search.indexOf(q) !== -1) {
                artistHits.push(artistsFlat[i]);
            }
        }

        var trackHits = [];
        for (var j = 0; j < tracksFlat.length; j++) {
            if (tracksFlat[j]._fold.indexOf(q) !== -1) {
                trackHits.push(tracksFlat[j]);
            }
        }

        var total = artistHits.length + trackHits.length;
        countEl.innerText = total;

        var html = "";
        if (artistHits.length) {
            html += "<h4>Artist matches (" + artistHits.length + ")</h4>";
            for (var i = 0; i < artistHits.length; i++) {
                var e = artistHits[i];
                var samples = "";
                for (var s = 0; s < e.samples.length; s++) {
                    samples += "<span class='archive-track'>" + escape(e.samples[s].date) + " &mdash; " + escape(e.samples[s].track) + "</span><br>";
                }
                html += "<div class='archive-artist'><span class='archive-count'>" + e.count + "</span> <strong>" + escape(e.artist) + "</strong> <span class='archive-shows'>(" + e.shows.length + " show" + (e.shows.length !== 1 ? "s" : "") + ")</span>" + (samples ? "<div class='archive-detail'>" + samples + "</div>" : "") + "</div>";
            }
        }
        if (trackHits.length) {
            html += "<h4 class='mt-3'>Track matches (" + trackHits.length + ")</h4>";
            // group by artist regardless of position in trackHits — it's in
            // original show order, not sorted by artist, so a naive
            // consecutive-run grouping would split one artist into several
            // groups whenever another artist's match falls between them
            var groups = [];
            var groupByArtist = {};
            for (var j = 0; j < trackHits.length; j++) {
                var t = trackHits[j];
                var g = groupByArtist[t._artist];
                if (!g) {
                    g = { artist: t.artist, tracks: [] };
                    groupByArtist[t._artist] = g;
                    groups.push(g);
                }
                g.tracks.push(t);
            }
            for (var gi = 0; gi < groups.length; gi++) {
                var grp = groups[gi];
                html += "<div class='archive-artist-group'><strong>" + escape(grp.artist) + "</strong><div class='archive-tracklist'>";
                for (var ti = 0; ti < grp.tracks.length; ti++) {
                    var tt = grp.tracks[ti];
                    html += "<span class='archive-track'>" + escape(tt.date) + " &mdash; " + escape(tt.track) + "</span><br>";
                }
                html += "</div></div>";
            }
        }
        if (!html) html = "<p class='text-muted'>No results found.</p>";
        el.innerHTML = html;
    }

    function prefillFromQuery() {
        var params = new URLSearchParams(window.location.search);
        var q = params.get("q");
        if (q) {
            var box = document.getElementById("search_box");
            if (box) box.value = q;
        }
    }

    window.search = search;
    prefillFromQuery();
    window.addEventListener("load", loadIndex);
})();