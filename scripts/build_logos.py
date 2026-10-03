"""Layout supplied PNG artwork in portable SVG viewports, without tracing it."""
import base64
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "assets" / "logos"


def artwork(name, width, height):
    encoded = base64.b64encode((ROOT / name).read_bytes()).decode("ascii")
    return f'<image width="{width}" height="{height}" href="data:image/png;base64,{encoded}"/>'


def svg(viewbox, body, label):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img"><title>MonkeyDream · {label}</title>{body}</svg>\n'


def viewport(image, box, x, y, width, height):
    return f'<svg x="{x}" y="{y}" width="{width}" height="{height}" viewBox="{box}" preserveAspectRatio="xMidYMid meet">{image}</svg>'


def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    for original, name in [("logo1.png", "source-horizontal.png"), ("logo2.png", "source-stacked.png")]:
        source = PROJECT / original
        if source.exists():
            shutil.copy2(source, ROOT / name)
        if not (ROOT / name).exists():
            raise FileNotFoundError(f"Missing artwork: {name}")
    horizontal = artwork("source-horizontal.png", 1448, 1086)
    stacked = artwork("source-stacked.png", 1254, 1254)
    horizontal_box = "20 330 1410 370"
    icon_box = "20 330 435 370"
    assets = {
        "logo-wordmark.svg": svg(horizontal_box, horizontal, "横版原图"),
        "logo-stacked.svg": svg("75 175 1110 910", stacked, "竖版原图"),
        "logo.svg": svg("0 0 256 256", viewport(horizontal, icon_box, 6, 20, 244, 216), "眨眼小猴头像"),
        "logo-wordmark-light.svg": svg("0 0 600 180", '<rect x="1" y="1" width="598" height="178" rx="28" fill="#fff"/>'+viewport(horizontal, horizontal_box, 18, 16, 564, 148), "深色背景横版徽章"),
        "logo-light.svg": svg("0 0 256 256", '<rect width="256" height="256" rx="56" fill="#fff"/>'+viewport(horizontal, icon_box, 12, 22, 232, 212), "深色背景头像徽章"),
        "favicon.svg": svg("0 0 64 64", '<rect width="64" height="64" rx="15" fill="#fff"/>'+viewport(horizontal, icon_box, 3, 5, 58, 54), "浏览器图标"),
        "logo-social.svg": svg("0 0 1200 630", '<rect width="1200" height="630" fill="#fff"/>'+viewport(horizontal, horizontal_box, 120, 190, 960, 252), "分享卡片"),
    }
    for name, content in assets.items():
        (ROOT / name).write_text(content, encoding="utf-8")
    (ROOT / "README.md").write_text("""# MonkeyDream Logo 使用规范

直接复用用户提供的 logo1.png（横版、眨眼）与 logo2.png（竖版、仰望）。
原始 PNG 保留不变；SVG 使用内嵌 PNG 和视口布局，不是纯矢量描边。

| 文件 | 使用位置 |
| --- | --- |
| logo-wordmark.svg | 桌面/手机导航、页脚 |
| logo-wordmark-light.svg | 深色背景；自带白色圆角徽章 |
| logo-stacked.svg | 关于页、介绍封面；保留月亮和星星 |
| logo.svg | 首页介绍、头像；横版同款眨眼小猴 |
| logo-light.svg | 深色背景头像；自带浅色衬底 |
| favicon.svg | 浏览器标签；同款眨眼小猴 |
| logo-social.svg | 1200×630 分享卡片 |

保持原有棕色 Monkey、橙色 Dream 和圆润字形，不重新输入文字、不拉伸。
横版建议展示宽度 186–300px，头像 48–128px；需要放大印刷时请另做纯矢量描摹。
网站浅色背景使用 multiply 混合模式弱化原图白底；深色背景使用徽章版。
运行 python scripts/build_logos.py 可重复生成。源图也保存在本目录，CI 可直接使用。
""", encoding="utf-8")
    print(f"Prepared {len(assets)} logo layouts from the two supplied images.")


if __name__ == "__main__":
    build()
