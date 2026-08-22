from pathlib import Path


def test_real_ollama_verifier_exists_and_is_read_only_by_design():
    script = Path(__file__).parents[1] / "scripts" / "verify_real_ollama.py"
    text = script.read_text(encoding="utf-8")
    assert "api/tags" in text
    assert "api/chat" in text
    assert "_assistant_tool_message" in text
    assert "_parse_tool_calls" in text
    assert "_tool_messages" in text
    # The verifier is intentionally limited to list_directory and does not call
    # write_file/run_command, so a real P0 run cannot mutate the target project.
    assert '"list_directory"' in text
    assert "write_file" not in text
    assert "run_command" not in text
