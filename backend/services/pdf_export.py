"""PDF rendering for the report templates.

WeasyPrint depends on native GTK libraries (Pango, cairo, GDK-PixBuf). When
those are absent the import raises OSError rather than ImportError, so both are
caught here — otherwise a missing system library surfaces as an opaque 500.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger('ats_resume_scorer')

_IMPORT_ERROR: Optional[str] = None

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as exc:  # noqa: BLE001 — native lib failures are OSError
    HTML = None  # type: ignore[assignment]
    WEASYPRINT_AVAILABLE = False
    _IMPORT_ERROR = str(exc)
    logger.warning(f'WeasyPrint unavailable — PDF export disabled: {exc}')


class PdfUnavailableError(RuntimeError):
    """Raised when PDF rendering can't run in this environment."""


def _unavailable_message() -> str:
    return (
        'PDF export is unavailable because WeasyPrint could not load its native '
        'libraries. On Windows install the GTK3 runtime; on Debian/Ubuntu install '
        'libcairo2, libpango-1.0-0, libpangoft2-1.0-0 and libffi-dev. '
        f'Underlying error: {_IMPORT_ERROR}'
    )


def generate_combined_pdf(html_docs: Dict[str, str]) -> bytes:
    """Render each HTML report and concatenate them into a single PDF."""
    if not WEASYPRINT_AVAILABLE:
        raise PdfUnavailableError(_unavailable_message())

    if not html_docs:
        raise ValueError('No report sections to render.')

    documents = [HTML(string=html).render() for html in html_docs.values()]

    combined = documents[0]
    for document in documents[1:]:
        combined.pages.extend(document.pages)

    return combined.write_pdf()
