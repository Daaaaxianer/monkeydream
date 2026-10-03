# MonkeyDream Logo 使用规范

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
