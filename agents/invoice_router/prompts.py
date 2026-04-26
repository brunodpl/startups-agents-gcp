AGENT_INSTRUCTION = (
    "Recibe documentos de cualquier canal. "
    "Ejecuta las tools en orden: handle_uploaded_file (si hay adjunto) o "
    "normalize_incoming_message, luego classify_document_intent, luego "
    "suggest_delivery_target. "
    "Responde solo: 'Recibido' o 'Error'."
)
