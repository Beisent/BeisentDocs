# BeisentDocs

轻量级 Markdown 文档站点生成器，纯 Python 实现，零外部依赖。

## 特性

- **零依赖** — 仅使用 Python 标准库，无需 `pip install`
- **Markdown 扩展** — GFM 表格、任务列表、脚注、高亮、删除线、提示块（NOTE/TIP/WARNING/IMPORTANT/CAUTION）
- **代码高亮** — 通过 Highlight.js 支持多语言语法高亮
- **数学公式** — 通过 KaTeX 渲染行内 `$...$` 和块级 `$$...$$` 公式
- **自动导航** — 侧边栏、面包屑、页内目录（TOC）自动生成
- **响应式设计** — 适配桌面和移动端
- **开发友好** — 内置 HTTP 服务器和文件监听自动重建

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
python build.py watch        # 监听 docs/ 变化，自动重建
```

## 项目结构

```
BeisentDocs/
├── build.py              # 构建脚本（Markdown 解析器 + 站点生成器）
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
│   └── section.html      # 分区页
├── static/               # 静态资源（CSS/JS）
└── dist/                 # 构建输出（自动生成）
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
| `icon` | [Lucide](https://lucide.dev/icons/) 图标名 |
| `order` | 排序权重，数字越小越靠前 |

### 分区

子目录即为分区，通过 `_index.md` 定义分区元数据。分区页会自动展示该目录下所有文档的卡片列表。

## 配置

`config.json` 用于配置顶部导航栏链接：

```json
{
  "nav": [
    {"label": "GitHub", "url": "https://github.com/beisent"}
  ]
}
```

## 自定义样式

编辑 `static/css/style.css` 中的 CSS 变量调整站点风格。HTML 模板位于 `templates/` 目录，使用 `{{变量名}}` 占位符，构建时自动替换。

## 技术栈

| 组件 | 技术 |
|:-----|:-----|
| 构建脚本 | Python 3.10+（标准库） |
| 代码高亮 | [Highlight.js](https://highlightjs.org/)（CDN） |
| 数学渲染 | [KaTeX](https://katex.org/)（CDN） |
| 图标 | [Lucide Icons](https://lucide.dev/)（CDN） |
| 输出 | 静态 HTML/CSS/JS |

## License

MIT
