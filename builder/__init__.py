"""BeisentDocs builder package."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

from builder.icons import ICONS
from builder.parser import MarkdownParser
from builder.site import SiteBuilder

__all__ = ["ICONS", "MarkdownParser", "SiteBuilder", "PROJECT_ROOT"]
