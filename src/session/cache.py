from src.server.client import LlamaClient
from src.session.session import Session

class CacheManager:
    def __init__(self, client: LlamaClient):
        self.client = client

    async def try_restore(self, session: Session, current_model: str) -> bool:
        if not session.is_cache_valid(current_model):
            return False
        result = await self.client.restore_slot(0, session.kv_cache["cache_file"])
        return result.get("n_restored", 0) > 0

    async def save(self, session: Session, current_model: str):
        cache_file = f"{session.id}.bin"
        result = await self.client.save_slot(0, cache_file)
        if result.get("n_saved", 0) > 0:
            session.update_cache(current_model, cache_file)