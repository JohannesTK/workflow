"""Data models for workflows and execution history"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkflowLanguage(str, Enum):
    """Supported workflow languages"""
    BASH = "bash"
    PYTHON = "python"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class WorkflowConfig(BaseModel):
    """Workflow configuration"""
    name: str
    description: str
    language: WorkflowLanguage
    code: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    tags: List[str] = Field(default_factory=list)
    env_vars: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 300  # seconds

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionResult(BaseModel):
    """Result of workflow execution"""
    workflow_name: str
    status: WorkflowStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None  # seconds
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FailurePattern(BaseModel):
    """Identified failure pattern from history"""
    pattern_type: str  # e.g., "timeout", "api_error", "dependency_missing"
    count: int
    last_seen: datetime
    error_messages: List[str]
    suggested_fixes: List[str] = Field(default_factory=list)
