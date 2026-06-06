"""
Quick smoke test for the LangGraph chat agent.
Runs against the Docker Postgres on localhost:5432.

Usage (from repo root with venv active):
    python test_chat_agent.py
"""

import os
import sys

# Use localhost instead of the Docker service name
TEST_DB_URL = "postgresql://phonox:phonox123@localhost:5432/phonox"
os.environ.setdefault("DATABASE_URL", TEST_DB_URL)

# Load ANTHROPIC_API_KEY from .env if not already set
if not os.environ.get("ANTHROPIC_API_KEY"):
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1]
                    break
    except FileNotFoundError:
        pass

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("❌  ANTHROPIC_API_KEY not set. Export it or add to .env")
    sys.exit(1)

# ── Load ANTHROPIC_CHAT_MODEL from .env ───────────────────────────────────
try:
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

from langchain_core.messages import AIMessage, HumanMessage
from backend.agent.chat_agent import get_chat_graph, init_chat_agent

SEPARATOR = "─" * 60


def run(label: str, thread_id: str, message: str, record_metadata=None):
    print(f"\n{SEPARATOR}")
    print(f"[{label}]  thread={thread_id}")
    print(f"User: {message}")
    graph = get_chat_graph()
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={
            "recursion_limit": 6,
            "configurable": {
                "thread_id": thread_id,
                "db": None,
                "record_metadata": record_metadata,
            },
        },
    )
    last = result["messages"][-1]
    print(f"Agent: {last.content[:400]}")

    # Show which tools were called
    from langchain_core.messages import ToolMessage
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    if tool_msgs:
        print(f"Tools used: {[m.name for m in tool_msgs]}")
    else:
        print("Tools used: none")
    return result


def main():
    print("Initialising chat agent …")
    init_chat_agent(TEST_DB_URL)
    print("✅  Checkpointer ready\n")

    # ── Test 1: general chat, no tools expected ──────────────────────────
    run(
        "General / no tools",
        thread_id="test_general_1",
        message="What is the Goldmine grading scale for vinyl?",
    )

    # ── Test 2: general chat, should trigger web_search ─────────────────
    run(
        "General / web_search expected",
        thread_id="test_general_2",
        message="What is the current market price for a mint copy of Dark Side of the Moon first UK pressing?",
    )

    # ── Test 3: memory — two turns on same thread ────────────────────────
    record_meta = {
        "artist": "Miles Davis",
        "title": "Kind of Blue",
        "year": 1959,
        "label": "Columbia",
        "catalog_number": "CL 1355",
        "barcode": None,
        "genres": ["jazz"],
        "estimated_value_eur": 120.0,
        "condition": "VG+",
        "spotify_url": None,
        "user_notes": None,
    }
    run(
        "Record chat / turn 1",
        thread_id="test_record_miles",
        message="What label was this originally released on?",
        record_metadata=record_meta,
    )
    run(
        "Record chat / turn 2 (memory check)",
        thread_id="test_record_miles",
        message="And what year was that?",   # relies on memory of previous turn
        record_metadata=record_meta,
    )

    print(f"\n{SEPARATOR}")
    print("✅  All tests completed.")


if __name__ == "__main__":
    main()
