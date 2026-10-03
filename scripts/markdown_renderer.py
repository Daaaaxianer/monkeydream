"""Markdown 渲染与 HTML 清洗工具。

- 使用 python-markdown 渲染(支持表格/代码高亮/TOC/围栏代码块等扩展)
- 使用 nh3(基于 Rust 的 HTML 清洗器) 过滤危险标签与属性, 防止 XSS
"""
import functools
import re
from html import escape

import markdown as md
import nh3
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class MathPreprocessor(Preprocessor):
    # Fenced code has already been stashed. Inline code is consumed unchanged.
    pattern = re.compile(r"(`+)([\s\S]*?)\1|(?P<display>\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\])|(?P<inline>\\\([^\n]+?\\\)|(?<!\\)\$(?!\$)[^\n$]+?(?<!\\)\$)")

    def run(self, lines):
        def protect(match):
            if match.group(1):
                return match.group(0)
            display = bool(match.group("display"))
            tag, cls = ("div", "math-display") if display else ("span", "math-inline")
            raw = match.group(0)
            inner = raw[2:-2] if display or raw.startswith("\\(") else raw[1:-1]
            delimiters = ("\\[", "\\]") if display else ("\\(", "\\)")
            html = f'<{tag} class="{cls}">{escape(delimiters[0] + inner + delimiters[1])}</{tag}>'
            placeholder = self.md.htmlStash.store(html)
            return f"\n\n{placeholder}\n\n" if display else placeholder
        return self.pattern.sub(protect, "\n".join(lines)).split("\n")


class MathExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(MathPreprocessor(md), "preserve_math", 24)

ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "b", "i", "u", "del", "s", "sub", "sup",
    "ul", "ol", "li", "blockquote", "pre", "code", "kbd",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "span", "div", "details", "summary",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target", "id", "class"},
    "li": {"id"},
    "sup": {"id"},
    "img": {"src", "alt", "title", "width", "height"},
    "code": {"class"},
    "pre": {"class"},
    "span": {"class"},
    "div": {"class"},
    "th": {"align"},
    "td": {"align"},
    "h1": {"id"}, "h2": {"id"}, "h3": {"id"}, "h4": {"id"}, "h5": {"id"}, "h6": {"id"},
}

URL_SCHEMES = {"http", "https", "mailto", "tel"}


@functools.lru_cache(maxsize=256)
def render_markdown(text: str) -> str:
    """将 Markdown 文本渲染为安全的 HTML。"""
    if not text:
        return ""
    md_converter = md.Markdown(
        extensions=[
            "extra",            # 表格、围栏代码、脚注、定义列表等
            "codehilite",       # 代码高亮(配合 Pygments)
            "toc",              # 标题锚点目录
            "sane_lists",       # 更严格的列表解析
            "nl2br",            # 换行转 <br>
            MathExtension(),
        ],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "highlight",
            },
            "toc": {"permalink": False},
        },
        output_format="html5",
    )
    html = md_converter.convert(text)
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        link_rel="noopener noreferrer",
    )
