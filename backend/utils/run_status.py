"""Persist observed training stages for dashboard status reporting."""

from contextlib import contextmanager
import json
from pathlib import Path

from utils.artifact_manager import utc_now, write_json

STAGES = [
    ("data", "Data validation and split"),
    ("training", "Cross-validation and fitting"),
    ("evaluation", "Held-out evaluation"),
    ("artifacts", "Candidate saved"),
    ("activation", "Model activation"),
]


class RunRecorder:
    def __init__(self, settings, version, stages=None):
        self.root = settings.base_dir / settings.artifacts_dir
        self.path = self.root / "runs" / f"{version}.json"
        self.record = {
            "run_id": version, "model_version": version, "status": "running",
            "started_at": utc_now(), "completed_at": None, "error": None,
            "stages": [{"id": key, "label": label, "status": "pending",
                        "started_at": None, "completed_at": None, "message": None}
                       for key, label in (stages or STAGES)],
        }
        self.save()
        write_json(self.root / "latest_run.json", {"run_id": version})

    @classmethod
    def resume(cls, settings, version, stages=None):
        path = settings.base_dir / settings.artifacts_dir / "runs" / f"{version}.json"
        if not path.exists():
            return cls(settings, version, stages)
        recorder = cls.__new__(cls)
        recorder.root, recorder.path = path.parent.parent, path
        recorder.record = json.loads(path.read_text(encoding="utf-8"))
        recorder.record.update(status="running", error=None, completed_at=None)
        recorder.save()
        return recorder

    def save(self):
        write_json(self.path, self.record)

    def stage(self, key):
        return next(stage for stage in self.record["stages"] if stage["id"] == key)

    def start_stage(self, key):
        self.stage(key).update(status="running", started_at=utc_now())
        self.save()

    def complete_stage(self, key):
        self.stage(key).update(status="completed", completed_at=utc_now())
        self.save()

    def skip_stage(self, key, message):
        self.stage(key).update(status="skipped", message=message)
        self.save()

    @contextmanager
    def observe(self, key):
        self.start_stage(key)
        yield
        self.complete_stage(key)

    def complete(self, **details):
        self.record.update(status="completed", completed_at=utc_now(), **details)
        self.save()

    def fail(self, error):
        message = str(error)
        for stage in self.record["stages"]:
            if stage["status"] == "running":
                stage.update(status="failed", completed_at=utc_now(), message=message)
        self.record.update(status="failed", error=message, completed_at=utc_now())
        self.save()


def read_latest_run(settings):
    root = settings.base_dir / settings.artifacts_dir
    pointer = root / "latest_run.json"
    if not pointer.exists():
        return None
    version = json.loads(pointer.read_text())["run_id"]
    path = (root / "runs" / f"{version}.json").resolve()
    if not path.is_relative_to((root / "runs").resolve()):
        raise ValueError("Invalid run status reference")
    return json.loads(path.read_text())


def record_activation(root: Path, version):
    path = root / "runs" / f"{version}.json"
    if path.exists():
        record = json.loads(path.read_text())
        stage = next(item for item in record["stages"] if item["id"] == "activation")
        now = utc_now()
        stage.update(status="completed", started_at=stage["started_at"] or now,
                     completed_at=now, message="Selected for inference")
        write_json(path, record)
