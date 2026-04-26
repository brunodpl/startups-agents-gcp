def normalize_incoming_message(
    channel: str,
    sender: str,
    text: str,
    filename: str = "",
) -> dict:
    """
    Normalizes an incoming WhatsApp or email message into a shared structure.

    Args:
        channel:  Origin channel. Must be 'whatsapp' or 'email'.
        sender:   Phone number or email address of the sender.
        text:     Body text of the message.
        filename: Optional name of the attached file.

    Returns:
        A dict with status and normalized fields, or an error message.
    """
    channel = (channel or "").strip().lower()
    sender = (sender or "").strip().lower()
    text = (text or "").strip()
    filename = (filename or "").strip()

    if channel not in {"whatsapp", "email"}:
        return {
            "status": "error",
            "error_message": f"Unknown channel '{channel}'. Must be 'whatsapp' or 'email'.",
        }

    return {
        "status": "success",
        "channel": channel,
        "sender": sender,
        "text": text,
        "filename": filename,
    }
