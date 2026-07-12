"""Live send_to_tia driver — runs the production path against a real TIA.

Usage:
  .venv\\Scripts\\python.exe 05_SCRIPTS\\dev\\script_send_to_tia_live.py [project_dir]

Drives factory_web.Api.send_to_tia exactly as the GUI button does (tag
table XML generation + tag table import + SCL import + compile) and
streams the background job log to stdout until the job finishes.

Defaults to the bundled demo project. Needs: tia_vXX toggle enabled in
.gui_settings.json, pythonnet in the venv, and the .apXX path set in the
project's PROJECT_STATE.json (tia_project_path).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / "05_SCRIPTS")):
    if p not in sys.path:
        sys.path.insert(0, p)

import factory_web as fw  # noqa: E402


def main() -> int:
    proj = (Path(sys.argv[1]) if len(sys.argv) > 1
            else ROOT / "examples" / "Demo_Beispielmaschine_4711")
    api = fw.Api()
    api.root = proj.resolve()
    print(f"project: {api.root}", flush=True)

    r = api.send_to_tia({})
    print("start:", json.dumps(r, ensure_ascii=False, default=str), flush=True)
    if not r.get("ok"):
        return 1

    job = api._tia_job
    seen = 0
    while True:
        for line in job["lines"][seen:]:
            print(line, flush=True)
        seen = len(job["lines"])
        if job["done"]:
            break
        time.sleep(3)

    print("\n--- RESULT ---", flush=True)
    print("ok :", job["ok"], flush=True)
    print("msg:", job["msg"], flush=True)
    for d in job["details"]:
        print("  ", d, flush=True)
    return 0 if job["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
