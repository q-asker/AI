async def create_chunks(text: str, quiz_count: int):
    try:
        chunks = []
        chunk_count = quiz_count // 5
        chunk_size = len(text) // chunk_count
        for i in range(chunk_count):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < chunk_count - 1 else len(text)
            chunks.append(text[start:end])

        return chunks
    except Exception as e:
        raise e