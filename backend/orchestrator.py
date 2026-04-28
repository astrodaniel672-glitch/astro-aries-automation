from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AgentTask:
    name: str
    description: str
    required_env: tuple[str, ...]


class OrchestratorAgent:
    """Coordinates automation agents without storing secrets in code.

    This class is intentionally small: it provides a central registry for the
    agents/modules that will be connected later, while secrets stay in runtime
    environment variables or managed secret stores.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self._tasks: dict[str, AgentTask] = {}

    def register(
        self,
        task: AgentTask,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._tasks[task.name] = task
        self._handlers[task.name] = handler

    def list_tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "name": task.name,
                "description": task.description,
                "required_env": list(task.required_env),
            }
            for task in self._tasks.values()
        ]

    def run(self, task_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        handler = self._handlers.get(task_name)
        if handler is None:
            return {
                "success": False,
                "message": f"Unknown task: {task_name}",
            }

        return handler(payload)


def create_default_orchestrator() -> OrchestratorAgent:
    orchestrator = OrchestratorAgent()

    orchestrator.register(
        AgentTask(
            name="orders.create",
            description="Create an order in the existing Supabase orders table.",
            required_env=("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"),
        ),
        lambda payload: {
            "success": False,
            "message": "orders.create is handled by backend.app /orders endpoint.",
            "payload_preview": payload,
        },
    )

    orchestrator.register(
        AgentTask(
            name="instagram.comment_reply",
            description="Prepare or send Instagram/Facebook comment replies via Meta integration.",
            required_env=("META_PAGE_TOKEN", "META_APP_SECRET"),
        ),
        lambda payload: {
            "success": False,
            "message": "instagram.comment_reply is not enabled yet. Add Meta handler before activation.",
            "payload_preview": payload,
        },
    )

    orchestrator.register(
        AgentTask(
            name="email.send",
            description="Prepare or send client emails through Gmail/App Password or another mail provider.",
            required_env=("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"),
        ),
        lambda payload: {
            "success": False,
            "message": "email.send is not enabled yet. Add mail handler before activation.",
            "payload_preview": payload,
        },
    )

    return orchestrator
