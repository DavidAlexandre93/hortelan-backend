from __future__ import annotations

import argparse
import re
import shutil
# O binario e resolvido e a chamada usa argv sem shell; as revisoes sao validadas.
import subprocess  # nosec B404

CONVENTIONAL_SUBJECT = re.compile(
    r'^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)'
    r'(\([a-z0-9._/-]+\))?(!)?: .{1,100}$'
)
ZERO_SHA = '0' * 40


def commit_subjects(base: str, head: str) -> list[str]:
    for revision_part in (base, head):
        if revision_part and (
            revision_part.startswith('-')
            or not re.fullmatch(r'[A-Za-z0-9._/-]{1,100}', revision_part)
        ):
            raise ValueError('Revisao Git invalida.')
    revision = head if not base or base == ZERO_SHA else f'{base}..{head}'
    git_executable = shutil.which('git')
    if not git_executable:
        raise RuntimeError('Executavel git nao encontrado.')
    result = subprocess.run(
        [git_executable, 'log', '--format=%s', revision],
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603
    return [subject for subject in result.stdout.splitlines() if subject]


def validate_subjects(subjects: list[str]) -> list[str]:
    return [subject for subject in subjects if not CONVENTIONAL_SUBJECT.fullmatch(subject)]


def main() -> None:
    parser = argparse.ArgumentParser(description='Valida subjects no padrao Conventional Commits.')
    parser.add_argument('--base', default='')
    parser.add_argument('--head', default='HEAD')
    args = parser.parse_args()
    invalid = validate_subjects(commit_subjects(args.base, args.head))
    if invalid:
        formatted = '\n'.join(f'- {subject}' for subject in invalid)
        raise SystemExit(f'Commits fora do padrao Conventional Commits:\n{formatted}')


if __name__ == '__main__':
    main()
