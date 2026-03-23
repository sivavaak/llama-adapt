import asyncio
import json
from src.server.manager import ServerManager
from src.server.client import LlamaClient
from src.session.session import Session
from src.session.storage import SessionStorage
from src.session.cache import CacheManager
from src.models.registry import ModelRegistry
from src.models.switcher import ModelSwitcher
from datetime import datetime, timezone

async def main():
    with open("config.json") as f:
        config = json.load(f)

    server = ServerManager(config)
    client = LlamaClient(f"http://localhost:{config['port']}")
    storage = SessionStorage(config["sessions_dir"])
    cache_manager = CacheManager(client)
    registry = ModelRegistry(config["models_dir"])
    switcher = ModelSwitcher(server, registry)

    server.start(registry.get_path(config["default_model"]))
    session = Session(config["default_system_prompt"])

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        session.add_user_message(user_input)
        response = await client.chat(session.get_messages_for_api())

        content = response["choices"][0]["message"]["content"]
        timings = response.get("timings", {})

        session.add_assistant_message(content, {
            "model": server.current_model,
            "tokens_prompt": response["usage"]["prompt_tokens"],
            "tokens_generated": response["usage"]["completion_tokens"],
            "generation_ms": timings.get("predicted_ms"),
            "prompt_ms": timings.get("prompt_ms"),
            "cache_n": timings.get("cache_n"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await cache_manager.save(session, server.current_model)
        storage.save(session)
        print(f"Assistant: {content}")

if __name__ == "__main__":
    asyncio.run(main())