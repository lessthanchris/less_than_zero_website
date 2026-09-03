"""Played-songs archive query tool for Less Than Zero.

Loads every per-show tracklist JSON in the website repo, normalises artist/title
names (fixing mojibake + collapsing case/punctuation/collab variants) and de-dupes
so a "have we played X?" lookup returns true merged counts instead of scattered
split spellings.

Usage:
    python played_archive.py crosscheck           # verify known split-variant cases merge
    python played_archive.py search "Alvvays"    # search an act: plays, shows, sample tracks
    python played_archive.py top [N]              # top-played acts, normalised (default 60)
    python played_archive.py --fix-json           # rewrite source tracklists with repaired mojibake
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

TRACKLISTS = Path(__file__).resolve().parent / "tracklists"


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------

def repair_mojibake(s: str) -> str:
    """Reverse UTF-8-bytes-decoded-as-Latin-1 corruption."""  
    if not s:
        return s
    for enc in ("latin-1", "cp1252"):
        try:
            fixed = s.encode(enc).decode("utf-8")
            if fixed != s and "\ufffd" not in fixed:
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s


_COLLAB = re.compile(
    r"\s*(?:,|&|\+|/|\bft\.?\b|\bfeat\.?\b|\bfeaturing\b"
    r"|\bversus\b|\bvs\.?\b|\bx\b|\bwith\b)\s*",
    re.I,
)


def _canon(s: str) -> str:
    """Normalised comparison key for an artist/song name."""
    s = repair_mojibake(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    parts = [p for p in _COLLAB.split(s) if p.strip()]
    canon_parts = []
    for p in parts:
        p = p.lower()
        p = re.sub(r"[^\w]+", " ", p).strip()
        if p and p not in canon_parts:
            canon_parts.append(p)
    return " ".join(canon_parts)


def names_match(query: str, name: str) -> bool:
    """True if query's normalised key appears as a whole-word substring in
    name's normalised key, or vice versa. Word boundaries prevent short
    queries (e.g. 'o') from falsely matching inside longer words."""
    q = _canon(query)
    n = _canon(name)
    if not q or not n:
        return False
    pattern = re.compile(r"\b" + re.escape(q) + r"\b")
    if pattern.search(n):
        return True
    pattern = re.compile(r"\b" + re.escape(n) + r"\b")
    return bool(pattern.search(q))


# ---------------------------------------------------------------------------
# load + index
# ---------------------------------------------------------------------------

def load_all() -> dict[str, dict]:
    """Return {canon_key: {canonical, count, shows, sample}} across all shows."""
    acc: dict[str, dict] = {}
    labels: dict[str, str] = {}
    for f in sorted(TRACKLISTS.glob("*.json")):
        try:
            slots = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        date = f.stem
        for s in slots:
            ar = (s.get("artist") or "").strip()
            tr = (s.get("track") or "").strip()
            if not ar:
                continue
            key = _canon(ar)
            if not key:
                continue
            labels[key] = labels.get(key, ar)
            e = acc.setdefault(
                key,
                {"canonical": ar, "count": 0, "shows": set(), "sample": []},
            )
            e["count"] += 1
            e["shows"].add(date)
            if tr and len(e["sample"]) < 4:
                e["sample"].append((date, tr))
    for key, e in acc.items():
        e["canonical"] = labels.get(key, key)
        e["shows"] = sorted(e["shows"])
    return acc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not TRACKLISTS.is_dir():
        print(f"tracklists dir not found: {TRACKLISTS}", file=sys.stderr)
        return 1

    acc = load_all()

    if "--fix-json" in argv:
        fixed = 0
        for f in sorted(TRACKLISTS.glob("*.json")):
            slots = json.loads(f.read_text(encoding="utf-8"))
            changed = False
            for s in slots:
                for k in ("artist", "track"):
                    if k in s:
                        repaired = repair_mojibake(str(s[k] or ""))
                        if repaired != s[k]:
                            s[k] = repaired
                            changed = True
            if changed:
                f.write_text(json.dumps(slots, indent=2, ensure_ascii=False) + "\n")
                fixed += 1
        print(f"Repaired mojibake in {fixed} show files")
        return 0

    if "crosscheck" in argv:
        prove = [
            ("Death Cab for Cutie", 45),
            ("Belle and Sebastian", 29),
            ("Bjork", None),
            ("Sigur Ros", 6),
        ]
        print("=== crosscheck: do known split-variant/mojibake cases merge? ===")
        for q, _ in prove:
            like = [
                e["canonical"]
                for e in acc.values()
                if names_match(q, e["canonical"])
            ]
            tot = sum(
                e["count"]
                for e in acc.values()
                if names_match(q, e["canonical"])
            )
            print(f"  {q:<30} -> {tot:4d} plays   ({', '.join(like)})")
        return 0

    if "search" in argv:
        q = " ".join(argv[argv.index("search") + 1:]).strip()
        if not q:
            print("usage: played_archive.py search <artist>")
            return 1
        hits = sorted(
            (e["count"], e["canonical"], e)
            for e in acc.values()
            if names_match(q, e["canonical"])
        )
        if not hits:
            print(f"Never played: {q}")
        else:
            for count, canon, e in hits[-30:][::-1]:
                shows = ", ".join(e["shows"])[:120]
                print(f"{count:4d}  {canon}   [{len(e['shows'])} shows: {shows}]")
                for d, t in e["sample"]:
                    print(f"             {d}: {t}")
        return 0

    if "top" in argv:
        idx = argv.index("top")
        n = int(argv[idx + 1]) if idx + 1 < len(argv) and argv[idx + 1].isdigit() else 60
        ranked = sorted(acc.values(), key=lambda e: e["count"], reverse=True)[:n]
        print(f"=== Top {len(ranked)} plays (normalised; {len(acc)} distinct acts) ===")
        for e in ranked:
            print(f"{e['count']:4d}  {e['canonical']}")
        return 0

    print("Usage: crosscheck | search <artist> | top [N] | --fix-json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))