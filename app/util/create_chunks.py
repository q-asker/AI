import math


async def create_chunks(text: str, quiz_count: int, quiz_count_per_chunk: int) -> list:
    try:
        chunks = []
        chunk_count = math.ceil(quiz_count / quiz_count_per_chunk)
        chunk_size = len(text) // chunk_count
        for i in range(chunk_count):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < chunk_count - 1 else len(text)
            chunks.append(text[start:end])

        return chunks
    except Exception as e:
        raise e
