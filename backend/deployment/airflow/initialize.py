"""Initialize only the dedicated local Airflow metadata store and login file."""

import json
import os
from pathlib import Path
import subprocess

subprocess.run(["airflow", "db", "migrate"], check=True)
path = Path(os.environ["AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE"])
path.parent.mkdir(parents=True, exist_ok=True)
if not path.exists():
    path.write_text(json.dumps({"admin": os.environ["AIRFLOW_ADMIN_PASSWORD"]}), encoding="utf-8")
    path.chmod(0o600)
