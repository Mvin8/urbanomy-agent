import asyncio
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.generate_docs import ROOT, render_documents


def test_generated_docs_match_live_interfaces_without_rewriting_files():
    for filename, expected in asyncio.run(render_documents()).items():
        path = ROOT / "docs" / filename
        assert path.read_text(encoding="utf-8") == expected, (
            f"{path.relative_to(ROOT)} is stale. Run python scripts/generate_docs.py"
        )


def test_documentation_links_resolve_inside_repository():
    paths = [ROOT / "README.md", ROOT / "RUN.md", ROOT / "tests/README.md", *sorted((ROOT / "docs").glob("*.md"))]
    for path in paths:
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            assert resolved.is_relative_to(ROOT)
            assert resolved.exists(), f"Broken link in {path.relative_to(ROOT)}: {target}"
