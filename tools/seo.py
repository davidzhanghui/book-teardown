#!/usr/bin/env python3
"""SEO 批量处理脚本（book-teardown）

功能：
1. 为全站 HTML 注入 description / canonical / Open Graph / Twitter Card / JSON-LD
   （注入块用 <!-- SEO-INJECT:START/END --> 包裹，重复执行幂等）
2. 生成 sitemap.xml / robots.txt / 404.html / assets/og-cover.png

用法：
    python3 tools/seo.py                      # 使用默认 BASE_URL
    BASE_URL=https://books.example.com python3 tools/seo.py

注意：md2html 重新生成 HTML 后需重跑本脚本。
"""
import html as ihtml
import json
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.environ.get("BASE_URL", "https://book-teardown.vercel.app").rstrip("/")
SITE_NAME = "Book Teardown · 拆书"
OG_IMAGE = "assets/og-cover.png"
MARK_S = "<!-- SEO-INJECT:START -->"
MARK_E = "<!-- SEO-INJECT:END -->"
DESC_LEN = 150


# ---------------------------------------------------------------- 工具

def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", ihtml.unescape(s)).strip()


def truncate(s: str, n: int = DESC_LEN) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip("，。；、,.; ") + "…"


def esc(s: str) -> str:
    return ihtml.escape(s, quote=True)


def url_for(rel: Path) -> str:
    """相对路径 -> 绝对 URL；index.html 归一到目录 URL。"""
    p = rel.as_posix()
    if p == "index.html":
        return BASE_URL + "/"
    if p.endswith("/index.html"):
        p = p[: -len("index.html")]
    return BASE_URL + "/" + urllib.parse.quote(p)


def file_date(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def page_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return strip_tags(m.group(1)) if m else ""


def first_para(html: str) -> str:
    m = re.search(r"CONTENT_START\s*-->(.*)", html, re.S)
    body = m.group(1) if m else html
    p = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
    return strip_tags(p.group(1)) if p else ""


def book_desc(book_dir: Path) -> str:
    """书目录页 description：取 00 导读「系列简介」第一段。"""
    md = sorted(book_dir.glob("00*.md"))
    if md:
        text = md[0].read_text(encoding="utf-8")
        m = re.search(r"^## [^\n]+\n+(.+?)(?:\n\n|\Z)", text, re.M | re.S)
        if m:
            para = re.sub(r"\*\*|__", "", m.group(1))
            return re.sub(r"\s+", " ", para).strip()
    return f"《{book_dir.name}》深度解读系列目录。"


def article_files(book_dir: Path):
    return sorted(p for p in book_dir.glob("*.html")
                  if p.name != "index.html")


# ---------------------------------------------------------------- JSON-LD

def ld_article(rel, title, desc, book, date, siblings):
    crumbs = [
        {"@type": "ListItem", "position": 1, "name": "拆书", "item": BASE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": book,
         "item": url_for(rel.parent / "index.html")},
        {"@type": "ListItem", "position": 3, "name": title, "item": url_for(rel)},
    ]
    graph = [
        {"@type": "Article", "headline": title, "description": desc,
         "inLanguage": "zh-CN", "datePublished": date, "dateModified": date,
         "author": {"@type": "Organization", "name": SITE_NAME},
         "isPartOf": {"@type": "Book", "name": book},
         "mainEntityOfPage": url_for(rel),
         "image": f"{BASE_URL}/{OG_IMAGE}"},
        {"@type": "BreadcrumbList", "itemListElement": crumbs},
    ]
    # 同系列上一篇/下一篇（relatedLink 帮助爬虫发现相邻篇目）
    idx = siblings.index(rel)
    rel_links = []
    if idx > 0:
        rel_links.append(url_for(siblings[idx - 1]))
    if idx < len(siblings) - 1:
        rel_links.append(url_for(siblings[idx + 1]))
    if rel_links:
        graph[0]["relatedLink"] = rel_links
    return {"@context": "https://schema.org", "@graph": graph}


def ld_book_index(rel, book, desc, date, articles):
    crumbs = [
        {"@type": "ListItem", "position": 1, "name": "拆书", "item": BASE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": book, "item": url_for(rel)},
    ]
    items = [{"@type": "ListItem", "position": i + 1,
              "name": page_title(a.read_text(encoding="utf-8")) or a.stem,
              "url": url_for(a.relative_to(ROOT))}
             for i, a in enumerate(articles)]
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": f"《{book}》解读系列 · 目录",
         "description": desc, "inLanguage": "zh-CN",
         "dateModified": date, "url": url_for(rel),
         "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL + "/"}},
        {"@type": "ItemList", "itemListElement": items},
        {"@type": "BreadcrumbList", "itemListElement": crumbs},
    ]}


def ld_master(book_dirs):
    items = [{"@type": "ListItem", "position": i + 1, "name": d.name,
              "url": url_for(d.relative_to(ROOT) / "index.html")}
             for i, d in enumerate(book_dirs)]
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": SITE_NAME,
         "description": "每本书一个解读系列：拆解全书结构与知识地图，逐篇回答一个核心问题。",
         "inLanguage": "zh-CN", "url": BASE_URL + "/",
         "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL + "/"}},
        {"@type": "ItemList", "itemListElement": items},
    ]}


# ---------------------------------------------------------------- meta 注入

def build_block(rel, kind, title, desc, date, ld, extra=""):
    canonical = url_for(rel)
    og_type = "article" if kind == "article" else "website"
    lines = [
        MARK_S,
        f'  <meta name="description" content="{esc(desc)}">',
        f'  <link rel="canonical" href="{canonical}">',
        f'  <meta property="og:type" content="{og_type}">',
        f'  <meta property="og:site_name" content="{esc(SITE_NAME)}">',
        f'  <meta property="og:title" content="{esc(title)}">',
        f'  <meta property="og:description" content="{esc(desc)}">',
        f'  <meta property="og:url" content="{canonical}">',
        f'  <meta property="og:image" content="{BASE_URL}/{OG_IMAGE}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{esc(title)}">',
        f'  <meta name="twitter:description" content="{esc(desc)}">',
        f'  <meta name="twitter:image" content="{BASE_URL}/{OG_IMAGE}">',
    ]
    if kind == "article":
        lines.append(f'  <meta property="article:published_time" content="{date}">')
        lines.append(f'  <meta property="article:modified_time" content="{date}">')
    if extra:
        lines.append(extra)
    lines.append('  <script type="application/ld+json">'
                 + json.dumps(ld, ensure_ascii=False, separators=(",", ":"))
                 + "</script>")
    lines.append(MARK_E)
    return "\n".join(lines)


def inject(path: Path, block: str):
    html = path.read_text(encoding="utf-8")
    html = re.sub(re.escape(MARK_S) + r".*?" + re.escape(MARK_E) + r"\n?",
                  "", html, flags=re.S)
    html = html.replace("</head>", block + "\n</head>", 1)
    path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------- OG 封面

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",                 # macOS
    "/System/Library/Fonts/PingFang.ttc",                         # macOS
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",     # Linux (Noto)
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",             # Linux (文泉驿)
    "C:/Windows/Fonts/msyh.ttc",                                  # Windows 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",                                # Windows 黑体
]


def _load_font(size, index=0):
    """按候选顺序加载中文字体；全部失败退回 PIL 默认字体（中文将无法渲染）。"""
    from PIL import ImageFont
    for p in FONT_CANDIDATES:
        if not os.path.exists(p):
            continue
        for idx in (index, 0):
            try:
                return ImageFont.truetype(p, size, index=idx)
            except OSError:
                continue
    print("warning: 未找到可用中文字体，回退到 PIL 默认字体（中文将无法渲染）")
    return ImageFont.load_default()


def gen_og_image():
    from PIL import Image, ImageDraw
    out = ROOT / OG_IMAGE
    out.parent.mkdir(exist_ok=True)
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#FAFAF7")
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, 24, H], fill="#D97757")
    dr.rectangle([0, H - 24, W, H], fill="#D97757")
    f_big = _load_font(92, index=1)
    f_sm = _load_font(40)
    dr.ellipse([72, 84, 100, 112], fill="#D97757")
    dr.text((120, 78), "BOOK TEARDOWN", font=f_sm, fill="#A85533")
    dr.text((72, 220), "拆书", font=f_big, fill="#1A1A1A")
    dr.text((72, 360), "一本书 · 一个系列 · 每篇只回答一个问题",
            font=f_sm, fill="#4A4A45")
    dr.text((72, 430), "观点 / 事实 / 争议 分层拆解", font=f_sm, fill="#6B6B66")
    img.save(out, "PNG", optimize=True)
    print(f"og image -> {out.relative_to(ROOT)}")


# ---------------------------------------------------------------- 站点文件

def gen_sitemap(entries):
    """entries: [(rel_path, lastmod, priority)]"""
    urls = "\n".join(
        f"  <url><loc>{url_for(r)}</loc><lastmod>{d}</lastmod>"
        f"<priority>{p}</priority></url>"
        for r, d, p in entries)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{urls}\n</urlset>\n")
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")


def gen_robots():
    (ROOT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /*.md$\n"
        "Disallow: /tools/\n\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")


def gen_404():
    (ROOT / "404.html").write_text(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>页面不存在 · 拆书</title>
  <style>
    body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
      background:#FAFAF7; color:#1A1A1A;
      font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans CJK SC',sans-serif; }}
    .box {{ text-align:center; padding:40px; }}
    .code {{ font-size:72px; font-weight:700; color:#D97757; margin:0; }}
    p {{ color:#6B6B66; }}
    a {{ display:inline-block; margin-top:16px; padding:12px 24px; background:#D97757;
      color:#fff; text-decoration:none; border-radius:8px; font-weight:600; }}
    a:hover {{ background:#C56843; }}
  </style>
</head>
<body>
  <div class="box">
    <p class="code">404</p>
    <p>这篇解读不存在，或已被移动。</p>
    <a href="{BASE_URL}/">返回书籍总目录</a>
  </div>
</body>
</html>
""", encoding="utf-8")


# ---------------------------------------------------------------- 主流程

def main():
    book_dirs = sorted(d for d in ROOT.iterdir()
                       if d.is_dir() and (d / "index.html").exists())
    entries = []
    n_art = 0

    # 总目录
    master = ROOT / "index.html"
    desc_master = ("书籍深度解读合集：每本书一个系列，先拆解全书结构与知识地图，"
                   "再逐篇回答一个核心问题，区分观点、事实与争议。")
    inject(master, build_block(Path("index.html"), "collection",
                               page_title(master.read_text(encoding="utf-8")),
                               desc_master, file_date(master),
                               ld_master(book_dirs)))
    entries.append((Path("index.html"), file_date(master), "1.0"))

    for d in book_dirs:
        articles = article_files(d)
        bdesc = truncate(book_desc(d))

        # 书目录页
        bidx = d / "index.html"
        rel = bidx.relative_to(ROOT)
        inject(bidx, build_block(rel, "collection",
                                 page_title(bidx.read_text(encoding="utf-8")),
                                 bdesc, file_date(bidx),
                                 ld_book_index(rel, d.name, bdesc,
                                               file_date(bidx), articles)))
        entries.append((rel, file_date(bidx), "0.8"))

        # 文章页
        sib_rels = [a.relative_to(ROOT) for a in articles]
        for a in articles:
            rel = a.relative_to(ROOT)
            h = a.read_text(encoding="utf-8")
            title = page_title(h) or a.stem
            desc = truncate(first_para(h)) or bdesc
            date = file_date(a)
            inject(a, build_block(rel, "article", title, desc, date,
                                  ld_article(rel, title, desc, d.name,
                                             date, sib_rels)))
            entries.append((rel, date, "0.6"))
            n_art += 1

    gen_og_image()
    gen_sitemap(entries)
    gen_robots()
    gen_404()
    print(f"books={len(book_dirs)} articles={n_art} urls={len(entries)}")
    print(f"BASE_URL={BASE_URL}")


if __name__ == "__main__":
    main()
