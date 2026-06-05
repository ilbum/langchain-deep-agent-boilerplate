"""Production-ready boilerplate for building Deep Agents on LangGraph.

Deep Agents follow a gather → synthesize → act loop: the orchestrator delegates
information-gathering to isolated sub-agents in parallel, synthesizes their results,
then delegates action-taking sub-agents with the synthesized output.

Key features:
- SDK-managed middleware via create_deep_agent() (todo list, filesystem, sub-agent delegation)
- Context isolation — sub-agents receive only their task, not the parent's history
- Declarative HITL — action tools declare interrupt_on; the framework handles pause/resume
- Swappable typed adapters (SearchAdapter, DocumentAdapter) swapped at assembly time
"""
