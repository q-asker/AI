async def create_chunks(text: str, chunk_count: int):
    try:
        # 최소 chunk 크기 설정 (너무 작은 chunk 방지)
        min_chunk_size = 200
        
        # 텍스트가 너무 짧은 경우 chunk_count 조정
        if len(text) < min_chunk_size * chunk_count:
            actual_chunk_count = max(1, len(text) // min_chunk_size)
            print(f"텍스트가 짧아서 chunk 개수를 {chunk_count}에서 {actual_chunk_count}로 조정합니다.")
            chunk_count = actual_chunk_count
        
        chunks = []
        
        # 문장 단위로 분할하기 위해 개행과 마침표 기준으로 나누기
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            if char in ['.', '!', '?', '\n'] and len(current_sentence.strip()) > 10:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 마지막 문장 추가
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        if not sentences:
            # 문장 분할이 실패한 경우 단순 분할
            chunk_size = len(text) // chunk_count
            for i in range(chunk_count):
                start = i * chunk_size
                end = (i + 1) * chunk_size if i < chunk_count - 1 else len(text)
                chunks.append(text[start:end])
        else:
            # 문장들을 chunk_count개의 그룹으로 분배
            sentences_per_chunk = len(sentences) // chunk_count
            remainder = len(sentences) % chunk_count
            
            start_idx = 0
            for i in range(chunk_count):
                sentences_in_this_chunk = sentences_per_chunk + (1 if i < remainder else 0)
                end_idx = start_idx + sentences_in_this_chunk
                
                chunk_sentences = sentences[start_idx:end_idx]
                chunk_text = ' '.join(chunk_sentences)
                
                # 빈 chunk 방지
                if chunk_text.strip():
                    chunks.append(chunk_text)
                
                start_idx = end_idx
        
        # 빈 chunk가 있으면 제거
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        # chunk가 없으면 원본 텍스트를 하나의 chunk로 사용
        if not chunks:
            chunks = [text]
        
        print(f"최종 생성된 chunk 개수: {len(chunks)}")
        return chunks
        
    except Exception as e:
        print(f"Chunk 생성 중 오류 발생: {e}")
        # 폴백: 단순 분할
        chunk_size = len(text) // chunk_count
        chunks = []
        for i in range(chunk_count):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < chunk_count - 1 else len(text)
            chunks.append(text[start:end])
        return chunks