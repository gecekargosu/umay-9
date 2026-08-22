"""
UMAY Approval Core Infrastructure Tests
Unit, integration, and cross-module tests for WAITING_FOR_APPROVAL flow.
"""
from __future__ import annotations

import json
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─── ApprovalManager Unit Tests ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_approval(tmp_path):
    """Her testi izole edilmiş ApprovalManager ile çalıştır."""
    from core import approval_manager
    import core.approval_manager as am_mod
    # Her test için geçici JSONL kullan
    test_log = tmp_path / "approvals.jsonl"
    original_log = am_mod.APPROVAL_LOG
    am_mod.APPROVAL_LOG = test_log
    # Singleton'ı sıfırla
    am_mod._manager = None
    yield
    am_mod.APPROVAL_LOG = original_log
    am_mod._manager = None


class TestApprovalManager:
    """ApprovalManager temel fonksiyon testleri."""

    def test_create_approval(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(
            task_id="task-test-001",
            tool_name="write_file",
            action="Dosya oluşturulacak: test.txt",
            target="test.txt",
            risk="medium",
        )
        assert apr.id.startswith("appr-")
        assert apr.task_id == "task-test-001"
        assert apr.tool_name == "write_file"
        assert apr.status == "PENDING"
        assert apr.risk == "medium"

    def test_approve(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(
            task_id="task-test-002",
            tool_name="run_command",
            action="Komut çalıştırılacak",
            risk="high",
        )
        result = am.approve(apr.id, responded_by="web:panel")
        assert result is not None
        assert result.status == "APPROVED"
        assert result.responded_by == "web:panel"
        assert result.responded_at is not None

    def test_reject(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(
            task_id="task-test-003",
            tool_name="gmail_send_email",
            action="E-posta gönderilecek",
            risk="high",
        )
        result = am.reject(apr.id, responded_by="telegram:cengiz", message="İstemiyorum")
        assert result is not None
        assert result.status == "REJECTED"
        assert result.response_message == "İstemiyorum"

    def test_cancel(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(
            task_id="task-test-004",
            tool_name="write_file",
            action="Dosya değiştirilecek",
            risk="medium",
        )
        result = am.cancel(apr.id, reason="Görev iptal edildi")
        assert result is not None
        assert result.status == "CANCELLED"

    def test_approve_nonexistent(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        result = am.approve("nonexistent-id")
        assert result is None

    def test_approve_already_approved(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(task_id="t1", tool_name="write_file", action="test", risk="low")
        am.approve(apr.id)
        # İkinci kez onaylayamaz
        result = am.approve(apr.id)
        assert result is None

    def test_pending_list(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        am.request_approval(task_id="t1", tool_name="write_file", action="a1", risk="low")
        am.request_approval(task_id="t2", tool_name="run_command", action="a2", risk="high")
        assert len(am.list_pending()) == 2
        # Birini onayla
        pending = am.list_pending()
        am.approve(pending[0].id)
        assert len(am.list_pending()) == 1

    def test_get_pending_for_task(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(task_id="task-xyz", tool_name="write_file", action="test", risk="low")
        found = am.get_pending_for_task("task-xyz")
        assert found is not None
        assert found.id == apr.id
        # Olmayan task
        assert am.get_pending_for_task("task-nonexistent") is None

    def test_timeout(self):
        from core.approval_manager import ApprovalManager
        am = ApprovalManager(timeout_seconds=0)  # hemen timeout
        am.request_approval(task_id="t1", tool_name="write_file", action="test", risk="low")
        time.sleep(0.01)
        timed_out = am.check_timeout()
        assert len(timed_out) == 1
        assert timed_out[0].status == "TIMEOUT"

    def test_tool_risk_classification(self):
        from core.approval_manager import ApprovalManager
        assert ApprovalManager.get_tool_risk("read_file") == "low"
        assert ApprovalManager.get_tool_risk("write_file") == "medium"
        assert ApprovalManager.get_tool_risk("gmail_send_email") == "high"
        assert ApprovalManager.get_tool_risk("rollback_backup") == "high"
        assert ApprovalManager.get_tool_risk("browser_click") == "medium"

    def test_describe_action(self):
        from core.approval_manager import ApprovalManager
        action, target = ApprovalManager.describe_action("write_file", {"path": "test.py"})
        assert "test.py" in action
        action, target = ApprovalManager.describe_action("run_command", {"command": "pytest"})
        assert "pytest" in action
        action, target = ApprovalManager.describe_action("gmail_send_email", {"to": "a@b.com", "subject": "Hello"})
        assert "a@b.com" in action


class TestNeedsApproval:
    """needs_approval fonksiyonu testleri."""

    def test_write_file_needs_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("write_file") is True

    def test_run_command_needs_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("run_command") is True

    def test_read_file_no_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("read_file") is False

    def test_list_directory_no_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("list_directory") is False

    def test_web_search_no_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("web_search") is False

    def test_browser_click_needs_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("browser_click") is True

    def test_browser_open_no_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("browser_open") is False

    def test_gmail_send_needs_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("gmail_send_email") is True

    def test_gmail_read_no_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("gmail_list_emails") is False

    def test_run_terminal_needs_approval(self):
        from core.approval_manager import needs_approval
        assert needs_approval("run_terminal_command") is True


class TestTaskStatus:
    """TaskStatus enum testleri."""

    def test_all_states_exist(self):
        from core.approval_manager import TaskStatus
        assert TaskStatus.PENDING.value == "PENDING"
        assert TaskStatus.RUNNING.value == "RUNNING"
        assert TaskStatus.WAITING_FOR_APPROVAL.value == "WAITING_FOR_APPROVAL"
        assert TaskStatus.APPROVED.value == "APPROVED"
        assert TaskStatus.REJECTED.value == "REJECTED"
        assert TaskStatus.RESUMING.value == "RESUMING"
        assert TaskStatus.COMPLETED.value == "COMPLETED"
        assert TaskStatus.FAILED.value == "FAILED"
        assert TaskStatus.CANCELLED.value == "CANCELLED"


# ─── Task State Extension Tests ─────────────────────────────────────────────

class TestTaskStateExtensions:
    """task_state.py genişletme testleri."""

    def test_waiting_for_approval(self, tmp_path):
        from core import task_state
        log_path = tmp_path / "tasks.jsonl"
        with patch.object(task_state, "TASK_LOG", log_path):
            task_state.waiting_for_approval(
                task_id="task-wait-001",
                step=3,
                workspace="/tmp/test",
                approval_id="appr-001",
                tool_name="write_file",
                action="Dosya oluşturulacak",
                target="test.txt",
                risk="medium",
            )
            assert log_path.exists()
            lines = log_path.read_text().strip().split("\n")
            assert len(lines) == 1
            event = json.loads(lines[0])
            assert event["event"] == "waiting_approval"
            assert event["status"] == "WAITING_FOR_APPROVAL"
            assert event["approval_id"] == "appr-001"

    def test_resume_task(self, tmp_path):
        from core import task_state
        log_path = tmp_path / "tasks.jsonl"
        with patch.object(task_state, "TASK_LOG", log_path):
            task_state.resume_task("task-resume-001", step=5, workspace="/tmp/test")
            lines = log_path.read_text().strip().split("\n")
            event = json.loads(lines[0])
            assert event["event"] == "resume"
            assert event["status"] == "RESUMING"

    def test_pending_tasks(self, tmp_path):
        from core import task_state
        log_path = tmp_path / "tasks.jsonl"
        with patch.object(task_state, "TASK_LOG", log_path):
            # Bir task başlat
            task_state.start_task("test request", "/tmp", "model", task_id="task-pending-001")
            # WAITING_FOR_APPROVAL'a geçir
            task_state.waiting_for_approval(
                task_id="task-pending-001", step=1, workspace="/tmp",
                approval_id="appr-001", tool_name="write_file", action="test",
            )
            pending = task_state.pending_tasks()
            assert len(pending) == 1
            assert pending[0]["task_id"] == "task-pending-001"

    def test_pending_tasks_empty(self, tmp_path):
        from core import task_state
        log_path = tmp_path / "tasks.jsonl"
        with patch.object(task_state, "TASK_LOG", log_path):
            assert task_state.pending_tasks() == []


# ─── Integration Tests ──────────────────────────────────────────────────────

class TestApprovalIntegration:
    """Approval + Task State entegrasyon testleri."""

    def test_full_approval_flow(self):
        """Tam onay akışı: create → approve → check."""
        from core.approval_manager import ApprovalManager, TaskStatus
        am = ApprovalManager()

        # 1. Onay talebi oluştur
        apr = am.request_approval(
            task_id="task-int-001",
            tool_name="write_file",
            action="Dosya oluşturulacak: output.py",
            target="output.py",
            risk="medium",
        )
        assert apr.status == "PENDING"

        # 2. Pending kontrolü
        found = am.get_pending_for_task("task-int-001")
        assert found is not None
        assert found.id == apr.id

        # 3. Onay ver
        result = am.approve(apr.id, responded_by="web:panel")
        assert result.status == "APPROVED"

        # 4. Artık pending değil
        found = am.get_pending_for_task("task-int-001")
        assert found is None

    def test_reject_flow(self):
        """Red akışı: create → reject."""
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()

        apr = am.request_approval(
            task_id="task-rej-001",
            tool_name="gmail_send_email",
            action="E-posta gönderilecek",
            risk="high",
        )
        result = am.reject(apr.id, responded_by="telegram:cengiz", message="Şimdi yapma")
        assert result.status == "REJECTED"

    def test_multiple_tasks_independent(self):
        """Birden fazla task bağımsız onaylanmalı."""
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()

        apr1 = am.request_approval(task_id="task-multi-001", tool_name="write_file", action="a1", risk="low")
        apr2 = am.request_approval(task_id="task-multi-002", tool_name="run_command", action="a2", risk="high")
        apr3 = am.request_approval(task_id="task-multi-003", tool_name="browser_click", action="a3", risk="medium")

        assert len(am.list_pending()) == 3

        # Sadece apr1'i onayla
        am.approve(apr1.id)
        assert len(am.list_pending()) == 2

        # apr2'yi red et
        am.reject(apr2.id)
        assert len(am.list_pending()) == 1

        # apr3 hala pending
        assert am.get_pending_for_task("task-multi-003") is not None

    def test_callback_notification(self):
        """Onay durumu değiştiğinde callback çağrılmalı."""
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        callback_data = []
        am.on_status_change(lambda r: callback_data.append(r.status))

        apr = am.request_approval(task_id="t1", tool_name="write_file", action="test", risk="low")
        assert len(callback_data) == 1  # created → PENDING

        am.approve(apr.id)
        assert len(callback_data) == 2  # approved → APPROVED
        assert callback_data[1] == "APPROVED"


class TestPersistence:
    """JSONL persistence testleri."""

    def test_approval_logged_to_jsonl(self, tmp_path):
        """Onaylar JSONL'e yazılır."""
        import core.approval_manager as am_mod
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(task_id="t1", tool_name="write_file", action="test", risk="low")
        assert am_mod.APPROVAL_LOG.exists()
        lines = am_mod.APPROVAL_LOG.read_text().strip().split("\n")
        last = json.loads(lines[-1])
        assert last["id"] == apr.id
        assert last["event"] == "created"

    def test_approve_logged_to_jsonl(self, tmp_path):
        """Onay verme olayı JSONL'e yazılır."""
        import core.approval_manager as am_mod
        from core.approval_manager import ApprovalManager
        am = ApprovalManager()
        apr = am.request_approval(task_id="t2", tool_name="write_file", action="test", risk="low")
        am.approve(apr.id, responded_by="test")
        lines = am_mod.APPROVAL_LOG.read_text().strip().split("\n")
        last = json.loads(lines[-1])
        assert last["event"] == "approved"
        assert last["responded_by"] == "test"


# ─── Cross-Module Tests ─────────────────────────────────────────────────────

class TestAgentIntegration:
    """Agent.py entegrasyon testleri."""

    def test_agent_imports(self):
        """Agent modülü approval_manager'ı doğru import ediyor mu?"""
        from core.agent import run_agent, approve_task
        from core.agent import needs_approval, get_pending_approval
        assert callable(run_agent)
        assert callable(approve_task)
        assert callable(needs_approval)

    def test_approve_task_function(self):
        """approve_task fonksiyonu çalışıyor mu?"""
        from core.agent import approve_task
        from core.approval_manager import ApprovalManager, get_approval_manager

        am = get_approval_manager()
        apr = am.request_approval(task_id="task-agent-001", tool_name="write_file", action="test", risk="low")

        result = approve_task("task-agent-001", responded_by="test")
        assert "Onay verildi" in result

    def test_approve_task_not_found(self):
        """Olmayan task için approve_task hata döndürmeli."""
        from core.agent import approve_task
        result = approve_task("nonexistent-task")
        assert "Onay bulunamadı" in result


# ─── Existing Chat Regression Tests ─────────────────────────────────────────

class TestExistingChatRegression:
    """Mevcut chat özelliklerinin bozulmadığını doğrula."""

    def test_router_intact(self):
        """Router hala çalışıyor mu?"""
        from core.router import model_sec
        model, task = model_sec("Sen kimsin?")
        assert task == "chat"
        model, task = model_sec("python kodu yaz")
        assert task == "coding"

    def test_engine_preferences_intact(self):
        """Engine model tercihleri korunuyor mu?"""
        from core.engine import MODEL_PREFERENCES
        assert "chat" in MODEL_PREFERENCES
        assert "agent" in MODEL_PREFERENCES
        assert "coding" in MODEL_PREFERENCES
        assert "reasoning" in MODEL_PREFERENCES

    def test_agent_tools_dispatch_intact(self):
        """Agent tools dispatch hala çalışıyor mu?"""
        from core.agent_tools import DISPATCH
        assert "read_file" in DISPATCH
        assert "write_file" in DISPATCH
        assert "web_search" in DISPATCH
        assert "run_command" in DISPATCH

    def test_identity_prompt_intact(self):
        """Identity prompt hala mevcut mu?"""
        from core.identity import UMAY_SYSTEM
        assert "UMAY" in UMAY_SYSTEM
        assert "Cengiz" in UMAY_SYSTEM
        assert len(UMAY_SYSTEM) > 1000
