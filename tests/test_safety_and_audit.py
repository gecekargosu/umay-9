import core.agent_tools as tools
from core.agent_tools import set_workspace, write_file, run_command, inspect_project

def test_write_requires_approval(tmp_path, monkeypatch):
    set_workspace(tmp_path); monkeypatch.setattr(tools,"EXECUTION_MODE","approval")
    try: write_file("x.txt","x")
    except PermissionError: pass
    else: raise AssertionError("write_file approval olmadan çalıştı")
    monkeypatch.setattr(tools,"EXECUTION_MODE","auto_fix")
    result=write_file("x.txt","x")
    assert result["created"] is True

def test_command_result_has_standard_status(tmp_path, monkeypatch):
    set_workspace(tmp_path); monkeypatch.setattr(tools,"EXECUTION_MODE","auto_fix")
    result=run_command("python -c \"print('ok')\"")
    assert result["status"]=="PASS" and result["returncode"]==0

def test_project_inspector(tmp_path):
    set_workspace(tmp_path); (tmp_path/"package.json").write_text("{}")
    assert "node" in inspect_project()["project_types"]


def test_run_command_requires_approval_for_mutating_command(tmp_path, monkeypatch):
    set_workspace(tmp_path); monkeypatch.setattr(tools,"EXECUTION_MODE","approval")
    try:
        run_command("python -c \"open('x.txt','w').write('x')\"")
    except PermissionError:
        pass
    else:
        raise AssertionError("Yan etkili komut approval olmadan çalıştı")

def test_audit_uses_current_workspace(tmp_path, monkeypatch):
    import core.audit as audit
    set_workspace(tmp_path)
    (tmp_path/"tests").mkdir()
    (tmp_path/"broken.py").write_text("def broken(:\n", encoding="utf-8")
    result = audit.run_static_audit()
    assert result["workspace"] == str(tmp_path)
    assert any(f["path"] == "broken.py" for f in result["syntax_findings"])


def test_audit_discovers_validation_commands(tmp_path):
    import json
    import core.audit as audit
    set_workspace(tmp_path)
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"lint": "oxlint", "build": "vite build"}}), encoding="utf-8")
    commands = audit.discover_validation_commands()
    assert {x["command"] for x in commands} == {"npm run lint", "npm run build"}


def test_online_tools_are_registered():
    names = {item["function"]["name"] for item in tools.TOOLS}
    assert {"web_search", "browser_open", "browser_read", "browser_click", "browser_type", "browser_screenshot", "browser_close"}.issubset(names)
