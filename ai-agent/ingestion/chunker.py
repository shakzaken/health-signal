from langchain_text_splitters import RecursiveCharacterTextSplitter


class Chunker:
    """
    Splits document text into overlapping chunks suitable for embedding.
    chunk_size=500 and overlap=50 are tuned for health documents
    which tend to have short, dense sections.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text: str) -> list[str]:
        """Split text into chunks. Returns an empty list if the text is empty."""
        return self._splitter.split_text(text)
