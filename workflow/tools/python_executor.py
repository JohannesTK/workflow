"""Python code execution tool"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .base import Tool, ToolResult


class PythonExecutor(Tool):
    """Execute Python code in a controlled environment"""

    def __init__(
        self,
        default_timeout: int = 300,
        use_virtualenv: bool = False,
        python_path: Optional[str] = None,
    ):
        super().__init__(
            name="python_executor",
            description="Execute Python code safely with timeout and monitoring"
        )
        self.default_timeout = default_timeout
        self.use_virtualenv = use_virtualenv
        self.python_path = python_path or sys.executable

    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        requirements: Optional[list[str]] = None,
        working_dir: Optional[str] = None,
    ) -> ToolResult:
        """Execute Python code"""
        start_time = time.time()

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            # Install requirements if provided
            if requirements:
                pip_result = await self._install_requirements(requirements)
                if not pip_result.success:
                    return pip_result

            # Prepare working directory
            cwd = Path(working_dir) if working_dir else Path.cwd()

            # Execute code
            process = await asyncio.create_subprocess_exec(
                self.python_path,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
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
                error=f"Code execution timed out after {timeout_val} seconds",
                duration=time.time() - start_time
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution error: {str(e)}",
                duration=time.time() - start_time
            )

        finally:
            # Clean up temp file
            try:
                Path(script_path).unlink()
            except:
                pass

    async def _install_requirements(self, requirements: list[str]) -> ToolResult:
        """Install Python packages"""
        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                self.python_path,
                "-m", "pip", "install",
                *requirements,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120  # 2 minutes for pip install
            )

            return ToolResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8', errors='replace'),
                error=stderr.decode('utf-8', errors='replace') if process.returncode != 0 else None,
                duration=time.time() - start_time
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to install requirements: {str(e)}",
                duration=time.time() - start_time
            )

    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for Anthropic tool format"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {self.default_timeout})"
                },
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Python packages to install before execution (optional)"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for code execution (optional)"
                }
            },
            "required": ["code"]
        }
