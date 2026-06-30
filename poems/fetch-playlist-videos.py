#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-playlist-videos.py -- update poems-media.json with videos from credited playlists.

Uses yt-dlp (must be on PATH) to list playlist contents -- no API key required.

Usage:
    python fetch-playlist-videos.py [--dry-run] [--force]

Flags:
  --dry-run   Print proposed changes without writing
  --force     Replace a poem's video even when its current video is already from a
              credited playlist, if a higher-priority match exists
"""

import json, re, sys, os, argparse, subprocess
import zhconv

def to_simp(s):
    """Convert traditional Chinese characters in s to simplified."""
    return zhconv.convert(s, "zh-hans")

HERE = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def local(name):
    return os.path.join(HERE, name)


# ---------------------------------------------------------------------------
# yt-dlp helpers
# ---------------------------------------------------------------------------

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist-cache")


def _parse_playlist_html(html):
    """Parse a browser-exported YouTube playlist HTML into [{id, title}, ...].

    Handles the new YouTube lockup layout where each video lives in a
    <div class="ytLockupViewModelHost ... content-id-VIDEO_ID ..."> block
    with an <h3 title="..."> for the title.
    Save browser HTML as playlist-cache/<PLAYLIST_ID>.html to use as fallback
    when yt-dlp cannot reach all items (e.g. members-only content).
    """
    shards = re.split(
        r'(?=<div[^>]+class="ytLockupViewModelHost[^"]*content-id-)', html
    )
    items = []
    seen = set()
    for shard in shards:
        m_id = re.search(
            r'/watch\?v=([\w-]+)&(?:amp;)?list=([\w-]+)&(?:amp;)?index=(\d+)', shard
        )
        m_title = re.search(r'<h3[^>]+title="([^"]+)"', shard)
        if m_id and m_title:
            vid = m_id.group(1)
            title = m_title.group(1).strip()
            if vid not in seen and title not in ("[Deleted video]", "[Private video]"):
                seen.add(vid)
                items.append({"id": vid, "title": title})
    return items


def fetch_playlist(playlist_url):
    """Return [{id, title}, ...] for all videos in a playlist.

    First checks playlist-cache/<PLAYLIST_ID>.html; if found, parses that
    (useful for members-only playlists exported from the browser).
    Otherwise calls yt-dlp, paging in 100-item chunks.
    """
    pid = extract_playlist_id(playlist_url)
    if pid:
        cache_file = os.path.join(_CACHE_DIR, pid + ".html")
        if os.path.exists(cache_file):
            with open(cache_file, encoding="utf-8", errors="replace") as fh:
                items = _parse_playlist_html(fh.read())
            if items:
                return items

    PAGE = 100
    items = []
    start = 1
    while True:
        end = start + PAGE - 1
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--no-warnings",
            "--print-json",
            "-I", "%d:%d" % (start, end),
            playlist_url,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        page_items = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line.decode("utf-8", errors="replace"))
            except Exception:
                continue
            vid_id = (obj.get("id") or "").strip()
            title  = (obj.get("title") or "").strip()
            if vid_id and title and title not in ("[Deleted video]", "[Private video]"):
                page_items.append({"id": vid_id, "title": title})
        items.extend(page_items)
        if len(page_items) < PAGE:
            break
        start += PAGE
    return items


def extract_playlist_id(url):
    m = re.search(r"list=([\w-]+)", url)
    return m.group(1) if m else None


def extract_video_id(url):
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/))([\w-]{6,})", url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Title matching
# All non-ASCII characters are written as \uXXXX escapes so this file
# is encoding-safe regardless of platform, editor, or Python version.
# ---------------------------------------------------------------------------

# Strip trailing qualifiers like （其一） or （节选） from poem titles.
# （=( ）=) ·=middle dot
_QUALIFIER = re.compile("[（(·][^）)·]*[）)]?$")


def _is_han(c):
    # CJK Unified Ideographs: U+4E00 to U+9FFF
    return "一" <= c <= "鿿"


def _title_occurs_standalone(needle, haystack):
    """
    True if `needle` appears in `haystack` without an adjacent Han character
    on either side.  Prevents "draw" matching "animation", etc.
    """
    pos = 0
    n = len(needle)
    while True:
        idx = haystack.find(needle, pos)
        if idx == -1:
            return False
        before_ok = (idx == 0) or not _is_han(haystack[idx - 1])
        after_ok  = (idx + n >= len(haystack)) or not _is_han(haystack[idx + n])
        if before_ok and after_ok:
            return True
        pos = idx + 1


def _title_occurs_prefix(needle, haystack):
    """
    Like _title_occurs_standalone but allows Han characters to follow the
    needle — handles cases where the local title is a well-known abbreviation
    of the full title used in the video (e.g. "十五夜望月" matching
    "十五夜望月寄杜郎中").  Only used for needles of 4+ characters to avoid
    false prefix matches on short titles like "江南" matching "江南春".
    """
    if len(needle) < 4:
        return False
    pos = 0
    n = len(needle)
    while True:
        idx = haystack.find(needle, pos)
        if idx == -1:
            return False
        before_ok = (idx == 0) or not _is_han(haystack[idx - 1])
        if before_ok:
            return True
        pos = idx + 1


def _poem_title_matches(poem_title, video_title_simp):
    """Standalone or prefix match for poem title against a simplified video title."""
    for title in [poem_title, _QUALIFIER.sub("", poem_title)]:
        if title and (
            _title_occurs_standalone(title, video_title_simp)
            or _title_occurs_prefix(title, video_title_simp)
        ):
            return True
    return False


def poem_in_video_title_only(poem_title, video_title):
    """Title-only variant — no author check. Converts video title to simplified
    before matching so traditional-character titles are handled."""
    return _poem_title_matches(poem_title, to_simp(video_title))


def poem_in_video(poem_title, author, video_title):
    """
    True if both the poem title AND the author appear in the video title.
    Both poem title and author are matched against a simplified version of the
    video title so traditional-character video titles are handled correctly.
    Poem title uses word-boundary / prefix matching.
    Author uses plain substring matching.
    """
    simp = to_simp(video_title)
    # Strip book-title brackets from classical-text authors like 《孟子》→ 孟子
    author_bare = author.strip("《》")
    if author_bare not in simp:
        return False
    return _poem_title_matches(poem_title, simp)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Sync poems-media.json with credited playlists (uses yt-dlp)"
    )
    ap.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    ap.add_argument(
        "--force", action="store_true",
        help="Upgrade to higher-priority playlist even if current video is already credited"
    )
    ap.add_argument(
        "--purge", action="store_true",
        help="Remove all existing video links before matching, then assign from credited playlists in priority order"
    )
    args = ap.parse_args()

    # load poems-media.json
    media_path = local("poems-media.json")
    with open(media_path, encoding="utf-8") as f:
        media = json.load(f)

    # discover video playlists from _credits (skip the audio-only entry)
    credits = media.get("_credits", [])
    playlists = []
    for c in credits:
        url = c.get("url", "")
        if "youtube.com/playlist" in url:
            pid = extract_playlist_id(url)
            if pid:
                playlists.append({
                    "name": c["name"], "id": pid, "url": url,
                    "titleOnly": bool(c.get("titleOnly")),
                })

    if not playlists:
        sys.exit("No YouTube playlists found in _credits.")

    print("=== %d credited video playlists (priority order) ===" % len(playlists))
    for i, pl in enumerate(playlists, 1):
        print("  %d. %s" % (i, pl["name"]))
    print()

    # fetch all playlist contents via yt-dlp
    pl_videos = {}
    for pl in playlists:
        print("Fetching: %s ..." % pl["name"], end=" ", flush=True)
        try:
            items = fetch_playlist(pl["url"])
            pl_videos[pl["id"]] = items
            print("%d videos" % len(items))
        except subprocess.TimeoutExpired:
            print("TIMEOUT -- skipped")
            pl_videos[pl["id"]] = []
        except Exception as e:
            print("ERROR: %s" % e)
            pl_videos[pl["id"]] = []

    # build reverse map: video_id -> {name, priority (0 = best)}
    vid_to_pl = {}
    for pri, pl in enumerate(playlists):
        for v in pl_videos.get(pl["id"], []):
            if v["id"] not in vid_to_pl:
                vid_to_pl[v["id"]] = {"name": pl["name"], "priority": pri}

    print("\nTotal unique credited videos: %d\n" % len(vid_to_pl))

    if args.purge:
        purged = 0
        for entry in media.values():
            if isinstance(entry, dict) and "video" in entry:
                del entry["video"]
                entry.pop("videoStart", None)
                purged += 1
        print("Purged %d existing video link(s).\n" % purged)

    # load all poem data
    poems = []
    for g in range(1, 7):
        fp = local("poems-g%d.json" % g)
        if not os.path.exists(fp):
            continue
        with open(fp, encoding="utf-8") as f:
            for p in json.load(f).get("poems", []):
                poems.append({"id": p["id"], "title": p["title"], "author": p.get("author", "")})

    print("Loaded %d poems from poems-g*.json" % len(poems))
    print("=" * 60)

    updates  = {}    # poem_id -> new video id
    problems = []    # poems whose current video is not in any credited playlist

    for poem in poems:
        pid, title, author = poem["id"], poem["title"], poem["author"]
        current_url = media.get(pid, {}).get("video", "")
        current_vid = extract_video_id(current_url) if current_url else ""
        current_pri = vid_to_pl[current_vid]["priority"] if current_vid in vid_to_pl else None

        if current_vid and current_pri is None:
            problems.append((title, pid, current_url))

        # find the best (highest-priority) match across playlists
        best = None
        for pri, pl in enumerate(playlists):
            for v in pl_videos.get(pl["id"], []):
                match = (
                    poem_in_video_title_only(title, v["title"])
                    if pl["titleOnly"]
                    else poem_in_video(title, author, v["title"])
                )
                if match:
                    best = {
                        "vid": v["id"], "vtitle": v["title"],
                        "playlist": pl["name"], "priority": pri,
                    }
                    break
            if best:
                break

        if not best or best["vid"] == current_vid:
            continue

        if current_vid and current_pri is not None:
            # current is already from a credited playlist
            if not args.force and not args.purge:
                continue
            if best["priority"] >= current_pri:
                continue  # no higher-priority match available

        if not current_vid:
            action = "ADD"
        elif current_pri is None:
            action = "REPLACE (not credited)"
        else:
            action = "UPGRADE (priority %d->%d)" % (current_pri + 1, best["priority"] + 1)

        print("[%s]  %s  (%s)" % (action, title, pid))
        print("  playlist : %s" % best["playlist"])
        print("  video    : %s" % best["vtitle"])
        print("  url      : https://www.youtube.com/watch?v=%s" % best["vid"])
        updates[pid] = best["vid"]

    if problems:
        print("\n-- Videos not from any credited playlist --")
        for title, pid, url in problems:
            print("  !  %s (%s): %s" % (title, pid, url))

    suffix = "[DRY RUN] " if args.dry_run else ""
    print("\n%s%d video link(s) to update." % (suffix, len(updates)))

    if updates and not args.dry_run:
        for pid, vid in updates.items():
            media.setdefault(pid, {})
            media[pid]["video"] = "https://www.youtube.com/watch?v=%s" % vid
            media[pid].setdefault("videoStart", 5)
        with open(media_path, "w", encoding="utf-8") as f:
            json.dump(media, f, ensure_ascii=False, indent=2)
        print("Written -> %s" % media_path)
    elif args.dry_run:
        print("(no files modified)")


if __name__ == "__main__":
    main()
