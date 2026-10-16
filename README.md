# Irad Times

Website of the *Irad Times* (*Irad Ubaktysy*), the independent English-language weekly of Talas, Irad, founded 1996. Part of the Irad worldbuilding project with [Irad Wiki](https://irad.wiki/), the [Talas Herald](https://talasherald.com/) and [IradOne](https://iradone.com/).

Static site for GitHub Pages, built by `python3 tools/build.py`.

| To change | Edit |
|---|---|
| A story | `content/stories/<slug>.txt` (header lines, blank line, paragraphs; `## ` subhead, `> ` pull quote, `- ` list, raw HTML blocks allowed) |
| This week's issue | `issue` in `content/site.json`; tag current stories `issue: <number>`, one with `lead: yes` |
| The "blocked" banner | `notice` in `content/site.json` (remove to hide) |
| Pages | `content/pages/*.html` |
| Layout | `tools/page.html`, `assets/times.css` |
| Address | `site_url` and `base_path` in `content/site.json` (for a custom domain set `base_path` to "") |

Archive stories (`kind: archive`) keep the headlines and dates the Irad Wiki cites. `pick: yes` puts one on the front page.
