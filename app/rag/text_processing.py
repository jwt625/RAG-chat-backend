import re
from typing import List, Dict
import frontmatter  # for parsing Jekyll markdown files

class TextProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_markdown(self, content: str) -> Dict:
        """Process Jekyll markdown content"""
        # Parse frontmatter and content
        post = frontmatter.loads(content)
        
        return {
            "metadata": dict(post.metadata),
            "content": post.content
        }

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences (rough approximation)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size:
                # Store current chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def process_post(self, post: Dict) -> List[Dict]:
        """Process a blog post into chunks with metadata"""
        processed_post = self.process_markdown(post["content"])
        chunks = self.chunk_text(processed_post["content"])
        
        # Create chunks with metadata
        return [{
            "id": f"{post['id']}_chunk_{i}",
            "post_id": post["id"],
            "chunk_index": i,
            "content": chunk,
            "metadata": {
                **processed_post["metadata"],
                "post_name": post["name"],
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
        } for i, chunk in enumerate(chunks)] 