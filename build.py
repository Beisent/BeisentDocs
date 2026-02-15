#!/usr/bin/env python3
"""BeisentDocs - Markdown to HTML documentation site generator."""

import os
import re
import json
import shutil
import hashlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Markdown parser (zero external dependencies)
# ---------------------------------------------------------------------------

class MarkdownParser:
    """Pure-Python Markdown-to-HTML converter with extensions."""

    def __init__(self):
        self.footnotes: dict[str, str] = {}
        self.headings: list[dict] = []

    # ---- public API -------------------------------------------------------

    def parse(self, text: str) -> str:
        self.footnotes.clear()
        self.headings.clear()
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
                slug = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text_h.lower()).strip('-')
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
        tag = "ol" if ordered else "ul"
        html = f"<{tag}>"
        for item in items:
            content = " ".join(item["lines"])
            # check for task list
            if content.startswith("[ ] "):
                content = f'<input type="checkbox" disabled> {self._inline(content[4:])}'
            elif content.startswith("[x] ") or content.startswith("[X] "):
                content = f'<input type="checkbox" checked disabled> {self._inline(content[4:])}'
            else:
                content = self._inline(content)
            html += f"<li>{content}</li>"
        html += f"</{tag}>"
        return html

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
        # inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        # images
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', text)
        # links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # bold + italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        # italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        # strikethrough
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        # mark / highlight
        text = re.sub(r'==(.+?)==', r'<mark>\1</mark>', text)
        # inline math
        text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', r'<span class="math-inline">\(\1\)</span>', text)
        # line break
        text = re.sub(r'  $', '<br>', text)
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
            return json.loads(config_path.read_text(encoding="utf-8"))
        return {}

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
        page = page.replace("{{nav_links}}", self._build_nav())
        page = page.replace("{{base_path}}", "")
        (self.dist_dir / "index.html").write_text(page, encoding="utf-8")

        # render section pages
        section_tpl = self._read_template("section.html")
        for section in all_sections:
            self._build_section_page(section, section_tpl, tree)

        # render doc pages
        doc_tpl = self._read_template("doc.html")
        for doc in all_docs:
            self._build_doc_page(doc, doc_tpl, tree)

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

    # ---- card generation --------------------------------------------------

    def _build_cards(self, section: dict, from_html_path: str) -> str:
        cards = []
        # section cards first
        for child in section["children"]:
            link = self._make_link(from_html_path, child["html_path"])
            icon = child["icon"]
            cards.append(
                f'<a href="{link}" class="card card-section">'
                f'<div class="card-icon"><i data-lucide="{icon}"></i></div>'
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
                f'<div class="card-icon"><i data-lucide="{icon}"></i></div>'
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
        open_attr = " open" if is_ancestor else ""

        html = f'<details class="nav-section"{open_attr}>'
        html += f'<summary class="nav-section-title">{section["title"]}</summary>'
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
        nav = self._build_nav()
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
        page = page.replace("{{nav_links}}", nav)
        page = page.replace("{{sidebar_nav}}", sidebar)
        page = page.replace("{{breadcrumbs}}", breadcrumbs)
        page = page.replace("{{base_path}}", base_path)

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
        nav = self._build_nav()
        sidebar = self._build_sidebar_nav(hp, tree)

        # breadcrumbs: section chain + doc title
        crumb_chain = self._get_crumb_chain(doc["section_slug"], tree)
        crumb_chain.append({"title": doc["meta"]["title"], "html_path": hp})
        breadcrumbs = self._build_breadcrumbs(crumb_chain, hp)

        page = template.replace("{{title}}", doc["meta"]["title"])
        page = page.replace("{{content}}", html_body)
        page = page.replace("{{toc}}", toc)
        page = page.replace("{{sidebar_nav}}", sidebar)
        page = page.replace("{{nav_links}}", nav)
        page = page.replace("{{breadcrumbs}}", breadcrumbs)
        page = page.replace("{{base_path}}", base_path)

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

    def _read_template(self, name: str) -> str:
        return (self.templates_dir / name).read_text(encoding="utf-8")


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
    last_hash = _dir_hash(docs_dir)

    print("==> Watching for changes ... (Ctrl+C to stop)")
    while True:
        time.sleep(1)
        current = _dir_hash(docs_dir)
        if current != last_hash:
            print("==> Change detected, rebuilding ...")
            builder.build()
            last_hash = current


def _dir_hash(path: Path) -> str:
    h = hashlib.md5()
    for f in sorted(path.rglob("*.md")):
        h.update(f.read_bytes())
        h.update(str(f.stat().st_mtime).encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        SiteBuilder().build()
        serve(port)
    elif len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch()
    else:
        SiteBuilder().build()
