# BeisentDocs

轻量级 Markdown 文档站点生成器，纯 Python 实现，零外部依赖。

## 特性

- **零依赖** — 仅使用 Python 标准库，无需 `pip install`
- **Markdown 扩展** — GFM 表格、任务列表、脚注、高亮、删除线、提示块（NOTE/TIP/WARNING/IMPORTANT/CAUTION）、嵌套列表
- **代码高亮** — 通过 Highlight.js 支持多语言语法高亮
- **数学公式** — 通过 KaTeX 渲染行内 `$...$` 和块级 `$$...$$` 公式
- **自动导航** — 侧边栏、面包屑、页内目录（TOC）、上一篇/下一篇自动生成
- **全文搜索** — 客户端搜索，支持 Ctrl+K / Cmd+K 快捷键
- **暗色模式** — 支持亮色/暗色主题切换，本地存储持久化
- **响应式设计** — 适配桌面和移动端
- **SEO 优化** — 自动生成 sitemap.xml、meta 标签、Open Graph 标签
- **开发友好** — 内置 HTTP 服务器、文件监听自动重建、LiveReload 热更新

## 快速开始

**前置条件：** Python 3.10+

```bash
git clone https://github.com/beisent/BeisentDocs.git
cd BeisentDocs

# 构建静态站点
python build.py

# 本地预览
python build.py serve
```

浏览器打开 `http://localhost:8000` 查看站点。

## 用法

```bash
python build.py              # 构建站点到 dist/
python build.py serve        # 构建并启动服务器（默认端口 8000）
python build.py serve 3000   # 指定端口
python build.py watch        # 监听文件变化，自动重建
python build.py dev          # 开发模式（自动重建 + LiveReload，默认端口 8000）
python build.py dev 3000     # 开发模式指定端口
```

## 项目结构

```
BeisentDocs/
├── build.py              # CLI 入口（构建/serve/watch/dev）
├── builder/              # 核心模块包
│   ├── __init__.py       # 包入口，导出 MarkdownParser、SiteBuilder
│   ├── icons.py          # 内置 SVG 图标数据
│   ├── parser.py         # Markdown 解析器
│   ├── site.py           # 站点生成器
│   └── server.py         # 开发服务器（serve/watch/dev）
├── config.json           # 站点配置（导航链接）
├── docs/                 # Markdown 源文件
│   ├── getting-started.md
│   ├── guides/
│   │   ├── _index.md     # 分区元数据
│   │   └── installation.md
│   └── ...
├── templates/            # HTML 页面模板
│   ├── index.html        # 首页
│   ├── doc.html          # 文档页
│   ├── section.html      # 分区页
│   └── 404.html          # 404 错误页
├── static/               # 静态资源（CSS/JS）
└── dist/                 # 构建输出（自动生成）
    ├── *.html            # 生成的 HTML 页面
    ├── search-index.json # 搜索索引
    ├── sitemap.xml       # 站点地图
    └── static/           # 复制的静态资源
```

## 编写文档

在 `docs/` 目录下添加 `.md` 文件即可。目录结构直接映射为站点 URL：

```
docs/getting-started.md   → /getting-started.html
docs/guides/_index.md     → /guides/index.html（分区页）
docs/guides/setup.md      → /guides/setup.html
```

### Frontmatter

文件开头可使用 YAML frontmatter 定义元数据：

```yaml
---
title: 文档标题
description: 简短描述
tag: guide
icon: book-open
order: 1
---
```

| 字段 | 说明 |
|:-----|:-----|
| `title` | 文档标题，未指定时从 `#` 标题提取 |
| `description` | 简短描述，用于卡片展示 |
| `tag` | 分类标签（guide/api/reference/tutorial/example/info） |
| `icon` | 内置 SVG 图标名（如 `book-open`、`code`、`rocket`） |
| `order` | 排序权重，数字越小越靠前 |

### 分区

子目录即为分区，通过 `_index.md` 定义分区元数据。分区页会自动展示该目录下所有文档的卡片列表。

## 配置

`config.json` 用于配置站点信息和导航栏链接：

```json
{
  "site_name": "BeisentDocs",
  "site_description": "极简文档",
  "footer_text": "Beisent Lab",
  "base_url": "https://beisent.github.io",
  "nav": [
    {"label": "GitHub", "url": "https://github.com/beisent"}
  ]
}
```

| 字段 | 说明 |
|:-----|:-----|
| `site_name` | 站点名称，显示在导航栏和页面标题 |
| `site_description` | 站点描述，显示在首页 |
| `footer_text` | 页脚版权信息 |
| `base_url` | 站点基础 URL，用于生成 sitemap.xml 和 SEO 标签 |
| `nav` | 顶部导航栏外部链接列表 |

## 自定义样式

编辑 `static/css/style.css` 中的 CSS 变量调整站点风格。HTML 模板位于 `templates/` 目录，使用 `{{变量名}}` 占位符，构建时自动替换。

## 技术栈

| 组件 | 技术 |
|:-----|:-----|
| 构建脚本 | Python 3.10+（标准库） |
| 代码高亮 | [Highlight.js](https://highlightjs.org/)（CDN） |
| 数学渲染 | [KaTeX](https://katex.org/)（CDN） |
| 图标 | 内置 SVG 图标（无外部依赖） |
| 输出 | 静态 HTML/CSS/JS |

## License

MIT
