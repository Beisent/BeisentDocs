---
title: Getting Started
description: BeisentDocs 项目介绍与快速上手指南
tag: guide
icon: rocket
order: 1
---

# Getting Started

**BeisentDocs** 是一个轻量级的 Markdown 文档站点生成器，使用纯 Python 实现，零外部依赖。它将 `docs/` 目录中的 Markdown 文件转换为美观的静态 HTML 文档网站。

## 核心特性

- **零依赖** — 仅使用 Python 标准库，无需 `pip install`
- **Markdown 解析** — 支持 GFM 表格、任务列表、脚注、高亮文本等扩展语法
- **代码高亮** — 通过 Highlight.js 支持多语言语法高亮
- **数学公式** — 通过 KaTeX 渲染行内公式 `$...$` 和块级公式 `$$...$$`
- **提示块** — 支持 NOTE、TIP、WARNING、IMPORTANT、CAUTION 五种提示块样式
- **自动导航** — 自动生成侧边栏导航、面包屑和页内目录（TOC）
- **响应式设计** — 适配桌面和移动端
- **开发服务器** — 内置 HTTP 服务器和文件监听自动重建

## 快速开始

**前置条件：** Python 3.10+

```bash
# 1. 克隆项目
git clone https://github.com/beisent/BeisentDocs.git
cd BeisentDocs

# 2. 构建静态站点
python build.py

# 3. 本地预览（默认端口 8000）
python build.py serve
```

在浏览器中打开 `http://localhost:8000` 即可查看生成的文档站点。

## 开发模式

Watch 模式会监听 `docs/` 目录的变化，自动触发重建：

```bash
python build.py watch
```

## 项目结构

```
BeisentDocs/
├── build.py              # 构建脚本（Markdown 解析器 + 站点生成器）
├── config.json           # 站点配置（导航链接等）
├── docs/                 # Markdown 源文件目录
│   ├── getting-started.md
│   ├── guides/
│   │   ├── _index.md     # 分区元数据
│   │   └── installation.md
│   └── ...
├── templates/            # HTML 页面模板
│   ├── index.html        # 首页模板
│   ├── doc.html          # 文档页模板
│   └── section.html      # 分区页模板
├── static/               # 静态资源
│   ├── css/style.css
│   └── js/main.js
└── dist/                 # 构建输出目录（自动生成）
```

## 下一步

- [安装与配置](guides/installation.html) — 详细的配置说明和目录组织方式
- [Markdown 语法指南](markdown-guide.html) — 支持的 Markdown 语法完整参考
- [数学公式示例](math-examples.html) — KaTeX 数学公式渲染示例
- [API 参考](api-reference.html) — MarkdownParser 和 SiteBuilder 的编程接口
