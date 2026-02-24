"""Site builder: reads docs/ and renders static HTML into dist/."""

import os
import re
import json
import shutil
from pathlib import Path

from builder.icons import ICONS
from builder.parser import MarkdownParser


class SiteBuilder:
    """Builds the documentation site from docs/ into dist/."""

    def __init__(self, docs_dir="docs", dist_dir="dist", static_dir="static",
                 templates_dir="templates"):
        from builder import PROJECT_ROOT
        self.base = PROJECT_ROOT
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
