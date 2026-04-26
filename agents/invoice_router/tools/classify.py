INVOICE_KEYWORDS = [
    "factura", "invoice", "ticket", "albaran", "albarán",
    "proveedor", "iva", "pdf", "adjunto", "adjunta",
    "recibo", "importe", "total", "fra",
]


def classify_document_intent(text: str, filename: str = "") -> dict:
    """
    Classifies whether the content is likely related to an invoice workflow.

    Uses simple keyword matching. Designed to be replaced by a full
    ML/LLM-based classifier in the next iteration.

    Args:
        text:     Message body text.
        filename: Optional name of the attached file.

    Returns:
        A dict with document_type, is_invoice_related, confidence and reason.
    """
    haystack = f"{text} {filename}".lower()

    if not haystack.strip():
        return {
            "status": "success",
            "document_type": "unknown",
            "is_invoice_related": False,
            "confidence": 0.20,
            "reason": "empty_content",
        }

    matched = [kw for kw in INVOICE_KEYWORDS if kw in haystack]

    if matched:
        return {
            "status": "success",
            "document_type": "invoice_related",
            "is_invoice_related": True,
            "confidence": 0.85,
            "reason": f"matched_keywords:{','.join(matched[:5])}",
        }

    return {
        "status": "success",
        "document_type": "other",
        "is_invoice_related": False,
        "confidence": 0.40,
        "reason": "no_invoice_keywords",
    }
