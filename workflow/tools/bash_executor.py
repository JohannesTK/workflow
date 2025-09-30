"""Bash command execution tool"""

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .base import Tool, ToolResult


class BashExecutor(Tool):
    """Execute bash commands in a controlled environment"""

    def __init__(
        self,
        default_timeout: int = 300,
        allowed_commands: Optional[list[str]] = None,
        denied_commands: Optional[list[str]] = None,
    ):
        super().__init__(
            name="bash_executor",
            description="Execute bash commands safely with timeout and monitoring"
        )
        self.default_timeout = default_timeout
        self.allowed_commands = set(allowed_commands or [])
        self.denied_commands = set(denied_commands or [
            "rm -rf /",
            "sudo rm",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",  # fork bomb
        ])

    def _is_command_allowed(self, command: str) -> tuple[bool, Optional[str]]:
        """Check if command is allowed to execute"""
        # Check denied commands
        for denied in self.denied_commands:
            if denied in command:
                return False, f"Denied command pattern: {denied}"

        # If allowed list exists, check it
        if self.allowed_commands:
            command_name = command.split()[0] if command.strip() else ""
            if command_name not in self.allowed_commands:
                return False, f"Command not in allowed list: {command_name}"

        return True, None

    async def execute(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        """Execute bash command"""
        start_time = time.time()

        # Validate command
        is_allowed, error_msg = self._is_command_allowed(command)
        if not is_allowed:
            return ToolResult(
                success=False,
                error=f"Command blocked: {error_msg}",
                duration=time.time() - start_time
            )

        # Prepare environment
        env = None
        if env_vars:
            import os
            env = os.environ.copy()
            env.update(env_vars)

        # Prepare working directory
        cwd = Path(working_dir) if working_dir else None
        if cwd and not cwd.exists():
            return ToolResult(
                success=False,
                error=f"Working directory does not exist: {working_dir}",
                duration=time.time() - start_time
            )

        # Execute command
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            # Wait with timeout
            timeout_val = timeout or self.default_timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_val
            )

            duration = time.time() - start_time

            return ToolResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8', errors='replace'),
                error=stderr.decode('utf-8', errors='replace') if process.returncode != 0 else None,
                data={
                    "exit_code": process.returncode,
                    "command": command,
                },
                duration=duration
            )

        except asyncio.TimeoutError:
            # Kill the process
            try:
                process.kill()
                await process.wait()
            except:
                pass

            return ToolResult(
                success=False,
                error=f"Command timed out after {timeout_val} seconds",
                duration=time.time() - start_time
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution error: {str(e)}",
                duration=time.time() - start_time
            )

    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for Anthropic tool format"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for command execution (optional)"
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {self.default_timeout})"
                },
                "env_vars": {
                    "type": "object",
                    "description": "Environment variables to set (optional)"
                }
            },
            "required": ["command"]
        }
