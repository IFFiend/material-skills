#!/usr/bin/env python3
"""Build deterministic archives with an explicit public-resource allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("campaign-batch", "guide-capture", "document-batch")
ALLOWED_DIRS = {"agents", "scripts", "references", "assets"}
ALLOWED_FILES = {"SKILL.md", "LICENSE", "requirements.txt"}


def package(destination):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Choose an empty destination")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"version":"0.1.0", "archives":[]}
    for name in SKILLS:
        folder = ROOT / "skills" / name
        selected = []
        for source in sorted(folder.rglob("*")):
            relative = source.relative_to(folder)
            if source.is_symlink():
                raise ValueError(f"Symlink not distributable: {source}")
            if not source.is_file() or "__pycache__" in relative.parts or source.suffix == ".pyc":
                continue
            if relative.parts[0] in ALLOWED_DIRS or str(relative) in ALLOWED_FILES:
                selected.append(source)
        for required in ("SKILL.md", "LICENSE", "agents/openai.yaml"):
            if folder / required not in selected:
                raise ValueError(f"Missing {name}/{required}")
        if (folder/"LICENSE").read_bytes() != (ROOT/"LICENSE").read_bytes():
            raise ValueError("License mismatch")
        archive = destination / f"{name}-0.1.0.zip"
        files = []
        with ZipFile(archive,"w",compression=ZIP_DEFLATED) as zipfile:
            for source in selected:
                path = f"{name}/{source.relative_to(folder).as_posix()}"
                content = source.read_bytes()
                info = ZipInfo(path, date_time=(2026,11,1,0,0,0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipfile.writestr(info,content)
                files.append({"path":path,"sha256":hashlib.sha256(content).hexdigest()})
        manifest["archives"].append({"name":archive.name,"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"files":files})
    (destination/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result=package(args.out)
    print(json.dumps({"archives":[a["name"] for a in result["archives"]]}))
