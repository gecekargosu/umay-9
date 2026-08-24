"""Tests for UMAY Sentinel core module."""
import json
import tempfile
import pathlib
import os
import sys

# Add watchdog to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts" / "watchdog"))

from sentinel import (
    Severity, SentinelEvent, Incident, IncidentEngine, IncidentStatus,
    HealthScore, calculate_health_score, calculate_risk_score,
    get_system_resources, TrendTracker, SelfMonitor,
    scan_for_secrets, observe_command, format_sentinel_report,
    SentinelState, should_run_full_regression, get_relevant_tests,
)


class TestSeverity:
    def test_all_levels_exist(self):
        levels = ["INFO", "SUCCESS", "NOTICE", "WARNING", "IMPORTANT", "CRITICAL", "SECURITY"]
        for level in levels:
            assert Severity(level).value == level

    def test_numeric_ordering(self):
        assert Severity.INFO.numeric < Severity.WARNING.numeric
        assert Severity.WARNING.numeric < Severity.CRITICAL.numeric
        assert Severity.CRITICAL.numeric < Severity.SECURITY.numeric

    def test_urgent_threshold(self):
        assert not Severity.INFO.telegram_urgent
        assert not Severity.WARNING.telegram_urgent
        assert Severity.IMPORTANT.telegram_urgent
        assert Severity.CRITICAL.telegram_urgent
        assert Severity.SECURITY.telegram_urgent

    def test_icons(self):
        for s in Severity:
            assert len(s.icon) > 0


class TestSentinelEvent:
    def test_creation(self):
        ev = SentinelEvent(
            event_type="test",
            severity=Severity.WARNING,
            source="test_source",
            component="test_component",
            message="Test message",
        )
        assert ev.event_type == "test"
        assert ev.severity == Severity.WARNING
        assert ev.risk_score == 0

    def test_to_dict(self):
        ev = SentinelEvent("test", Severity.INFO, "src", "comp", "msg")
        d = ev.to_dict()
        assert d["event_type"] == "test"
        assert d["severity"] == "INFO"
        assert "timestamp" in d


class TestIncidentEngine:
    def test_create_incident(self):
        with tempfile.TemporaryDirectory() as td:
            ie = IncidentEngine(pathlib.Path(td))
            inc = ie.create_incident("Test incident", Severity.WARNING)
            assert inc.incident_id.startswith("INC-")
            assert inc.severity == Severity.WARNING
            assert inc.status == IncidentStatus.OPEN

    def test_incident_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            ie = IncidentEngine(pathlib.Path(td))
            inc = ie.create_incident("Test", Severity.CRITICAL)
            inc.resolve()
            assert inc.status == IncidentStatus.RESOLVED
            assert inc.resolved_at is not None

    def test_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            ie = IncidentEngine(pathlib.Path(td))
            ie.create_incident("API down", Severity.CRITICAL)
            assert ie.has_recent_similar("API down", hours=1)
            assert not ie.has_recent_similar("Different incident", hours=1)

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            ie = IncidentEngine(pathlib.Path(td))
            ie.create_incident("Test", Severity.WARNING)
            ie._save()
            ie2 = IncidentEngine(pathlib.Path(td))
            assert len(ie2.get_recent_incidents(1)) == 1


class TestHealthScore:
    def test_healthy(self):
        h = calculate_health_score(
            docker_healthy=True, api_healthy=True,
            regression_passed=574, regression_failed=0,
            p1_failed=0, human_use_failed=0,
            syntax_errors=0, security_issues=0,
            critical_changes=0, high_risk_changes=0,
            ram_percent=50, disk_percent=60,
        )
        assert h.overall >= 90
        assert h.level == "HEALTHY"

    def test_degraded(self):
        h = calculate_health_score(
            docker_healthy=False, api_healthy=False,
            regression_passed=400, regression_failed=174,
            p1_failed=5, human_use_failed=8,
            syntax_errors=15, security_issues=3,
            critical_changes=10, high_risk_changes=15,
            ram_percent=95, disk_percent=95,
        )
        assert h.overall < 50

    def test_ram_warning(self):
        h = calculate_health_score(
            docker_healthy=True, api_healthy=True,
            regression_passed=574, regression_failed=0,
            p1_failed=0, human_use_failed=0,
            syntax_errors=0, security_issues=0,
            critical_changes=0, high_risk_changes=0,
            ram_percent=95, disk_percent=50,
        )
        assert h.system < 100

    def test_to_dict(self):
        h = calculate_health_score()
        d = h.to_dict()
        assert "overall" in d
        assert "level" in d


class TestRiskScore:
    def test_critical_file_high_risk(self):
        score = calculate_risk_score("MODIFIED", "core/engine.py", True, 5000)
        assert score > 60

    def test_test_file_low_risk(self):
        score = calculate_risk_score("MODIFIED", "tests/test_foo.py", False, 1000)
        assert score < 30

    def test_env_high_risk(self):
        score = calculate_risk_score("MODIFIED", ".env", False, 500)
        assert score > 50

    def test_deleted_higher_than_modified(self):
        d = calculate_risk_score("DELETED", "core/engine.py", True, 5000)
        m = calculate_risk_score("MODIFIED", "core/engine.py", True, 5000)
        assert d > m


class TestResourceMonitor:
    def test_returns_data(self):
        res = get_system_resources()
        assert "ram_percent" in res
        assert "disk_percent" in res
        assert isinstance(res["ram_percent"], (int, float))


class TestTrendTracker:
    def test_record_and_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            tt = TrendTracker(pathlib.Path(td))
            for v in [50, 52, 55, 58, 62]:
                tt.record("test", v)
            bl = tt.get_baseline("test")
            assert bl is not None
            assert 50 < bl < 60

    def test_trend_rising(self):
        with tempfile.TemporaryDirectory() as td:
            tt = TrendTracker(pathlib.Path(td))
            for v in [10, 20, 30, 40, 50]:
                tt.record("metric", v)
            assert tt.get_trend("metric") == "rising"

    def test_trend_stable(self):
        with tempfile.TemporaryDirectory() as td:
            tt = TrendTracker(pathlib.Path(td))
            for v in [50, 50, 50, 50, 50]:
                tt.record("metric", v)
            assert tt.get_trend("metric") == "stable"

    def test_anomaly_detection(self):
        with tempfile.TemporaryDirectory() as td:
            tt = TrendTracker(pathlib.Path(td))
            for v in [50, 50, 50, 50, 50]:
                tt.record("metric", v)
            assert tt.check_anomaly("metric", 55.0) is False   # (55-50)/50 = 0.1 < 1.5
            assert tt.check_anomaly("metric", 130.0) is True   # (130-50)/50 = 1.6 > 1.5


class TestSelfMonitor:
    def test_record_success(self):
        with tempfile.TemporaryDirectory() as td:
            sm = SelfMonitor(pathlib.Path(td))
            sm.record_success(120.0)
            h = sm.is_healthy()
            assert h["healthy"]
            assert h["run_count"] == 1

    def test_consecutive_errors(self):
        with tempfile.TemporaryDirectory() as td:
            sm = SelfMonitor(pathlib.Path(td))
            for _ in range(5):
                sm.record_error("test error")
            h = sm.is_healthy()
            assert not h["healthy"]


class TestSecretScanner:
    def test_clean_env(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / ".env"
            p.write_text("FOO=bar\nBAZ=qux\n")
            issues = scan_for_secrets(pathlib.Path(td), [{"path": ".env"}])
            assert len(issues) == 0

    def test_detects_token(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / ".env"
            p.write_text('TOKEN="1234567890abcdef"\n')
            issues = scan_for_secrets(pathlib.Path(td), [{"path": ".env"}])
            assert len(issues) > 0

    def test_detects_private_key(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "key.pem"
            p.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIB...")
            issues = scan_for_secrets(pathlib.Path(td), [{"path": "key.pem"}])
            assert len(issues) > 0


class TestCommandObserver:
    def test_safe_command(self):
        assert observe_command("echo hello") is None
        assert observe_command("python test.py") is None

    def test_risky_commands(self):
        ev = observe_command("rm -rf /etc/passwd")
        assert ev is not None
        assert ev.severity == Severity.CRITICAL

        ev = observe_command("sudo apt install")
        assert ev is not None
        assert ev.severity == Severity.SECURITY

    def test_format(self):
        ev = observe_command("rm -rf /")
        assert ev.event_type == "risky_command"
        assert ev.risk_score > 0


class TestSmartTestRunner:
    def test_core_change_needs_full_regression(self):
        changes = [{"path": "core/engine.py", "type": "MODIFIED"}]
        assert should_run_full_regression(changes) is True

    def test_test_only_change(self):
        changes = [{"path": "tests/test_foo.py", "type": "MODIFIED"}]
        assert should_run_full_regression(changes) is False

    def test_relevant_tests(self):
        changes = [{"path": "core/intent_router.py", "type": "MODIFIED"}]
        tests = get_relevant_tests(changes)
        assert "tests/test_engineering_hardening.py" in tests


class TestSentinelState:
    def test_record_event(self):
        with tempfile.TemporaryDirectory() as td:
            ss = SentinelState(pathlib.Path(td))
            ev = SentinelEvent("test", Severity.INFO, "src", "comp", "msg")
            ss.record_event(ev)
            events = ss.get_recent_events(1)
            assert len(events) == 1

    def test_maybe_create_incident(self):
        with tempfile.TemporaryDirectory() as td:
            ss = SentinelState(pathlib.Path(td))
            ev = SentinelEvent("test", Severity.CRITICAL, "src", "comp", "Critical error")
            inc = ss.maybe_create_incident(ev)
            assert inc is not None
            assert inc.severity == Severity.CRITICAL
