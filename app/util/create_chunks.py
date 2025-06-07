import math
from typing import List

from pydantic.v1 import BaseModel


class ChunkInfo(BaseModel):
    text: str
    referenced_pages: List[int]
    quiz_count: int


def create_chunks(
    pages: List[str],
    total_quiz_count: int,
    minimum_page_text_length_per_chunk: int,
    max_chunk_count: int,
) -> List[ChunkInfo]:

    page_count = len(pages)

    if total_quiz_count < page_count:
        chunks = handle_quiz_smaller_than_total_page(total_quiz_count, pages)

    elif total_quiz_count > page_count:
        chunks = handle_quiz_larger_than_total_page(total_quiz_count, pages)

    else:
        chunks = handle_quiz_same_as_total_page(total_quiz_count, pages)

    chunks = add_prefix_suffix(chunks, pages, minimum_page_text_length_per_chunk)

    chunks = compress_chunks(max_chunk_count, chunks)
    return chunks


def compress_chunks(max_chunk_count: int, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
    if len(chunks) <= max_chunk_count:
        return chunks

    base_size = len(chunks) // max_chunk_count
    remainder = len(chunks) % max_chunk_count

    compressed_chunks = []
    idx = 0
    for i in range(max_chunk_count):

        group_size = base_size + 1 if i < remainder else base_size

        merged_chunk = ChunkInfo(text="", referenced_pages=[], quiz_count=0)
        index_set = set([])
        for _ in range(group_size):
            chunk = chunks[idx]
            merged_chunk.text += chunk.text
            for referenced_page in chunk.referenced_pages:
                index_set.add(referenced_page)
            idx += 1
            merged_chunk.quiz_count += chunk.quiz_count

        merged_chunk.referenced_pages = list(sorted(index_set))
        compressed_chunks.append(merged_chunk)

    return compressed_chunks


def add_prefix_suffix(
    chunks, one_based_pages, minimum_page_text_length_per_chunk
) -> List[ChunkInfo]:
    for idx, chunk in enumerate(chunks):
        first_ref = chunk.referenced_pages[0]
        last_ref = chunk.referenced_pages[-1]

        prev_page = first_ref - 1
        next_page = last_ref + 1

        while True:
            added_any = False

            if prev_page >= 1:
                chunk.text = one_based_pages[prev_page] + chunk.text
                chunk.referenced_pages.insert(0, prev_page)
                added_any = True
                prev_page -= 1

            if next_page < len(one_based_pages):
                chunk.text = chunk.text + one_based_pages[next_page]
                chunk.referenced_pages.append(next_page)
                added_any = True
                next_page += 1

            if not added_any:
                break

            if len(chunk.text) > minimum_page_text_length_per_chunk:
                break

    return chunks


def handle_quiz_smaller_than_total_page(
    total_quiz_count: int, pages: List[str]
) -> List[ChunkInfo]:
    chunks = []
    last_page_index = len(pages) - 1
    page_per_quiz = last_page_index / total_quiz_count

    for quiz_sequence in range(total_quiz_count):
        start = math.floor(quiz_sequence * page_per_quiz) + 1
        end = math.floor((quiz_sequence + 1) * page_per_quiz)

        text = ""
        referenced_pages = []
        for i, page in enumerate(pages[start : end + 1], start=start):
            text = text + page
            referenced_pages.append(i)

        chunks.append(
            ChunkInfo(text=text, referenced_pages=referenced_pages, quiz_count=1)
        )

    return chunks


def handle_quiz_larger_than_total_page(
    total_quiz_count: int, pages: List[str]
) -> List[ChunkInfo]:

    chunks = []
    page_count = len(pages) - 1
    page_per_quiz = page_count / total_quiz_count

    quiz_counts = [0] * (page_count + 1)

    for k in range(total_quiz_count):
        page_idx = math.floor(k * page_per_quiz) + 1
        if page_idx > page_count:
            page_idx = page_count
        quiz_counts[page_idx] += 1

    for i in range(1, page_count + 1):
        chunk_info = ChunkInfo(
            text=pages[i],
            referenced_pages=[i],
            quiz_count=quiz_counts[i],
        )
        chunks.append(chunk_info)

    return chunks


def handle_quiz_same_as_total_page(
    total_quiz_count: int, pages: List[str]
) -> List[ChunkInfo]:

    chunks = []
    last_page_index = len(pages) - 1
    page_per_quiz = last_page_index / total_quiz_count

    for quiz_sequence in range(total_quiz_count):
        cur_page_index = math.floor(quiz_sequence * page_per_quiz) + 1

        chunks.append(
            ChunkInfo(
                text=pages[cur_page_index],
                referenced_pages=[cur_page_index],
                quiz_count=1,
            )
        )

    return chunks
