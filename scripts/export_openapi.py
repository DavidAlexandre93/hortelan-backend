from __future__ import annotations

import json
from pathlib import Path

from app.main import app

OUTPUT_PATH = Path(__file__).resolve().parents[1] / 'docs' / 'openapi.json'


def render_openapi() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def main() -> None:
    OUTPUT_PATH.write_text(render_openapi(), encoding='utf-8', newline='\n')
    print(OUTPUT_PATH)


if __name__ == '__main__':
    main()
