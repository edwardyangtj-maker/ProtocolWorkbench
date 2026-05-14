from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from protocol_workbench.core.models import Project, new_id
from protocol_workbench.core.config_store import ConfigStore


class ProjectManager:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self.current_project: Project | None = None

    def new_project(self, name: str = "New Project", description: str = "") -> Project:
        project = Project(name=name, description=description)
        self.current_project = project
        return project

    def save_project(self, project: Project | None = None) -> str:
        if project is None:
            project = self.current_project
        if project is None:
            raise ValueError("No project to save")
        project.updated_at = datetime.now().isoformat()
        path = self.config_store.save_project(project)
        self.current_project = project
        return path

    def open_project(self, path: str) -> Project:
        project = self.config_store.load_project(path)
        self.current_project = project
        return project

    def close_project(self):
        self.current_project = None

    def export_project(self, project: Project | None = None, export_path: str = "") -> str:
        if project is None:
            project = self.current_project
        if project is None:
            raise ValueError("No project to export")

        if export_path:
            zip_path = Path(export_path)
        else:
            export_dir = Path(os.path.expanduser("~")) / "Desktop"
            export_dir.mkdir(parents=True, exist_ok=True)
            zip_path = export_dir / f"{project.name}.zip"

        temp_dir = Path(str(zip_path) + "_tmp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.config_store.save_json(project.to_dict(), str(temp_dir / "project.json"))

            if project.environments:
                self.config_store.save_json(
                    [e.to_dict() for e in project.environments],
                    str(temp_dir / "environments.json"),
                )
            if project.endpoints:
                self.config_store.save_json(
                    [e.to_dict() for e in project.endpoints],
                    str(temp_dir / "endpoints.json"),
                )
            if project.frame_rules:
                self.config_store.save_json(
                    [f.to_dict() for f in project.frame_rules],
                    str(temp_dir / "frame_rules.json"),
                )
            if project.message_templates:
                self.config_store.save_json(
                    [t.to_dict() for t in project.message_templates],
                    str(temp_dir / "message_templates.json"),
                )
            if project.scenarios:
                self.config_store.save_json(
                    [s.to_dict() for s in project.scenarios],
                    str(temp_dir / "scenarios.json"),
                )
            if project.variables:
                self.config_store.save_json(
                    project.variables,
                    str(temp_dir / "variables.json"),
                )

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.iterdir():
                    if file_path.is_file():
                        zf.write(file_path, file_path.name)

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

        return str(zip_path)

    def import_project(self, zip_path: str) -> Project:
        temp_dir = Path(zip_path + "_extracted")
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            project_json = temp_dir / "project.json"
            if not project_json.exists():
                raise ValueError("Invalid project package: project.json not found")

            project = self.config_store.load_project(str(project_json))
            project.id = new_id()
            self.current_project = project
            return project

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def list_recent_projects(self) -> list[dict]:
        return self.config_store.list_projects()
