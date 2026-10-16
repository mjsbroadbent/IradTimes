#!/usr/bin/env python3
"""Builds the Irad Times website from content/ into static HTML.

    python3 tools/build.py

Stories live in content/stories/*.txt, one file each: a block of "key: value"
header lines, a blank line, then the body, one paragraph per blank-line
separated block. Lines starting "## " are subheads, "> " a pull quote.
Pages (about, access, ...) live in content/pages/*.html with the same header.

Header keys: headline, dek, date (YYYY-MM-DD), section, byline, image,
caption, kind (story | editorial | brief | archive), issue (current issue
stories carry the issue number), note (archive line under the dek).
"""
import html, json, re, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
SITE = CFG["site_url"].rstrip("/") + "/"
MONTHS = "January February March April May June July August September October November December".split()


def esc(s):
    return html.escape(s, quote=True)


def nice_date(d, weekday=False):
    s = f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    return (d.strftime("%A ") + s) if weekday else s


def parse(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    head, _, body = text.partition("\n\n")
    meta = {}
    for line in head.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    meta["body"] = body.strip()
    meta["slug"] = path.stem
    if "date" in meta:
        meta["d"] = datetime.date.fromisoformat(meta["date"])
    return meta


def inline(s):
    # *italic* and [text](url); everything else is literal HTML-escaped text,
    # except a few entities written as-is.
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    return s


def body_html(body):
    out = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            out.append(f"<h2>{inline(block[3:])}</h2>")
        elif block.startswith("> "):
            out.append(f'<blockquote class="pull">{inline(block[2:])}</blockquote>')
        elif block.startswith("- "):
            items = "".join(f"<li>{inline(x[2:])}</li>" for x in block.split("\n") if x.startswith("- "))
            out.append(f"<ul>{items}</ul>")
        elif block.startswith("<"):
            out.append(block)  # raw HTML block (tables, figures)
        else:
            out.append(f"<p>{inline(' '.join(block.split()))}</p>")
    return "\n".join(out)


def lede(body, n=158):
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if b and not b.startswith(("#", ">", "<", "-")):
            t = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", " ".join(b.split())).replace("*", "")
            return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"
    return ""


def url_of(s):
    if s["kind"] == "archive":
        return f"archive/{s['d'].year}/{s['slug']}.html"
    return f"{s['d'].year}/{s['d'].month:02d}/{s['slug']}.html"


TEMPLATE = (ROOT / "tools" / "page.html").read_text(encoding="utf-8")


def page(path, title, body, desc, depth, og_image=None, og_type="website", extra_head="", rel=None):
    rel = ("../" * depth) if rel is None else rel
    canonical = SITE + ("" if path == "index.html" else path)
    img = SITE + (og_image or "img/og-default.jpg")
    issue = CFG["issue"]
    d = datetime.date.fromisoformat(issue["date"])
    out = (TEMPLATE
           .replace("{{title}}", esc(title))
           .replace("{{desc}}", esc(desc))
           .replace("{{canonical}}", esc(canonical))
           .replace("{{og_image}}", esc(img))
           .replace("{{og_type}}", og_type)
           .replace("{{extra_head}}", extra_head)
           .replace("{{rel}}", rel)
           .replace("{{issue_line}}", f"{nice_date(d, True)} · No. {issue['number']:,} · Vol. {issue['volume']}")
           .replace("{{notice}}", notice_html(rel))
           .replace("{{body}}", body)
           .replace("{{rel}}", rel))
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(out, encoding="utf-8")
    return canonical


def notice_html(rel):
    n = CFG.get("notice")
    if not n:
        return ""
    return f'<div class="notice"><div class="wrap"><strong>{esc(n["title"])}</strong> {esc(n["text"])} <a href="{rel}access.html">How to read us</a></div></div>'


def figure(s, rel, cls="lead"):
    if not s.get("image"):
        return ""
    cap = f"<figcaption>{inline(s.get('caption', ''))}</figcaption>" if s.get("caption") else ""
    return f'<figure class="{cls}"><img src="{rel}img/{s["image"]}" alt="{esc(s.get("alt", s.get("caption", "")).replace("*", ""))}" loading="lazy">{cap}</figure>'


def byline(s):
    bits = []
    if s.get("byline"):
        bits.append(f'<span class="by">By {esc(s["byline"])}</span>')
    bits.append(f'<time datetime="{s["date"]}">{nice_date(s["d"])}</time>')
    return f'<p class="meta">{" · ".join(bits)}</p>'


def main():
    stories = sorted((parse(p) for p in (ROOT / "content" / "stories").glob("*.txt")), key=lambda s: s["date"], reverse=True)
    for s in stories:
        s.setdefault("kind", "story")
        s["url"] = url_of(s)
    pages = {p.stem: parse(p) for p in (ROOT / "content" / "pages").glob("*.html")}
    urls = []
    issue_no = str(CFG["issue"]["number"])
    current = [s for s in stories if s.get("issue") == issue_no]
    archive = [s for s in stories if s["kind"] == "archive"]

    # story pages
    for s in stories:
        depth = s["url"].count("/")
        rel = "../" * depth
        kicker = s.get("section", "")
        note = f'<p class="note">{inline(s["note"])}</p>' if s.get("note") else ""
        more = [x for x in current if x is not s][:4] if s in current else [x for x in archive if x is not s and abs(x["d"].year - s["d"].year) < 6][:4]
        more_html = "".join(f'<li><a href="{rel}{x["url"]}">{esc(x["headline"])}</a> <span>{nice_date(x["d"])}</span></li>' for x in more)
        ld = {
            "@context": "https://schema.org", "@type": "NewsArticle" if s["kind"] != "editorial" else "OpinionNewsArticle",
            "headline": s["headline"], "datePublished": s["date"], "description": s.get("dek") or lede(s["body"]),
            "publisher": {"@type": "NewsMediaOrganization", "name": "Irad Times"}, "url": SITE + s["url"],
        }
        if s.get("byline"):
            ld["author"] = [{"@type": "Person", "name": n.strip()} for n in re.split(r" and |, ", s["byline"])]
        if s.get("image"):
            ld["image"] = SITE + "img/" + s["image"]
        body = f'''<article class="story {s["kind"]}">
<p class="kicker">{esc(kicker)}</p>
<h1>{inline(s["headline"])}</h1>
{f'<p class="dek">{inline(s["dek"])}</p>' if s.get("dek") else ""}
{note}
{byline(s)}
{figure(s, rel)}
<div class="text">
{body_html(s["body"])}
</div>
{'<p class="free">The Times keeps its investigations free to read. If they are worth something to you, <a href="' + rel + 'subscribe.html">subscribe to the paper</a>.</p>' if s["kind"] in ("story", "archive") else ""}
</article>
{f'<aside class="more"><h3>{"Also in this issue" if s in current else "From the archive"}</h3><ul>{more_html}</ul></aside>' if more_html else ""}'''
        head = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>'
        urls.append((page(s["url"], f'{s["headline"]} | Irad Times', body, s.get("dek") or lede(s["body"]), depth,
                          og_image=("img/" + s["image"]) if s.get("image") else None, og_type="article", extra_head=head), s["date"]))

    # front page
    lead = next(s for s in current if s.get("lead") == "yes")
    rest = [s for s in current if s is not lead and s["kind"] == "story"]
    editorial = next((s for s in current if s["kind"] == "editorial"), None)
    briefs = [s for s in current if s["kind"] == "brief"]
    def thumb(s, cls="sq"):
        return f'<a href="{s["url"]}"><img class="{cls}" src="img/{s["image"]}" alt=""></a>' if s.get("image") else ""
    mods = "".join(f'''<div class="mod-story">{thumb(s)}<p class="slug">{esc(s.get("section", ""))}</p>
<h3><a href="{s["url"]}">{inline(s["headline"])}</a></h3><p class="by">by {esc(s.get("byline", ""))}</p><p>{inline(s.get("dek", ""))}</p></div>''' for s in rest[2:])
    brief_html = "".join(f'<li><a href="{s["url"]}">{inline(s["headline"])}</a></li>' for s in briefs)
    picks = [a for a in archive if a.get("pick") == "yes"]
    picks_html = "".join(f'<li><a href="{a["url"]}">{inline(a["headline"])}</a> <span>{a["d"].year}</span></li>' for a in picks)
    popular = [lead] + rest[:3] + ([editorial] if editorial else [])
    pop_html = "".join(f'<li><a href="{s["url"]}">{inline(s["headline"])}</a></li>' for s in popular)
    front = f'''<div class="fp">
<div class="fp-main">
<div class="fp-top">
<div class="lead-box">
<a href="{lead["url"]}"><img src="img/{lead["image"]}" alt="{esc(lead.get("caption", "").replace("*", ""))}"></a>
<p class="credit">{inline(lead.get("caption", ""))}</p>
<p class="slug">{esc(lead.get("section", ""))}</p>
<h2><a href="{lead["url"]}">{inline(lead["headline"])}</a></h2>
<p class="by">by {esc(lead.get("byline", ""))}</p>
<p>{esc(lede(lead["body"], 330))}</p>
<ul class="related"><li><a href="{lead["url"]}">Read the investigation</a></li><li><a href="archive/2019/the-antimony-shareholders-nobody-can-name.html">2019: The Antimony Shareholders Nobody Can Name</a></li></ul>
</div>
<div class="second">
{"".join(f'<div class="sec-story"><h2><a href="{s["url"]}">{inline(s["headline"])}</a></h2><p>{inline(s.get("dek", ""))}</p></div>' for s in rest[:2])}
{f'<div class="sec-story ed"><p class="slug">The Times says</p><h2><a href="{editorial["url"]}">{inline(editorial["headline"])}</a></h2><p>{esc(lede(editorial["body"], 200))}</p></div>' if editorial else ""}
</div>
</div>
<div class="banner"><a href="access.html"><strong>Blocked in Irad since 15 October.</strong> Read the Times on Tulpar, by email, or on paper every Thursday &rsaquo;</a></div>
<div class="mod"><h4>This week's paper <a href="issue/">all stories &rsaquo;</a></h4>{mods}</div>
<div class="cols2">
<div class="mod"><h4>In brief <a href="issue/">more &rsaquo;</a></h4><ul class="list">{brief_html}</ul></div>
<div class="mod"><h4>The record <a href="archive/">since 1996 &rsaquo;</a></h4><ul class="list">{picks_html}</ul></div>
</div>
</div>
<div class="fp-right">
<div class="rbox"><h4>Don't miss</h4>
<div class="dm"><a href="archive/2007/the-drafts-framework-treaty-and-protocols.html"><img src="img/bill-of-sale-1.jpg" alt=""></a><h3><a href="archive/2007/the-drafts-framework-treaty-and-protocols.html">The Drafts, 26 February 2007</a></h3><p>The special edition that printed the treaty to sell Irad, in full.</p></div>
<div class="dm"><a href="access.html"><img src="img/newsroom.jpg" alt=""></a><h3><a href="access.html">If we are blocked</a></h3><p>How to read us, and every block since 2013.</p></div>
</div>
<div class="rbox"><h4>Most read</h4><div class="tabs"><span class="on">Read</span><span>Shared</span><span>Printed</span></div><ol class="list pop">{pop_html}</ol></div>
<div class="rbox paper"><h4>The paper</h4><p><b>On the stands every Thursday</b> in Talas, Nurzhan and Iyık Janyl. 24 pages, 5 som.</p><p><a href="subscribe.html">Subscribe at home or abroad &rsaquo;</a><br><a href="tips.html">Send us documents &rsaquo;</a></p></div>
</div>
</div>'''
    ld_site = {"@context": "https://schema.org", "@type": "WebSite", "name": "Irad Times", "url": SITE}
    urls.insert(0, (page("index.html", "Irad Times | The independent weekly of Irad since 1996", front,
                         CFG["description"], 0, og_image="img/" + lead["image"],
                         extra_head=f'<script type="application/ld+json">{json.dumps(ld_site)}</script>'), CFG["issue"]["date"]))

    # issue page (this week's paper)
    issue_list = "".join(f'<li><span class="kicker">{esc(s.get("section", ""))}</span> <a href="../{s["url"]}">{inline(s["headline"])}</a></li>' for s in current)
    urls.append((page("issue/index.html", f"This week's paper, No. {issue_no} | Irad Times",
                      f'<h1>This week’s paper</h1><p class="meta">No. {int(issue_no):,}, {nice_date(datetime.date.fromisoformat(CFG["issue"]["date"]), True)}</p><ul class="issue-list">{issue_list}</ul><p>Earlier issues are in the <a href="../archive/">archive</a>; the paper’s investigations are free to read.</p>',
                      f"Everything in the Irad Times of {nice_date(datetime.date.fromisoformat(CFG['issue']['date']))}.", 1), CFG["issue"]["date"]))

    # archive index
    by_year = {}
    for a in archive + [s for s in stories if s["kind"] != "archive"]:
        by_year.setdefault(a["d"].year, []).append(a)
    arch = ['<h1>Archive</h1><p class="intro">The investigations that made the Times, from the first issue in April 1996. Archive stories are free to read. The paper’s full back numbers can be seen on paper at the National Library of Irad, Talas State University, and at our office on Printers’ Lane.</p>']
    for y in sorted(by_year, reverse=True):
        rows = "".join(f'<li><a href="../{a["url"]}">{inline(a["headline"])}</a> <span>{nice_date(a["d"])}</span></li>' for a in sorted(by_year[y], key=lambda a: a["date"], reverse=True))
        arch.append(f'<h2 id="{y}">{y}</h2><ul class="archive-list">{rows}</ul>')
    urls.append((page("archive/index.html", "Archive: investigations since 1996 | Irad Times", "\n".join(arch),
                      "Every investigation in the Irad Times archive, from the 2007 Bill of Sale drafts and the grain auction to antimony and the Public Integrity Commission.", 1), CFG["issue"]["date"]))

    # plain pages
    for name, p in pages.items():
        path = "404.html" if name == "404" else f"{name}.html"
        body = p["body"]
        base = "/" + CFG.get("base_path", "").strip("/") + "/" if CFG.get("base_path", "").strip("/") else "/"
        c = page(path, f'{p["headline"]} | Irad Times' if name != "404" else "Page not found | Irad Times", body,
                 p.get("dek", ""), 0, rel=base if name == "404" else None)
        if name != "404":
            urls.append((c, CFG["issue"]["date"]))

    # sitemap and robots
    sm = "\n".join(f"  <url><loc>{esc(u)}</loc><lastmod>{d}</lastmod></url>" for u, d in urls)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sm}\n</urlset>\n', encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    print(f"built {len(urls)} pages")


if __name__ == "__main__":
    main()
