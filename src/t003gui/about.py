"""Help-menu content: the About box and the links the Help menu opens. Qt-free text is built by `about_html`."""
from __future__ import annotations

from html import escape

from . import __version__

REPO_URL = "https://github.com/MiNombreEsPablo/t003-label-gui"
RELEASES_URL = f"{REPO_URL}/releases"
ISSUES_URL = f"{REPO_URL}/issues"


def about_html(printer: str, font_count: int, version: str = __version__, link_color: str | None = None) -> str:
    link = f' style="color:{link_color}"' if link_color else ""
    return (
        f"<h3>T003 Label Studio {escape(version)}</h3>"
        "<p>Design and print labels on the ORGBRO T003 thermal label printer over USB.</p>"
        f"<p>Printer: <b>{escape(printer)}</b></p>"
        f"<p>Includes {font_count} bundled open-source font families (SIL Open Font License; licences are kept "
        "with the fonts).</p>"
        f'<p>MIT licence · <a href="{REPO_URL}"{link}>GitHub repository</a></p>'
    )
