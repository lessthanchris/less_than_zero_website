"""Build the artist co-occurrence graph for the /graph.html visualization.

Standalone, like played_archive.py — not part of app.py's build (needs
networkx, which isn't installed by default; see requirements.txt). Re-run
this whenever you want the graph refreshed after new shows are added:

    pip install -r requirements.txt
    python3 build_graph.py

Writes docs/static/graph.json, consumed client-side by docs/static/graph.js.

Algorithm: every pair of artists that ever played in the same show gets an
edge, weighted by how close together they were sequenced (1/distance in
track positions) — tracks placed next to each other by the host carry a much
stronger signal than ones 80 tracks apart in the same 2-hour show, but nothing
is hard-cut to zero. A track credited to multiple artists (e.g. "A & B") is
split into its component artists at parse time (reusing played_archive.py's
_COLLAB regex) — since collaborators share a track's position, they land at
distance=0, which gets a large explicit bonus: collabs fall out of the
proximity model as the strongest possible connection, no special-casing
needed beyond the split.

Each node then keeps only its TOP_K strongest edges (union across all nodes)
so the graph stays legible rather than a 62k-edge hairball — validated
against the real corpus (154 shows) at TOP_K=6: 2,288 nodes, ~10,000 edges,
only 1 fully isolated node. Louvain community detection (networkx, purely
local — no cloud ML, no external API) then assigns each node a cluster,
which produced clean recognizable genre neighborhoods with zero manual
tagging when validated.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

import played_archive as pa

TRACKLISTS = Path(__file__).resolve().parent / "tracklists"
OUT_PATH = Path(__file__).resolve().parent / "docs" / "static" / "graph.json"

COLLAB_BONUS = 5.0  # same-track (distance=0) — strongest possible edge
TOP_K = 6  # keep each node's K strongest neighbors; union across all nodes


def build_edge_weights() -> tuple[dict[str, str], Counter, dict[tuple[str, str], float]]:
    """Returns (canon_key -> display_name, canon_key -> play count,
    (a,b) -> summed proximity weight) across every show."""
    labels: dict[str, str] = {}
    counts: Counter = Counter()
    edge_weight: dict[tuple[str, str], float] = defaultdict(float)

    for f in sorted(TRACKLISTS.glob("*.json")):
        tracklist = json.loads(f.read_text(encoding="utf-8"))
        tokens: list[tuple[int, str]] = []
        for pos, track in enumerate(tracklist):
            raw = (track.get("artist") or "").strip()
            if not raw:
                continue
            for piece in pa._COLLAB.split(raw):
                piece = piece.strip()
                if not piece:
                    continue
                key = pa._canon(piece)
                if not key:
                    continue
                labels.setdefault(key, piece)
                counts[key] += 1
                tokens.append((pos, key))

        n = len(tokens)
        for i in range(n):
            pi, ki = tokens[i]
            for j in range(i + 1, n):
                pj, kj = tokens[j]
                if ki == kj:
                    continue
                dist = pj - pi
                w = COLLAB_BONUS if dist == 0 else 1.0 / dist
                a, b = sorted((ki, kj))
                edge_weight[(a, b)] += w

    return labels, counts, edge_weight


def build_graph(labels: dict[str, str], counts: Counter, edge_weight: dict[tuple[str, str], float]) -> nx.Graph:
    neighbors: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), w in edge_weight.items():
        neighbors[a][b] = w
        neighbors[b][a] = w

    graph = nx.Graph()
    graph.add_nodes_from(counts.keys())
    for node, nbrs in neighbors.items():
        top = sorted(nbrs.items(), key=lambda kv: -kv[1])[:TOP_K]
        for other, w in top:
            if graph.has_edge(node, other):
                graph[node][other]["weight"] = max(graph[node][other]["weight"], w)
            else:
                graph.add_edge(node, other, weight=w)
    return graph


def main() -> None:
    labels, counts, edge_weight = build_edge_weights()
    graph = build_graph(labels, counts, edge_weight)

    communities = nx.algorithms.community.louvain_communities(graph, weight="weight", seed=42)
    communities = sorted(communities, key=len, reverse=True)
    cluster_of = {node: i for i, community in enumerate(communities) for node in community}

    nodes = [
        {"id": key, "name": labels[key], "count": counts[key], "cluster": cluster_of.get(key, -1)}
        for key in counts
    ]
    edges = [
        {"source": u, "target": v, "weight": round(d["weight"], 3)}
        for u, v, d in graph.edges(data=True)
    ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False), encoding="utf-8")

    isolated = sum(1 for n in graph.nodes if graph.degree(n) == 0)
    print(f"Artists: {len(nodes)}, edges: {len(edges)}, clusters: {len(communities)}, isolated: {isolated}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
