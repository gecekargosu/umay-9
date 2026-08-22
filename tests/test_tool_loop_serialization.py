import json
from core.agent import _normalize_tool_call, _parse_tool_calls, _assistant_tool_message, _bounded_tool_result

def test_string_arguments_become_object():
    c=_normalize_tool_call({"id":"x","function":{"name":"read_file","arguments":'{"path":"README.md"}'}})
    assert isinstance(c["function"]["arguments"],dict)
    assert c["function"]["arguments"]["path"]=="README.md"

def test_native_and_compat_have_same_shape():
    native=_parse_tool_calls({"tool_calls":[{"id":"n","type":"function","function":{"name":"list_directory","arguments":'{"recursive":true}'}}]})[0]
    compat=_parse_tool_calls({"content":json.dumps({"name":"list_directory","arguments":{"recursive":True}})})[0]
    assert native["function"]["name"]==compat["function"]["name"]
    assert native["function"]["arguments"]==compat["function"]["arguments"]

def test_assistant_message_uses_object_arguments():
    msg=_assistant_tool_message([{"id":"x","type":"function","function":{"name":"list_directory","arguments":{"recursive":True}}}])
    assert isinstance(msg["tool_calls"][0]["function"]["arguments"],dict)

def test_large_tool_result_is_bounded():
    out=_bounded_tool_result({"workspace":"X","entries":[{"path":str(i)} for i in range(5000)]})
    assert len(out)<=18000
    assert '"truncated": true' in out


def test_assistant_message_preserves_tool_call_id():
    msg=_assistant_tool_message([{"id":"call-42","type":"function","function":{"name":"list_directory","arguments":{}}}])
    assert msg["tool_calls"][0]["id"] == "call-42"


def test_task_state_checkpoint_round_trip(tmp_path, monkeypatch):
    import core.task_state as state
    monkeypatch.setattr(state, "TASK_LOG", tmp_path / "tasks.jsonl")
    task_id = state.start_task("test", str(tmp_path), "qwen3:8b")
    state.checkpoint(task_id, 1, str(tmp_path), "WAITING_MODEL", ["read_file"], [{"role":"user","content":"test"}])
    assert state.load_task(task_id)["step"] == 1
    assert state.load_task(task_id)["messages"][0]["content"] == "test"
    state.finish_task(task_id, 1, "COMPLETED", "ok")
    assert state.load_task(task_id)["status"] == "COMPLETED"


def test_online_requests_route_to_agent_mode():
    from run_umay import is_agent_request
    assert is_agent_request("internetten araştır UMAY hakkında güncel bilgi bul")
    assert is_agent_request("bu siteye git ve incele")
