import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import check_conventional_commits, export_openapi


def test_conventional_commit_validation_and_git_range(monkeypatch) -> None:
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs == {'check': True, 'capture_output': True, 'text': True}
        return SimpleNamespace(stdout='feat(api): add health\nfix: repair timeout\n')

    monkeypatch.setattr(check_conventional_commits.subprocess, 'run', run)
    monkeypatch.setattr(check_conventional_commits.shutil, 'which', lambda _: 'C:/Git/git.exe')
    subjects = check_conventional_commits.commit_subjects('base-sha', 'head-sha')

    assert subjects == ['feat(api): add health', 'fix: repair timeout']
    assert calls[0][-1] == 'base-sha..head-sha'
    assert check_conventional_commits.validate_subjects(subjects) == []
    assert check_conventional_commits.validate_subjects(['bad commit']) == ['bad commit']


def test_conventional_commit_cli_rejects_invalid_subject(monkeypatch) -> None:
    monkeypatch.setattr(
        check_conventional_commits,
        'commit_subjects',
        lambda *_: ['feature without convention'],
    )
    monkeypatch.setattr('sys.argv', ['check-conventional-commits'])
    with pytest.raises(SystemExit, match='fora do padrao'):
        check_conventional_commits.main()


def test_openapi_export_is_deterministic(tmp_path: Path, monkeypatch, capsys) -> None:
    output = tmp_path / 'openapi.json'
    monkeypatch.setattr(export_openapi, 'OUTPUT_PATH', output)

    first = export_openapi.render_openapi()
    second = export_openapi.render_openapi()
    assert first == second
    assert json.loads(first)['openapi'].startswith('3.1')

    export_openapi.main()
    assert output.read_text(encoding='utf-8') == first
    assert str(output) in capsys.readouterr().out


def test_github_workflows_are_valid_yaml_and_quality_gate_is_strict() -> None:
    workflow_dir = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
    workflows = list(workflow_dir.glob('*.yml'))
    assert workflows
    parsed = [yaml.safe_load(path.read_text(encoding='utf-8')) for path in workflows]
    assert all(isinstance(workflow.get('jobs'), dict) for workflow in parsed)

    pipeline = (workflow_dir / 'cicd.yml').read_text(encoding='utf-8')
    assert "python-version: '3.12'" in pipeline
    assert 'mypy app api scripts' in pipeline
    assert 'pytest -q --cov=app --cov=api --cov=scripts' in pipeline
    assert 'pip-audit --local --skip-editable' in pipeline
