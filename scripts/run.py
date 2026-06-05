"""Stream the deep agent locally and print all steps as they happen.

Usage:
    uv run scripts/run.py "your message here"
    uv run scripts/run.py  # prompts for input

When a tool requires approval (interrupt_on), you will be prompted:
    approve  — let the tool run
    reject   — block the tool (optionally add a reason: "reject: too risky")
"""

import json
import sys
import uuid

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from deep_agent.agent import create_graph

graph = create_graph(checkpointer=MemorySaver())


def _extract_text(content) -> str:
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content or ""


def _ask_approval(action_requests: list) -> dict:
    decisions = []
    for req in action_requests:
        tool_name = req.get("action", {}).get("name", "unknown")
        tool_args = req.get("action", {}).get("args", {})
        print(f"\n{'─'*60}")
        print(f"[interrupt] tool: {tool_name}")
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


def run(user_input: str) -> None:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    inputs = {"messages": [HumanMessage(content=user_input)]}

    print(f"\n{'='*60}")
    print(f"User: {user_input}")
    print(f"{'='*60}\n")

    while True:
        for chunk, metadata in graph.stream(inputs, config=config, stream_mode="messages"):
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

        # Check for pending interrupts
        state = graph.get_state(config)
        pending = [intr for task in state.tasks for intr in getattr(task, "interrupts", [])]

        if not pending:
            break

        for intr in pending:
            value = intr.value
            if isinstance(value, dict) and "action_requests" in value:
                resume_payload = _ask_approval(value["action_requests"])
                inputs = Command(resume=resume_payload)

    print(f"\n\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = input("Message: ").strip()

    run(user_input)
