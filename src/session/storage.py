import json
import os
from src.session.session import Session

class SessionStorage:
    def __init__(self, sessions_dir: str):
        self.sessions_dir = sessions_dir

    def save(self, session: Session):
        path = os.path.join(self.sessions_dir, f"{session.id}.json")
        with open(path, "w") as f:
            json.dump(self._serialize(session), f, indent=2)

    def load(self, session_id: str) -> Session:
        path = os.path.join(self.sessions_dir, f"{session_id}.json")
        with open(path, "r") as f:
            data = json.load(f)
        return self._deserialize(data)

    def list_sessions(self) -> list[str]:
        return [
            f.replace(".json", "")
            for f in os.listdir(self.sessions_dir)
            if f.endswith(".json")
        ]

    def _serialize(self, session: Session) -> dict:
        return {
            "id": session.id,
            "created_at": session.created_at,
            "messages": session.messages,
            "kv_cache": session.kv_cache,
        }

    def _deserialize(self, data: dict) -> Session:
        session = Session()
        session.id = data["id"]
        session.created_at = data["created_at"]
        session.messages = data["messages"]
        session.kv_cache = data.get("kv_cache")
        return session