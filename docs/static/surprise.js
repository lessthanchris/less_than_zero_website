(function () {
    "use strict";

    var SHOWS_LIST_URL = "/static/shows_list.json";
    var shows = null;

    function go() {
        if (shows && shows.length) {
            var pick = shows[Math.floor(Math.random() * shows.length)];
            window.location.href = "/" + pick + ".html";
            return;
        }
        fetch(SHOWS_LIST_URL).then(function (r) { return r.json(); }).then(function (data) {
            shows = data;
            go();
        });
    }

    function init() {
        var triggers = document.querySelectorAll("[data-surprise]");
        for (var i = 0; i < triggers.length; i++) {
            triggers[i].addEventListener("click", function (e) {
                e.preventDefault();
                go();
            });
        }
    }

    window.addEventListener("DOMContentLoaded", init);
})();
