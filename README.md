# MonkeyDream

简洁的个人静态博客：HTML、CSS、JavaScript、SVG。访问网站不需要 Python、Django、数据库或服务器进程。Python 仅用于在本地或 GitHub Actions 将 Markdown 生成静态文件。

## 目录

- `content/posts/`：公开文章 Markdown。
- `content/site.json`：站点名称、描述与正式网址。
- `content/tools.json`：公开工具与项目链接。
- `assets/`：统一 SVG Logo、样式与浏览器脚本。
- `study_materials/`：学习包和课程索引，学习路线位于博客内。
- `scripts/`：静态构建、Logo 生成、检查与测试。
- `site/`：生成后可直接托管的完整网站。
- `.github/workflows/pages.yml`：GitHub Pages 自动构建与发布。

首页只包含简介与最新文章；学习路线和文献资源从博客进入。支持全文本地搜索、文章类型与证据状态筛选、课程关联、归档、分类、标签、RSS、目录、代码复制、表格横向滚动、脚注和数学公式。公式由浏览器加载固定版本 MathJax CDN 渲染，正文与其余功能不依赖该 CDN。

## 本地生成和预览

```powershell
python -m pip install -r build-requirements.txt
python scripts/build_logos.py
python -m unittest discover -s scripts -p test_static.py
python scripts/build_site.py
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

打开 http://127.0.0.1:8000/ 。构建会先检查内部页面、资源及锚点，再替换 `site/`。直接打开 HTML 也能阅读正文；完整预览建议用上述静态文件服务器。它仅用于本地预览，无需部署到线上。

## 发布文章

复制 `content/post-template.md` 到 `content/posts/`，填写元数据和正文。顶部 `---` 之间使用 JSON（不是任意 YAML），以避免额外解析依赖。设置 `draft: false` 才会进入网站。完整示例和证据状态说明见 `docs/博士学习博客使用说明.md`。

文章图片放入 `assets/uploads/`，正文可使用相对路径，例如 `../../../assets/uploads/figure.png`。文章 slug 决定固定 URL `/blog/post/<slug>/`，已发布后尽量保持不变。

草稿不进入生成网站，但公开 GitHub 仓库中的源文件仍可被阅读。私人复盘放在仓库外；不要把敏感资料写入文章源文件。构建额外移除 `## 私人记录附页` 起的正文。

## GitHub Pages 和已有域名

1. 将项目源文件提交到 GitHub 公开仓库的 `main` 分支；不要提交本地恢复备份。
2. 仓库 Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**。
3. 推送后工作流会构建网站并仅上传 `site/`，PR 仅构建检查，不发布。
4. `content/site.json` 当前网址为 `https://monkeydream.top`，构建相应生成 `CNAME`。在 Pages 设置中填写同一自定义域名，并按 GitHub 提示设置域名 DNS；验证通过后开启 HTTPS。

域名由你自行续费。GitHub Free 的公开仓库可使用 Pages；服务受 GitHub 当前额度和政策约束，不作永久免费承诺。

官方说明：[自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[自定义域名](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)。本次仅准备配置，没有改变你的 DNS 或上线仓库。

## Logo

`assets/logos/` 直接复用用户提供的横版与竖版 PNG，提供导航横排、深色徽章、竖排、头像、favicon 和分享卡片 7 种布局。网站导航与小图标统一采用横版的眨眼小猴，关于页采用仰望月亮的竖版。SVG 是内嵌原图的布局封装，不是纯矢量重绘；原字形与图案不变。预览 `/logos/`，尺寸与使用规则见 `assets/logos/README.md`。运行 `scripts/build_logos.py` 后重新生成。

## 旧系统恢复备份

旧 Django 源码、数据库、环境配置、媒体和旧文档已保存在本地 `_private_backup/django-original.zip`。该目录已被 `.gitignore` 排除，构建和发布均不会读取或上传它。旧登录、注册、管理后台、评论写入及数据库进度功能已移除。实际学习成果通过博客记录，计划索引不自动宣称完成。
