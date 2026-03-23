import uuid
from datetime import datetime, timezone

class Session:
    def __init__(self, system_prompt: str = None):
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.messages = []
        self.kv_cache = None

        if system_prompt:
            self.messages.append({
                "id": str(uuid.uuid4()),
                "role": "system",
                "content": system_prompt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def add_user_message(self, content: str):
        self.messages.append({
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_assistant_message(self, content: str, metadata: dict):
        self.messages.append({
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        })

    def get_messages_for_api(self) -> list[dict]:
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages
        ]

    def invalidate_cache(self):
        self.kv_cache = None

    def update_cache(self, model_file: str, cache_file: str):
        self.kv_cache = {
            "model_file": model_file,
            "cache_file": cache_file,
            "valid_through_message_id": self.messages[-1]["id"],
        }

    def is_cache_valid(self, current_model_file: str) -> bool:
        if not self.kv_cache:
            return False
        if self.kv_cache["model_file"] != current_model_file:
            return False
        if self.kv_cache["valid_through_message_id"] != self.messages[-1]["id"]:
            return False
        return True