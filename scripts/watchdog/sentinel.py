"""
UMAY SENTINEL — Core Engine
=============================
KÖPEK'in beyin merkezi.

Modüller:
- Severity (sınflandırma)
- Event (olay modeli)
- Incident Engine (korelasyon + lifecycle)
- Health Score (genel sağlık puanı)
- Resource Monitor (CPU/RAM/Disk)
- Trend Tracker (baseline + trend)
- Smart Test Runner (değişiklik bazlı test)
- Self Monitor (kendi sağlığını izleme)

Watchdog KENDİ BAŞINA KOD DEĞİŞTİRMEZ.
Gözle → Analiz Et → Sınıflandır → Raporla.
"""

import json
import os
import platform
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ─── Severity System ─────────────────────────────────────────

class Severity(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    IMPORTANT = "IMPORTANT"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"

    @property
    def numeric(self) -> int:
        return {
            "INFO": 0, "SUCCESS": 1, "NOTICE": 2,
            "WARNING": 3, "IMPORTANT": 4, "CRITICAL": 5, "SECURITY": 6,
        }[self.value]

    @property
    def icon(self) -> str:
        return {
            "INFO": "ℹ️", "SUCCESS": "✅", "NOTICE": "📋",
            "WARNING": "⚠️", "IMPORTANT": "❗", "CRITICAL": "🔴", "SECURITY": "🛡️",
        }[self.value]

    @property
    def telegram_urgent(self) -> bool:
        """Should this severity trigger immediate Telegram alert?"""
        return self.numeric >= Severity.IMPORTANT.numeric


# ─── Event Model ─────────────────────────────────────────────

@dataclass
class SentinelEvent:
    event_type: str          # e.g., "file_changed", "test_failed", "api_down"
    severity: Severity
    source: str              # e.g., "file_monitor", "test_runner", "api_health"
    component: str           # e.g., "core/intent_router.py", "docker"
    message: str
    details: dict = field(default_factory=dict)
    risk_score: int = 0      # 0-100
    correlation_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


# ─── Incident Engine ─────────────────────────────────────────

class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: Severity
    status: IncidentStatus = IncidentStatus.OPEN
    events: list = field(default_factory=list)
    related_changes: list = field(default_factory=list)
    risk_score: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None

    def add_event(self, event: SentinelEvent):
        self.events.append(event.to_dict())
        self.updated_at = datetime.now().isoformat()
        # Update risk score to max of all events
        self.risk_score = max(self.risk_score, event.risk_score)

    def resolve(self):
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "severity": self.severity.value,
            "status": self.status.value,
            "events": self.events,
            "related_changes": self.related_changes,
            "risk_score": self.risk_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }


class IncidentEngine:
    """Manages incidents — creation, correlation, lifecycle."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_file = state_dir / "incidents.json"
        self._incidents: dict[str, Incident] = {}
        self._counter = 0
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for inc_data in data.get("incidents", []):
                    inc = Incident(
                        incident_id=inc_data["incident_id"],
                        title=inc_data["title"],
                        severity=Severity(inc_data["severity"]),
                        status=IncidentStatus(inc_data.get("status", "OPEN")),
                        events=inc_data.get("events", []),
                        related_changes=inc_data.get("related_changes", []),
                        risk_score=inc_data.get("risk_score", 0),
                        created_at=inc_data.get("created_at", ""),
                        updated_at=inc_data.get("updated_at", ""),
                        resolved_at=inc_data.get("resolved_at"),
                    )
                    self._incidents[inc.incident_id] = inc
                self._counter = data.get("counter", 0)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "counter": self._counter,
            "incidents": [inc.to_dict() for inc in self._incidents.values()],
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_incident(self, title: str, severity: Severity,
                        related_changes: list = None) -> Incident:
        """Create a new incident."""
        self._counter += 1
        inc_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{self._counter:03d}"
        inc = Incident(
            incident_id=inc_id,
            title=title,
            severity=severity,
            related_changes=related_changes or [],
        )
        self._incidents[inc_id] = inc
        self._save()
        return inc

    def get_open_incidents(self) -> list[Incident]:
        return [inc for inc in self._incidents.values()
                if inc.status in (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)]

    def get_recent_incidents(self, hours: int = 24) -> list[Incident]:
        cutoff = datetime.now().timestamp() - hours * 3600
        result = []
        for inc in self._incidents.values():
            try:
                created = datetime.fromisoformat(inc.created_at).timestamp()
                if created >= cutoff:
                    result.append(inc)
            except (ValueError, TypeError):
                continue
        return result

    def has_recent_similar(self, title: str, hours: int = 2) -> bool:
        """Check if a similar incident was recently created (dedup)."""
        recent = self.get_recent_incidents(hours)
        return any(title.lower() in inc.title.lower() for inc in recent)


# ─── Health Score ─────────────────────────────────────────────

@dataclass
class HealthScore:
    overall: int = 100
    system: int = 100
    application: int = 100
    tests: int = 100
    security: int = 100
    files: int = 100

    @property
    def level(self) -> str:
        if self.overall >= 90:
            return "HEALTHY"
        elif self.overall >= 75:
            return "WARNING"
        elif self.overall >= 50:
            return "DEGRADED"
        elif self.overall >= 25:
            return "CRITICAL"
        else:
            return "EMERGENCY"

    @property
    def icon(self) -> str:
        return {
            "HEALTHY": "🟢", "WARNING": "🟡", "DEGRADED": "🟠",
            "CRITICAL": "🔴", "EMERGENCY": "🚨",
        }[self.level]

    def to_dict(self) -> dict:
        return asdict(self) | {"level": self.level}


def calculate_health_score(
    docker_healthy: bool = True,
    api_healthy: bool = True,
    regression_passed: int = 0,
    regression_failed: int = 0,
    p1_failed: int = 0,
    human_use_failed: int = 0,
    syntax_errors: int = 0,
    security_issues: int = 0,
    critical_changes: int = 0,
    high_risk_changes: int = 0,
    ram_percent: float = 0,
    disk_percent: float = 0,
) -> HealthScore:
    """Calculate health score 0-100 based on multiple factors."""

    # System score (0-100)
    system = 100
    if ram_percent > 90:
        system -= 30
    elif ram_percent > 80:
        system -= 15
    elif ram_percent > 70:
        system -= 5
    if disk_percent > 90:
        system -= 20
    elif disk_percent > 80:
        system -= 10
    if not docker_healthy:
        system -= 25
    system = max(0, system)

    # Application score
    application = 100
    if not api_healthy:
        application -= 30
    if not docker_healthy:
        application -= 20
    if syntax_errors > 5:
        application -= 20
    elif syntax_errors > 0:
        application -= 5
    application = max(0, application)

    # Test score
    test_total = regression_passed + regression_failed
    if test_total > 0:
        pass_rate = regression_passed / test_total
        tests = int(pass_rate * 100)
    else:
        tests = 100
    if p1_failed > 0:
        tests = min(tests, 50)  # P1 failures cap at 50
    if human_use_failed > 0:
        tests = min(tests, 70)
    tests = max(0, tests)

    # Security score
    security = 100
    if security_issues > 0:
        security = max(0, 100 - security_issues * 25)
    security = max(0, security)

    # File change risk
    files = 100
    if critical_changes > 3:
        files -= 30
    elif critical_changes > 0:
        files -= 15
    if high_risk_changes > 5:
        files -= 20
    elif high_risk_changes > 0:
        files -= 10
    files = max(0, files)

    # Overall = weighted average
    overall = int(
        system * 0.20 +
        application * 0.25 +
        tests * 0.30 +
        security * 0.15 +
        files * 0.10
    )
    overall = max(0, min(100, overall))

    return HealthScore(
        overall=overall,
        system=system,
        application=application,
        tests=tests,
        security=security,
        files=files,
    )


# ─── Resource Monitor ────────────────────────────────────────

def get_system_resources() -> dict:
    """Get CPU, RAM, Disk usage. Cross-platform."""
    resources = {
        "cpu_percent": 0,
        "ram_percent": 0,
        "ram_used_gb": 0,
        "ram_total_gb": 0,
        "disk_percent": 0,
        "disk_used_gb": 0,
        "disk_total_gb": 0,
        "platform": platform.system(),
    }

    # Try psutil first
    try:
        import psutil
        resources["cpu_percent"] = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        resources["ram_percent"] = round(ram.percent, 1)
        resources["ram_used_gb"] = round(ram.used / (1024**3), 1)
        resources["ram_total_gb"] = round(ram.total / (1024**3), 1)
        disk = psutil.disk_usage("/")
        resources["disk_percent"] = round(disk.percent, 1)
        resources["disk_used_gb"] = round(disk.used / (1024**3), 1)
        resources["disk_total_gb"] = round(disk.total / (1024**3), 1)
        return resources
    except ImportError:
        pass

    # Fallback: platform-specific commands
    try:
        if platform.system() == "Windows":
            # RAM
            out = subprocess.run(
                "wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:csv",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            for line in out.stdout.strip().split("\n"):
                parts = line.strip().split(",")
                if len(parts) >= 3 and parts[1].isdigit():
                    total_kb = int(parts[1])
                    free_kb = int(parts[2])
                    used_kb = total_kb - free_kb
                    resources["ram_total_gb"] = round(total_kb / (1024**2), 1)
                    resources["ram_used_gb"] = round(used_kb / (1024**2), 1)
                    resources["ram_percent"] = round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0
                    break
            # Disk
            out = subprocess.run(
                "wmic logicaldisk get Size,FreeSpace,DeviceID /format:csv",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            for line in out.stdout.strip().split("\n"):
                parts = line.strip().split(",")
                if len(parts) >= 4 and parts[2].isdigit():
                    total = int(parts[2])
                    free = int(parts[3])
                    used = total - free
                    resources["disk_total_gb"] = round(total / (1024**3), 1)
                    resources["disk_used_gb"] = round(used / (1024**3), 1)
                    resources["disk_percent"] = round((used / total) * 100, 1) if total > 0 else 0
                    break
        elif platform.system() == "Linux":
            out = subprocess.run("free -b", shell=True, capture_output=True, text=True, timeout=5)
            for line in out.stdout.split("\n"):
                if line.startswith("Mem:"):
                    parts = line.split()
                    total = int(parts[1])
                    used = int(parts[2])
                    resources["ram_total_gb"] = round(total / (1024**3), 1)
                    resources["ram_used_gb"] = round(used / (1024**3), 1)
                    resources["ram_percent"] = round((used / total) * 100, 1) if total > 0 else 0
                    break
            out = subprocess.run("df -B1 /", shell=True, capture_output=True, text=True, timeout=5)
            for line in out.stdout.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    total = int(parts[1])
                    used = int(parts[2])
                    resources["disk_total_gb"] = round(total / (1024**3), 1)
                    resources["disk_used_gb"] = round(used / (1024**3), 1)
                    resources["disk_percent"] = round((used / total) * 100, 1) if total > 0 else 0
                    break
    except Exception:
        pass

    return resources


# ─── Trend Tracker ───────────────────────────────────────────

class TrendTracker:
    """Tracks baselines and trends for key metrics."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_file = state_dir / "trends.json"
        self._data: dict[str, list] = {}
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def record(self, metric: str, value: Any):
        """Record a metric value with timestamp."""
        if metric not in self._data:
            self._data[metric] = []
        self._data[metric].append({
            "value": value,
            "ts": datetime.now().isoformat(),
        })
        # Keep last 200 entries per metric
        self._data[metric] = self._data[metric][-200:]
        self._save()

    def get_baseline(self, metric: str, window: int = 10) -> Optional[float]:
        """Get baseline (average of last N values)."""
        entries = self._data.get(metric, [])
        if len(entries) < 2:
            return None
        recent = entries[-window:]
        values = [e["value"] for e in recent if isinstance(e["value"], (int, float))]
        return sum(values) / len(values) if values else None

    def get_trend(self, metric: str) -> str:
        """Get trend direction: rising, falling, stable."""
        entries = self._data.get(metric, [])
        if len(entries) < 3:
            return "insufficient_data"
        recent = entries[-5:]
        values = [e["value"] for e in recent if isinstance(e["value"], (int, float))]
        if len(values) < 3:
            return "insufficient_data"
        # Simple linear trend
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        avg_diff = sum(diffs) / len(diffs)
        if avg_diff > 2:
            return "rising"
        elif avg_diff < -2:
            return "falling"
        return "stable"

    def check_anomaly(self, metric: str, current_value: float, threshold: float = 1.5) -> bool:
        """Check if current value is anomalous compared to baseline."""
        baseline = self.get_baseline(metric)
        if baseline is None or baseline == 0:
            return False
        return abs(current_value - baseline) / baseline > threshold


# ─── Smart Test Runner ──────────────────────────────────────

def should_run_full_regression(changed_files: list[dict]) -> bool:
    """Decide if full regression is needed based on changes."""
    # Always run full regression if core files changed
    core_files = {
        "core/agent.py", "core/agent_tools.py", "core/engine.py",
        "core/intent_router.py", "core/model_providers.py",
        "ui/panel_server.py",
    }
    for change in changed_files:
        path = change.get("path", "")
        if path in core_files:
            return True
        # Config changes need Docker rebuild check
        if path in ("Dockerfile", "docker-compose.yml", "requirements.txt"):
            return True
    return False


def get_relevant_tests(changed_files: list[dict]) -> list[str]:
    """Get list of relevant test files based on changes."""
    test_map = {
        "core/intent_router.py": ["tests/test_engineering_hardening.py"],
        "core/agent_tools.py": ["tests/test_agent_tools.py", "tests/test_safety_and_audit.py"],
        "core/engine.py": ["tests/test_engineering_hardening.py"],
        "core/conversation_store.py": ["tests/test_conversation_store.py"],
        "core/approval_manager.py": ["tests/test_approval.py"],
        "core/failure_recovery.py": ["tests/test_failure_recovery.py"],
        "core/document_reader.py": ["tests/test_document_reader.py"],
    }
    tests = set()
    for change in changed_files:
        path = change.get("path", "")
        if path in test_map:
            tests.update(test_map[path])
    return sorted(tests)


# ─── Self Monitor ────────────────────────────────────────────

class SelfMonitor:
    """Monitors the watchdog's own health."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_file = state_dir / "self_monitor.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "last_successful_run": None,
            "last_run_duration": 0,
            "last_error": None,
            "run_count": 0,
            "error_count": 0,
            "consecutive_errors": 0,
        }

    def _save(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def record_success(self, duration: float):
        self._data["last_successful_run"] = datetime.now().isoformat()
        self._data["last_run_duration"] = round(duration, 1)
        self._data["last_error"] = None
        self._data["run_count"] = self._data.get("run_count", 0) + 1
        self._data["consecutive_errors"] = 0
        self._save()

    def record_error(self, error: str):
        self._data["last_error"] = error
        self._data["error_count"] = self._data.get("error_count", 0) + 1
        self._data["consecutive_errors"] = self._data.get("consecutive_errors", 0) + 1
        self._save()

    def is_healthy(self, expected_interval_minutes: int = 20) -> dict:
        """Check if watchdog itself is healthy."""
        result = {"healthy": True, "warnings": []}

        last_run = self._data.get("last_successful_run")
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run)
                minutes_ago = (datetime.now() - last_dt).total_seconds() / 60
                if minutes_ago > expected_interval_minutes * 3:
                    result["healthy"] = False
                    result["warnings"].append(
                        f"Last successful run was {int(minutes_ago)} min ago "
                        f"(expected every {expected_interval_minutes} min)"
                    )
            except (ValueError, TypeError):
                pass
        else:
            result["warnings"].append("No successful run recorded yet")

        consecutive = self._data.get("consecutive_errors", 0)
        if consecutive >= 3:
            result["healthy"] = False
            result["warnings"].append(f"{consecutive} consecutive errors")

        result["run_count"] = self._data.get("run_count", 0)
        result["error_count"] = self._data.get("error_count", 0)
        return result

    def to_dict(self) -> dict:
        return self._data.copy()


# ─── Risk Score Calculator ───────────────────────────────────

def calculate_risk_score(change_type: str, path: str, is_critical: bool, size: int = 0) -> int:
    """Calculate risk score 0-100 for a file change."""
    score = 0
    if change_type == "NEW":
        score += 10
    elif change_type == "DELETED":
        score += 30
    elif change_type == "MODIFIED":
        score += 15
    if is_critical:
        score += 40
    if path.startswith("core/") and path.endswith(".py"):
        score += 25
    elif path.startswith("ui/"):
        score += 15
    elif path.startswith("agents/"):
        score += 20
    elif path in ("Dockerfile", "docker-compose.yml", "requirements.txt"):
        score += 20
    elif "test" in path.lower():
        score += 5
    elif path.endswith(".md"):
        score += 2
    elif path.endswith(".json"):
        score += 5
    elif path.endswith(".env"):
        score += 50
    if size > 100000:
        score += 15
    elif size > 50000:
        score += 5
    return min(100, score)


# ─── Secret Scanner ──────────────────────────────────────────

def scan_for_secrets(project_dir: Path, changed_files: list[dict] = None) -> list[dict]:
    """Scan files for potential secrets. Never logs actual values."""
    issues = []
    patterns = [
        (r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]([^'\"]{10,})", "API key"),
        (r"(?:token|secret|password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{10,})", "Token/Password"),
        (r"(?:private[_-]?key)\s*[=:]\s*['\"]([^'\"]{10,})", "Private key"),
        (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "Private key block"),
        (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
        (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style API key"),
    ]

    files_to_scan = []
    if changed_files:
        files_to_scan = [project_dir / c["path"] for c in changed_files
                         if (project_dir / c["path"]).exists()]
    else:
        # Scan key config files
        for name in [".env", ".env.local", ".env.production"]:
            p = project_dir / name
            if p.exists():
                files_to_scan.append(p)

    for filepath in files_to_scan:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            for line_num, line in enumerate(content.split("\n"), 1):
                if line.strip().startswith("#"):
                    continue
                for pattern, description in patterns:
                    if __import__("re").search(pattern, line, __import__("re").IGNORECASE):
                        issues.append({
                            "file": str(filepath.relative_to(project_dir)),
                            "line": line_num,
                            "type": description,
                            "severity": "SECURITY",
                        })
        except (OSError, PermissionError):
            continue

    return issues


# ─── Command Observer ────────────────────────────────────────

RISKY_COMMAND_PATTERNS = [
    (r"\bformat\b", "Disk format", "CRITICAL"),
    (r"\bdel\s+/[sq]\b", "Force delete", "CRITICAL"),
    (r"\brd\s+/[sq]\b", "Force remove dir", "CRITICAL"),
    (r"\brm\s+-rf\s+/", "Recursive delete root", "CRITICAL"),
    (r"\bsudo\b", "Privilege escalation", "SECURITY"),
    (r"\bchmod\s+777\b", "Overly permissive", "SECURITY"),
    (r"\bshutdown\b", "System shutdown", "CRITICAL"),
    (r"\bcurl\b.*\b-d\b", "Data upload via curl", "WARNING"),
    (r"\bwget\b", "Download", "NOTICE"),
    (r"\bencoded.*command\b", "Encoded command", "SECURITY"),
]


def observe_command(command: str, source: str = "umay_tool") -> Optional[SentinelEvent]:
    """Observe a command and create an event if risky."""
    for pattern, description, severity_str in RISKY_COMMAND_PATTERNS:
        if __import__("re").search(pattern, command, __import__("re").IGNORECASE):
            return SentinelEvent(
                event_type="risky_command",
                severity=Severity(severity_str),
                source=source,
                component="run_command",
                message=f"Risky command detected: {description}",
                details={"command": command[:200], "risk_type": description},
                risk_score=80 if severity_str == "CRITICAL" else 60 if severity_str == "SECURITY" else 30,
            )
    return None


# ─── Format Telegram Message ──────────────────────────────────

def format_sentinel_report(
    health: HealthScore,
    resources: dict,
    events: list[SentinelEvent],
    incidents: list[Incident],
    changes: list[dict],
    regression: dict,
    p1: dict,
    human_use: dict,
    security_issues: list[dict],
    syntax_result: dict,
    self_health: dict,
    duration: float,
    timestamp: str,
) -> str:
    """Format a comprehensive sentinel report for Telegram."""
    lines = []

    # Header
    lines.append("🤖 <b>UMAY SENTINEL</b>")
    lines.append(f"⏱ {timestamp[:16].replace('T', ' ')}")
    lines.append("")

    # Health Score
    lines.append(f"{health.icon} <b>SAĞLIK: {health.overall}/100 ({health.level})</b>")
    lines.append(f"  Sistem: {health.system} | Uygulama: {health.application}")
    lines.append(f"  Testler: {health.tests} | Güvenlik: {health.security} | Dosyalar: {health.files}")
    lines.append("")

    # Resources
    ram_icon = "🔴" if resources.get("ram_percent", 0) > 90 else "🟡" if resources.get("ram_percent", 0) > 80 else "🟢"
    lines.append(f"💻 <b>Sistem:</b> RAM {resources.get('ram_percent', '?')}% {ram_icon}"
                 f" | Disk {resources.get('disk_percent', '?')}%"
                 f" | CPU {resources.get('cpu_percent', '?')}%")
    lines.append("")

    # Changes
    if changes:
        new_c = sum(1 for c in changes if c.get("type") == "NEW")
        mod_c = sum(1 for c in changes if c.get("type") == "MODIFIED")
        del_c = sum(1 for c in changes if c.get("type") == "DELETED")
        lines.append(f"📝 <b>Değişiklikler:</b> +{new_c} ~{mod_c} -{del_c}")
        for c in changes[:5]:
            icon = {"NEW": "🆕", "MODIFIED": "✏️", "DELETED": "🗑️"}.get(c.get("type", ""), "📄")
            risk = c.get("risk_score", 0)
            risk_icon = "🔴" if risk > 60 else "🟡" if risk > 30 else "🟢"
            lines.append(f"  {icon} {c.get('path', '?')} (risk: {risk}) {risk_icon}")
        if len(changes) > 5:
            lines.append(f"  ... +{len(changes)-5} more")
        lines.append("")

    # Regression
    reg_pass = regression.get("passed", 0)
    reg_fail = regression.get("failed", 0)
    lines.append(f"🧪 <b>Regression:</b> {reg_pass} PASS, {reg_fail} FAIL")
    if reg_fail > 0:
        lines.append(f"  ⚠️ REGRESSION DETECTED")
    lines.append("")

    # P1
    p1_fails = [name for name, data in p1.items()
                if isinstance(data, dict) and data.get("fail", 0) > 0]
    if p1_fails:
        lines.append(f"🚨 <b>P1 REGRESSION:</b> {', '.join(p1_fails)}")
    else:
        lines.append("✅ <b>P1:</b> All PASS")
    lines.append("")

    # Human Use
    hu_pass = human_use.get("pass", 0)
    hu_total = human_use.get("total", 0)
    lines.append(f"👤 <b>Human Use:</b> {hu_pass}/{hu_total} PASS")
    lines.append("")

    # Security
    if security_issues:
        lines.append(f"🛡️ <b>Güvenlik:</b> ⚠️ {len(security_issues)} issue")
        for issue in security_issues[:3]:
            if isinstance(issue, dict):
                lines.append(f"  • {issue.get('type', '?')} — {issue.get('file', '?')}:{issue.get('line', '?')}")
            else:
                lines.append(f"  • {issue}")
    else:
        lines.append("🛡️ <b>Güvenlik:</b> ✅ Temiz")
    lines.append("")

    # Incidents
    open_inc = [inc for inc in incidents if inc.status.value in ("OPEN", "INVESTIGATING")]
    if open_inc:
        lines.append(f"🚨 <b>Açık Olaylar:</b> {len(open_inc)}")
        for inc in open_inc[:3]:
            lines.append(f"  • {inc.incident_id}: {inc.title}")
        lines.append("")

    # Self-monitoring
    if not self_health.get("healthy", True):
        lines.append("🔧 <b>Sentinel Uyarısı:</b>")
        for w in self_health.get("warnings", []):
            lines.append(f"  ⚠️ {w}")
        lines.append("")

    # Syntax
    syn_errors = syntax_result.get("errors", [])
    if syn_errors:
        lines.append(f"🐍 <b>Syntax:</b> ❌ {len(syn_errors)} hata")
    else:
        lines.append(f"🐍 <b>Syntax:</b> ✅ {syntax_result.get('total', 0)} dosya OK")

    lines.append("")
    lines.append(f"📊 <i>{duration:.0f}s</i>")

    return "\n".join(lines)


# ─── Sentinel State ──────────────────────────────────────────

class SentinelState:
    """Manages all sentinel state: events, incidents, trends, self-monitor."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.incidents = IncidentEngine(state_dir)
        self.trends = TrendTracker(state_dir)
        self.self_monitor = SelfMonitor(state_dir)
        self._events_file = state_dir / "events.jsonl"
        self._recent_events: list[dict] = []

    def record_event(self, event: SentinelEvent):
        """Record an event to log and memory."""
        self._recent_events.append(event.to_dict())
        # Append to JSONL log
        try:
            with open(self._events_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except OSError:
            pass

    def get_recent_events(self, hours: int = 1) -> list[dict]:
        """Get events from last N hours."""
        cutoff = datetime.now().timestamp() - hours * 3600
        result = []
        try:
            if self._events_file.exists():
                with open(self._events_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            ts = event.get("timestamp", "")
                            if ts:
                                event_time = datetime.fromisoformat(ts).timestamp()
                                if event_time >= cutoff:
                                    result.append(event)
                        except (json.JSONDecodeError, ValueError):
                            continue
        except OSError:
            pass
        return result

    def maybe_create_incident(self, event: SentinelEvent) -> Optional[Incident]:
        """Create incident if severity warrants it and not duplicate."""
        if event.severity.numeric < Severity.WARNING.numeric:
            return None

        title = f"{event.severity.value}: {event.message}"
        if self.incidents.has_recent_similar(title, hours=1):
            # Add to existing incident instead
            open_incidents = self.incidents.get_open_incidents()
            for inc in open_incidents:
                if event.severity.value.lower() in inc.title.lower():
                    inc.add_event(event)
                    self.incidents._save()
                    return inc
            return None

        inc = self.incidents.create_incident(
            title=title,
            severity=event.severity,
            related_changes=event.details.get("related_changes", []),
        )
        inc.add_event(event)
        self.incidents._save()
        return inc
