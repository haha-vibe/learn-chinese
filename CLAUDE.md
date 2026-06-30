# Learn Chinese (認漢字) — Project Guide

Reference for the author and for Claude Code agents working on this repo.
Keep this file updated when features or design decisions change.

## What it is

A self-contained Chinese character–learning web app for a single learner
(originally built for the author's child). Students see a character and either
recall it (**練習 / practice**) or take a multiple-choice + pinyin quiz
(**測驗 / quiz**), with per-student progress tracked locally.

## Running it

- **No build, no server.** Open [`learnchinese.html`](learnchinese.html)
  directly in a browser.
  When served, the app auto-fetches the dictionary from [`hanzi/`](hanzi/); when
  opened via `file://`, click **選擇 JSON 檔** and select both
  [`hanzi/tps-dictionary.json`](hanzi/tps-dictionary.json) and
  [`hanzi/cedict-supplement.json`](hanzi/cedict-supplement.json). They are
  loaded into **IndexedDB** (too large for localStorage) and persist.
- [`hanzi/build-dict.py`](hanzi/build-dict.py) regenerates the dictionary JSONs
  from CC-CEDICT + the TPS frequency list + [`hanzi/progressive-dictionary.txt`].

## File layout

The repo holds **two apps**: `learnchinese.html` (认汉字) and `poems.html` (小学古诗).
The two HTML files and the shared `sw.js` live at the root; each app's data and
scripts live in its own subfolder (`hanzi/`, `poems/`).

| File | Role |
| --- | --- |
| `learnchinese.html` | The 认汉字 app — HTML, CSS, and JS in one file (root). |
| `poems.html` | The 小学古诗 app — single file (root). See "Poem media system" below. |
| `sw.js` | Shared service worker; caches both apps' shells + subfolder data (root). |
| `hanzi/build-dict.py` | Offline script to (re)build the dictionary data (reads `../learnchinese.html`). |
| `hanzi/tps-dictionary.json` | Generated dictionary the app consumes (readings, defs, examples, frequency rank, graded example words). |
| `hanzi/cedict-supplement.json` | Supplemental CC-CEDICT entries. |
| `hanzi/progressive-dictionary.txt` | Source word list for the build. |

Each app is intentionally **one HTML file**: easy to share, host anywhere, or
run offline. Prefer keeping it that way over splitting into modules. The lone
shared file is `sw.js` (browsers forbid inline/`blob:` SW registration, so it
must be separate); registration lives inline in each page's `<head>`.

## Offline & auto-update (`sw.js`)

- **Network-first.** Each same-origin GET goes to the network first and refreshes
  the cache; the cache is served only when the network fails (offline). So a
  reload always shows the latest content. `CORE_ASSETS` is precached on install
  for first-load offline support. **Bump `CACHE` on every deploy** — it both
  drops stale caches and is what signals a code update to open tabs.
- **Two update prompts → one banner.** A long-open tab won't otherwise notice a
  deploy, so each page, on a 30-min timer + on tab-focus, does two checks:
  1. `reg.update()` — the browser byte-compares `sw.js`; a changed worker installs
     and *waits* (install no longer calls `skipWaiting`), surfacing a **"new
     version"** banner.
  2. `postMessage({type:'CHECK_UPDATES'})` — the SW diffs each cached `CORE_ASSET`
     against the server by **`ETag`/`Last-Modified`** (read-only; `HEAD` requests)
     and, if any changed, posts `DATA_CHANGED`, surfacing a **"content updated"**
     banner. The cache is the single source of truth for "what the user has," so
     no page-side version bookkeeping.
- **Reload button** always activates a waiting worker first (`SKIP_WAITING` →
  `controllerchange` → reload) if one exists, else a plain reload — so one click
  picks up a data change, a code change, or both at once. A `controllerchange`
  reload is gated by an `updating` flag so the first-install `clients.claim()`
  never triggers a surprise reload.
- Why the page drives it (not the SW alone): a SW has no DOM (can't show the
  banner or reload) and is killed when idle (no reliable timer). The SW owns the
  cache + diff + messaging; the page owns the timer + UI. Data detection only
  works when hosted (needs server validators); irrelevant on `file://`.

## Data model

All learner state lives in the browser.

- **`localStorage["students"]`** — `{ "<name>": { stats, mastery, progress } }`
  - `stats[simp] = [seen, wrong]` — used for 弱字 ordering (weak-first sort).
  - `mastery[simp] = { p: <count>, t: <count> }` — correctness count per mode
    (`p` = practice, `t` = quiz). Answer right → `+1`, wrong → `-1`, clamped to
    **`[-5, 1]`** (`COUNT_MIN`/`COUNT_MAX`).
    - count `≥ 1` → "learned" for that mode (`isLearned`); removed from random
      selection (sequential mode still shows it).
    - count `< 0` → "weak" (shown in the 需加強 list and pulled by 弱字 mode).
  - `progress[date] = { L12:[p,t], L3:[p,t], L4:[p,t], L5:[p,t] }` —
    end-of-day cumulative *learned* counts (per level, per mode) for the
    progress chart + completion prediction. **Only written on days with
    activity** (`recordProgress` upserts the `YYYY-MM-DD` key on every
    `markCorrect`/`markWrong`/`undo`), so idle days never appear — the series
    is a list of *practice days*, gaps collapsed. `predictCompletion` takes a
    **moving average of the last 5 practice-day increments** as the rate and
    projects practice-days remaining to reach the level's full character count.
- **IndexedDB** — the dictionary entries, keyed by simplified character.

`simpToWord` maps simplified char → word object; `ZH_GLOSS` holds the short
Chinese gloss shown under each character.

## Features & options

Setup screen (hidden `<select>`s driven by segmented buttons):

- **Mode**: 練習 (practice) / 測驗 (quiz).
- **Level**: `L12` (L1–L2), `L3`, `L4`, `L5` — see `WORDS` and `LEVEL_LABEL`.
- **Script**: 簡體 (simplified) / 繁體 (traditional).
- **Order**:
  - 隨機 (random) — weighted random, weaker (more negative count) characters
    surface earlier; "learned" characters are excluded.
  - 順序 (sequential) — fixed order, includes everything.
  - **弱字 (weak) — only characters answered wrong (negative `mastery` count in
    practice *or* quiz). Weakest-first. Alerts if there are none yet.**
- **Session size**: 20 / 50 / 100 / 全部.
- **Hint visibility (練習 only)**: 點擊 (tap) / 延遲 (delay 3s) / 始終 (always) /
  關閉 (off).
- **Audio (練習 only)**: 手動 (manual) / 自動 (auto) / 關閉 (off), via Web Speech
  synthesis. Off in quiz to avoid leaking the answer.

### Practice mode

- Always shows the character, its Chinese gloss (`ZH_GLOSS`), and trad/simp
  alternate.
- **Pinyin practice field** (`#practicePyInput`): auto-focused each character.
  Student types pinyin, presses **確認 / Enter**:
  - matching is **tone-insensitive** (`normPy` strips tone marks & numbers);
  - reveals the description/hint panel **with `force: true`** (shows even if the
    hint setting is tap/off) plus the correct pinyin;
  - colors the field green/red;
  - **a wrong pinyin blocks "+1" for that character** (`_practicePyWrong` →
    `markCorrect` refuses, +1 button disabled). Empty submit = just reveal, no
    penalty. No dictionary entry = no grading.
- Hint panel content: pinyin, English/tagged defs, graded example words,
  frequency rank.

### Quiz mode

- Pinyin input + multiple-choice meaning (distractors from same level).
- Auto-scores; reveals correct answer and hint on submit.

### Scoring, review, undo

- `markCorrect`/`markWrong` adjust score + `mastery` count + `stats`.
- Wrong characters are **re-inserted ~5 positions later** so they recur until
  correct.
- **Undo** restores the previous state from `history` snapshots.

### Progress chart & completion prediction (setup page)

- **Hidden by default.** Each practice/quiz bar in the per-student progress
  panel (`renderStudentProgress`) is clickable (`toggleProgressChart(lvl,key)`):
  clicking a bar opens an inline-SVG line chart of cumulative learned characters
  over **practice days** for *that* level + mode, inserted directly beneath its
  row. **At most one chart is open** — clicking another bar switches; clicking
  the active bar again closes it (`chartSel` holds `{lvl,key}` or `null`, reset
  on student switch).
- A dashed green segment projects the curve to 100%; the caption gives the rate
  (avg characters/practice-day) and **estimated practice-days remaining** to
  finish the level. States: `done` (🎉), `insufficient` (<2 practice days),
  `stalled` (rate ≤ 0, can't project), `ok` (shows the estimate).
- Inline SVG only — keeps the no-dependency, single-file rule. Don't reach for
  a charting library.

### Keyboard shortcuts (test page)

| Key | Action |
| --- | --- |
| `=` / `+` | +1 (blocked if pinyin was wrong in practice) |
| `-` / `_` | +0 (mark wrong) |
| `Space` | toggle hint (practice, unless 始終) |
| `P` | speak (when not typing in the pinyin field) |
| `Enter` | submit (practice pinyin / quiz) |
| `Backspace` | return to previous character (outside the pinyin field) |
| `←` | return to previous character (works **inside** the pinyin field too) |
| `1`–`4` | select quiz option (when input not focused) |

**Pinyin field input rule:** only **alphanumerics** are typed into
`#practicePyInput` (pinyin letters + tone digits); editing keys (Backspace,
Delete, →, etc.) work normally; modifier combos pass through; **all other keys
are routed to the hotkeys** instead of being typed. Because Backspace is used
for editing here, `←` is the in-field "go back" shortcut.

## Notable design decisions

- **Single-file, offline-first, no dependencies.** Runs by double-clicking.
- **Per-student local state**, no accounts/backend. Multiple students by name.
- **弱字 = wrong-answer set**, derived automatically from `mastery` counts (no
  manual marking) — characters earn their way in by being missed.
- **Tone-insensitive pinyin matching** keeps input forgiving for young learners.
- **Reveal-with-descriptions**: in practice the correct pinyin is shown together
  with the meaning, not before — so the student recalls first.
- **Quiz never auto-plays audio** (would leak the answer).
- **Translation disabled** (`<html translate="no">`, `notranslate` meta + body
  class) so browser/extension auto-translate doesn't convert the very
  characters being taught.

## Poem media system

### Files

| File | Role |
| --- | --- |
| `poems/poems-g1.json` – `poems-g6.json` | Poem lists (id, title, author, pinyin) for grades 1–6. |
| `poems/poems-edb.json` | EDB-curriculum poems not yet in the grade files (title only; to be expanded). |
| `poems/poems-media.json` | Maps poem id → `{ audio, audioStart, video, videoStart }`. Top-level `_credits` array declares allowed sources in priority order. |
| `poems/fetch-playlist-videos.py` | Syncs `poems-media.json` video links from credited YouTube playlists. Requires `yt-dlp` and `zhconv` on PATH / installed. |
| `poems/playlist-cache/<ID>.html` | Browser-exported playlist HTML used as fallback when yt-dlp cannot enumerate all items (e.g. members-only content). |

### `_credits` structure

Each entry in the `_credits` array of `poems-media.json`:

```json
{
  "name": "Display name",
  "url": "https://www.youtube.com/playlist?list=PLAYLIST_ID",
  "note": "optional free-text",
  "titleOnly": true   // omit or false to require author in video title too
}
```

- Entries are processed in order; first match wins.
- `titleOnly: true` skips the author check (used for playlists whose video titles don't include the poet's name, e.g. 可可读课本).
- Classical-text authors stored as `《孟子》` have their brackets stripped before matching.

### Matching logic (`fetch-playlist-videos.py`)

- Video title is converted from traditional → simplified (`zhconv`) before matching.
- Author: plain substring match (brackets stripped).
- Poem title: word-boundary match (no adjacent Han character on either side) **or** prefix match (≥ 4 chars, left-boundary only — handles abbreviated local titles like 十五夜望月 matching 十五夜望月寄杜郎中).
- Trailing qualifiers like `（其一）` are stripped and the bare title is also tried.

### Updating video links

```bash
# Dry run — show proposed changes without writing
python fetch-playlist-videos.py --dry-run

# Apply — only adds links for poems that have none
python fetch-playlist-videos.py

# Force — upgrade to higher-priority source even if already linked
python fetch-playlist-videos.py --force

# Purge and reassign from scratch (use after reordering _credits)
python fetch-playlist-videos.py --purge
```

### Browser-export fallback for large / members-only playlists

yt-dlp can only enumerate public playlist items (YouTube serves 100 per page,
and members-only items are invisible without authentication). For any playlist
that needs full coverage:

1. Open the playlist URL in Chrome (log in if needed for members-only content).
2. Scroll to the bottom so all videos are loaded.
3. In DevTools → Elements, find `<div id="contents">`, right-click →
   **Copy → Copy outerHTML**.
4. Save the clipboard to `poems/playlist-cache/<PLAYLIST_ID>.html`
   (the playlist ID is the `list=…` value in the URL).

`fetch_playlist()` checks for this file first; if found it parses the HTML
instead of calling yt-dlp, giving access to the full list including
members-only items that were visible when you exported.

## Conventions for future edits

- Keep everything in `learnchinese.html` unless there's a strong reason not to.
- UI text is **Traditional Chinese**; match the surrounding tone and wording.
- After editing the JS, sanity-check syntax (the script is one big block).
- Update this file when you add a mode, option, shortcut, or data-model change.

## Privacy

This guide contains no secrets and is safe to commit publicly. (There is no way
to make a single file private inside a public GitHub repo — to keep it private,
add it to `.gitignore` so it stays local only.)

## License

CC BY-NC-SA 4.0 — see [`LICENSE`](LICENSE) and [`README.md`](README.md).
Copyright © 2026 [haha-vibe](https://github.com/haha-vibe). The author retains
all rights and may relicense commercially.
