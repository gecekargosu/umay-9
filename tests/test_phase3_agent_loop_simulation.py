import json

import core.agent as agent


def test_agent_multi_turn_loop_simulation(monkeypatch, tmp_path):
    workspace = tmp_path / 'fixture'
    workspace.mkdir()
    (workspace / 'README.md').write_text('# UMAY fixture\n', encoding='utf-8')
    agent.set_workspace(str(workspace))

    turns = iter([
        {'message': {'role': 'assistant', 'content': '', 'tool_calls': [
            {'id': 'sim-1', 'type': 'function', 'function': {
                'name': 'read_file', 'arguments': json.dumps({'path': 'README.md'})
            }}
        ]}},
        {'message': {'role': 'assistant', 'content': 'SIMULATED AGENT LOOP PASS'}},
    ])
    seen = []

    def fake_chat(messages, **kwargs):
        seen.append(messages)
        return next(turns)

    monkeypatch.setattr(agent, 'chat', fake_chat)
    monkeypatch.setattr(agent, 'resolve_model', lambda task: 'qwen2.5-coder:7b')
    monkeypatch.setattr(agent, 'eylem_baslat', lambda *a, **k: 'sim-action')
    monkeypatch.setattr(agent, 'eylem_tamamla', lambda *a, **k: None)
    monkeypatch.setattr(agent, 'eylem_hata', lambda *a, **k: None)

    answer = agent.run_agent('README dosyasını oku', max_steps=3)
    assert answer == 'SIMULATED AGENT LOOP PASS'
    assert len(seen) == 2
    second_messages = seen[1]
    assistant = next(m for m in second_messages if m.get('role') == 'assistant' and m.get('tool_calls'))
    assert isinstance(assistant['tool_calls'][0]['function']['arguments'], dict)
    assert any(m.get('role') == 'tool' for m in second_messages)
