import pytest
from app.rag.text_processing import TextProcessor

# Test data
TEST_POST = {
    "id": "test123",
    "name": "2024-01-01-test-post.md",
    "content": """---
layout: post
title: Test Post
date: 2024-01-01
categories: test
---
# First Section
This is the first paragraph of content.

## Subsection
This is a subsection with some content.
It continues on multiple lines.

# Second Section
Another section with different content.
""",
    "url": "https://example.com/test-post"
}

# Real data from GitHub repo
REAL_POST = {
    "id": "abc123",
    "name": "2025-05-26-weekly-OFS-48.md",
    "content": """---
layout: post
title: "Weekly OFS #48"
date: 2025-05-26
categories: weekly
tags: [weekly, research, optics]
---

# Weekly Summary

This week's focus was on advanced optical systems and their applications in quantum computing.

## Research Progress

- Completed simulation of quantum optical gates
- Analyzed coherence properties of the system
- Started writing the methods section of the paper

## Next Steps

1. Run additional verification tests
2. Compare results with theoretical predictions
3. Begin drafting the results section
""",
    "url": "https://github.com/jwt625/jwt625.github.io/blob/main/_posts/2025-05-26-weekly-OFS-48.md"
}

def test_text_processor_initialization():
    processor = TextProcessor()
    assert processor is not None
    assert hasattr(processor, 'chunk_size')
    assert hasattr(processor, 'chunk_overlap')

def test_extract_metadata():
    processor = TextProcessor()
    metadata = processor._extract_metadata(TEST_POST["content"])
    
    assert metadata is not None
    assert metadata["layout"] == "post"
    assert metadata["title"] == "Test Post"
    assert metadata["date"] == "2024-01-01"
    assert metadata["categories"] == "test"

def test_remove_frontmatter():
    processor = TextProcessor()
    content = processor._remove_frontmatter(TEST_POST["content"])
    
    assert "---" not in content[:10]  # Front matter should be removed
    assert "# First Section" in content
    assert "layout: post" not in content

def test_process_post():
    processor = TextProcessor()
    chunks = processor.process_post(TEST_POST)
    
    assert len(chunks) > 0
    
    # Check first chunk
    first_chunk = chunks[0]
    assert "id" in first_chunk
    assert "content" in first_chunk
    assert "metadata" in first_chunk
    
    # Verify metadata in chunks
    for chunk in chunks:
        assert chunk["metadata"]["url"] == TEST_POST["url"]
        assert chunk["metadata"]["post_name"] == TEST_POST["name"]
        assert isinstance(chunk["metadata"]["chunk_index"], int)
        assert isinstance(chunk["metadata"]["total_chunks"], int)
        assert chunk["metadata"]["chunk_index"] <= chunk["metadata"]["total_chunks"]

def test_process_post_with_empty_content():
    empty_post = {
        "id": "empty123",
        "name": "empty-post.md",
        "content": "",
        "url": "https://example.com/empty"
    }
    
    processor = TextProcessor()
    chunks = processor.process_post(empty_post)
    assert len(chunks) == 0

def test_process_post_without_frontmatter():
    no_frontmatter_post = {
        "id": "nofm123",
        "name": "no-frontmatter.md",
        "content": "# Just Content\nNo front matter here.",
        "url": "https://example.com/no-frontmatter"
    }
    
    processor = TextProcessor()
    chunks = processor.process_post(no_frontmatter_post)
    assert len(chunks) > 0
    assert "content" in chunks[0]

def test_chunk_size_limits():
    processor = TextProcessor()
    long_content = "Test content. " * 1000  # Create a very long post
    long_post = {
        "id": "long123",
        "name": "long-post.md",
        "content": long_content,
        "url": "https://example.com/long"
    }
    
    chunks = processor.process_post(long_post)
    
    # Verify each chunk is within size limits
    for chunk in chunks:
        assert len(chunk["content"]) <= processor.chunk_size
        if chunk["metadata"]["chunk_index"] > 1:  # Not first chunk
            assert len(chunk["content"]) >= processor.chunk_overlap

def test_process_real_post():
    """Test processing with real data from GitHub repo"""
    processor = TextProcessor()
    chunks = processor.process_post(REAL_POST)
    
    assert len(chunks) > 0, "Should generate at least one chunk"
    
    # Check first chunk
    first_chunk = chunks[0]
    assert "id" in first_chunk
    assert "content" in first_chunk
    assert "metadata" in first_chunk
    
    # Verify metadata
    assert first_chunk["metadata"]["title"] == "Weekly OFS #48"
    assert first_chunk["metadata"]["categories"] == "weekly"
    assert first_chunk["metadata"]["tags"] == "weekly, research, optics"
    
    # Verify content
    assert "Weekly Summary" in first_chunk["content"]
    assert "quantum computing" in ' '.join(chunk["content"] for chunk in chunks)
    
    # Print chunk details for debugging
    print("\nChunks generated from real post:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"Content length: {len(chunk['content'])}")
        print(f"Content preview: {chunk['content'][:100]}...") 