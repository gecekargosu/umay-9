"""Tests for new modules added in UMAY 9.02."""
import io
import os
import json
import tempfile

from core.orchestrator import Orchestrator, AgentRole, AgentStatus
from core.file_manager import validate_file, save_upload, FileValidationError, DangerousFileError, FileTooLargeError
from core.archive import ArchiveStore, ArchiveEntry
from core.job_pipeline import JobListing, match_cv_to_job, analyze_job_listing, generate_cover_letter, build_search_queries


class TestOrchestrator:
    def test_create_task(self):
        o = Orchestrator()
        task = o.create_task("Test task", AgentRole.GENERAL)
        assert task.task_id.startswith("task-")
        assert task.status == AgentStatus.IDLE

    def test_status(self):
        o = Orchestrator()
        status = o.get_status()
        assert "agents" in status
        assert len(status["agents"]) == 6

    def test_agent_config(self):
        o = Orchestrator()
        web_agent = o._agents[AgentRole.WEB]
        assert web_agent.can_use_tool("web_search")
        assert not web_agent.can_use_tool("gmail_send_email")

    def test_execute_simple(self):
        o = Orchestrator()
        # This will fail because there's no real LLM, but it shouldn't crash
        result = o.execute_simple("test", AgentRole.GENERAL)
        assert "task_id" in result
        assert "status" in result


class TestFileManager:
    def test_validate_safe(self):
        validate_file("document.pdf", 1000)  # Should not raise

    def test_validate_dangerous(self):
        try:
            validate_file("virus.exe", 1000)
            assert False, "Should have raised"
        except DangerousFileError:
            pass

    def test_validate_too_large(self):
        try:
            validate_file("big.pdf", 100 * 1024 * 1024)
            assert False, "Should have raised"
        except FileTooLargeError:
            pass

    def test_validate_empty(self):
        try:
            validate_file("empty.pdf", 0)
            assert False, "Should have raised"
        except FileValidationError:
            pass

    def test_save_upload(self):
        data = io.BytesIO(b"Hello, this is a test file content")
        result = save_upload(data, "test.txt", source="test")
        assert result["size"] > 0
        assert result["source"] == "test"
        # Cleanup
        os.unlink(result["path"])


class TestArchive:
    def test_add_and_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import core.archive as arc_mod
            old_mem = arc_mod.MEMORY_DIR
            old_arch = arc_mod.ARCHIVE_DIR
            arc_mod.MEMORY_DIR = os.path.join(tmpdir, "UMAY_MEMORY")
            arc_mod.ARCHIVE_DIR = os.path.join(tmpdir, "UMAY_ARCHIVE")
            try:
                store = ArchiveStore()
                entry = ArchiveEntry(
                    content="Test entry about Python programming",
                    topic="TEKNIK",
                    keywords=["python", "test"],
                )
                store.add(entry)

                # Search by topic
                results = store.search_by_topic("TEKNIK")
                assert len(results) == 1
                assert results[0]["content"] == entry.content

                # Search by keywords
                results = store.search_keywords(["python"])
                assert len(results) == 1

                # Duplicate check
                added_again = store.add(entry)
                assert not added_again
            finally:
                arc_mod.MEMORY_DIR = old_mem
                arc_mod.ARCHIVE_DIR = old_arch


class TestJobPipeline:
    def test_analyze_job_listing(self):
        text = """Senior Python Developer
Location: Istanbul
Experience: 5+ years
Skills: Python, Django, PostgreSQL, Docker, AWS
Requirements: Strong Python knowledge
"""
        job = analyze_job_listing(text, url="https://example.com/job")
        assert "Python" in job.title or "python" in job.description.lower()
        assert len(job.skills) > 0

    def test_match_cv_to_job(self):
        profile = {
            "skills": ["Python", "Django", "Docker"],
            "experience_years": 5,
        }
        job = JobListing(
            skills=["Python", "Django", "PostgreSQL", "Docker", "AWS"],
        )
        match = match_cv_to_job(profile, job)
        assert match.match_score > 0
        assert "Python" in match.matched_skills
        assert "PostgreSQL" in match.missing_skills or "AWS" in match.missing_skills

    def test_generate_cover_letter(self):
        profile = {"name": "Test User", "experience_summary": "5 yıl deneyim"}
        job = JobListing(title="Python Developer", company="TestCo")
        match = match_cv_to_job(profile, job)
        letter = generate_cover_letter(profile, job, match)
        assert "TestCo" in letter or "Test User" in letter

    def test_build_search_queries(self):
        queries = build_search_queries("Python Developer", "Istanbul", ["remote"])
        assert len(queries) >= 2
