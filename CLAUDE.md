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
- On first use, import the dictionary: click **選擇 JSON 檔** and select both
  [`tps-dictionary.json`](tps-dictionary.json) and
  [`cedict-supplement.json`](cedict-supplement.json). They are loaded into
  **IndexedDB** (too large for localStorage) and persist across sessions.
- [`build-dict.py`](build-dict.py) regenerates the dictionary JSONs from
  CC-CEDICT + the TPS frequency list + [`progressive-dictionary.txt`].

## File layout

| File | Role |
| --- | --- |
| `learnchinese.html` | The entire app — HTML, CSS, and JS in one file. |
| `sw.js` | Service worker for offline support (the one allowed separate file — browsers forbid inline/`blob:` SW registration). |
| `build-dict.py` | Offline script to (re)build the dictionary data. |
| `tps-dictionary.json` | Generated dictionary the app consumes (readings, defs, examples, frequency rank, graded example words). |
| `cedict-supplement.json` | Supplemental CC-CEDICT entries. |
| `progressive-dictionary.txt` | Source word list for the build. |

The app is intentionally **one HTML file**: easy to share, host anywhere, or
run offline. Prefer keeping it that way over splitting into modules. The lone
exception is `sw.js`: when hosted (e.g. GitHub Pages) the browser must fetch
the page over the network on each visit, so with no network there is nothing
to load. The service worker caches the page shell (stale-while-revalidate) so
it opens offline after one online visit. Registration lives inline in
`learnchinese.html`'s `<head>`; the worker file itself must be separate because
browsers forbid inline SW registration.

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
