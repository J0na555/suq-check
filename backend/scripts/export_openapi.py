from pathlib import Path

import yaml

from app.main import app


def main() -> None:
    output = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()

