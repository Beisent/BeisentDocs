#!/usr/bin/env python3
"""BeisentDocs - Markdown to HTML documentation site generator."""

import os
import re
import json
import shutil
import hashlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Inline SVG icon data (replaces Lucide CDN dependency)
# ---------------------------------------------------------------------------

ICONS = {
    "book-open": (
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    "code": (
        '<polyline points="16 18 22 12 16 6"/>'
        '<polyline points="8 6 2 12 8 18"/>'
    ),
    "graduation-cap": (
        '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/>'
        '<path d="M6 12v5c0 2 4 3 6 3s6-1 6-3v-5"/>'
    ),
    "bookmark": (
        '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>'
    ),
    "lightbulb": (
        '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
        '<path d="M9 18h6"/>'
        '<path d="M10 22h4"/>'
    ),
    "rocket": (
        '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>'
        '<path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>'
        '<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>'
        '<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>'
    ),
    "download": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" y1="15" x2="12" y2="3"/>'
    ),
    "settings": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "file-text": (
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="16" y1="13" x2="8" y2="13"/>'
        '<line x1="16" y1="17" x2="8" y2="17"/>'
        '<line x1="10" y1="9" x2="8" y2="9"/>'
    ),
    "folder": (
        '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2z"/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/>'
    ),
}

# ---------------------------------------------------------------------------
# Markdown parser (zero external dependencies)
# ---------------------------------------------------------------------------

class MarkdownParser:
    """Pure-Python Markdown-to-HTML converter with extensions."""

    def __init__(self):
        self.footnotes: dict[str, str] = {}
        self.headings: list[dict] = []
        self.heading_slugs: dict[str, int] = {}  # track slug usage for deduplication

    # ---- public API -------------------------------------------------------

    def parse(self, text: str) -> str:
        self.footnotes.clear()
        self.headings.clear()
        self.heading_slugs.clear()
        text = text.replace("\r\n", "\n")
        text = self._extract_footnotes(text)
        html = self._parse_blocks(text)
        html = self._insert_footnotes(html)
        return html

    # ---- footnotes --------------------------------------------------------

    def _extract_footnotes(self, text: str) -> str:
        def _repl(m):
            self.footnotes[m.group(1)] = m.group(2).strip()
            return ""
        return re.sub(r'^\[\^(\w+)\]:\s*(.+)$', _repl, text, flags=re.M)

    def _insert_footnotes(self, html: str) -> str:
        if not self.footnotes:
            return html
        def _repl(m):
            key = m.group(1)
            if key in self.footnotes:
                return (f'<sup class="footnote-ref" id="fnref-{key}">'
                        f'<a href="#fn-{key}">{key}</a></sup>')
            return m.group(0)
        html = re.sub(r'\[\^(\w+)\]', _repl, html)
        items = "".join(
            f'<li id="fn-{k}"><p>{self._inline(v)}'
            f' <a href="#fnref-{k}" class="footnote-back">&#8617;</a></p></li>'
            for k, v in self.footnotes.items()
        )
        html += f'\n<section class="footnotes"><hr><ol>{items}</ol></section>'
        return html

    # ---- block-level parsing ---------------------------------------------

    def _parse_blocks(self, text: str) -> str:
        lines = text.split("\n")
        result: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # fenced code block
            m = re.match(r'^(`{3,}|~{3,})\s*(\S*)', line)
            if m:
                fence, lang = m.group(1)[0], m.group(2)
                code_lines: list[str] = []
                i += 1
                while i < len(lines) and not re.match(rf'^{re.escape(fence)}{{3,}}\s*$', lines[i]):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # skip closing fence
                code = self._escape_html("\n".join(code_lines))
                lang_attr = f' class="language-{lang}"' if lang else ""
                result.append(f'<pre><code{lang_attr}>{code}</code></pre>')
                continue

            # math block ($$...$$)
            if line.strip().startswith("$$"):
                math_lines = [line.strip().removeprefix("$$")]
                i += 1
                while i < len(lines) and "$$" not in lines[i]:
                    math_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    math_lines.append(lines[i].strip().removesuffix("$$"))
                    i += 1
                expr = "\n".join(math_lines).strip()
                result.append(f'<div class="math-block">$${expr}$$</div>')
                continue

            # heading
            m = re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                level = len(m.group(1))
                text_h = m.group(2).strip()
                base_slug = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text_h.lower()).strip('-')

                # deduplicate slug
                if base_slug in self.heading_slugs:
                    self.heading_slugs[base_slug] += 1
                    slug = f"{base_slug}-{self.heading_slugs[base_slug]}"
                else:
                    self.heading_slugs[base_slug] = 0
                    slug = base_slug

                self.headings.append({"level": level, "text": text_h, "slug": slug})
                result.append(
                    f'<h{level} id="{slug}">'
                    f'<a class="anchor" href="#{slug}">#</a> '
                    f'{self._inline(text_h)}</h{level}>'
                )
                i += 1
                continue

            # horizontal rule
            if re.match(r'^(\*{3,}|-{3,}|_{3,})\s*$', line):
                result.append("<hr>")
                i += 1
                continue

            # blockquote
            if line.startswith(">"):
                bq_lines: list[str] = []
                while i < len(lines) and (lines[i].startswith(">") or (lines[i].strip() and bq_lines)):
                    bq_lines.append(re.sub(r'^>\s?', '', lines[i]))
                    i += 1
                inner = self._parse_blocks("\n".join(bq_lines))

                # check for admonition-style: [!NOTE], [!TIP], etc.
                am = re.match(r'<p>\[!(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\]', inner)
                if am:
                    kind = am.group(1).lower()
                    inner = re.sub(r'<p>\[!\w+\]\s*', '<p>', inner, count=1)
                    result.append(f'<blockquote class="admonition admonition-{kind}">'
                                  f'<p class="admonition-title">{kind.upper()}</p>{inner}</blockquote>')
                else:
                    result.append(f"<blockquote>{inner}</blockquote>")
                continue

            # unordered list
            if re.match(r'^[\s]*[-*+]\s', line):
                items, i = self._collect_list_items(lines, i, ul=True)
                result.append(self._build_list(items, ordered=False))
                continue

            # ordered list
            if re.match(r'^[\s]*\d+\.\s', line):
                items, i = self._collect_list_items(lines, i, ul=False)
                result.append(self._build_list(items, ordered=True))
                continue

            # table
            if i + 1 < len(lines) and re.match(r'^\|.*\|$', line) and re.match(r'^\|[\s:|-]+\|$', lines[i+1]):
                table_lines: list[str] = []
                while i < len(lines) and lines[i].startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                result.append(self._parse_table(table_lines))
                continue

            # blank line
            if not line.strip():
                i += 1
                continue

            # paragraph
            para_lines: list[str] = []
            while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6}\s|```|~~~|>|\*{3,}|-{3,}|_{3,}|\|)', lines[i]):
                para_lines.append(lines[i])
                i += 1
            result.append(f"<p>{self._inline(' '.join(para_lines))}</p>")

        return "\n".join(result)

    # ---- list helpers -----------------------------------------------------

    def _collect_list_items(self, lines, i, ul):
        pat = r'^(\s*)([-*+])\s' if ul else r'^(\s*)(\d+)\.\s'
        items: list[dict] = []
        while i < len(lines):
            m = re.match(pat, lines[i])
            if m:
                indent = len(m.group(1))
                content = re.sub(pat, '', lines[i])
                items.append({"indent": indent, "lines": [content]})
                i += 1
            elif lines[i].strip() and items:
                items[-1]["lines"].append(lines[i].strip())
                i += 1
            else:
                break
        return items, i

    def _build_list(self, items, ordered):
        if not items:
            return ""

        def build_nested(items, start_idx=0, parent_indent=0):
            tag = "ol" if ordered else "ul"
            html = f"<{tag}>"
            i = start_idx
            while i < len(items):
                item = items[i]
                indent = item["indent"]

                # if this item is less indented than parent, we're done with this level
                if indent < parent_indent:
                    break

                # if this item is more indented, skip it (will be handled by recursion)
                if indent > parent_indent:
                    i += 1
                    continue

                # process this item
                content = " ".join(item["lines"])
                # check for task list
                if content.startswith("[ ] "):
                    content = f'<input type="checkbox" disabled> {self._inline(content[4:])}'
                elif content.startswith("[x] ") or content.startswith("[X] "):
                    content = f'<input type="checkbox" checked disabled> {self._inline(content[4:])}'
                else:
                    content = self._inline(content)

                html += f"<li>{content}"

                # check if next item is nested
                if i + 1 < len(items) and items[i + 1]["indent"] > indent:
                    nested_html, next_i = build_nested(items, i + 1, indent + 2)
                    html += nested_html
                    i = next_i
                else:
                    i += 1

                html += "</li>"

            html += f"</{tag}>"
            return html, i

        result, _ = build_nested(items)
        return result

    # ---- table ------------------------------------------------------------

    def _parse_table(self, table_lines):
        headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
        aligns_raw = [c.strip() for c in table_lines[1].strip("|").split("|")]
        aligns = []
        for a in aligns_raw:
            if a.startswith(":") and a.endswith(":"):
                aligns.append("center")
            elif a.endswith(":"):
                aligns.append("right")
            else:
                aligns.append("left")

        def _style(idx):
            if idx < len(aligns):
                return f' style="text-align:{aligns[idx]}"'
            return ""

        html = '<div class="table-wrapper"><table><thead><tr>'
        for idx, h in enumerate(headers):
            html += f"<th{_style(idx)}>{self._inline(h)}</th>"
        html += "</tr></thead><tbody>"
        for row_line in table_lines[2:]:
            cols = [c.strip() for c in row_line.strip("|").split("|")]
            html += "<tr>"
            for idx, c in enumerate(cols):
                html += f"<td{_style(idx)}>{self._inline(c)}</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        return html

    # ---- inline parsing ---------------------------------------------------

    def _inline(self, text: str) -> str:
        # protect inline code first by replacing with placeholders
        code_blocks = []
        def save_code(m):
            code_blocks.append(m.group(1))
            return f"\x00CODE{len(code_blocks)-1}\x00"
        text = re.sub(r'`([^`]+)`', save_code, text)

        # images
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', text)
        # links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # bold + italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        # italic (avoid matching underscores in words)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)
        # strikethrough
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        # mark / highlight
        text = re.sub(r'==(.+?)==', r'<mark>\1</mark>', text)
        # inline math
        text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', r'<span class="math-inline">\(\1\)</span>', text)
        # line break
        text = re.sub(r'  $', '<br>', text)

        # restore code blocks
        def restore_code(m):
            idx = int(m.group(1))
            return f'<code>{code_blocks[idx]}</code>'
        text = re.sub(r'\x00CODE(\d+)\x00', restore_code, text)

        return text

    @staticmethod
    def _escape_html(text: str) -> str:
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Site builder
# ---------------------------------------------------------------------------

class SiteBuilder:
    """Builds the documentation site from docs/ into dist/."""

    def __init__(self, docs_dir="docs", dist_dir="dist", static_dir="static",
                 templates_dir="templates"):
        self.base = Path(__file__).parent
        self.docs_dir = self.base / docs_dir
        self.dist_dir = self.base / dist_dir
        self.static_dir = self.base / static_dir
        self.templates_dir = self.base / templates_dir
        self.parser = MarkdownParser()
        self.config = self._load_config()

    # ---- public entry point -----------------------------------------------

    def _load_config(self) -> dict:
        config_path = self.base / "config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            config = {}
        # set defaults
        config.setdefault("site_name", "BeisentDocs")
        config.setdefault("site_description", "Documentation Site")
        config.setdefault("footer_text", "Documentation")
        config.setdefault("base_url", "")
        config.setdefault("nav", [])
        return config

    def build(self):
        print("==> Building BeisentDocs ...")
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.dist_dir.mkdir(parents=True)

        # copy static assets
        if self.static_dir.exists():
            shutil.copytree(self.static_dir, self.dist_dir / "static")

        # build section tree
        tree = self._build_section_tree()
        all_docs = self._flatten_docs(tree)
        all_sections = self._flatten_sections(tree)

        if not all_docs and not all_sections:
            print("    No .md files found in docs/. Add .md files to docs/ directory.")
            return

        # render root index page
        index_tpl = self._read_template("index.html")
        root_html = "index.html"
        page = index_tpl.replace("{{cards}}", self._build_cards(tree, root_html))
        page = self._apply_common_vars(page, "")
        (self.dist_dir / "index.html").write_text(page, encoding="utf-8")

        # render section pages
        section_tpl = self._read_template("section.html")
        for section in all_sections:
            self._build_section_page(section, section_tpl, tree)

        # render doc pages
        doc_tpl = self._read_template("doc.html")
        for doc in all_docs:
            self._build_doc_page(doc, doc_tpl, tree)

        # generate search index
        self._build_search_index(all_docs)

        # generate sitemap
        self._build_sitemap(all_docs, all_sections)

        # generate 404 page
        self._build_404_page()

        print(f"==> Done! {len(all_docs)} docs, {len(all_sections)} sections built into dist/")

    # ---- section tree construction ----------------------------------------

    def _build_section_tree(self) -> dict:
        return self._build_section(self.docs_dir, 0, "")

    def _build_section(self, dir_path: Path, depth: int, slug: str) -> dict:
        section = {
            "title": slug.split("/")[-1].replace("-", " ").title() if slug else "Home",
            "description": "",
            "icon": "folder",
            "order": 99,
            "slug": slug,
            "html_path": f"{slug}/index.html" if slug else "index.html",
            "content": "",
            "docs": [],
            "children": [],
            "depth": depth,
        }

        # read _index.md for section metadata
        index_md = dir_path / "_index.md"
        if index_md.exists():
            text = index_md.read_text(encoding="utf-8")
            meta, body = self._extract_meta(text)
            if "title" in meta:
                section["title"] = meta["title"]
            if "description" in meta:
                section["description"] = meta["description"]
            if "icon" in meta:
                section["icon"] = meta["icon"]
            if "order" in meta:
                try:
                    section["order"] = int(meta["order"])
                except ValueError:
                    pass
            section["content"] = self.parser.parse(body) if body.strip() else ""

        # collect .md files (skip _index.md)
        for md_file in sorted(dir_path.iterdir()):
            if md_file.is_file() and md_file.suffix == ".md" and md_file.name != "_index.md":
                section["docs"].append(self._make_doc(md_file, slug, depth))

        section["docs"].sort(key=lambda d: (int(d["meta"].get("order", "99")), d["meta"]["title"]))

        # recurse into subdirectories
        for subdir in sorted(dir_path.iterdir()):
            if subdir.is_dir() and not subdir.name.startswith((".", "_")):
                child_slug = f"{slug}/{subdir.name}" if slug else subdir.name
                section["children"].append(
                    self._build_section(subdir, depth + 1, child_slug)
                )

        section["children"].sort(key=lambda s: (s["order"], s["title"]))
        return section

    def _make_doc(self, md_path: Path, section_slug: str, depth: int) -> dict:
        text = md_path.read_text(encoding="utf-8")
        meta, body = self._extract_meta(text)
        stem = md_path.stem
        slug = f"{section_slug}/{stem}" if section_slug else stem
        return {
            "path": md_path,
            "slug": slug,
            "html_path": f"{slug}.html",
            "meta": meta,
            "body": body,
            "section_slug": section_slug,
            "depth": depth,
        }

    # ---- tree flattening --------------------------------------------------

    def _flatten_docs(self, section: dict) -> list[dict]:
        result = list(section["docs"])
        for child in section["children"]:
            result.extend(self._flatten_docs(child))
        return result

    def _flatten_sections(self, section: dict) -> list[dict]:
        result = []
        for child in section["children"]:
            result.append(child)
            result.extend(self._flatten_sections(child))
        return result

    # ---- path utilities ---------------------------------------------------

    @staticmethod
    def _compute_base_path(html_path: str) -> str:
        depth = html_path.count("/")
        return "../" * depth

    @staticmethod
    def _make_link(from_html_path: str, to_html_path: str) -> str:
        from_dir = os.path.dirname(from_html_path) or "."
        return os.path.relpath(to_html_path, from_dir)

    # ---- frontmatter ------------------------------------------------------

    @staticmethod
    def _extract_meta(text: str) -> tuple[dict, str]:
        meta = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
                body = parts[2]
        if "title" not in meta:
            m = re.match(r'^#\s+(.+)', body.strip())
            if m:
                meta["title"] = m.group(1)
            else:
                meta["title"] = "Untitled"
        if "description" not in meta:
            for line in body.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    meta["description"] = line[:160]
                    break
            else:
                meta["description"] = ""
        return meta, body

    # ---- icon helper ------------------------------------------------------

    def _pick_icon(self, doc: dict) -> str:
        if "icon" in doc["meta"]:
            return doc["meta"]["icon"]
        icons = {"guide": "book-open", "api": "code", "tutorial": "graduation-cap",
                 "reference": "bookmark", "example": "lightbulb", "start": "rocket",
                 "install": "download", "config": "settings"}
        for k, v in icons.items():
            if k in doc["slug"].lower() or k in doc["meta"].get("title", "").lower():
                return v
        return "file-text"

    def _get_icon_svg(self, icon_name: str, size: int = 20) -> str:
        inner = ICONS.get(icon_name, ICONS["file-text"])
        return (
            f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{inner}</svg>'
        )

    # ---- card generation --------------------------------------------------

    def _build_cards(self, section: dict, from_html_path: str) -> str:
        cards = []
        # section cards first
        for child in section["children"]:
            link = self._make_link(from_html_path, child["html_path"])
            icon = child["icon"]
            cards.append(
                f'<a href="{link}" class="card card-section">'
                f'<div class="card-icon">{self._get_icon_svg(icon)}</div>'
                f'<div class="card-body">'
                f'<span class="card-tag">section</span>'
                f'<h3>{child["title"]}</h3>'
                f'<p>{child["description"]}</p>'
                f'</div></a>'
            )
        # document cards
        for doc in section["docs"]:
            link = self._make_link(from_html_path, doc["html_path"])
            icon = self._pick_icon(doc)
            tag = doc["meta"].get("tag", "doc")
            cards.append(
                f'<a href="{link}" class="card">'
                f'<div class="card-icon">{self._get_icon_svg(icon)}</div>'
                f'<div class="card-body">'
                f'<span class="card-tag">{tag}</span>'
                f'<h3>{doc["meta"]["title"]}</h3>'
                f'<p>{doc["meta"].get("description", "")}</p>'
                f'</div></a>'
            )
        return "\n".join(cards)

    # ---- top navbar links (external, from config.json) ---------------------

    def _build_nav(self) -> str:
        nav_items = self.config.get("nav", [])
        links = []
        for item in nav_items:
            url = item.get("url", "#")
            label = item.get("label", "")
            links.append(f'<a href="{url}">{label}</a>')
        return "\n".join(links)

    # ---- sidebar navigation (recursive tree) ------------------------------

    def _build_sidebar_nav(self, current_html_path: str, tree: dict) -> str:
        html = '<div class="nav-group">'
        for doc in tree["docs"]:
            active = " active" if doc["html_path"] == current_html_path else ""
            link = self._make_link(current_html_path, doc["html_path"])
            html += f'<a href="{link}" class="nav-link{active}">{doc["meta"]["title"]}</a>'
        html += '</div>'
        for child in tree["children"]:
            html += self._build_sidebar_section(child, current_html_path)
        return html

    def _build_sidebar_section(self, section: dict, current_html_path: str) -> str:
        is_ancestor = current_html_path.startswith(section["slug"] + "/")
        is_current = current_html_path == section["html_path"]
        open_attr = " open" if is_ancestor or is_current else ""

        section_link = self._make_link(current_html_path, section["html_path"])
        active = " active" if is_current else ""

        html = f'<details class="nav-section"{open_attr}>'
        html += (f'<summary class="nav-section-title">'
                 f'<a href="{section_link}" class="nav-section-link{active}">{section["title"]}</a>'
                 f'</summary>')
        html += '<div class="nav-section-content">'

        for doc in section["docs"]:
            active = " active" if doc["html_path"] == current_html_path else ""
            link = self._make_link(current_html_path, doc["html_path"])
            html += f'<a href="{link}" class="nav-link{active}">{doc["meta"]["title"]}</a>'

        for child in section["children"]:
            html += self._build_sidebar_section(child, current_html_path)

        html += '</div></details>'
        return html

    # ---- breadcrumbs ------------------------------------------------------

    def _get_crumb_chain(self, target_slug: str, tree: dict) -> list[dict]:
        if not target_slug:
            return []
        parts = target_slug.split("/")
        chain = []
        current = tree
        slug_so_far = ""
        for part in parts:
            slug_so_far = f"{slug_so_far}/{part}" if slug_so_far else part
            for child in current["children"]:
                if child["slug"] == slug_so_far:
                    chain.append({"title": child["title"], "html_path": child["html_path"]})
                    current = child
                    break
        return chain

    def _build_breadcrumbs(self, crumb_chain: list[dict], current_html_path: str) -> str:
        if not crumb_chain:
            return ""
        home_link = self._make_link(current_html_path, "index.html")
        html = '<nav class="breadcrumbs">'
        html += f'<a href="{home_link}" class="breadcrumb-link">Home</a>'
        for i, crumb in enumerate(crumb_chain):
            html += '<span class="breadcrumb-sep">/</span>'
            if i == len(crumb_chain) - 1:
                html += f'<span class="breadcrumb-current">{crumb["title"]}</span>'
            else:
                link = self._make_link(current_html_path, crumb["html_path"])
                html += f'<a href="{link}" class="breadcrumb-link">{crumb["title"]}</a>'
        html += '</nav>'
        return html

    # ---- section page rendering -------------------------------------------

    def _build_section_page(self, section: dict, template: str, tree: dict):
        hp = section["html_path"]
        base_path = self._compute_base_path(hp)
        cards = self._build_cards(section, hp)
        sidebar = self._build_sidebar_nav(hp, tree)
        crumb_chain = self._get_crumb_chain(section["slug"], tree)
        breadcrumbs = self._build_breadcrumbs(crumb_chain, hp)

        section_content = ""
        if section["content"]:
            section_content = f'<div class="prose">{section["content"]}</div>'

        page = template.replace("{{title}}", section["title"])
        page = page.replace("{{description}}", section["description"])
        page = page.replace("{{section_content}}", section_content)
        page = page.replace("{{cards}}", cards)
        page = page.replace("{{sidebar_nav}}", sidebar)
        page = page.replace("{{breadcrumbs}}", breadcrumbs)
        page = self._apply_common_vars(page, base_path)

        out = self.dist_dir / hp
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")

    # ---- doc page rendering -----------------------------------------------

    def _build_doc_page(self, doc: dict, template: str, tree: dict):
        html_body = self.parser.parse(doc["body"])
        headings = list(self.parser.headings)
        toc = self._build_toc(headings)

        hp = doc["html_path"]
        base_path = self._compute_base_path(hp)
        sidebar = self._build_sidebar_nav(hp, tree)

        # breadcrumbs: section chain + doc title
        crumb_chain = self._get_crumb_chain(doc["section_slug"], tree)
        crumb_chain.append({"title": doc["meta"]["title"], "html_path": hp})
        breadcrumbs = self._build_breadcrumbs(crumb_chain, hp)

        # canonical URL
        base_url = self.config.get("base_url", "").rstrip("/")
        canonical_url = f"{base_url}/{hp}" if base_url else ""

        # prev/next navigation
        all_docs = self._flatten_docs(tree)
        doc_nav = self._build_doc_nav(doc, all_docs, hp)

        page = template.replace("{{title}}", doc["meta"]["title"])
        page = page.replace("{{description}}", doc["meta"].get("description", ""))
        page = page.replace("{{canonical_url}}", canonical_url)
        page = page.replace("{{content}}", html_body)
        page = page.replace("{{toc}}", toc)
        page = page.replace("{{sidebar_nav}}", sidebar)
        page = page.replace("{{breadcrumbs}}", breadcrumbs)
        page = page.replace("{{doc_nav}}", doc_nav)
        page = self._apply_common_vars(page, base_path)

        out = self.dist_dir / hp
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")

    @staticmethod
    def _build_toc(headings) -> str:
        if not headings:
            return ""
        html = '<nav class="toc"><h4>On this page</h4><ul>'
        for h in headings:
            indent = (h["level"] - 1) * 12
            html += (f'<li style="padding-left:{indent}px">'
                     f'<a href="#{h["slug"]}" class="toc-link" '
                     f'data-level="{h["level"]}">{h["text"]}</a></li>')
        html += "</ul></nav>"
        return html

    def _build_doc_nav(self, current_doc: dict, all_docs: list[dict], current_html_path: str) -> str:
        """Build prev/next navigation for document pages."""
        try:
            idx = next(i for i, d in enumerate(all_docs) if d["html_path"] == current_doc["html_path"])
        except StopIteration:
            return ""

        html = '<nav class="doc-nav">'
        if idx > 0:
            prev_doc = all_docs[idx - 1]
            prev_link = self._make_link(current_html_path, prev_doc["html_path"])
            html += (f'<a href="{prev_link}" class="doc-nav-link doc-nav-prev">'
                     f'<span class="doc-nav-label">← 上一篇</span>'
                     f'<span class="doc-nav-title">{prev_doc["meta"]["title"]}</span></a>')
        else:
            html += '<div></div>'

        if idx < len(all_docs) - 1:
            next_doc = all_docs[idx + 1]
            next_link = self._make_link(current_html_path, next_doc["html_path"])
            html += (f'<a href="{next_link}" class="doc-nav-link doc-nav-next">'
                     f'<span class="doc-nav-label">下一篇 →</span>'
                     f'<span class="doc-nav-title">{next_doc["meta"]["title"]}</span></a>')

        html += '</nav>'
        return html

    def _read_template(self, name: str) -> str:
        return (self.templates_dir / name).read_text(encoding="utf-8")

    def _build_search_index(self, all_docs: list[dict]):
        """Generate search index JSON for client-side search."""
        index = []
        for doc in all_docs:
            # strip HTML tags from body for plain text content
            plain_text = re.sub(r'<[^>]+>', '', self.parser.parse(doc["body"]))
            # get first 200 chars as excerpt
            excerpt = plain_text[:200].strip()
            if len(plain_text) > 200:
                excerpt += "..."

            index.append({
                "title": doc["meta"]["title"],
                "description": doc["meta"].get("description", ""),
                "url": doc["html_path"],
                "content": plain_text[:1000],  # limit content for index size
                "excerpt": excerpt
            })

        index_path = self.dist_dir / "search-index.json"
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_sitemap(self, all_docs: list[dict], all_sections: list[dict]):
        """Generate sitemap.xml for SEO."""
        from datetime import datetime
        base_url = self.config.get("base_url", "").rstrip("/")
        if not base_url:
            return  # skip sitemap if no base_url configured

        now = datetime.now().strftime("%Y-%m-%d")
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        # add homepage
        xml += f'  <url>\n    <loc>{base_url}/</loc>\n'
        xml += f'    <lastmod>{now}</lastmod>\n    <priority>1.0</priority>\n  </url>\n'

        # add sections
        for section in all_sections:
            url = f"{base_url}/{section['html_path']}"
            xml += f'  <url>\n    <loc>{url}</loc>\n'
            xml += f'    <lastmod>{now}</lastmod>\n    <priority>0.8</priority>\n  </url>\n'

        # add docs
        for doc in all_docs:
            url = f"{base_url}/{doc['html_path']}"
            xml += f'  <url>\n    <loc>{url}</loc>\n'
            xml += f'    <lastmod>{now}</lastmod>\n    <priority>0.9</priority>\n  </url>\n'

        xml += '</urlset>'

        sitemap_path = self.dist_dir / "sitemap.xml"
        sitemap_path.write_text(xml, encoding="utf-8")

    def _build_404_page(self):
        """Generate 404 error page."""
        template = self._read_template("404.html")
        page = self._apply_common_vars(template, "")
        (self.dist_dir / "404.html").write_text(page, encoding="utf-8")

    def _apply_common_vars(self, page: str, base_path: str) -> str:
        """Apply common template variables to a page."""
        from datetime import datetime
        page = page.replace("{{site_name}}", self.config["site_name"])
        page = page.replace("{{site_description}}", self.config["site_description"])
        page = page.replace("{{footer_text}}", self.config["footer_text"])
        page = page.replace("{{current_year}}", str(datetime.now().year))
        page = page.replace("{{nav_links}}", self._build_nav())
        page = page.replace("{{base_path}}", base_path)
        return page


# ---------------------------------------------------------------------------
# Dev server with watch
# ---------------------------------------------------------------------------

def serve(port=8000):
    import http.server
    import socketserver

    os.chdir(Path(__file__).parent / "dist")
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"==> Serving at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n==> Server stopped.")


def watch():
    import time
    builder = SiteBuilder()
    builder.build()

    docs_dir = Path(__file__).parent / "docs"
    templates_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"
    config_file = Path(__file__).parent / "config.json"

    last_hash = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)

    print("==> Watching for changes ... (Ctrl+C to stop)")
    while True:
        time.sleep(1)
        current = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)
        if current != last_hash:
            print("==> Change detected, rebuilding ...")
            builder.build()
            last_hash = current


def _compute_watch_hash(docs_dir: Path, templates_dir: Path, static_dir: Path, config_file: Path) -> str:
    """Compute hash of all watched files."""
    h = hashlib.md5()

    # Hash docs
    for f in sorted(docs_dir.rglob("*.md")):
        h.update(f.read_bytes())
        h.update(str(f.stat().st_mtime).encode())

    # Hash templates
    if templates_dir.exists():
        for f in sorted(templates_dir.rglob("*.html")):
            h.update(f.read_bytes())
            h.update(str(f.stat().st_mtime).encode())

    # Hash static files
    if static_dir.exists():
        for f in sorted(static_dir.rglob("*")):
            if f.is_file():
                h.update(f.read_bytes())
                h.update(str(f.stat().st_mtime).encode())

    # Hash config
    if config_file.exists():
        h.update(config_file.read_bytes())
        h.update(str(config_file.stat().st_mtime).encode())

    return h.hexdigest()


def dev(port=8000):
    """Run development server with auto-rebuild and live reload."""
    import threading
    import time
    import http.server
    import socketserver

    builder = SiteBuilder()

    # Inject live reload script into templates during dev mode
    def inject_livereload(html: str) -> str:
        reload_script = '''
<script>
(function() {
  let lastCheck = Date.now();
  setInterval(() => {
    fetch('/livereload-check?' + lastCheck)
      .then(res => res.text())
      .then(data => {
        if (data === 'reload') {
          console.log('[LiveReload] Reloading...');
          location.reload();
        }
        lastCheck = Date.now();
      })
      .catch(() => {});
  }, 1000);
})();
</script>
</body>'''
        return html.replace('</body>', reload_script)

    # Custom handler with live reload endpoint
    class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
        last_build_time = time.time()

        def do_GET(self):
            if self.path.startswith('/livereload-check'):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                query_time = float(self.path.split('?')[1]) / 1000 if '?' in self.path else 0
                if LiveReloadHandler.last_build_time > query_time:
                    self.wfile.write(b'reload')
                else:
                    self.wfile.write(b'ok')
            else:
                super().do_GET()

    # Initial build with livereload injection
    builder.build()
    for html_file in builder.dist_dir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        html_file.write_text(inject_livereload(content), encoding="utf-8")

    # Start file watcher in background thread
    docs_dir = Path(__file__).parent / "docs"
    templates_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"
    config_file = Path(__file__).parent / "config.json"

    last_hash = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)

    def watch_files():
        nonlocal last_hash
        while True:
            time.sleep(1)
            current = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)
            if current != last_hash:
                print("==> Change detected, rebuilding ...")
                builder.build()
                # Re-inject livereload script
                for html_file in builder.dist_dir.rglob("*.html"):
                    content = html_file.read_text(encoding="utf-8")
                    html_file.write_text(inject_livereload(content), encoding="utf-8")
                LiveReloadHandler.last_build_time = time.time()
                last_hash = current

    watcher_thread = threading.Thread(target=watch_files, daemon=True)
    watcher_thread.start()

    # Start HTTP server
    os.chdir(builder.dist_dir)
    with socketserver.TCPServer(("", port), LiveReloadHandler) as httpd:
        print(f"==> Dev server running at http://localhost:{port}")
        print("==> Watching for changes with live reload enabled...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n==> Server stopped.")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        SiteBuilder().build()
        serve(port)
    elif len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch()
    elif len(sys.argv) > 1 and sys.argv[1] == "dev":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        dev(port)
    else:
        SiteBuilder().build()
