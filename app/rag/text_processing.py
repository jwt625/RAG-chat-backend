import re
from typing import List, Dict
import frontmatter  # for parsing Jekyll markdown files
from datetime import datetime
from ..config import get_settings

settings = get_settings()

class TextProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or int(settings.CHUNK_SIZE)
        self.chunk_overlap = chunk_overlap or int(settings.CHUNK_OVERLAP)

    def _extract_metadata(self, content: str) -> Dict:
        """Extract metadata from Jekyll frontmatter"""
        post = frontmatter.loads(content)
        metadata = {}
        for key, value in post.metadata.items():
            if isinstance(value, datetime):
                metadata[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                metadata[key] = str(value)
            else:
                metadata[key] = str(value)
        return metadata

    def _remove_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content"""
        post = frontmatter.loads(content)
        return post.content

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if not text.strip():
            return []

        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences (rough approximation)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If a single sentence is longer than chunk_size, split it by words
            if sentence_length > self.chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence into smaller pieces
                words = sentence.split()
                current_piece = []
                current_piece_length = 0
                
                for word in words:
                    word_length = len(word)
                    if current_piece_length + word_length + (1 if current_piece else 0) > self.chunk_size:
                        if current_piece:
                            chunks.append(' '.join(current_piece))
                        current_piece = [word]
                        current_piece_length = word_length
                    else:
                        current_piece.append(word)
                        current_piece_length += word_length + (1 if current_piece else 0)
                
                if current_piece:
                    current_chunk = current_piece
                    current_length = current_piece_length
            
            # Normal case: add sentence to current chunk
            elif current_length + sentence_length + (1 if current_chunk else 0) > self.chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_chunk:
                    # Calculate overlap while respecting size limit
                    overlap_words = []
                    overlap_length = 0
                    for word in reversed(current_chunk):
                        if overlap_length + len(word) + 1 > self.chunk_overlap:
                            break
                        overlap_words.insert(0, word)
                        overlap_length += len(word) + 1
                    
                    current_chunk = overlap_words + [sentence]
                    current_length = sum(len(word) for word in current_chunk) + len(current_chunk) - 1
                else:
                    current_chunk = [sentence]
                    current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + (1 if len(current_chunk) > 1 else 0)
        
        # Add the last chunk if it exists and isn't too long
        if current_chunk and current_length <= self.chunk_size:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def process_post(self, post: Dict) -> List[Dict]:
        """Process a blog post into chunks with metadata"""
        if not post["content"].strip():
            return []

        metadata = self._extract_metadata(post["content"])
        content = self._remove_frontmatter(post["content"])
        chunks = self.chunk_text(content)
        
        # Create chunks with metadata
        return [{
            "id": f"{post['id']}_chunk_{i}",
            "content": chunk,
            "metadata": {
                **metadata,
                "post_name": post["name"],
                "url": post.get("url", ""),
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
        } for i, chunk in enumerate(chunks)] 