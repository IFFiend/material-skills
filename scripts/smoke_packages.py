#!/usr/bin/env python3
"""Run each extracted archive without repository imports; dependencies must exist."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def smoke(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/"manifest.json").read_text())
    results = []
    scripts = {"campaign-batch":"campaign.py", "guide-capture":"guide.py", "document-batch":"documents.py"}
    for archive in manifest["archives"]:
        path = directory/archive["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != archive["sha256"]:
            raise ValueError(f"Archive checksum mismatch: {path.name}")
        with tempfile.TemporaryDirectory(prefix="skill-package-") as temporary:
            root = Path(temporary)
            with ZipFile(path) as bundle:
                for item in bundle.infolist():
                    target = (root/item.filename).resolve()
                    if not target.is_relative_to(root.resolve()):
                        raise ValueError("Unsafe archive path")
                bundle.extractall(root)
            for item in archive["files"]:
                if hashlib.sha256((root/item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                    raise ValueError("Extracted file checksum mismatch")
            name = archive["files"][0]["path"].split("/")[0]
            skill = root/name
            output = root/"result"
            env = os.environ.copy()
            env.pop("PYTHONPATH",None)
            run = subprocess.run([sys.executable,str(skill/"scripts"/scripts[name]),str(skill/"assets/demo.json"),"--out",str(output)],
                                 cwd=skill,env=env,text=True,capture_output=True,timeout=60)
            if run.returncode:
                raise RuntimeError(f"{name} failed: {run.stdout}\n{run.stderr}")
            report = json.loads((output/"report.json").read_text())
            if report["status"] != "technical_pass" or not (output/"index.html").is_file():
                raise RuntimeError(f"{name}: incomplete demo")
            if name == "campaign-batch" and (report["rendered"] != 9 or report["failed"]):
                raise RuntimeError("Campaign archive missed exports")
            results.append({"skill":name,"status":"pass","execution":"extracted archive only; existing interpreter dependencies"})
    return results


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    args=parser.parse_args()
    print(json.dumps(smoke(args.directory),indent=2))
