"""Pure-Python Markdown-to-HTML converter with extensions."""

import re


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
                # Escape template placeholders to prevent replacement
                code = code.replace("{{", "&#123;&#123;").replace("}}", "&#125;&#125;")
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
            while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6}\s|```|~~~|>|\*{3,}|-{3,}|_{3,}|\||[\s]*[-*+]\s|[\s]*\d+\.\s)', lines[i]):
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
            code = self._escape_html(code_blocks[idx])
            # Also escape template placeholders to prevent replacement
            code = code.replace("{{", "&#123;&#123;").replace("}}", "&#125;&#125;")
            return f'<code>{code}</code>'
        text = re.sub(r'\x00CODE(\d+)\x00', restore_code, text)

        return text

    @staticmethod
    def _escape_html(text: str) -> str:
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))
