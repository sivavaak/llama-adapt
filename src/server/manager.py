import subprocess
import httpx
import time

class ServerManager:
    def __init__(self, config: dict):
        self.config = config
        self.process = None
        self.current_model = None

    def start(self, model_path: str):
        self.stop()
        # temperature, other params?
        self.process = subprocess.Popen([
            "llama-server",
            "--model", model_path,
            "--slot-save-path", self.config["cache_dir"],
            "--port", str(self.config["port"]),
            "-np", str(self.config["n_slots"]),            
        ])
        self.current_model = model_path
        self._wait_until_ready()
    
    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
    
    def _wait_until_ready(self):
        for _ in range(30):
            try:
                httpx.get(f"http://localhost:{self.config['port']}/health")
                return
            except httpx.ConnectError:
                time.sleep(1)
        raise RuntimeError("Server failed to start.")
    
    