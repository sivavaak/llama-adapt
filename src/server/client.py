import httpx

class LlamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def chat(self, messages: list[dict], slot_id: int = 0) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": messages,
                    "cache_prompt": True,
                    "id_slot": slot_id,
                },
            )
            return response.json()
        
    async def save_slot(self, slot_id: int, filename: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/slots/{slot_id}?action=save",
                json={"filename": filename},
            )
            return response.json()
    
    async def restore_slot(self, slot_id: int, filename: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/slots/{slot_id}?action=restore",
                json={"filename": filename},
            )
            return response.json()
        
    