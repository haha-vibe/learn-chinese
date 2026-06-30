# Learn Chinese

Two self-contained, single-file web apps:

- **认汉字** — [`learnchinese.html`](learnchinese.html): character learning with a
  progressive dictionary and spaced practice (data in [`hanzi/`](hanzi/)).
- **小学古诗** — [`poems.html`](poems.html): primary-school poem recitation with
  pinyin, tone-sandhi highlighting, and audio/video (data in [`poems/`](poems/)).

Open either HTML file in a browser. Each app fetches its data from its own
subfolder when served, and falls back to a manual file picker when opened via
`file://`.

## Contents

Shared, at the repo root:

| File | Description |
| --- | --- |
| `learnchinese.html` | The 认汉字 (character-learning) app. |
| `poems.html` | The 小学古诗 (poem-learning) app. |
| `sw.js` | Shared service worker — network-first caching for offline use, plus a "new version / content updated" reload prompt for open tabs. Bump its `CACHE` on each deploy. |

`hanzi/` — character-learning data & build script:

| File | Description |
| --- | --- |
| `hanzi/build-dict.py` | Builds the dictionary data (reads `../learnchinese.html` for the WORDS list). |
| `hanzi/progressive-dictionary.txt` | Source dictionary used by the build. |
| `hanzi/cedict-supplement.json` | Supplemental CC-CEDICT entries. |
| `hanzi/tps-dictionary.json` | Generated dictionary consumed by the app. |

`poems/` — poem data & media pipeline:

| File | Description |
| --- | --- |
| `poems/poems-g1.json` – `poems-g6.json` | Per-grade poem data (text, per-char pinyin/meaning, notes, tone sandhi). |
| `poems/poems-edb.json` | Additional poems from the HK EDB curriculum list. |
| `poems/poems-media.json` | Maps each poem to its audio (HK EDB Putonghua) and video links; `_credits` lists the credited sources in priority order. |
| `poems/fetch-playlist-videos.py` | Syncs video links in `poems-media.json` from the credited playlists (requires `yt-dlp` and `zhconv`). |
| `poems/playlist-cache/` | Browser-exported playlist HTML files used as fallback when yt-dlp cannot enumerate all items. Save as `<PLAYLIST_ID>.html`. |

## License

Copyright © 2026 [haha-vibe](https://github.com/haha-vibe). All rights reserved.

This project — including all source code, data, and content — is licensed
under the **[Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International License (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/)**.

You are free to **fork, share, and adapt** this project, provided that you:

- **Give credit** — attribute the original author
  ([haha-vibe](https://github.com/haha-vibe/learn-chinese)), link back to this
  repository, and indicate any changes you made;
- **Keep it non-commercial** — do not use the material for commercial purposes;
- **Share alike** — distribute any derivative work under this same license.

See the [`LICENSE`](LICENSE) file for full details.

### Commercial use

The license above applies to third parties. As the sole copyright holder,
haha-vibe retains full rights to this work and may offer it under different
terms. **For commercial licensing, please contact the repository owner via
[GitHub](https://github.com/haha-vibe).**
