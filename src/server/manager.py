import subprocess
import httpx
import time
import threading

CLI_FLAG_MAP = {
    "ctx_size": "--ctx-size",
    "n_gpu_layers": "--n-gpu-layers",
}

class ServerManager:
    def __init__(self, config: dict, verbose: bool = False):
        self.config = config
        self.process = None
        self.current_model = None
        self.verbose = verbose
        self._log_thread = None

    def start(self, model_path: str):
        self.stop()
        # temperature, other params?
        args = [
            "llama-server",
            "--model", model_path,
            "--slots",
            "--slot-save-path", self.config["cache_dir"],
            "--port", str(self.config["port"]),
            "-np", str(self.config["n_slots"]),
        ]
        for key, value in self.config.get("server_params", {}).items():
            flag = CLI_FLAG_MAP.get(key)
            if flag:
                args += [flag, str(value)]
        self.process = subprocess.Popen(args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        )
        self.current_model = model_path
        self._start_log_thread()
        self._wait_until_ready()
    
    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        if self._log_thread:
            self._log_thread.join(timeout=2)
            self._log_thread = None
        
    def _start_log_thread(self):
        def drain():
            for line in self.process.stdout:
                if self.verbose:
                    print(line, end="", flush=True)
        
        self._log_thread = threading.Thread(target=drain, daemon=True)
        self._log_thread.start()
    
    def _wait_until_ready(self):
        for _ in range(30):
            try:
                httpx.get(f"http://localhost:{self.config['port']}/health")
                return
            except httpx.ConnectError:
                time.sleep(1)
        raise RuntimeError("Server failed to start.")
    
