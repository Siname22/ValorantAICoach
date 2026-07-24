import logging
from typing import Any

from agents.shared.context import AgentContext

logger = logging.getLogger(__name__)


def agent_started(
    agent_name: str, context: AgentContext, metadata: dict[str, Any] | None = None
) -> None:
    """Logs when an agent starts its execution."""
    log_data = {
        "event": "agent_started",
        "agent_name": agent_name,
        "request_id": context.request_id,
        "execution_id": context.execution_id,
        "metadata": metadata or {},
    }
    logger.info("Agent started: %s", agent_name, extra=log_data)


def agent_finished(
    agent_name: str,
    context: AgentContext,
    result: Any,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Logs when an agent finishes its execution successfully."""
    log_data = {
        "event": "agent_finished",
        "agent_name": agent_name,
        "request_id": context.request_id,
        "execution_id": context.execution_id,
        "result_type": str(type(result)),
        "metadata": metadata or {},
    }
    logger.info("Agent finished: %s", agent_name, extra=log_data)


def agent_failed(
    agent_name: str,
    context: AgentContext,
    error: Exception,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Logs when an agent fails during execution."""
    log_data = {
        "event": "agent_failed",
        "agent_name": agent_name,
        "request_id": context.request_id,
        "execution_id": context.execution_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "metadata": metadata or {},
    }
    logger.error(
        "Agent failed: %s - %s", agent_name, error, exc_info=True, extra=log_data
    )
