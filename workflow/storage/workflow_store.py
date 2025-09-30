"""Workflow storage manager"""

import json
from pathlib import Path
from typing import List, Optional
import yaml

from .models import WorkflowConfig, WorkflowLanguage


class WorkflowStore:
    """Manages workflow storage and retrieval"""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize workflow store

        Args:
            base_dir: Base directory for workflows (defaults to ~/workflows)
        """
        if base_dir is None:
            base_dir = Path.home() / "workflows"

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_workflow_dir(self, name: str) -> Path:
        """Get directory path for workflow"""
        return self.base_dir / name

    def _get_config_path(self, name: str) -> Path:
        """Get config file path"""
        return self._get_workflow_dir(name) / "config.yaml"

    def _get_code_path(self, name: str, language: WorkflowLanguage) -> Path:
        """Get code file path"""
        ext = "sh" if language == WorkflowLanguage.BASH else "py"
        return self._get_workflow_dir(name) / f"workflow.{ext}"

    def _get_memory_path(self, name: str) -> Path:
        """Get agent memory file path"""
        return self._get_workflow_dir(name) / "CLAUDE.md"

    def exists(self, name: str) -> bool:
        """Check if workflow exists"""
        return self._get_workflow_dir(name).exists()

    def save(self, workflow: WorkflowConfig) -> None:
        """Save workflow to disk"""
        workflow_dir = self._get_workflow_dir(workflow.name)
        workflow_dir.mkdir(parents=True, exist_ok=True)

        # Save config
        config_data = workflow.model_dump()
        code = config_data.pop("code")  # Don't store code in config

        with open(self._get_config_path(workflow.name), 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        # Save code
        code_path = self._get_code_path(workflow.name, workflow.language)
        with open(code_path, 'w') as f:
            f.write(code)

        # Make bash scripts executable
        if workflow.language == WorkflowLanguage.BASH:
            code_path.chmod(0o755)

        # Create memory file if it doesn't exist
        memory_path = self._get_memory_path(workflow.name)
        if not memory_path.exists():
            with open(memory_path, 'w') as f:
                f.write(f"# Workflow: {workflow.name}\n\n")
                f.write(f"{workflow.description}\n\n")
                f.write("## Execution History\n\n")

    def load(self, name: str) -> Optional[WorkflowConfig]:
        """Load workflow from disk"""
        if not self.exists(name):
            return None

        # Load config
        config_path = self._get_config_path(name)
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Load code
        language = WorkflowLanguage(config_data['language'])
        code_path = self._get_code_path(name, language)
        with open(code_path, 'r') as f:
            code = f.read()

        config_data['code'] = code
        return WorkflowConfig(**config_data)

    def list_workflows(self) -> List[str]:
        """List all workflow names"""
        if not self.base_dir.exists():
            return []

        workflows = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and self._get_config_path(item.name).exists():
                workflows.append(item.name)

        return sorted(workflows)

    def delete(self, name: str) -> bool:
        """Delete workflow"""
        if not self.exists(name):
            return False

        import shutil
        workflow_dir = self._get_workflow_dir(name)
        shutil.rmtree(workflow_dir)
        return True

    def update_memory(self, name: str, content: str, append: bool = True) -> None:
        """Update workflow's agent memory"""
        memory_path = self._get_memory_path(name)

        if append and memory_path.exists():
            with open(memory_path, 'a') as f:
                f.write(f"\n{content}\n")
        else:
            with open(memory_path, 'w') as f:
                f.write(content)

    def get_memory(self, name: str) -> Optional[str]:
        """Get workflow's agent memory"""
        memory_path = self._get_memory_path(name)
        if not memory_path.exists():
            return None

        with open(memory_path, 'r') as f:
            return f.read()
