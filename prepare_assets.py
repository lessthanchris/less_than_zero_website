#!/usr/bin/env python3
"""Interactive wizard: turn an asset_drop/{iso_date} tile + tracklist into a
live show update.

    python3 prepare_assets.py                  # pick a date, answer prompts
    python3 prepare_assets.py 2026-09-03        # skip date picking
    python3 prepare_assets.py 2026-09-03 -y \\
        --mixcloud-name my-show --patreon 123   # non-interactive (scripting)

Reads asset_drop/{iso_date}.png (or .jpg) and asset_drop/{iso_date}.txt,
writes tracklists/{iso_date}.json and docs/images/{iso_date}[.thumbnail].jpg,
inserts the show into shows.json (newest-first), then rebuilds the site
(python3 app.py) and refreshes the artist graph (venv/bin/python3
build_graph.py) so search/graph/sitemap are all current in one step.

If asset_drop/{iso_date}.mkv is present, also offers to extract
asset_drop/{iso_date}.mp3 (ffmpeg, libmp3lame -q:a 2) for the manual Patreon
audio-post upload — the site itself never hosts per-show audio, so this file
is Patreon prep only, not something that gets committed.

If qobuz-id is blank, offers to generate a brand-new Qobuz playlist from
this show's tracklist via `~/crate-digger`'s `show-playlist` command (needs
~/crate-digger/.venv set up and a cached Qobuz token — see its README) —
this is a real, live API call that creates a public playlist on the Qobuz
account immediately, distinct from crate-digger's `evergreen` command which
only ever replaces one fixed always-current playlist.

Any field left blank (mixcloud-name, patreon, qobuz-id, spotify-id) can be
filled in later by re-running with --force once it's posted.

Does not commit or push — review the diff and do that yourself.

Needs `rich` and `Pillow` installed globally (pip install --user rich
Pillow), same as app.py needs Jinja2 globally — run this as plain
`python3 prepare_assets.py`, NOT `venv/bin/python3 prepare_assets.py`. It
shells out to `python3 app.py` using its own interpreter (sys.executable),
and venv/ only has networkx (for build_graph.py), not Jinja2.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

if sys.prefix != sys.base_prefix:
    sys.exit(
        "error: don't run prepare_assets.py from venv/ — it shells out to "
        "`python3 app.py` with its own interpreter, and venv/ has networkx "
        "but not Jinja2. Run it as plain `python3 prepare_assets.py` "
        "(rich + Pillow installed globally) instead."
    )

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

console = Console()

ROOT = Path(__file__).resolve().parent
ASSET_DROP = ROOT / "asset_drop"
IMAGES_DIR = ROOT / "docs" / "images"
TRACKLISTS_DIR = ROOT / "tracklists"
SHOWS_FILE = ROOT / "shows.json"

CRATE_DIGGER_DIR = Path.home() / "crate-digger"
CRATE_DIGGER_PYTHON = CRATE_DIGGER_DIR / ".venv" / "bin" / "python3"

TILE_SIZE = 800
THUMB_SIZE = 400

ORDINAL_SUFFIX = {1: "st", 2: "nd", 3: "rd"}


def ordinal(day):
    if 11 <= day % 100 <= 13:
        return f"{day}th"
    return f"{day}{ORDINAL_SUFFIX.get(day % 10, 'th')}"


def display_date_from_iso(iso_date):
    from datetime import date
    y, m, d = (int(x) for x in iso_date.split("-"))
    dt = date(y, m, d)
    return f"{ordinal(dt.day)} {dt.strftime('%B')} {dt.year}"


def parse_tracklist(txt_path):
    """'01. Artist - Track' per line -> [{"artist":..., "track":...}, ...]"""
    tracks = []
    for line in txt_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+\.\s*", "", line)
        if " - " not in line:
            console.print(f"  [yellow]! could not split artist/track, skipping:[/] {line!r}")
            continue
        artist, track = line.split(" - ", 1)
        tracks.append({"artist": artist.strip(), "track": track.strip()})
    return tracks


def make_images(source_path, iso_date):
    from PIL import Image

    img = Image.open(source_path).convert("RGB")
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

    tile = img.resize((TILE_SIZE, TILE_SIZE), Image.LANCZOS)
    thumb = img.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)

    tile_path = IMAGES_DIR / f"{iso_date}.jpg"
    thumb_path = IMAGES_DIR / f"{iso_date}.thumbnail.jpg"
    tile.save(tile_path, "JPEG", quality=90)
    thumb.save(thumb_path, "JPEG", quality=90)
    return tile_path, thumb_path


def find_source_image(iso_date):
    for ext in (".png", ".jpg", ".jpeg"):
        p = ASSET_DROP / f"{iso_date}{ext}"
        if p.exists():
            return p
    return None


def load_shows():
    if SHOWS_FILE.exists():
        return json.loads(SHOWS_FILE.read_text(encoding="utf-8"))
    return []


def discover_dates():
    """iso_dates with an asset_drop/{iso_date}.txt, newest first."""
    return sorted(
        (p.stem for p in ASSET_DROP.glob("*.txt") if re.match(r"^\d{4}-\d{2}-\d{2}$", p.stem)),
        reverse=True,
    )


def ffprobe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return None


def extract_mp3(mkv_path, iso_date, force):
    mp3_path = ASSET_DROP / f"{iso_date}.mp3"
    if mp3_path.exists() and not force:
        console.print(f"   [dim]{mp3_path.name} already exists, skipping (--force to re-extract)[/]")
        return mp3_path
    if not shutil.which("ffmpeg"):
        console.print("   [red]ffmpeg not found on PATH, skipping mp3 extraction[/]")
        return None

    duration = ffprobe_duration(mkv_path)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1", "-nostats",
        "-i", str(mkv_path), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(mp3_path),
    ]
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("extracting mp3", total=duration)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and duration and value.lstrip("-").isdigit():
                progress.update(task, completed=min(int(value) / 1_000_000, duration))
            elif key == "progress" and value == "end":
                progress.update(task, completed=duration)
        proc.wait()
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)
    return mp3_path


def generate_qobuz_playlist(tracklist_path, display_date):
    """Create a NEW dedicated Qobuz playlist from this show's tracklist via
    crate-digger's `show-playlist` command and return its numeric id, or
    None on failure. This is a real, live API call — it creates a public
    playlist visible on the account immediately."""
    if not CRATE_DIGGER_PYTHON.exists():
        console.print(f"   [red]crate-digger venv not found at {CRATE_DIGGER_PYTHON}, skipping[/]")
        return None
    cmd = [
        str(CRATE_DIGGER_PYTHON), "-m", "crate_digger", "show-playlist",
        "--tracklist", str(tracklist_path), "--qobuz",
        "--name", f"Less Than Zero — {display_date}",
    ]
    result = subprocess.run(cmd, cwd=CRATE_DIGGER_DIR, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        console.print(f"   [dim]{line}[/]")
    if result.returncode != 0:
        console.print(f"   [red]qobuz playlist generation failed:[/] {result.stderr.strip()}")
        return None
    m = re.search(r"qobuz_id:\s*(\d+)", result.stdout)
    return m.group(1) if m else None


def pick_date(cli_date):
    if cli_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", cli_date):
            sys.exit(f"error: iso_date must be YYYY-MM-DD, got {cli_date!r}")
        return cli_date

    candidates = discover_dates()
    if not candidates:
        sys.exit(f"error: no asset_drop/*.txt found (looked in {ASSET_DROP})")
    if len(candidates) == 1:
        return candidates[0]

    shows = load_shows()
    known = {s["iso_date"] for s in shows}
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#")
    table.add_column("Date")
    table.add_column("Status")
    for i, d in enumerate(candidates, 1):
        status = "[yellow]already in shows.json[/]" if d in known else "[green]new[/]"
        table.add_row(str(i), d, status)
    console.print(table)
    idx = IntPrompt.ask("Which show?", choices=[str(i) for i in range(1, len(candidates) + 1)], default="1")
    return candidates[int(idx) - 1]


def run_wizard(args):
    iso_date = pick_date(args.iso_date)

    shows = load_shows()
    existing = next((s for s in shows if s["iso_date"] == iso_date), None)
    force = args.force
    if existing and not force:
        if args.yes:
            sys.exit(f"error: {iso_date} is already in shows.json — pass --force to overwrite/update it")
        console.print(f"[yellow]{iso_date} is already in shows.json.[/]")
        if not Confirm.ask("Overwrite/update it?", default=True):
            sys.exit(0)
        force = True

    txt_path = ASSET_DROP / f"{iso_date}.txt"
    if not txt_path.exists():
        sys.exit(f"error: missing {txt_path}")
    img_source = find_source_image(iso_date)
    if img_source is None:
        sys.exit(f"error: missing asset_drop/{iso_date}.png (or .jpg)")
    mkv_path = ASSET_DROP / f"{iso_date}.mkv"

    tracklist_path = TRACKLISTS_DIR / f"{iso_date}.json"
    if tracklist_path.exists() and not force:
        sys.exit(f"error: {tracklist_path} already exists — pass --force to overwrite")

    tracks = parse_tracklist(txt_path)
    if not tracks:
        sys.exit("error: parsed zero tracks, aborting before touching shows.json")

    console.print(Panel(f"[bold]{iso_date}[/]  —  {txt_path.name}, {img_source.name}"
                         + (f", {mkv_path.name}" if mkv_path.exists() else ""),
                         title="Assets found", border_style="cyan"))

    preview = Table(show_header=True, header_style="bold cyan", title=f"{len(tracks)} tracks")
    preview.add_column("#", justify="right")
    preview.add_column("Artist")
    preview.add_column("Track")
    for i, t in enumerate(tracks, 1):
        preview.add_row(str(i), t["artist"], t["track"])
    console.print(preview)

    if not args.yes and not Confirm.ask("Tracklist looks right?", default=True):
        sys.exit("Aborted — fix asset_drop/{}.txt and re-run".format(iso_date))

    default_display = args.display_date or (existing or {}).get("display_date") or display_date_from_iso(iso_date)
    default_mixcloud = args.mixcloud_name or (existing or {}).get("mixcloud_name", "")
    default_patreon = args.patreon or (existing or {}).get("patreon", "")
    default_qobuz = args.qobuz_id or (existing or {}).get("qobuz_id", "")
    default_spotify = args.spotify_id or (existing or {}).get("spotify_id", "")

    do_qobuz_gen = args.generate_qobuz
    if args.yes:
        display_date, mixcloud_name, patreon, qobuz_id, spotify_id = (
            default_display, default_mixcloud, default_patreon, default_qobuz, default_spotify,
        )
    else:
        console.print(Panel("Leave blank and press Enter to fill in later.", border_style="dim"))
        display_date = Prompt.ask("Display date", default=default_display)
        mixcloud_name = Prompt.ask("Mixcloud name", default=default_mixcloud)
        patreon = Prompt.ask("Patreon post ID", default=default_patreon)
        if not default_qobuz and not do_qobuz_gen:
            do_qobuz_gen = Confirm.ask(
                "Generate a new Qobuz playlist for this show now? "
                "(creates a real public playlist on your Qobuz account)",
                default=True,
            )
        qobuz_id = default_qobuz if do_qobuz_gen else Prompt.ask("Qobuz playlist ID", default=default_qobuz)
        spotify_id = Prompt.ask("Spotify playlist ID", default=default_spotify)

    do_mp3 = False
    if mkv_path.exists() and not args.no_mp3:
        do_mp3 = args.yes or Confirm.ask(f"Extract mp3 from {mkv_path.name} for Patreon?", default=True)

    do_graph = not args.no_graph
    if not args.yes:
        do_graph = Confirm.ask("Refresh artist graph after rebuild?", default=do_graph)

    if not args.yes:
        summary = Table(show_header=False, box=None)
        summary.add_row("display_date", display_date)
        summary.add_row("mixcloud_name", mixcloud_name or "[dim](blank)[/]")
        summary.add_row("patreon", patreon or "[dim](blank)[/]")
        summary.add_row("qobuz_id", "[cyan](will be generated)[/]" if do_qobuz_gen else (qobuz_id or "[dim](blank)[/]"))
        summary.add_row("spotify_id", spotify_id or "[dim](blank)[/]")
        summary.add_row("extract mp3", "yes" if do_mp3 else "no")
        summary.add_row("refresh graph", "yes" if do_graph else "no")
        console.print(Panel(summary, title="Review", border_style="cyan"))
        if not Confirm.ask("Proceed?", default=True):
            sys.exit(0)

    console.rule(f"Preparing {iso_date}")

    tracklist_path.write_text(json.dumps(tracks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    console.print(f"[green]✓[/] wrote {tracklist_path.relative_to(ROOT)} ({len(tracks)} tracks)")

    tile_path, thumb_path = make_images(img_source, iso_date)
    console.print(f"[green]✓[/] wrote {tile_path.relative_to(ROOT)}, {thumb_path.relative_to(ROOT)}")

    mp3_path = None
    if do_mp3:
        mp3_path = extract_mp3(mkv_path, iso_date, force)
        if mp3_path:
            console.print(f"[green]✓[/] wrote {mp3_path.relative_to(ROOT)} (for manual Patreon upload)")

    if do_qobuz_gen:
        with console.status("generating Qobuz playlist (crate-digger)..."):
            generated_id = generate_qobuz_playlist(tracklist_path, display_date)
        if generated_id:
            qobuz_id = generated_id
            console.print(f"[green]✓[/] created Qobuz playlist — qobuz_id: {qobuz_id}")
        else:
            console.print("[yellow]! Qobuz playlist generation failed — qobuz_id left as-is[/]")

    entry = {
        "iso_date": iso_date,
        "display_date": display_date,
        "mixcloud_name": mixcloud_name,
        "patreon": patreon,
        "spotify_id": spotify_id,
        "soundcloud_id": "",
        "qobuz_id": qobuz_id,
    }
    if existing:
        shows[shows.index(existing)] = entry
    else:
        shows.insert(0, entry)
    SHOWS_FILE.write_text(json.dumps(shows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    console.print(f"[green]✓[/] {'updated' if existing else 'inserted'} shows.json entry ({display_date})")

    with console.status("rebuilding site (python3 app.py)..."):
        subprocess.run([sys.executable, "app.py"], cwd=ROOT, check=True, capture_output=True)
    console.print("[green]✓[/] rebuilt site")

    if do_graph:
        venv_python = ROOT / "venv" / "bin" / "python3"
        if venv_python.exists():
            with console.status("refreshing artist graph (build_graph.py)..."):
                subprocess.run([str(venv_python), "build_graph.py"], cwd=ROOT, check=True, capture_output=True)
            console.print("[green]✓[/] refreshed artist graph")
        else:
            console.print("[yellow]skipped graph refresh: venv/bin/python3 not found (see CLAUDE.md)[/]")

    rel = lambda p: p.relative_to(ROOT)
    next_steps = (
        f"git add shows.json {rel(tracklist_path)} {rel(tile_path)} {rel(thumb_path)} docs/\n"
        f'git commit -m "Add show ({display_date})"\n'
        f"git push"
    )
    if mp3_path:
        next_steps += f"\n\nUpload {rel(mp3_path)} to Patreon, then re-run with --force --patreon <post-id>."
    for field, val in (("mixcloud_name", mixcloud_name), ("patreon", patreon),
                        ("qobuz_id", qobuz_id), ("spotify_id", spotify_id)):
        if not val:
            next_steps += f"\n(note: {field} still blank — re-run with --force once you have it)"
    console.print(Panel(next_steps, title="Done — review, then", border_style="green"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso_date", nargs="?", help="Show date, YYYY-MM-DD (prompts to pick one if omitted)")
    ap.add_argument("--display-date", help="e.g. '3rd September 2026' (auto-computed if omitted)")
    ap.add_argument("--mixcloud-name", default="")
    ap.add_argument("--patreon", default="")
    ap.add_argument("--qobuz-id", default="")
    ap.add_argument("--spotify-id", default="")
    ap.add_argument("--no-graph", action="store_true", help="skip the artist graph rebuild")
    ap.add_argument("--no-mp3", action="store_true", help="skip mp3 extraction from asset_drop/{iso_date}.mkv")
    ap.add_argument("--generate-qobuz", action="store_true",
                     help="create a new Qobuz playlist from this show's tracklist via crate-digger "
                     "(real API call — creates a public playlist on your account)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing entry for this date")
    ap.add_argument("-y", "--yes", action="store_true",
                     help="non-interactive: skip all prompts/confirmations, use flag values and defaults")
    args = ap.parse_args()

    try:
        run_wizard(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted.[/]")
        sys.exit(130)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]command failed:[/] {' '.join(e.cmd)}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
