#!/usr/bin/env python3
"""Check portable skill metadata and resources, not creative quality."""
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def check():
    errors = []
    license_data = (ROOT / "LICENSE").read_bytes()
    for folder in sorted((ROOT / "skills").iterdir()):
        if not folder.is_dir():
            continue
        try:
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            front, body = text.split("---", 2)[1:]
            meta = yaml.safe_load(front)
            if meta.get("name") != folder.name or not re.fullmatch(r"[a-z0-9-]{1,63}", meta["name"]):
                errors.append(f"{folder.name}: invalid name")
            if not isinstance(meta.get("description"), str) or not meta["description"].strip():
                errors.append(f"{folder.name}: missing description")
            for target in re.findall(r"\]\(([^)]+)\)", body):
                if not target.startswith(("http://", "https://", "#")) and not (folder / target.split("#")[0]).is_file():
                    errors.append(f"{folder.name}: missing linked resource {target}")
            if (folder / "LICENSE").read_bytes() != license_data:
                errors.append(f"{folder.name}: license differs from root")
            metadata = yaml.safe_load((folder / "agents/openai.yaml").read_text())
            if not metadata.get("interface", {}).get("display_name"):
                errors.append(f"{folder.name}: missing UI name")
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
            errors.append(f"{folder.name}: {exc}")
    return errors


if __name__ == "__main__":
    errors = check()
    print("\n".join(errors) if errors else "All skill packages are structurally valid.")
    raise SystemExit(bool(errors))
