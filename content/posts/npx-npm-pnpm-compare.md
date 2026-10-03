---
{
  "title": "npx / npm / pnpm 对比",
  "slug": "npx-npm-pnpm-compare",
  "summary": "一文搞懂 npx / npm / pnpm 三者的区别与联系：npm 与 pnpm 负责安装管理，npx 负责临时执行。附常用命令等价对照表。",
  "article_type": "other",
  "evidence_status": "unspecified",
  "code_url": "",
  "data_url": "",
  "date": "2026-08-21",
  "updated": "2026-08-21",
  "category": "技术分享",
  "category_slug": "tech",
  "tags": [
    {
      "name": "Node.js",
      "slug": "nodejs"
    },
    {
      "name": "npm",
      "slug": "npm"
    },
    {
      "name": "pnpm",
      "slug": "pnpm"
    },
    {
      "name": "包管理",
      "slug": "package-manager"
    }
  ],
  "sessions": [],
  "draft": false
}
---

## 一句话总结

`npm` 和 `pnpm` 是**包管理器**（负责安装、管理依赖），而 `npx` 是 npm 自带的**执行工具**（临时运行包命令，无需全局安装）。三者职责常被混淆，本文用一张表讲清楚。

## npm：Node 官方包管理器

`npm` 随 Node.js 自带，无需额外安装，是最基础的包管理工具。

```bash
npm install pkg      # 本地安装
npm install -g pkg   # 全局安装
npm run script       # 执行脚本
npm exec pkg         # npm v7+ 等价于 npx
```

> **缺点**：旧版本采用嵌套依赖结构，磁盘占用较大；`node_modules` 体积偏大。

## npx：执行工具，不是包管理器

`npx` 是 npm 附带的**执行工具**，用于运行包命令，**可以不全局安装**。

```bash
npx create-vite@latest
# 等价于
npm exec create-vite@latest
```

> **执行逻辑**：优先调用本地 `node_modules/.bin` 下的命令；找不到时临时下载运行，结束后自动清理。
>
> npm@7 之后官方推荐使用 `npm exec`，`npx` 保留兼容。

## pnpm：更快、更省磁盘的替代方案

`pnpm` 是独立的第三方包管理器，需要单独安装，不随 Node.js 自带。

```bash
pnpm add pkg        # 本地安装
pnpm add -g pkg     # 全局安装
pnpm run script     # 运行脚本
pnpm dlx pkg        # ✨ pnpm 版的 npx，临时运行包
```

- **核心优势**：硬链接 + 内容可寻址存储，磁盘复用率高，安装速度远快于 npm
- 命令与 npm 几乎一一对应，迁移成本低

## 常用等价对照表

| 功能       | npm           | pnpm              |
| ---------- | ------------- | ----------------- |
| 安装依赖   | `npm install` | `pnpm install`    |
| 安装包     | `npm i xxx`   | `pnpm add xxx`    |
| 临时执行包 | `npx xxx`     | `pnpm dlx xxx`    |
| 运行脚本   | `npm run dev` | `pnpm dev`        |
| 卸载包     | `npm rm xxx`  | `pnpm remove xxx` |

## 小提醒

1. 别混淆职责：**npm / pnpm 负责安装管理；npx / pnpm dlx 负责执行**
2. 新项目优先选择 pnpm（速度与磁盘更优）；老项目保持原有管理器，避免混用。
