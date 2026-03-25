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
import sys
import os

def select_session(storage: SessionStorage, config: dict) -> Session:
    sessions = storage.list_sessions()

    if not sessions:
        print("[SYSTEM] No existing sessions. Starting new session.")
        return Session(config["default_system_prompt"])

    print("[SYSTEM] Existing sessions:")
    for i, sid in enumerate(sessions):
        session = storage.load(sid)
        label = session.title or sid
        print(f"  [{i}] {label}")
    print(f"  [n] New session")

    choice = input("[SYSTEM] Select session: ").strip().lower()

    if choice == "n":
        return Session(config["default_system_prompt"])

    try:
        idx = int(choice)
        if 0 <= idx < len(sessions):
            session = storage.load(sessions[idx])
            print(f"Loaded session {session.title or session.id}")
            return session
    except ValueError:
        pass

    print("[SYSTEM] Invalid choice. Starting new session.")
    return Session(config["default_system_prompt"])

def prompt_new_session(config: dict) -> Session:
    return Session(config["default_system_prompt"])

def switch_session(storage: SessionStorage, config: dict) -> Session | None:
    sessions = storage.list_sessions()
    if not sessions:
        print("[SYSTEM] No saved sessions.")
        return None

    print("Sessions:")
    for i, sid in enumerate(sessions):
        s = storage.load(sid)
        label = s.title or sid
        print(f"  [{i}] {label}")

    choice = input("[SYSTEM] Select session (or blank to cancel): ").strip()
    if not choice:
        return None

    try:
        idx = int(choice)
        if 0 <= idx < len(sessions):
            session = storage.load(sessions[idx])
            print(f"[SYSTEM] Switched to: {session.title or session.id}")
            return session
    except ValueError:
        pass

    print("[SYSTEM] Invalid choice.")
    return None

async def main():

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    with open("config.json") as f:
        config = json.load(f)

    server = ServerManager(config, verbose=verbose)
    client = LlamaClient(f"http://localhost:{config['port']}")
    storage = SessionStorage(config["sessions_dir"])
    cache_manager = CacheManager(client)
    registry = ModelRegistry(config["models_dir"])
    switcher = ModelSwitcher(server, registry)
    generation_params = config.get("generation_params", {}).copy()
    token_budget = (
        config["server_params"]["ctx_size"] // config["n_slots"]
        - generation_params.get("max_tokens", 512)
        - 64
    )

    server.start(registry.get_path(config["default_model"]))
    session = select_session(storage, config)
    await cache_manager.try_restore(session, server.current_model)

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        if user_input == "/help":
            print("""
            Commands:
            /help                 Show this message
            /verbose              Toggle server logs
            /title <title>        Set session title
            /params               Show generation params
            /set <key> <value>    Set a generation param
            /model list           List all available models
            /model switch <model> Switch the current session model
            /session list         List all sessions
            /session new          Start a new session
            /session switch       Switch to another session
            /session delete       Delete current session
            """)
            continue

        if user_input == "/verbose":
            server.verbose = not server.verbose
            print(f"[SYSTEM] Verbose: {'on' if server.verbose else 'off'}")
            continue

        if user_input.startswith("/title "):
            session.set_title(user_input[7:].strip())
            print(f"[SYSTEM] Title set: {session.title}")
            storage.save(session)
            continue

        if user_input == "/params":
            for k, v in generation_params.items():
                print(f"  {k} = {v}")
            continue

        if user_input.startswith("/set "):
            parts = user_input.split(maxsplit=2)
            if len(parts) == 3:
                _, key, raw = parts
                try:
                    generation_params[key] = float(raw)
                    print(f"[SYSTEM] Set {key} = {generation_params[key]}")
                except ValueError:
                    print(f"[SYSTEM] Invalid value: {raw}")
            continue

        if user_input == "/model list":
            models = registry.list_models()
            for i, m in enumerate(models):
                marker = " *" if registry.get_path(m) == server.current_model else ""
                print(f"  [{i}] {m}{marker}")
            continue

        if user_input == "/model switch":
            models = registry.list_models()
            for i, m in enumerate(models):
                marker = " *" if registry.get_path(m) == server.current_model else ""
                print(f"  [{i}] {m}{marker}")

            choice = input("[SYSTEM] Select model (or blank to cancel): ").strip()
            if not choice:
                continue

            try:
                idx = int(choice)
                if 0 <= idx < len(models):
                    switcher.switch(models[idx], session)
                    print(f"[SYSTEM] Switched to: {models[idx]}")
            except ValueError:
                print("[SYSTEM] Invalid choice.")
            continue

        if user_input == "/session list":
            sessions = storage.list_sessions()
            for i, sid in enumerate(sessions):
                s = storage.load(sid)
                label = s.title or sid
                marker = " *" if sid == session.id else ""
                print(f"  [{i}] {label}{marker}")
            continue

        if user_input == "/session new":
            storage.save(session)
            session = prompt_new_session(config)
            print("[SYSTEM] New session started.")
            continue

        if user_input == "/session switch":
            storage.save(session)
            result = switch_session(storage, config)
            if result:
                session = result
                await cache_manager.try_restore(session, server.current_model)
            continue

        if user_input == "/session delete":
            confirm = input(f"Delete '{session.title or session.id}'? (y/n): ").strip().lower()
            if confirm == "y":
                os.remove(os.path.join(config["sessions_dir"], f"{session.id}.json"))
                print("[SYSTEM] Session deleted.")
                session = prompt_new_session(config)
            continue

        if user_input.startswith("/"):
            print(f"[SYSTEM] Unknown command: {user_input.split()[0]}")
            continue

        session.add_user_message(user_input)

        if session.title is None:
            session.auto_title()

        response = await client.chat(
            session.get_windowed_messages(token_budget),
            params=generation_params,
        )

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