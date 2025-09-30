"""Execution history storage using SQLite"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json

from .models import ExecutionResult, WorkflowStatus, FailurePattern


class HistoryStore:
    """Manages execution history storage"""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize history store

        Args:
            db_path: Path to SQLite database (defaults to ~/workflows/history.db)
        """
        if db_path is None:
            workflows_dir = Path.home() / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            db_path = workflows_dir / "history.db"

        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    duration REAL,
                    exit_code INTEGER,
                    stdout TEXT,
                    stderr TEXT,
                    error_message TEXT
                )
            """)

            # Create index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_name
                ON executions(workflow_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON executions(status)
            """)

    def save_execution(self, result: ExecutionResult) -> int:
        """Save execution result

        Returns:
            Execution ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO executions (
                    workflow_name, status, started_at, finished_at,
                    duration, exit_code, stdout, stderr, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.workflow_name,
                result.status.value,
                result.started_at.isoformat(),
                result.finished_at.isoformat() if result.finished_at else None,
                result.duration,
                result.exit_code,
                result.stdout,
                result.stderr,
                result.error_message,
            ))

            return cursor.lastrowid

    def get_executions(
        self,
        workflow_name: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
    ) -> List[ExecutionResult]:
        """Get execution history

        Args:
            workflow_name: Filter by workflow name
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of execution results
        """
        query = "SELECT * FROM executions WHERE 1=1"
        params = []

        if workflow_name:
            query += " AND workflow_name = ?"
            params.append(workflow_name)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append(ExecutionResult(
                    workflow_name=row['workflow_name'],
                    status=WorkflowStatus(row['status']),
                    started_at=datetime.fromisoformat(row['started_at']),
                    finished_at=datetime.fromisoformat(row['finished_at']) if row['finished_at'] else None,
                    duration=row['duration'],
                    exit_code=row['exit_code'],
                    stdout=row['stdout'],
                    stderr=row['stderr'],
                    error_message=row['error_message'],
                ))

            return results

    def get_failure_patterns(
        self,
        workflow_name: str,
        min_count: int = 2,
    ) -> List[FailurePattern]:
        """Analyze execution history to find failure patterns

        Args:
            workflow_name: Workflow to analyze
            min_count: Minimum number of occurrences to be considered a pattern

        Returns:
            List of identified failure patterns
        """
        # Get failed executions
        failures = self.get_executions(
            workflow_name=workflow_name,
            status=WorkflowStatus.FAILED,
            limit=50
        )

        if not failures:
            return []

        # Group by error patterns
        patterns: dict = {}

        for failure in failures:
            if not failure.error_message:
                continue

            # Simple pattern detection (can be improved)
            pattern_key = self._extract_pattern_key(failure.error_message)

            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    'count': 0,
                    'messages': [],
                    'last_seen': failure.started_at,
                }

            patterns[pattern_key]['count'] += 1
            patterns[pattern_key]['messages'].append(failure.error_message)
            if failure.started_at > patterns[pattern_key]['last_seen']:
                patterns[pattern_key]['last_seen'] = failure.started_at

        # Convert to FailurePattern objects
        result = []
        for pattern_type, data in patterns.items():
            if data['count'] >= min_count:
                result.append(FailurePattern(
                    pattern_type=pattern_type,
                    count=data['count'],
                    last_seen=data['last_seen'],
                    error_messages=data['messages'][:5],  # Keep first 5 examples
                ))

        return sorted(result, key=lambda p: p.count, reverse=True)

    def _extract_pattern_key(self, error_message: str) -> str:
        """Extract a pattern key from error message"""
        # Remove specific values to group similar errors
        error_lower = error_message.lower()

        if 'timeout' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'network_error'
        elif 'permission' in error_lower or 'denied' in error_lower:
            return 'permission_error'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'not_found'
        elif 'rate limit' in error_lower or '429' in error_lower:
            return 'rate_limit'
        elif 'authentication' in error_lower or '401' in error_lower:
            return 'auth_error'
        elif 'syntax' in error_lower:
            return 'syntax_error'
        elif 'import' in error_lower or 'module' in error_lower:
            return 'dependency_error'
        else:
            # Extract first word of error for generic grouping
            words = error_message.split()
            return words[0].lower() if words else 'unknown'

    def get_stats(self, workflow_name: str) -> dict:
        """Get execution statistics for a workflow"""
        with sqlite3.connect(self.db_path) as conn:
            # Total executions
            total = conn.execute(
                "SELECT COUNT(*) FROM executions WHERE workflow_name = ?",
                (workflow_name,)
            ).fetchone()[0]

            # Success rate
            successes = conn.execute(
                "SELECT COUNT(*) FROM executions WHERE workflow_name = ? AND status = ?",
                (workflow_name, WorkflowStatus.SUCCESS.value)
            ).fetchone()[0]

            # Average duration
            avg_duration = conn.execute(
                "SELECT AVG(duration) FROM executions WHERE workflow_name = ? AND status = ?",
                (workflow_name, WorkflowStatus.SUCCESS.value)
            ).fetchone()[0]

            return {
                'total_executions': total,
                'successful': successes,
                'failed': total - successes,
                'success_rate': (successes / total * 100) if total > 0 else 0,
                'avg_duration': avg_duration or 0,
            }
