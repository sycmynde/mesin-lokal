"""
Wrapper tipis: interface lama (Memory class) → backend baru (SQLite memory_manager).
File asli ada di ~/mesin/gudang/memory.py
"""
from core.memory_manager import (
    get_memory_summary,
    search_memory,
    get_all_memory,
    add_memory,
    load_memory,
    save_memory,
)


class Memory:

    def __init__(self):
        pass

    def build_context(self):
        """Pengganti build_context lama → pakai summary dari DB."""
        return get_memory_summary()

    def search(self, query):
        results = search_memory(query)
        return [{"value": r} for r in results]

    def search_relevant(self, query, limit=5):
        results = search_memory(query, limit=limit)
        return [{"value": r, "score": 0.5} for r in results]

    def remember(self, category, key, value):
        return add_memory(category, key, value)

    def recall(self):
        return get_all_memory()

    def load(self):
        return load_memory()

    def save(self, data):
        save_memory(data)
