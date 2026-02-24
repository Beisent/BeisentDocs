---
title: API 参考
description: MarkdownParser 和 SiteBuilder 的 Python 编程接口
tag: api
icon: code
order: 5
---

# API 参考

BeisentDocs 的核心由两个类组成：`MarkdownParser` 负责 Markdown 解析，`SiteBuilder` 负责站点构建。

## MarkdownParser

纯 Python 实现的 Markdown 转 HTML 解析器。

### 基本用法

```python
from builder import MarkdownParser

parser = MarkdownParser()
html = parser.parse("# Hello World\n\nThis is **bold** text.")
```

### 属性

| 属性 | 类型 | 说明 |
|:-----|:-----|:-----|
| `footnotes` | `dict[str, str]` | 解析过程中收集的脚注 |
| `headings` | `list[dict]` | 解析过程中收集的标题列表，每项包含 `level`、`text`、`slug` |

`headings` 在每次调用 `parse()` 后更新，可用于生成目录。

### 支持的语法扩展

| 语法 | 写法 | 说明 |
|:-----|:----:|:-----|
| 围栏代码块 | ` ``` ` / `~~~` | 支持语言标注 |
| 行内数学 | `$...$` | KaTeX 行内公式 |
| 块级数学 | `$$...$$` | KaTeX 块级公式 |
| 表格 | `\| ... \|` | GFM 风格，支持对齐 |
| 任务列表 | `- [x]` / `- [ ]` | 复选框 |
| 删除线 | `~~text~~` | 删除效果 |
| 高亮 | `==text==` | 标记高亮 |
| 提示块 | `> [!TYPE]` | NOTE、TIP、WARNING、IMPORTANT、CAUTION |
| 脚注 | `[^key]` | 引用式脚注 |

## SiteBuilder

站点生成器，将 `docs/` 中的 Markdown 文件构建为完整的静态 HTML 站点。

### 构造函数

```python
from builder import SiteBuilder

builder = SiteBuilder(
    docs_dir="docs",           # Markdown 源文件目录
    dist_dir="dist",           # 输出目录
    static_dir="static",       # 静态资源目录
    templates_dir="templates"  # HTML 模板目录
)
```

所有参数均为相对于项目根目录的路径，默认值即为项目的标准目录结构。

### 方法

#### `build()`

执行完整的站点构建流程：

1. 清空 `dist/` 目录
2. 复制 `static/` 资源到 `dist/static/`
3. 递归扫描 `docs/` 构建分区树
4. 渲染首页、分区页和文档页
5. 输出到 `dist/`

```python
builder = SiteBuilder()
builder.build()
```

> [!NOTE]
> 如果 `docs/` 目录中没有任何 `.md` 文件，构建会输出提示信息并跳过。

## CLI 用法

```bash
# 构建站点
python build.py

# 构建并启动本地服务器
python build.py serve        # 默认端口 8000
python build.py serve 3000   # 指定端口

# 监听模式（文件变化自动重建）
python build.py watch
```
