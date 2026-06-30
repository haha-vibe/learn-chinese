# Learn Chinese

An interactive web app for learning Chinese, built around a progressive
dictionary and spaced practice. Open [`learnchinese.html`](learnchinese.html)
in a browser to use it.

## Contents

| File | Description |
| --- | --- |
| `learnchinese.html` | The single-file web app. |
| `sw.js` | Service worker for offline support. |
| `build-dict.py` | Script that builds the dictionary data. |
| `progressive-dictionary.txt` | Source dictionary used by the build. |
| `cedict-supplement.json` | Supplemental CC-CEDICT entries. |
| `tps-dictionary.json` | Generated dictionary consumed by the app. |
| `poems-g1.json` – `poems-g6.json` | Poem lists for grades 1–6 (id, title, author, pinyin). |
| `poems-edb.json` | Additional poems from the HK EDB curriculum list. |
| `poems-media.json` | Maps each poem to its audio and video links; `_credits` lists the credited YouTube playlists in priority order. |
| `fetch-playlist-videos.py` | Syncs video links in `poems-media.json` from the credited playlists (requires `yt-dlp` and `zhconv`). |
| `playlist-cache/` | Browser-exported playlist HTML files used as fallback when yt-dlp cannot enumerate all items (e.g. members-only content). Save as `<PLAYLIST_ID>.html`. |

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
