from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from protocol_workbench.core.models import Project


class ConfigStore:
    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.expanduser("~"), ".protocol_workbench")
        self.base_dir = Path(base_dir)
        self.projects_dir = self.base_dir / "projects"
        self.templates_dir = self.base_dir / "templates"
        self.logs_dir = self.base_dir / "logs"
        self._state_file = self.base_dir / "state.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.base_dir, self.projects_dir, self.templates_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_last_project_path(self) -> str | None:
        if not self._state_file.exists():
            return None
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            path = state.get("last_project_path", "")
            if path and Path(path).exists():
                return path
        except Exception:
            pass
        return None

    def set_last_project_path(self, path: str):
        state = {}
        if self._state_file.exists():
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                pass
        state["last_project_path"] = path
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def save_project(self, project: Project, path: str | None = None) -> str:
        if path is None:
            project_dir = self.projects_dir / project.id
            project_dir.mkdir(parents=True, exist_ok=True)
            path = str(project_dir / "project.json")
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)

        data = project.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def load_project(self, path: str) -> Project:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Project.from_dict(data)

    def list_projects(self) -> list[dict]:
        results = []
        if not self.projects_dir.exists():
            return results
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                json_path = project_dir / "project.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        results.append({
                            "id": data.get("id", ""),
                            "name": data.get("name", ""),
                            "path": str(json_path),
                        })
                    except Exception:
                        pass
        return results

    def delete_project(self, project_id: str) -> bool:
        project_dir = self.projects_dir / project_id
        if project_dir.exists() and project_dir.is_dir():
            import shutil
            shutil.rmtree(project_dir)
            return True
        return False

    def save_json(self, data: Any, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_log_dir(self, environment_name: str = "") -> Path:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        if environment_name:
            dir_name = f"{date_str}_{environment_name}"
        else:
            dir_name = date_str
        log_dir = self.logs_dir / dir_name
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
