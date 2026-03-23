import os

class ModelRegistry:
    def __init__(self, models_dir: str):
        self.models_dir = models_dir

    def list_models(self) -> list[str]:
        return [
            f for f in os.listdir(self.models_dir)
            if f.endswith(".gguf")
        ]

    def get_path(self, filename: str) -> str:
        return os.path.join(self.models_dir, filename)