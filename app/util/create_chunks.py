from typing import List

from pydantic.v1 import BaseModel
from typing_extensions import Dict


class ChunkInfo(BaseModel):
    referenced_pages: List[int]
    quiz_count: int
    gpt_content: Dict = {}


def create_page_chunks(
    page_numbers: List[int],
    total_quiz_count: int,
    max_chunk_count: int,
) -> List[ChunkInfo]:

    # 청크 별 퀴즈 개수 분배
    chunks: List[ChunkInfo] = []
    for i in range(total_quiz_count):
        if i // max_chunk_count == 0:
            chunks.append(ChunkInfo(quiz_count=1, referenced_pages=[]))
        else:
            chunks[i % max_chunk_count].quiz_count += 1

    # 각 청크에 페이지 할당
    real_chunk_count = len(chunks)
    page_count = len(page_numbers)
    basic_page_count_per_chunk = page_count // real_chunk_count
    extra_pages = page_count % real_chunk_count
    cur = 0
    for chunk in chunks:
        pages_for_this_chunk = basic_page_count_per_chunk
        if extra_pages > 0:
            pages_for_this_chunk += 1
            extra_pages -= 1

        # 앞뒤로 한 페이지씩 여유를 둔다.
        if pages_for_this_chunk < 3:
            if cur == 0:
                chunk.referenced_pages = page_numbers[0:3]
            elif cur == len(page_numbers) - 1:
                chunk.referenced_pages = page_numbers[-3:]
            else:
                chunk.referenced_pages = page_numbers[cur - 1 : cur + 2]
        else:
            chunk.referenced_pages = page_numbers[cur : cur + pages_for_this_chunk]
        cur += pages_for_this_chunk

    return chunks
