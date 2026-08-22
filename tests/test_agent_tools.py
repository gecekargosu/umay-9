from pathlib import Path
from core.agent_tools import set_workspace, list_directory, read_file, search_files, inspect_project

def test_workspace_tools_and_inspector(tmp_path):
    (tmp_path/'backend').mkdir(); (tmp_path/'backend'/'main.py').write_text('TODO: test\\n',encoding='utf-8')
    (tmp_path/'requirements.txt').write_text('pytest\\n',encoding='utf-8')
    (tmp_path/'tests').mkdir()
    set_workspace(tmp_path)
    assert list_directory('.', True)['count'] >= 3
    assert 'TODO' in read_file('backend/main.py')['content']
    assert search_files('TODO')['matches']
    info=inspect_project(); assert 'python' in info['project_types']; assert 'tests' in info['project_types']
