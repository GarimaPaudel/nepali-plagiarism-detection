"""
PDF report generation using ReportLab with Nepali font support.
"""
from io import BytesIO

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from src.database.models.submission import PlagiarismResult


def _register_font() -> str:
    from src.config import settings
    font_path = settings.FONT_PATH
    try:
        pdfmetrics.registerFont(TTFont("NotoSansDevanagari", font_path))
        return "NotoSansDevanagari"
    except Exception:
        return "Helvetica"


def build_pdf_report(
    buffer: BytesIO,
    submitted_text: str,
    results: list[PlagiarismResult],
) -> None:
    font_name = _register_font()
    stylesheet = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "body", parent=stylesheet["BodyText"], fontName=font_name, fontSize=11
    )

    all_matches = [tuple(m) for r in results for m in (r.matched_sentences or [])]

    pdf = SimpleDocTemplate(buffer)
    elements = [
        Paragraph("Plagiarism Report", stylesheet["Title"]),
        Spacer(1, 0.2 * inch),
    ]

    # Highlight copied sentences in the submitted text
    highlighted = submitted_text
    for match in all_matches:
        sentence = match[0]
        highlighted = highlighted.replace(sentence, f'<font color="blue">{sentence}</font>')
    elements.append(Paragraph(f"<b>Submitted Text:</b> {highlighted}", body_style))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("Detailed Results", stylesheet["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    for r in results:
        elements.append(Paragraph(f"<b>File:</b> {r.reference_filename}", body_style))
        if r.tfidf_similarity is not None:
            elements.append(Paragraph(f"TF-IDF Similarity: {r.tfidf_similarity:.2%}", body_style))
        if r.xlm_similarity is not None:
            elements.append(Paragraph(f"XLM-RoBERTa Similarity: {r.xlm_similarity:.2%}", body_style))

        matches = r.matched_sentences or []
        if matches:
            elements.append(Paragraph("<b>Exact Matches (Rabin-Karp):</b>", body_style))
            for m in matches:
                sentence, sent_idx, char_idx = m[0], m[1], m[2]
                elements.append(
                    Paragraph(
                        f"&nbsp;&nbsp;• '{sentence}' (sentence {sent_idx}, char {char_idx})",
                        body_style,
                    )
                )
        else:
            elements.append(Paragraph("No exact sentence matches found.", body_style))

        elements.append(Spacer(1, 0.2 * inch))

    pdf.build(elements)
