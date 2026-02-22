---
title: 更新日志
description: 版本历史和发布说明
tag: info
icon: clock
order: 10
---

# 更新日志

## v1.0.0

BeisentDocs 首个正式版本。

### 新增功能

- 纯 Python Markdown 转 HTML 解析器（零外部依赖）
- 通过 Highlight.js 支持代码语法高亮
- 通过 KaTeX 支持数学公式渲染
- GFM 表格（支持左/中/右对齐）
- 任务列表（复选框）
- 提示块（NOTE、TIP、WARNING、IMPORTANT、CAUTION）
- 脚注支持
- 自动侧边栏导航生成
- 页内目录（TOC）生成
- 面包屑导航
- 文档卡片网格首页
- YAML frontmatter 元数据
- 响应式移动端适配
- 内置 HTTP 开发服务器
- 文件监听自动重建（watch 模式）

### 技术细节

```
语言：       Python 3.10+
外部依赖：   无（仅使用标准库）
客户端依赖： Highlight.js, KaTeX（CDN 加载），内置 SVG 图标
输出格式：   静态 HTML/CSS/JS
```
