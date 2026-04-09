import re

async def chunk_by_words(text: str, max_words: int = 5000) -> list[str]:
    """
    Splits text into chunks by word count while preserving sentence boundaries.
    Prevents mid-sentence cuts that cause robotic TTS seams.
    """
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []

    # 1. Split into sentences (keeps punctuation attached)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_words = []
    current_count = 0

    for sent in sentences:
        sent_words = sent.split()
        sent_count = len(sent_words)

        #  If a single sentence exceeds the limit, split it intelligently
        if sent_count > max_words:
            if current_words:
                chunks.append(' '.join(current_words))
                current_words = []
                current_count = 0

            # First try splitting at commas/semicolons for natural pauses
            sub_parts = re.split(r'(?<=[,;:])\s+', sent)
            for part in sub_parts:
                part_words = part.split()
                if len(part_words) > max_words:
                    # Fallback: hard split by max_words
                    for i in range(0, len(part_words), max_words):
                        chunks.append(' '.join(part_words[i:i+max_words]))
                elif current_count + len(part_words) <= max_words:
                    current_words.extend(part_words)
                    current_count += len(part_words)
                else:
                    chunks.append(' '.join(current_words))
                    current_words = part_words
                    current_count = len(part_words)
        else:
            # Normal case: add to current chunk or flush
            if current_count + sent_count <= max_words:
                current_words.extend(sent_words)
                current_count += sent_count
            else:
                chunks.append(' '.join(current_words))
                current_words = sent_words
                current_count = sent_count

    if current_words:
        chunks.append(' '.join(current_words))

    # Filter out noise/tiny fragments
    return [c for c in chunks if len(c.split()) >= 5]




async def clean_text(text: str) -> str:
    """Removes common PDF extraction artifacts before TTS."""

    # Remove page numbers
    text = re.sub(r'Page\s+\d+', '', text, flags=re.IGNORECASE)
    
    # Fix hyphenated line breaks (con-\nversation → conversation)
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    
    # Normalize whitespace & punctuation spacing
    text = re.sub(r'\s+([.,;:!?])\s*', r'\1 ', text)  # "word ," → "word,"
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    
    # Remove orphaned symbols/artifacts
    text = re.sub(r'[※†‡§¶]\s*', '', text)  # Footnote markers
    
    # Fix common ligatures
    text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace('ﬀ', 'ff')
    
    return text.strip()