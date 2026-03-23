from src.server.manager import ServerManager
from src.session.session import Session
from src.models.registry import ModelRegistry

class ModelSwitcher:
    def __init__(self, server: ServerManager, registry: ModelRegistry):
        self.server = server
        self.registry = registry

    def switch(self, model_filename: str, session: Session):
        path = self.registry.get_path(model_filename)
        session.invalidate_cache()
        self.server.start(path)