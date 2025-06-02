import pytest
import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set test environment variables
os.environ["CHROMA_PERSIST_DIRECTORY"] = "/tmp/test_chroma"
os.environ["CHUNK_SIZE"] = "500"
os.environ["CHUNK_OVERLAP"] = "100"

@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test"""
    yield
    # Clean up ChromaDB test directory after tests
    if os.path.exists("/tmp/test_chroma"):
        import shutil
        shutil.rmtree("/tmp/test_chroma") 