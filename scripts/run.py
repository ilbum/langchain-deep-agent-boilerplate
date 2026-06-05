"""Stream the deep agent locally and print all steps as they happen.

Usage:
    uv run scripts/run.py "your message here"
    uv run scripts/run.py           # prompts for input
    uv run scripts/run.py -y "..."  # auto-approve all interrupts

When a tool requires approval (interrupt_on), you will be prompted:
    approve  — let the tool run
    reject   — block the tool (optionally add a reason: "reject: too risky")
"""

import json
import sys
import uuid

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from deep_agent.agent import create_graph

graph = create_graph(checkpointer=MemorySaver())


def _extract_text(content) -> str:
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content or ""


def _auto_approve(action_requests: list) -> dict:
    for req in action_requests:
        print(f"\n[auto-approve] {req.get('name', 'unknown')}")
    return {"decisions": [{"type": "approve"} for _ in action_requests]}


def _ask_approval(action_requests: list) -> dict:
    decisions = []
    for req in action_requests:
        tool_name = req.get("name", "unknown")
        tool_args = req.get("args", {})
        description = req.get("description", "")
        print(f"\n{'─'*60}")
        print(f"[interrupt] tool: {tool_name}")
        if description:
            print(f"[interrupt] {description}")
        else:
            print(f"[interrupt] args:\n{json.dumps(tool_args, indent=2)[:800]}")
        print("\napprove / reject [reason]")
        print(f"{'─'*60}")

        raw = input("> ").strip().lower()

        if raw.startswith("reject"):
            parts = raw.split(":", 1)
            decision = {"type": "reject"}
            if len(parts) > 1:
                decision["message"] = parts[1].strip()
        else:
            decision = {"type": "approve"}

        decisions.append(decision)

    return {"decisions": decisions}


def _stream_and_collect(inputs, config) -> list:
    """Stream one pass, printing output. Returns list of Interrupt objects hit."""
    interrupts = []

    for step in graph.stream(inputs, config=config, stream_mode=["messages", "updates"]):
        mode, data = step

        if mode == "messages":
            chunk, metadata = data
            if isinstance(chunk, AIMessageChunk):
                for tc in chunk.tool_call_chunks:
                    if tc.get("name"):
                        print(f"\n[tool call] {tc['name']}", end="", flush=True)
                    if tc.get("args"):
                        print(tc["args"], end="", flush=True)
                text = _extract_text(chunk.content)
                if text and not chunk.tool_call_chunks:
                    print(text, end="", flush=True)
            elif isinstance(chunk, ToolMessage):
                node = metadata.get("langgraph_node", "")
                preview = chunk.content[:300] + ("..." if len(chunk.content) > 300 else "")
                print(f"\n[tool result:{node}] {preview}")

        elif mode == "updates":
            for update in data.values():
                # Interrupt objects come through as non-dict values
                if not isinstance(update, dict) and hasattr(update, "__iter__"):
                    for item in update:
                        if hasattr(item, "value") and "action_requests" in getattr(item, "value", {}):
                            interrupts.append(item)

    return interrupts


def run(user_input: str, *, yes: bool = False) -> None:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    inputs = {"messages": [HumanMessage(content=user_input)]}

    print(f"\n{'='*60}")
    print(f"User: {user_input}")
    print(f"{'='*60}\n")

    while True:
        interrupts = _stream_and_collect(inputs, config)

        if not interrupts:
            break

        # Key resume by interrupt ID — required when multiple interrupts fire concurrently
        handler = _auto_approve if yes else _ask_approval
        resume = {}
        for intr in interrupts:
            resume[intr.id] = handler(intr.value["action_requests"])

        inputs = Command(resume=resume)

    print(f"\n\n{'='*60}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    yes = "-y" in args or "--yes" in args
    args = [a for a in args if a not in {"-y", "--yes"}]

    user_input = " ".join(args) if args else input("Message: ").strip()
    run(user_input, yes=yes)
