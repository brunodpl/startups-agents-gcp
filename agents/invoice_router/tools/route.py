def suggest_delivery_target(
    channel: str,
    is_invoice_related: bool,
    filename: str = "",
) -> dict:
    """
    Suggests a draft delivery target based on channel and document type.

    Rules are intentionally simple and hardcoded for the draft.
    Will be replaced by per-tenant config from Supabase delivery_targets
    in the next iteration.

    Args:
        channel:            Normalised channel ('whatsapp' or 'email').
        is_invoice_related: Result from classify_document_intent.
        filename:           Optional filename for extension-based rules.

    Returns:
        A dict with target, path_hint and reason.
    """
    if not is_invoice_related:
        return {
            "status": "success",
            "target": "review",
            "path_hint": "manual-review/",
            "reason": "not_invoice_related",
        }

    if channel == "whatsapp":
        return {
            "status": "success",
            "target": "drive",
            "path_hint": "drive/inbox/whatsapp/",
            "reason": "default_whatsapp_rule",
        }

    if channel == "email" and (filename or "").lower().endswith(".pdf"):
        return {
            "status": "success",
            "target": "api",
            "path_hint": "api/invoices/import",
            "reason": "email_pdf_rule",
        }

    return {
        "status": "success",
        "target": "local",
        "path_hint": "local/inbox/",
        "reason": "fallback_rule",
    }
