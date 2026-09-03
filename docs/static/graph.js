(function () {
    "use strict";

    var GRAPH_URL = "/static/graph.json";

    var canvas, ctx, page, searchInput, searchResults, infoPanel;
    var width, height, dpr;
    var nodes = [], edges = [], renderEdges = [], nodeById = {};
    var numClusters = 1;
    var transform = d3.zoomIdentity;
    var simulation;
    var hoverNode = null;

    function clusterColor(i) {
        var hue = (i * (360 / Math.max(numClusters, 1))) % 360;
        return "hsl(" + hue.toFixed(0) + ", 55%, 55%)";
    }

    function resize() {
        var rect = page.getBoundingClientRect();
        width = rect.width;
        height = rect.height;
        dpr = Math.min(window.devicePixelRatio || 1, 2); // capped: 3x actual pixels to rasterize isn't worth it here
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + "px";
        canvas.style.height = height + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function radiusFor(d) {
        return Math.max(2.5, Math.sqrt(d.count) * 1.6);
    }

    function draw() {
        ctx.clearRect(0, 0, width, height);
        ctx.save();
        ctx.translate(transform.x, transform.y);
        ctx.scale(transform.k, transform.k);

        var maxWeight = 1;
        for (var i = 0; i < edges.length; i++) {
            if (edges[i].weight > maxWeight) maxWeight = edges[i].weight;
        }

        // the physics simulation uses every edge (needed for correct
        // clustering/layout), but only draw the stronger half — the rest
        // are near-invisible anyway (alpha < ~0.06) and it roughly halves
        // the per-frame draw calls
        ctx.lineCap = "round";
        for (i = 0; i < renderEdges.length; i++) {
            var e = renderEdges[i];
            var s = e.source, t = e.target;
            if (typeof s !== "object" || typeof t !== "object") continue;
            var frac = Math.min(1, e.weight / maxWeight);
            ctx.strokeStyle = "rgba(60, 70, 80, " + (0.04 + frac * 0.35).toFixed(3) + ")";
            ctx.lineWidth = 0.5 + frac * 2;
            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(t.x, t.y);
            ctx.stroke();
        }

        for (i = 0; i < nodes.length; i++) {
            var n = nodes[i];
            var r = radiusFor(n);
            ctx.beginPath();
            ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = clusterColor(n.cluster);
            ctx.globalAlpha = (hoverNode && hoverNode !== n) ? 0.35 : 1;
            ctx.fill();
            if (n === hoverNode) {
                ctx.lineWidth = 2 / transform.k;
                ctx.strokeStyle = "#212529";
                ctx.stroke();
            }
            ctx.globalAlpha = 1;
        }

        // labels for larger nodes only, and always for the hovered node —
        // skipped entirely while the simulation is still actively moving:
        // text is unreadable mid-motion anyway, and it's the most expensive
        // thing drawn per frame
        var settled = !simulation || simulation.alpha() < 0.05;
        if (settled) {
            ctx.font = "11px 'Nunito', system-ui, sans-serif";
            ctx.fillStyle = "#212529";
            for (i = 0; i < nodes.length; i++) {
                n = nodes[i];
                r = radiusFor(n);
                if (n === hoverNode || (r > 9 && transform.k > 0.6)) {
                    ctx.fillText(n.name, n.x + r + 3, n.y + 3);
                }
            }
        } else if (hoverNode) {
            ctx.font = "11px 'Nunito', system-ui, sans-serif";
            ctx.fillStyle = "#212529";
            ctx.fillText(hoverNode.name, hoverNode.x + radiusFor(hoverNode) + 3, hoverNode.y + 3);
        }

        ctx.restore();
    }

    function toGraphCoords(px, py) {
        return [(px - transform.x) / transform.k, (py - transform.y) / transform.k];
    }

    function findNode(px, py) {
        // built lazily, only when actually hit-testing (hover/click/drag) —
        // rebuilding this every physics tick was the main cause of jerkiness
        var qt = d3.quadtree(nodes, function (d) { return d.x; }, function (d) { return d.y; });
        var p = toGraphCoords(px, py);
        var best = null, bestDist = Infinity;
        qt.visit(function (node, x0, y0, x1, y1) {
            if (!node.length) {
                do {
                    var d = node.data;
                    var dx = d.x - p[0], dy = d.y - p[1];
                    var dist = dx * dx + dy * dy;
                    var r = radiusFor(d) + 4;
                    if (dist < r * r && dist < bestDist) {
                        best = d;
                        bestDist = dist;
                    }
                } while ((node = node.next));
            }
            return x0 > p[0] + 30 || x1 < p[0] - 30 || y0 > p[1] + 30 || y1 < p[1] - 30;
        });
        return best;
    }

    function showInfo(n) {
        document.getElementById("graph-info-name").textContent = n.name;
        var times = n.count === 1 ? "Played once" : "Played " + n.count + " times";
        document.getElementById("graph-info-count").textContent = times;
        document.getElementById("graph-info-search-link").href =
            "/archive.html?q=" + encodeURIComponent(n.name);
        infoPanel.hidden = false;
    }

    function focusNode(n) {
        hoverNode = n;
        showInfo(n);
        var scale = 1.6;
        var t = d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(scale)
            .translate(-n.x, -n.y);
        d3.select(canvas).transition().duration(500).call(zoomBehavior.transform, t);
    }

    var zoomBehavior;

    function setupInteraction() {
        var sel = d3.select(canvas);

        zoomBehavior = d3.zoom()
            .scaleExtent([0.15, 8])
            .on("zoom", function (event) {
                transform = event.transform;
                draw();
            });
        sel.call(zoomBehavior);
        // the simulation centers itself on graph-space (0,0) — without this,
        // that origin lands at the canvas's top-left pixel instead of its middle
        sel.call(zoomBehavior.transform, d3.zoomIdentity.translate(width / 2, height / 2));

        var dragSim = d3.drag()
            .subject(function (event) {
                var m = toGraphCoords(event.x, event.y);
                return findNode(event.x, event.y) || { x: m[0], y: m[1] };
            })
            .on("start", function (event) {
                if (!event.subject.id) return;
                event.sourceEvent.stopPropagation(); // don't let d3-zoom's own pan also fire
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            })
            .on("drag", function (event) {
                if (!event.subject.id) return;
                var p = toGraphCoords(event.x, event.y);
                event.subject.fx = p[0];
                event.subject.fy = p[1];
            })
            .on("end", function (event) {
                if (!event.subject.id) return;
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            });
        sel.call(dragSim);

        sel.on("mousemove", function (event) {
            var n = findNode(event.offsetX, event.offsetY);
            if (n !== hoverNode) {
                hoverNode = n;
                canvas.style.cursor = n ? "pointer" : "grab";
                draw();
            }
        });

        sel.on("click", function (event) {
            var n = findNode(event.offsetX, event.offsetY);
            if (n) focusNode(n);
        });

        document.getElementById("graph-info-close").addEventListener("click", function () {
            infoPanel.hidden = true;
            hoverNode = null;
            draw();
        });

        window.addEventListener("resize", function () {
            resize();
            draw();
        });
    }

    function setupSearch() {
        searchInput.addEventListener("input", function () {
            var q = searchInput.value.trim().toLowerCase();
            searchResults.innerHTML = "";
            if (!q) return;
            var hits = nodes.filter(function (n) {
                return n.name.toLowerCase().indexOf(q) !== -1;
            });
            hits.sort(function (a, b) { return b.count - a.count; });
            hits.slice(0, 8).forEach(function (n) {
                var row = document.createElement("div");
                row.className = "graph-search-hit";
                row.textContent = n.name;
                row.addEventListener("click", function () {
                    searchResults.innerHTML = "";
                    searchInput.value = n.name;
                    focusNode(n);
                });
                searchResults.appendChild(row);
            });
        });
    }

    function init() {
        page = document.getElementById("graph-page");
        canvas = document.getElementById("graph-canvas");
        ctx = canvas.getContext("2d");
        searchInput = document.getElementById("graph_search");
        searchResults = document.getElementById("graph_search_results");
        infoPanel = document.getElementById("graph-info");
        if (!page || !canvas) return;

        resize();

        fetch(GRAPH_URL).then(function (r) { return r.json(); }).then(function (data) {
            nodes = data.nodes;
            edges = data.edges;
            nodeById = {};
            nodes.forEach(function (n) { nodeById[n.id] = n; });
            numClusters = d3.max(nodes, function (n) { return n.cluster; }) + 1;

            edges.forEach(function (e) {
                e.source = nodeById[e.source];
                e.target = nodeById[e.target];
            });
            edges = edges.filter(function (e) { return e.source && e.target; });
            var sortedWeights = edges.map(function (e) { return e.weight; }).sort(function (a, b) { return a - b; });
            var medianWeight = sortedWeights[Math.floor(sortedWeights.length / 2)] || 0;
            renderEdges = edges.filter(function (e) { return e.weight >= medianWeight; });

            simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(edges)
                    .distance(function (d) { return Math.max(20, 90 / Math.sqrt(d.weight)); })
                    .strength(function (d) { return Math.min(1, d.weight / 8); }))
                .force("charge", d3.forceManyBody().strength(-25).distanceMax(400).theta(1.1))
                .force("center", d3.forceCenter(0, 0))
                .force("collide", d3.forceCollide().radius(function (d) { return radiusFor(d) + 1; }))
                .alphaDecay(0.05) // settle faster (~90 ticks vs d3's default ~300) — smoother startup
                .on("tick", draw);

            setupInteraction();
            setupSearch();
        });
    }

    window.addEventListener("DOMContentLoaded", init);
})();
