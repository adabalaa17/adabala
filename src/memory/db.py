import os
from motor.motor_asyncio import AsyncIOMotorClient
import chromadb
from chromadb.config import Settings

# --- MongoDB Setup for Operational Data ---
# Stores agent roles, system states, historical reports, and the CTO's decisions
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "agent_orchestrator"

class MongoDatabase:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]

    async def get_collection(self, collection_name: str):
        return self.db[collection_name]

    async def save_report(self, report_data: dict):
        reports_col = await self.get_collection("reports")
        result = await reports_col.insert_one(report_data)
        return str(result.inserted_id)

    async def get_latest_report(self):
        reports_col = await self.get_collection("reports")
        report = await reports_col.find_one(sort=[("_id", -1)])
        return report

# --- ChromaDB Setup for Agent Shared Memory ---
# Vector database where agents can search for code snippets, past decisions, and context
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

class VectorMemoryDatabase:
    def __init__(self):
        # We use a persistent local client for vector storage
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        # We ensure a collection for shared agent memory exists
        self.collection = self.client.get_or_create_collection(
            name="shared_agent_memory",
            metadata={"hnsw:space": "cosine"}
        )

    def add_memory(self, memory_id: str, text: str, metadata: dict = None):
        if metadata is None:
            metadata = {}
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[memory_id]
        )

    def search_memory(self, query_text: str, n_results: int = 5):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

# Expose instances
mongo_db = MongoDatabase()
vector_db = VectorMemoryDatabase()