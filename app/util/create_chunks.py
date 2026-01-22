import math
from typing import List

from pydantic.v1 import BaseModel


class ChunkInfo(BaseModel):
    referenced_pages: List[int]
    quiz_count: int


def create_page_chunks(
    page_count: int,
    total_quiz_count: int,
    max_chunk_count: int,
) -> List[ChunkInfo]:
    if total_quiz_count < page_count:
        chunks = handle_quiz_smaller_than_total_page(total_quiz_count, page_count)
    elif total_quiz_count > page_count:
        chunks = handle_quiz_larger_than_total_page(total_quiz_count, page_count)
    else:
        chunks = handle_quiz_same_as_total_page(total_quiz_count, page_count)

    return compress_chunks(max_chunk_count, chunks)


def compress_chunks(max_chunk_count: int, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
    if len(chunks) <= max_chunk_count:
        return chunks

    base_size = len(chunks) // max_chunk_count
    remainder = len(chunks) % max_chunk_count

    compressed_chunks = []
    idx = 0
    for i in range(max_chunk_count):

        group_size = base_size + 1 if i < remainder else base_size

        merged_chunk = ChunkInfo(referenced_pages=[], quiz_count=0)
        index_set = set([])
        for _ in range(group_size):
            chunk = chunks[idx]
            for referenced_page in chunk.referenced_pages:
                index_set.add(referenced_page)
            idx += 1
            merged_chunk.quiz_count += chunk.quiz_count

        merged_chunk.referenced_pages = list(sorted(index_set))
        compressed_chunks.append(merged_chunk)

    return compressed_chunks


def handle_quiz_smaller_than_total_page(
    total_quiz_count: int, page_count: int
) -> List[ChunkInfo]:
    chunks = []
    page_per_quiz = page_count / total_quiz_count

    for quiz_sequence in range(total_quiz_count):
        start = math.floor(quiz_sequence * page_per_quiz) + 1
        end = math.floor((quiz_sequence + 1) * page_per_quiz)

        referenced_pages = list(range(start, end + 1))

        chunks.append(ChunkInfo(referenced_pages=referenced_pages, quiz_count=1))

    return chunks


def handle_quiz_larger_than_total_page(
    total_quiz_count: int, page_count: int
) -> List[ChunkInfo]:

    chunks = []
    page_per_quiz = page_count / total_quiz_count

    quiz_counts = [0] * (page_count + 1)

    for k in range(total_quiz_count):
        page_idx = math.floor(k * page_per_quiz) + 1
        if page_idx > page_count:
            page_idx = page_count
        quiz_counts[page_idx] += 1

    for i in range(1, page_count + 1):
        chunk_info = ChunkInfo(
            referenced_pages=[i],
            quiz_count=quiz_counts[i],
        )
        chunks.append(chunk_info)

    return chunks

def handle_quiz_same_as_total_page(
    total_quiz_count: int, page_count: int
) -> List[ChunkInfo]:

    chunks = []
    page_per_quiz = page_count / total_quiz_count

    for quiz_sequence in range(total_quiz_count):
        cur_page_index = math.floor(quiz_sequence * page_per_quiz) + 1

        chunks.append(
            ChunkInfo(
                referenced_pages=[cur_page_index],
                quiz_count=1,
            )
        )

    return chunks
