#!/usr/bin/env python3
"""
RAG System Demo Script with DeepSeek API Integration

This script demonstrates how to use the RAG system to:
1. Update content from the blog
2. Search for relevant information  
3. Generate AI responses using DeepSeek API

Usage:
    python scripts/test_rag_demo.py

Environment Requirements:
    DEEPSEEK_API_KEY=your_deepseek_api_key
"""

import asyncio
import httpx
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.rag.ingestion import ContentIngester
from app.api.rag import SearchQuery, GenerateQuery
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGDemo:
    """Demonstration class for the RAG system"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ingester = ContentIngester()
        
    async def demo_content_update(self, most_recent_only=True):
        """Demonstrate content update from blog"""
        print("\n" + "="*60)
        print("1. CONTENT UPDATE DEMO")
        print("="*60)
        
        try:
            print(f"📥 Updating content (most_recent_only={most_recent_only})...")
            result = await self.ingester.update_content(most_recent_only=most_recent_only)
            
            if result["status"] == "success":
                print(f"✅ {result['message']}")
                print(f"📊 Collection now has {self.ingester.collection.count()} total documents")
            else:
                print(f"❌ Update failed: {result['message']}")
                return False
                
        except Exception as e:
            print(f"❌ Content update error: {e}")
            return False
            
        return True
    
    def demo_content_search(self, query="quantum computing"):
        """Demonstrate content search"""
        print("\n" + "="*60)
        print("2. CONTENT SEARCH DEMO")
        print("="*60)
        
        try:
            print(f"🔍 Searching for: '{query}'")
            
            results = self.ingester.collection.query(
                query_texts=[query],
                n_results=3,
                include=["documents", "metadatas", "distances"]
            )
            
            if results and results["documents"] and results["documents"][0]:
                print(f"✅ Found {len(results['documents'][0])} relevant chunks:")
                
                for i, (doc, meta, dist) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0], 
                    results["distances"][0]
                ), 1):
                    print(f"\n--- Result {i} (Distance: {dist:.3f}) ---")
                    print(f"📄 Source: {meta.get('title', 'Unknown')} ({meta.get('date', 'Unknown')})")
                    print(f"🔗 Post: {meta.get('post_name', 'Unknown')}")
                    print(f"📝 Content preview: {doc[:200]}...")
                    
                return results
            else:
                print("❌ No search results found")
                return None
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return None
    
    async def demo_deepseek_api(self, context_chunks, user_query):
        """Demonstrate DeepSeek API integration"""
        print("\n" + "="*60) 
        print("3. DEEPSEEK API INTEGRATION DEMO")
        print("="*60)
        
        if not self.settings.DEEPSEEK_API_KEY:
            print("❌ DEEPSEEK_API_KEY not configured in environment")
            return None
            
        try:
            # Format context
            context_text = "\n\n".join([
                f"Context {i+1} (Source: {meta.get('title', 'Unknown')}, Date: {meta.get('date', 'Unknown')}):\n{doc}"
                for i, (doc, meta) in enumerate(zip(
                    context_chunks["documents"][0],
                    context_chunks["metadatas"][0]
                ))
            ])
            
            # Build prompt
            prompt = f"""You are an AI research assistant helping users find and summarize information from a technical blog.

Your task is to:
1. Analyze the provided context from blog posts
2. Extract relevant information that answers the user's question  
3. Provide a clear, well-structured response
4. Always cite your sources using the format [Title (Date)]
5. If the context doesn't contain enough information, acknowledge this

Here is the relevant context from the blog:

{context_text}

Question: {user_query}

Answer (remember to cite sources):"""

            print(f"🤖 Sending query to DeepSeek API...")
            print(f"📝 User question: '{user_query}'")
            print(f"📚 Using {len(context_chunks['documents'][0])} context chunks")
            
            # Call DeepSeek API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.DEEPSEEK_API_KEY.get_secret_value()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 8000
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    generated_text = data["choices"][0]["message"]["content"]
                    
                    print("✅ DeepSeek API Response:")
                    print("-" * 40)
                    print(generated_text)
                    print("-" * 40)
                    
                    return generated_text
                else:
                    print(f"❌ DeepSeek API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ DeepSeek API error: {e}")
            return None
    
    async def demo_complete_rag_workflow(self):
        """Demonstrate the complete RAG workflow"""
        print("\n" + "🚀" + " RAG SYSTEM COMPLETE WORKFLOW DEMO " + "🚀")
        print("="*80)
        
        # Step 1: Update content
        content_updated = await self.demo_content_update(most_recent_only=True)
        if not content_updated:
            print("❌ Cannot proceed without content. Please check your connection and try again.")
            return
        
        # Step 2: Search for content
        test_queries = [
            "quantum computing and error correction",
            "machine learning algorithms", 
            "software development best practices"
        ]
        
        for query in test_queries:
            print(f"\n{'='*20} Testing Query: '{query}' {'='*20}")
            
            # Search
            search_results = self.demo_content_search(query)
            
            if search_results:
                # Generate response with DeepSeek
                await self.demo_deepseek_api(search_results, query)
            else:
                print(f"⚠️ Skipping DeepSeek demo for '{query}' - no search results")
        
        print("\n" + "✅" + " RAG WORKFLOW DEMO COMPLETED " + "✅")
        print("="*80)

    def demo_system_status(self):
        """Show current system status"""
        print("\n" + "="*60)
        print("SYSTEM STATUS")
        print("="*60)
        
        try:
            collection = self.ingester.collection
            count = collection.count()
            
            print(f"📊 ChromaDB Collection: {collection.name}")
            print(f"📄 Total documents: {count}")
            print(f"🔑 DeepSeek API Key: {'✅ Configured' if self.settings.DEEPSEEK_API_KEY else '❌ Missing'}")
            print(f"📁 Chroma Directory: {self.settings.CHROMA_PERSIST_DIRECTORY}")
            
            if count > 0:
                # Get sample metadata
                sample = collection.get(limit=1, include=["metadatas"])
                if sample and sample["metadatas"]:
                    meta = sample["metadatas"][0]
                    print(f"📝 Sample document metadata:")
                    for key, value in meta.items():
                        print(f"   {key}: {value}")
                        
        except Exception as e:
            print(f"❌ Status check error: {e}")

async def main():
    """Main demo function"""
    demo = RAGDemo()
    
    # Show system status first
    demo.demo_system_status()
    
    # Ask user what to demo
    print("\n" + "🎯" + " DEMO OPTIONS " + "🎯")
    print("1. Complete workflow (recommended)")
    print("2. Content update only")
    print("3. Search demo only") 
    print("4. DeepSeek API test only")
    print("5. System status only")
    
    try:
        choice = input("\nSelect demo option (1-5): ").strip()
        
        if choice == "1":
            await demo.demo_complete_rag_workflow()
        elif choice == "2":
            await demo.demo_content_update(most_recent_only=False)
        elif choice == "3":
            query = input("Enter search query (or press Enter for 'quantum computing'): ").strip()
            demo.demo_content_search(query or "quantum computing")
        elif choice == "4":
            if demo.settings.DEEPSEEK_API_KEY:
                # Create dummy context for API test
                dummy_context = {
                    "documents": [["Quantum computing is a rapidly evolving field with applications in cryptography, optimization, and simulation."]],
                    "metadatas": [[{"title": "Quantum Computing Intro", "date": "2025-01-01"}]]
                }
                await demo.demo_deepseek_api(dummy_context, "What is quantum computing?")
            else:
                print("❌ DeepSeek API key not configured")
        elif choice == "5":
            demo.demo_system_status()
        else:
            print("Invalid choice. Running complete workflow demo...")
            await demo.demo_complete_rag_workflow()
            
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

if __name__ == "__main__":
    asyncio.run(main())