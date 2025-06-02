import re
from typing import List, Dict
import frontmatter  # for parsing Jekyll markdown files
from datetime import datetime
from ..config import get_settings
import logging
import json

# Set up logging
logger = logging.getLogger(__name__)

settings = get_settings()

class TextProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or int(settings.CHUNK_SIZE)
        self.chunk_overlap = chunk_overlap or int(settings.CHUNK_OVERLAP)
        logger.info(f"TextProcessor initialized with chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap}")

    def _extract_metadata(self, content: str) -> Dict:
        """Extract metadata from Jekyll frontmatter"""
        logger.debug(f"Extracting metadata from content: {content[:200]}...")
        post = frontmatter.loads(content)
        metadata = {}
        for key, value in post.metadata.items():
            if isinstance(value, datetime):
                metadata[key] = value.isoformat()
            elif isinstance(value, list):
                metadata[key] = ', '.join(str(v) for v in value)
            elif isinstance(value, dict):
                metadata[key] = json.dumps(value)
            else:
                metadata[key] = str(value)
        logger.debug(f"Extracted metadata: {metadata}")
        return metadata

    def _remove_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content"""
        post = frontmatter.loads(content)
        logger.debug(f"Content after removing frontmatter: {post.content[:200]}...")
        return post.content

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        logger.debug(f"Chunking text: {text[:200]}...")
        if not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences (rough approximation)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        logger.debug(f"Split text into {len(sentences)} sentences")
        
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
        
        logger.debug(f"Generated {len(chunks)} chunks")
        return chunks

    def process_post(self, post: Dict) -> List[Dict]:
        """Process a blog post into chunks with metadata"""
        logger.info(f"Processing post: {post['name']}")
        logger.debug(f"Post content: {post['content'][:200]}...")
        
        if not post["content"].strip():
            logger.warning(f"Empty content for post: {post['name']}")
            return []

        metadata = self._extract_metadata(post["content"])
        content = self._remove_frontmatter(post["content"])
        chunks = self.chunk_text(content)
        
        logger.info(f"Generated {len(chunks)} chunks for post: {post['name']}")
        
        # Create chunks with metadata
        processed_chunks = [{
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
        
        logger.debug(f"First chunk preview (if any): {processed_chunks[0]['content'][:200] if processed_chunks else 'No chunks'}")
        return processed_chunks 