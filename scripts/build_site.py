"""Build a standalone HTML/CSS/JS site. No web framework or database is used."""
import json
import re
import shutil
import sys
import zipfile
import posixpath
from pathlib import Path
from html import escape as esc
from urllib.parse import quote
from datetime import date
from xml.sax.saxutils import escape as xml_escape
from pygments.formatters import HtmlFormatter
from markdown_renderer import render_markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site_build"
CONFIG = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
BASE = CONFIG["url"].rstrip("/")
TYPES = {"note": "方法笔记", "reading": "文献精读", "replication": "论文复现", "project": "研究项目", "weekly": "学习周记", "other": "其他文章"}
EVIDENCE = {"unspecified": "未标注", "plan": "计划 / 待运行", "literature": "文献解读", "simulation": "教学模拟", "analysis": "实际分析", "partial": "部分复现", "replication": "原数据核心复现", "validation": "独立验证"}


def load_posts():
    posts = []
    for path in (ROOT / "content/posts").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
        if not match:
            raise ValueError(f"Missing JSON metadata: {path.name}")
        item = json.loads(match[1])
        if item.get("draft", True):
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", item["slug"]):
            raise ValueError(f"Unsafe slug: {path.name}")
        if any(p["slug"] == item["slug"] for p in posts):
            raise ValueError("Duplicate article slug")
        date.fromisoformat(item["date"])
        body = re.split(r"(?m)^## 私人记录附页[^\n]*\n", text[match.end():])[0]
        item["body"] = body
        item["url"] = "blog/post/" + item["slug"] + "/"
        item["html"] = render_markdown(body)
        # Private notes/credentials never enter the source format or published index.
        posts.append(item)
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def relative(page, target):
    if target.startswith(("https://", "http://", "mailto:", "#")):
        return target
    directory = page.rsplit("/", 1)[0] if "/" in page else "."
    path, sep, fragment = target.partition("#")
    result = posixpath.relpath(path or ".", directory)
    if path.endswith("/"):
        result += "/"
    return result + (sep + fragment if sep else "")


def link(page, target, text, cls=""):
    return f'<a href="{esc(relative(page, target), quote=True)}" class="{cls}">{esc(text)}</a>'


def layout(page, title, body, active="", article=False, description=None):
    asset = lambda path: esc(relative(page, "assets/" + path), quote=True)
    nav = "".join(f'<a href="{esc(relative(page, url), quote=True)}"' + (' aria-current="page"' if key == active else "") + f'>{label}</a>' for key, label, url in [("home", "首页", "index.html"), ("blog", "博客", "blog/"), ("archive", "归档", "blog/archive/"), ("tools", "小工具", "tools/"), ("about", "关于", "about/")])
    math = f'<script defer src="{asset("js/math-config.js")}"></script><script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js"></script>' if article else ""
    desc = esc(description or CONFIG["description"], quote=True)
    canonical = BASE + "/" + (page[:-10] if page.endswith("index.html") else page)
    return f'''<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{desc}">
<title>{esc(title)} · MonkeyDream</title><link rel="canonical" href="{esc(canonical,quote=True)}">
<link rel="icon" href="{asset('logos/favicon.svg')}" type="image/svg+xml"><link rel="stylesheet" href="{asset('css/site.css')}"><link rel="stylesheet" href="{asset('css/syntax.css')}">
<link rel="alternate" type="application/rss+xml" title="MonkeyDream" href="{esc(relative(page,'feed.xml'),quote=True)}">
<script defer src="{asset('js/site.js')}"></script>{math}</head><body>
<header class="site-header"><div class="shell nav"><a class="brand" href="{esc(relative(page,'index.html'),quote=True)}"><img src="{asset('logos/logo-wordmark.svg')}" width="224" height="42" alt="MonkeyDream"></a><button class="menu-button" type="button" aria-expanded="false" aria-controls="main-nav">菜单</button><nav id="main-nav" class="nav-links" aria-label="主导航">{nav}</nav></div></header>
<main>{body}</main><footer class="site-footer"><div class="shell footer-inner"><div><a href="{esc(relative(page,'index.html'),quote=True)}"><img src="{asset('logos/logo-wordmark.svg')}" width="186" height="35" alt="MonkeyDream"></a><p>© {date.today().year} MonkeyDream · 保持好奇，慢慢记录。</p></div><nav class="footer-links" aria-label="页脚导航">{link(page,'about/','关于')}{link(page,'feed.xml','RSS')}</nav></div></footer><button type="button" class="back-top" aria-label="返回顶部" hidden>↑</button></body></html>'''


def write(page, text):
    path = OUT / page
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def post_row(page, post):
    category = link(page, "blog/category/" + quote(post["category_slug"]) + "/", post["category"]) if post.get("category_slug") else ""
    return f'<article class="post-row"><div class="meta"><time datetime="{post["date"]}">{post["date"].replace("-", ".")}</time>{category}</div><h2>{link(page,post["url"],post["title"])}</h2><p>{esc(post.get("summary", ""))}</p>{link(page,post["url"],"阅读全文 ↗","read-link")}</article>'


def article_page(post, posts):
    page = post["url"] + "index.html"
    category = link(page,"blog/category/"+post["category_slug"]+"/",post["category"]) if post.get("category_slug") else ""
    tags = "".join(link(page,"blog/tag/"+t["slug"]+"/","#"+t["name"]) for t in post.get("tags",[]))
    meta = f'<div class="meta"><time datetime="{post["date"]}">{post["date"]}</time><span>{max(1,round(len(post["body"])/400))} 分钟阅读</span>{category}</div><div class="meta">{tags}</div>'
    evidence = EVIDENCE.get(post.get("evidence_status"), "未标注")
    links = "".join(link(page,"blog/learning/#"+s[:3],s) for s in post.get("sessions", []))
    for field, label in [("code_url", "代码与环境 ↗"), ("data_url", "数据入口 ↗")]:
        url = post.get(field, "")
        if url.startswith(("https://", "http://")):
            links += link(page,url,label)
    info = f'<section class="evidence" aria-label="文章与证据状态"><strong>{TYPES.get(post.get("article_type"),"其他文章")} · {evidence}</strong><p>更新于 {esc(post.get("updated",post["date"]))}</p><div class="evidence-links">{links}</div></section>' if post.get("article_type") != "other" or links else ""
    index = posts.index(post)
    adjacent = "".join(link(page,p["url"],label+p["title"]) for p,label in [(posts[index-1] if index else None,"← 较新："),(posts[index+1] if index+1<len(posts) else None,"较早：")] if p)
    body = f'<div class="shell article-layout"><article class="article-main"><header class="article-head">{link(page,"blog/","← 博客")}<h1>{esc(post["title"])}</h1>{meta}</header>{info}<div class="article-body" id="article-body">{post["html"]}</div><nav class="article-next" aria-label="相邻文章">{adjacent}</nav></article><aside class="article-toc"><strong>文章目录</strong><nav id="toc" aria-label="文章目录"></nav></aside></div>'
    write(page, layout(page,post["title"],body,"blog",True,post.get("summary")))


def blog_page(posts, subset=None, title="博客", page="blog/index.html"):
    shown = posts if subset is None else subset
    options = lambda labels: "".join(f'<option value="{key}">{label}</option>' for key,label in labels.items())
    data = [{"url":relative(page,p["url"]),"title":p["title"],"summary":p.get("summary",""),"type":p.get("article_type","other"),"evidence":p.get("evidence_status","unspecified"),"category":p.get("category_slug",""),"tags":[t["slug"] for t in p.get("tags",[])],"sessions":p.get("sessions",[]),"search":p["title"]+" "+p.get("summary","")+" "+p["body"]} for p in shown]
    encoded = json.dumps(data,ensure_ascii=False).replace("<","\\u003c")
    cards = "".join('<div data-post="'+str(i)+'">'+post_row(page,p)+"</div>" for i,p in enumerate(shown))
    body = f'<section class="shell page"><h1>{esc(title)}</h1><div class="blog-links">{link(page,"blog/learning/","学习路线")}{link(page,"blog/resources/","文献与数据资源")}{link(page,"blog/archive/","文章归档")}</div><form class="filters" id="blog-filter"><input type="search" name="q" aria-label="搜索文章" placeholder="搜索标题、摘要或正文…"><select name="type" aria-label="文章类型"><option value="">所有类型</option>{options(TYPES)}</select><select name="evidence" aria-label="证据状态"><option value="">所有证据状态</option>{options(EVIDENCE)}</select><input name="session" aria-label="课程编号" placeholder="课程编号 W01-S01"><button class="button" type="submit">筛选</button><button class="button" type="reset">清除</button></form><p id="filter-count" class="filter-count" aria-live="polite">{len(shown)} 篇文章</p><noscript><p class="no-script">全部公开文章列于下方；启用JavaScript可使用本地搜索。</p></noscript>{cards}<p id="search-empty" class="empty" hidden>没有匹配的文章，试试其他关键词。</p><script type="application/json" id="post-index">{encoded}</script></section>'
    write(page,layout(page,title,body,"blog"))


def build():
    if OUT.is_symlink() or OUT.resolve() != ROOT / "_site_build":
        raise ValueError("Unsafe output directory")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT/"assets",OUT/"assets")
    (OUT/"assets/css/syntax.css").write_text(HtmlFormatter(style="friendly").get_style_defs(".highlight"),encoding="utf-8")
    posts = load_posts()
    page = "index.html"
    body = f'<div class="shell journal"><header class="intro"><img src="{relative(page,"assets/logos/logo.svg")}" width="78" height="78" alt="微笑眨眼的小猴"><div><h1>你好，欢迎来到 MonkeyDream。</h1><p>{esc(CONFIG["description"])}</p>{link(page,"about/","关于我 ↗")}</div></header><section aria-labelledby="latest-title"><div class="section-heading"><h2 id="latest-title">最新文章</h2>{link(page,"blog/","全部博客 →")}</div>{"".join(post_row(page,p) for p in posts[:8]) or "<p class=empty>还没有公开文章。</p>"}</section></div>'
    write(page,layout(page,"个人博客",body,"home"))
    blog_page(posts)
    for post in posts:
        article_page(post,posts)
    categories = {p["category_slug"]:p["category"] for p in posts if p.get("category_slug")}
    for slug,name in categories.items():
        if not re.fullmatch(r"[a-z0-9-]+",slug): raise ValueError("Unsafe category slug")
        blog_page(posts,[p for p in posts if p.get("category_slug")==slug],name,"blog/category/"+slug+"/index.html")
    tags = {t["slug"]:t["name"] for p in posts for t in p.get("tags",[])}
    for slug,name in tags.items():
        if not re.fullmatch(r"[a-z0-9-]+",slug): raise ValueError("Unsafe tag slug")
        blog_page(posts,[p for p in posts if slug in [t["slug"] for t in p.get("tags",[])]],name,"blog/tag/"+slug+"/index.html")
    page="blog/archive/index.html"
    years=sorted({p["date"][:4] for p in posts},reverse=True)
    body='<section class="shell page"><h1>文章归档</h1>'+"".join(f'<h2 class="archive-year">{y}</h2>'+"".join(post_row(page,p) for p in posts if p["date"].startswith(y)) for y in years)+"</section>"
    write(page,layout(page,"文章归档",body,"archive"))
    page="about/index.html"
    body='<section class="shell page article-body"><h1>关于我</h1><p>你好，我是 MonkeyDream。从生物信息学走向公共卫生与预防医学、流行病与卫生统计学，研究兴趣包括疾病预测与肠道微生物组。</p><p>这里记录学习总结、文献阅读、方法实践，也分享生活与日常思考。学习记录是博客的一部分，慢慢积累，不急着给每一步下结论。</p>'+link(page,"blog/","阅读博客 →")+"</section>"
    body=body.replace('<h1>关于我</h1>', '<img class="about-logo" src="'+relative(page,'assets/logos/logo-stacked.svg')+'" width="240" alt="MonkeyDream 仰望月亮的小猴"><h1>关于我</h1>')
    write(page,layout(page,"关于我",body,"about"))
    tools=json.loads((ROOT/"content/tools.json").read_text(encoding="utf-8"))
    page="tools/index.html"
    body='<section class="shell page"><h1>小工具</h1><p class="page-lead">自己使用或整理的小工具与项目。</p><div class="tool-grid">'+"".join(f'<article class="tool-card"><h2>{link(page,"tools/"+t["slug"]+"/",t["name"])}</h2><p>{esc(t["summary"])}</p>{link(page,t["url"],"访问项目 ↗")}</article>' for t in tools)+"</div></section>"
    write(page,layout(page,"小工具",body,"tools"))
    for t in tools:
        if not re.fullmatch(r"[a-z0-9-]+",t["slug"]) or not t["url"].startswith(("http://","https://")): raise ValueError("Invalid tool")
        page="tools/"+t["slug"]+"/index.html"
        body=f'<section class="shell page article-body"><h1>{esc(t["name"])}</h1><p class="page-lead">{esc(t["summary"])}</p>{link(page,t["url"],"打开项目 ↗","button")}{render_markdown(t.get("description", ""))}</section>'
        write(page,layout(page,t["name"],body,"tools",True))
    build_learning(posts)
    build_logos_page()
    page="404.html"
    missing=layout(page,"页面未找到",'<section class="shell not-found"><img src="assets/logos/logo.svg" alt="小猴"><h1>这条小路还没有内容。</h1><p>'+link(page,"index.html","返回首页")+"</p></section>")
    missing=missing.replace('<head>', '<head><base href="'+esc(BASE+'/',quote=True)+'">')
    write(page,missing)
    (OUT/".nojekyll").touch()
    (OUT/"CNAME").write_text(BASE.split("//",1)[1].split("/")[0]+"\n",encoding="utf-8")
    sitemap=[BASE+"/"+(p.relative_to(OUT).as_posix()[:-10] if p.name=="index.html" else p.relative_to(OUT).as_posix()) for p in OUT.rglob("*.html") if p.name!="404.html"]
    write("sitemap.xml",'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join('<url><loc>'+xml_escape(u)+'</loc></url>' for u in sitemap)+"</urlset>")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: "+BASE+"/sitemap.xml\n")
    feed='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>MonkeyDream</title><link>'+BASE+'</link><description>'+xml_escape(CONFIG["description"])+"</description>"
    for p in posts[:20]:
        url=BASE+"/"+p["url"]
        feed+='<item><title>'+xml_escape(p["title"])+'</title><link>'+url+'</link><guid>'+url+'</guid><description>'+xml_escape(p.get("summary",""))+'</description></item>'
    write("feed.xml",feed+"</channel></rss>")
    # Keep the former RSS URL working without a backend.
    write("feed/index.html",redirect_page("feed/index.html","feed.xml"))
    from verify_site import verify
    verify(OUT)
    final=ROOT/"site"
    if final.is_symlink() or final.resolve()!=ROOT/"site": raise ValueError("Unsafe final directory")
    if final.exists(): shutil.rmtree(final)
    OUT.rename(final)
    print(f"Built {len(posts)} articles, {len(tools)} tools; ready to host site/ as static files.")


def redirect_page(page,target):
    dest=esc(relative(page,target),quote=True)
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url='+dest+'"><title>页面已移动</title><a href="'+dest+'">继续访问</a></html>'


def build_learning(posts):
    folder=ROOT/"study_materials"
    downloads=OUT/"downloads";downloads.mkdir()
    for path in folder.glob("*.md"): shutil.copy2(path,downloads/path.name)
    with zipfile.ZipFile(downloads/"MonkeyDream-study.zip","w",zipfile.ZIP_DEFLATED) as z:
        for path in folder.glob("*.md"): z.write(path,path.name)
    sessions=json.loads((folder/"curriculum.json").read_text(encoding="utf-8"))
    page="blog/learning/index.html"
    body='<section class="shell page"><h1>学习路线</h1><p class="page-lead">24周通用流行病学训练：96次必修与24次选修。作为博客的学习索引，任务计划与实际成果分别记录。</p>'+link(page,"downloads/MonkeyDream-study.zip","下载完整学习包 ↓","button")
    body+='<nav class="week-nav" aria-label="按周跳转">'+"".join(link(page,"#W"+f"{w:02}","W"+f"{w:02}") for w in range(1,25))+"</nav>"
    for week in range(1,25):
        group=[s for s in sessions if s["week"]==week]
        body+=f'<section class="week" id="W{week:02}"><h2>W{week:02} · {esc(group[0]["week_title"])}</h2>'
        for s in group:
            related="".join(link(page,p["url"],p["title"],"session-post") for p in posts if s["code"] in p.get("sessions",[]))
            prompt=f'按24周通用流行病学学习方案，开始{s["code"]}：{s["title"]}。本次3小时，R优先。请整理学习记录与博客Markdown，明确区分原文报告、教学模拟、实际分析与待完成内容。'
            body+=f'<details class="session"><summary>{s["code"]} · {esc(s["title"])}'+(' · 选修' if s["number"]==5 else '')+f'</summary><div class="session-body"><p>{esc(s["task"])}</p><p class="output"><strong>最低产出：</strong>{esc(s["deliverable"])}</p><div class="refs">{render_markdown(s["references"])}</div>{related or "<p>尚无关联的公开记录。</p>"}<button class="button" type="button" data-copy="{esc(prompt,quote=True)}">复制开课指令</button></div></details>'
        body+='</section>'
    write(page,layout(page,"学习路线",body+"</section>","blog"))
    page="blog/resources/index.html"
    source=(folder/"03_文献与数据资源库.md").read_text(encoding="utf-8")
    write(page,layout(page,"文献与数据资源",'<section class="shell page article-body"><h1>文献与数据资源</h1><p class="page-lead">来自既有学习包，实际使用时核验文献全文与数据获取条件。</p>'+link(page,"downloads/MonkeyDream-study.zip","下载学习包 ↓","button")+render_markdown(source)+"</section>","blog",True))
    for old,new in [("learning/index.html","blog/learning/"),("resources/index.html","blog/resources/")]: write(old,redirect_page(old,new))


def build_logos_page():
    page="logos/index.html"
    variants=[("logo-wordmark.svg","导航栏 / 页脚 · 横排",False),("logo-wordmark-light.svg","深色背景 · 横排徽章",True),("logo-stacked.svg","关于页 / 封面 · 竖排",False),("logo.svg","首页介绍 / 头像 · 眨眼小猴",False),("logo-light.svg","深色背景 · 头像徽章",True),("favicon.svg","浏览器标签 · 小图标",False),("logo-social.svg","链接分享 · 1200 × 630",False)]
    body='<section class="shell page"><h1>MonkeyDream Logo</h1><p class="page-lead">直接使用你提供的横版与竖版 Logo，保留原有猴子造型、棕橙配色与圆润字形。导航、头像和标签统一使用眨眼小猴，介绍页保留仰望月亮的版本。</p><p class="logo-note">下载文件为内嵌原始 PNG 的 SVG 布局封装，保留原图质量，不属于纯矢量重绘。浅色背景配合网站混合模式，深色背景使用白色徽章。</p><div class="logo-grid">'
    for file,label,dark in variants:
        url=relative(page,"assets/logos/"+file)
        body+=f'<section class="logo-card'+(' dark' if dark else '')+f'"><h2>{label}</h2><img src="{url}" alt="{label}"><a href="{url}" download>下载 SVG ↓</a></section>'
    write(page,layout(page,"Logo设计",body+"</div></section>"))


if __name__=="__main__":
    build()
