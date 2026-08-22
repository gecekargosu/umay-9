"""UMAY Multi-Agent Orchestrator.

Manages sub-agents with controlled permissions, tool access, and timeouts.
Main agent delegates tasks to specialist sub-agents and validates results.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any

from core.utils.logger import log


class AgentRole(str, Enum):
    WEB = "web_researcher"
    GMAIL = "gmail_agent"
    TELEGRAM = "telegram_agent"
    BROWSER = "browser_agent"
    CODE = "code_agent"
    DOCUMENT = "document_agent"
    GENERAL = "general_agent"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


@dataclass
class AgentConfig:
    """Configuration for a sub-agent."""
    role: AgentRole
    allowed_tools: list[str] = field(default_factory=list)
    timeout_seconds: int = 120
    requires_approval: bool = False
    max_retries: int = 2
    description: str = ""


@dataclass
class AgentTask:
    """A task assigned to a sub-agent."""
    task_id: str
    description: str
    role: AgentRole
    params: dict = field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    retries: int = 0


# Default agent configurations
AGENT_CONFIGS: dict[AgentRole, AgentConfig] = {
    AgentRole.WEB: AgentConfig(
        role=AgentRole.WEB,
        allowed_tools=["web_search", "browser_open", "browser_read", "research_topic", "quick_research"],
        timeout_seconds=180,
        description="Web araştırması ve site analizi",
    ),
    AgentRole.GMAIL: AgentConfig(
        role=AgentRole.GMAIL,
        allowed_tools=["gmail_list_emails", "gmail_search", "gmail_get_email", "gmail_summarize"],
        timeout_seconds=60,
        requires_approval=False,
        description="E-posta okuma ve analiz",
    ),
    AgentRole.BROWSER: AgentConfig(
        role=AgentRole.BROWSER,
        allowed_tools=["browser_open", "browser_read", "browser_click", "browser_type", "browser_screenshot"],
        timeout_seconds=120,
        description="Tarayıcı otomasyonu",
    ),
    AgentRole.CODE: AgentConfig(
        role=AgentRole.CODE,
        allowed_tools=["read_code", "generate_code", "find_bugs", "write_test", "run_code_tests"],
        timeout_seconds=120,
        description="Kod analiz ve üretimi",
    ),
    AgentRole.DOCUMENT: AgentConfig(
        role=AgentRole.DOCUMENT,
        allowed_tools=["read_document", "scan_directory", "search_in_documents"],
        timeout_seconds=60,
        description="Belge okuma ve analiz",
    ),
    AgentRole.GENERAL: AgentConfig(
        role=AgentRole.GENERAL,
        allowed_tools=["list_directory", "read_file", "search_files", "get_system_info"],
        timeout_seconds=60,
        description="Genel görevler",
    ),
}


class SubAgent:
    """A specialist sub-agent."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus.IDLE
        self.current_task: AgentTask | None = None

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if this agent is allowed to use a specific tool."""
        if not self.config.allowed_tools:
            return True  # No restriction
        return tool_name in self.config.allowed_tools

    def execute(self, task: AgentTask) -> AgentTask:
        """Execute a task. Returns the updated task with result."""
        task.status = AgentStatus.RUNNING
        task.started_at = time.time()
        self.current_task = task
        self.status = AgentStatus.RUNNING

        log(f"[ORCHESTRATOR] {self.config.role.value} executing: {task.description[:60]}")

        try:
            # Delegate to the appropriate handler based on role
            result = self._dispatch(task)
            task.result = result
            task.status = AgentStatus.COMPLETED
            self.status = AgentStatus.COMPLETED
        except TimeoutError:
            task.status = AgentStatus.TIMEOUT
            task.error = f"Timeout after {self.config.timeout_seconds}s"
            self.status = AgentStatus.TIMEOUT
            log(f"[ORCHESTRATOR] {self.config.role.value} TIMEOUT")
        except Exception as exc:
            task.status = AgentStatus.FAILED
            task.error = str(exc)
            self.status = AgentStatus.FAILED
            log(f"[ORCHESTRATOR] {self.config.role.value} FAILED: {exc}")
        finally:
            task.completed_at = time.time()
            self.current_task = None

        return task

    def _dispatch(self, task: AgentTask) -> Any:
        """Dispatch task to the appropriate handler."""
        from core.engine import ask as llm_ask

        if self.config.role == AgentRole.WEB:
            return self._handle_web(task)
        elif self.config.role == AgentRole.GMAIL:
            return self._handle_gmail(task)
        elif self.config.role == AgentRole.BROWSER:
            return self._handle_browser(task)
        elif self.config.role == AgentRole.CODE:
            return self._handle_code(task)
        elif self.config.role == AgentRole.DOCUMENT:
            return self._handle_document(task)
        else:
            return self._handle_general(task)

    def _handle_web(self, task: AgentTask) -> dict:
        from core.web_research import quick_research
        query = task.params.get("query", task.description)
        return quick_research(query)

    def _handle_gmail(self, task: AgentTask) -> dict:
        from core.gmail_agent import gmail_list_emails
        query = task.params.get("query", "")
        return gmail_list_emails(query)

    def _handle_browser(self, task: AgentTask) -> dict:
        from agents.browser_agent import BrowserAgent
        url = task.params.get("url", "")
        agent = BrowserAgent(gorunur=False)
        try:
            agent.baslat()
            agent.git(url)
            return {"url": url, "status": "navigated", "title": agent.sayfa_baslik()}
        finally:
            agent.kapat()

    def _handle_code(self, task: AgentTask) -> dict:
        from core.code_agent import analyze_project
        path = task.params.get("path", ".")
        return analyze_project(path)

    def _handle_document(self, task: AgentTask) -> dict:
        from core.document_reader import read_document
        path = task.params.get("path", "")
        return read_document(path)

    def _handle_general(self, task: AgentTask) -> dict:
        from core.engine import ask as llm_ask
        return {"response": llm_ask(task.description)}


class Orchestrator:
    """Multi-agent orchestrator that manages sub-agents."""

    def __init__(self):
        self._agents: dict[AgentRole, SubAgent] = {}
        self._task_counter = 0
        for role, config in AGENT_CONFIGS.items():
            self._agents[role] = SubAgent(config)

    def _next_task_id(self) -> str:
        self._task_counter += 1
        return f"task-{self._task_counter:04d}"

    def create_task(self, description: str, role: AgentRole, params: dict | None = None) -> AgentTask:
        """Create a new task."""
        task_id = self._next_task_id()
        return AgentTask(
            task_id=task_id,
            description=description,
            role=role,
            params=params or {},
        )

    def execute_task(self, task: AgentTask) -> AgentTask:
        """Execute a task using the appropriate sub-agent."""
        agent = self._agents.get(task.role)
        if not agent:
            task.status = AgentStatus.FAILED
            task.error = f"No agent for role: {task.role}"
            return task
        return agent.execute(task)

    def execute_simple(self, description: str, role: AgentRole = AgentRole.GENERAL, params: dict | None = None) -> dict:
        """Create and execute a task in one step. Returns result dict."""
        task = self.create_task(description, role, params)
        task = self.execute_task(task)
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
        }

    def get_status(self) -> dict:
        """Get orchestrator status."""
        agents_status = {}
        for role, agent in self._agents.items():
            agents_status[role.value] = {
                "status": agent.status.value,
                "allowed_tools": agent.config.allowed_tools,
                "timeout": agent.config.timeout_seconds,
                "description": agent.config.description,
            }
        return {
            "agents": agents_status,
            "total_tasks": self._task_counter,
        }


# Global singleton
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
