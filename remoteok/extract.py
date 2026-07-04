import email
import quopri

def extract_html(path: str) -> str:
    """
    Extract the HTML portion from an MHTML snapshot.
    Returns a raw HTML string.
    """
    with open(path, "rb") as f:
        msg = email.message_from_bytes(f.read())

    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=False)  # raw string (QP-encoded)

            # Ensure payload is bytes
            if isinstance(payload, str):
                payload = payload.encode("latin-1")

            decoded = quopri.decodestring(payload)
            return decoded.decode("utf-8", errors="replace")

    raise ValueError("No text/html part found in MHTML")
