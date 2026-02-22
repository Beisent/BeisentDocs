---
title: 安装与配置
description: 详细的安装步骤、目录组织、config.json 配置和 frontmatter 字段说明
order: 1
icon: settings
---

# 安装与配置

## 安装

BeisentDocs 使用纯 Python 标准库实现，无需安装任何第三方包。

```bash
git clone https://github.com/beisent/BeisentDocs.git
cd BeisentDocs
```

确认 Python 版本 >= 3.10：

```bash
python --version
```

## 构建命令

```bash
# 构建站点，输出到 dist/ 目录
python build.py

# 构建并启动本地服务器（默认端口 8000）
python build.py serve

# 指定端口
python build.py serve 3000

# 监听模式，docs/ 有变化时自动重建
python build.py watch
```

## 站点配置（config.json）

项目根目录的 `config.json` 用于配置顶部导航栏的外部链接：

```json
{
  "nav": [
    {"label": "GitHub", "url": "https://github.com/beisent"},
    {"label": "Blog", "url": "https://example.com/blog"}
  ]
}
```

`nav` 数组中的每个对象会渲染为顶部导航栏的链接。

## 文档目录组织

所有 Markdown 文件放在 `docs/` 目录下。目录结构直接映射为站点的 URL 结构：

```
docs/
├── getting-started.md        → /getting-started.html
├── markdown-guide.md         → /markdown-guide.html
├── guides/
│   ├── _index.md             → /guides/index.html（分区页）
│   ├── installation.md       → /guides/installation.html
│   └── advanced/
│       ├── _index.md         → /guides/advanced/index.html
│       └── deployment.md     → /guides/advanced/deployment.html
└── api/
    ├── _index.md             → /api/index.html
    └── endpoints.md          → /api/endpoints.html
```

### 分区（Section）

子目录即为一个分区。在子目录中放置 `_index.md` 文件来定义分区的元数据：

```yaml
---
title: 指南
description: 使用教程和操作指南
icon: book-open
order: 1
---

这里可以写分区的介绍内容（可选）。
```

分区页面会自动展示该目录下所有文档的卡片列表。

## Frontmatter 字段

每个 Markdown 文件开头可以使用 YAML frontmatter 定义元数据：

```yaml
---
title: 文档标题
description: 简短描述，用于卡片展示和 SEO
tag: guide
icon: book-open
order: 1
---
```

### 字段说明

| 字段 | 必填 | 说明 |
|:-----|:----:|:-----|
| `title` | 否 | 文档标题。未指定时自动从第一个 `#` 标题提取 |
| `description` | 否 | 简短描述。未指定时自动截取正文前 160 个字符 |
| `tag` | 否 | 分类标签，显示在卡片上。如 `guide`、`api`、`reference`、`tutorial`、`example`、`info` |
| `icon` | 否 | 卡片图标，使用内置 SVG 图标名。如 `book-open`、`code`、`rocket` |
| `order` | 否 | 排序权重，数字越小越靠前，默认 99 |

### 自动图标推断

如果未指定 `icon`，系统会根据文档的 slug 或标题自动推断图标：

| 关键词 | 图标 |
|:-------|:-----|
| guide | `book-open` |
| api | `code` |
| tutorial | `graduation-cap` |
| reference | `bookmark` |
| example | `lightbulb` |
| start | `rocket` |
| install | `download` |
| config | `settings` |

未匹配到关键词时使用默认图标 `file-text`。

## 模板自定义

HTML 模板位于 `templates/` 目录，可直接编辑：

| 模板文件 | 用途 |
|:---------|:-----|
| `index.html` | 首页，包含 hero 区域和文档卡片网格 |
| `doc.html` | 文档页，三栏布局：侧边栏 + 正文 + 目录 |
| `section.html` | 分区页，展示子文档卡片列表 |

模板中使用 `{{变量名}}` 占位符，构建时由 `SiteBuilder` 自动替换。

### 可用模板变量

**通用变量：**
- `{{base_path}}` — 相对于站点根目录的路径前缀
- `{{nav_links}}` — 顶部导航链接（来自 config.json）

**文档页变量（doc.html）：**
- `{{title}}` — 文档标题
- `{{content}}` — 渲染后的 HTML 正文
- `{{toc}}` — 页内目录
- `{{sidebar_nav}}` — 侧边栏导航树
- `{{breadcrumbs}}` — 面包屑导航

**分区页变量（section.html）：**
- `{{title}}` — 分区标题
- `{{description}}` — 分区描述
- `{{section_content}}` — 分区正文（来自 `_index.md`）
- `{{cards}}` — 子文档/子分区卡片网格

## 静态资源

`static/` 目录中的文件会在构建时原样复制到 `dist/static/`。可以在此放置自定义的 CSS、JavaScript 或图片资源。

> [!TIP]
> 修改 `static/css/style.css` 中的 CSS 变量可以快速调整站点的整体风格（字体、颜色、间距等）。
