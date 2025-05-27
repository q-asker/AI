async def create_chunks(text: str, chunk_count: int):
    try:
        chunks = []
        chunk_size = len(text) // chunk_count
        for i in range(chunk_count):
            chunks.append(text[i * chunk_size: (i + 1) * chunk_size])

        return chunks
    except Exception as e:
        raise e