from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks suitable for embedding.
    chunk_size=500 and overlap=50 are tuned for health documents
    which tend to have short, dense sections.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)
