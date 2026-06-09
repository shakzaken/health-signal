"""
Language detection utilities shared across the ai-agent.
"""


def is_english(text: str) -> bool:
    """Return True if the text is predominantly ASCII alphabetic characters.

    Uses a simple heuristic: if more than 80% of alphabetic characters are
    ASCII (i.e. Latin-script), the text is considered English.  This reliably
    separates Hebrew (Clalit PDFs) from English journal / supplement entries
    without requiring an external library.
    """
    ascii_alpha = sum(1 for c in text if ord(c) < 128 and c.isalpha())
    total_alpha = sum(1 for c in text if c.isalpha())
    return total_alpha == 0 or (ascii_alpha / total_alpha) > 0.8
