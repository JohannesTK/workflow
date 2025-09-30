"""Executor agent for running workflows"""

from datetime import datetime
from typing import Optional
from .base_agent import BaseAgent
from ..storage.models import ExecutionResult, WorkflowStatus, WorkflowLanguage
from ..tools.bash_executor import BashExecutor
from ..tools.python_executor import PythonExecutor


EXECUTOR_SYSTEM_PROMPT = """You are a workflow execution specialist.

Your role is to safely execute workflows and provide clear feedback on their progress and results.

Responsibilities:
- Execute workflows in a controlled environment
- Monitor execution progress
- Capture all output (stdout and stderr)
- Detect and report failures clearly
- Provide timing information
- Suggest next steps based on results

When executing workflows:
1. Validate the workflow code before execution
2. Check for required dependencies
3. Execute with appropriate timeout
4. Monitor for common failure patterns
5. Provide detailed execution summary

Safety guidelines:
- Never execute code that could harm the system
- Respect timeout limits
- Capture and sanitize all output
- Report errors with context

Output format:
- Use clear progress indicators (Step 1/N, ✓, ✗)
- Show execution time for each step
- Highlight warnings and errors
- Provide actionable error messages"""


class ExecutorAgent(BaseAgent):
    """Agent specialized in executing workflows"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="executor",
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
            api_key=api_key,
        )

        # Initialize executors
        self.bash_executor = BashExecutor()
        self.python_executor = PythonExecutor()

    async def execute_workflow(
        self,
        workflow_name: str,
        code: str,
        language: WorkflowLanguage,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute a workflow

        Args:
            workflow_name: Name of the workflow
            code: Code to execute
            language: Language (bash or python)
            timeout: Execution timeout in seconds
            working_dir: Working directory

        Returns:
            ExecutionResult with outcome
        """
        started_at = datetime.now()

        try:
            # Execute based on language
            if language == WorkflowLanguage.BASH:
                result = await self.bash_executor.execute(
                    command=code,
                    timeout=timeout,
                    working_dir=working_dir,
                )
            elif language == WorkflowLanguage.PYTHON:
                result = await self.python_executor.execute(
                    code=code,
                    timeout=timeout,
                    working_dir=working_dir,
                )
            else:
                return ExecutionResult(
                    workflow_name=workflow_name,
                    status=WorkflowStatus.FAILED,
                    started_at=started_at,
                    finished_at=datetime.now(),
                    error_message=f"Unsupported language: {language}",
                )

            finished_at = datetime.now()

            # Convert tool result to execution result
            return ExecutionResult(
                workflow_name=workflow_name,
                status=WorkflowStatus.SUCCESS if result.success else WorkflowStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                duration=result.duration,
                exit_code=result.data.get("exit_code") if result.data else None,
                stdout=result.output,
                stderr=result.error,
                error_message=result.error if not result.success else None,
            )

        except Exception as e:
            return ExecutionResult(
                workflow_name=workflow_name,
                status=WorkflowStatus.FAILED,
                started_at=started_at,
                finished_at=datetime.now(),
                error_message=f"Execution error: {str(e)}",
            )

    async def validate_workflow(
        self,
        code: str,
        language: WorkflowLanguage,
    ) -> dict:
        """Validate workflow code before execution

        Args:
            code: Code to validate
            language: Code language

        Returns:
            Dict with validation results
        """
        prompt = f"Validate this {language.value} workflow code for safety and correctness:\n\n"
        prompt += f"```{language.value}\n{code}\n```\n\n"
        prompt += "Check for:\n"
        prompt += "1. Dangerous commands (rm -rf, mkfs, etc.)\n"
        prompt += "2. Syntax errors\n"
        prompt += "3. Missing error handling\n"
        prompt += "4. Required dependencies\n"
        prompt += "5. Potential issues\n\n"
        prompt += "Respond with: SAFE or UNSAFE, followed by explanation."

        response = await self.send_message(prompt)

        is_safe = "SAFE" in response["message"] and "UNSAFE" not in response["message"]

        return {
            "is_safe": is_safe,
            "message": response["message"],
            "usage": response["usage"],
        }

    async def analyze_execution(
        self,
        result: ExecutionResult,
    ) -> dict:
        """Analyze execution result and provide insights

        Args:
            result: Execution result to analyze

        Returns:
            Dict with analysis
        """
        prompt = "Analyze this workflow execution:\n\n"
        prompt += f"Status: {result.status.value}\n"
        prompt += f"Duration: {result.duration:.2f}s\n" if result.duration else "Duration: N/A\n"

        if result.stdout:
            prompt += f"\nStdout:\n{result.stdout[:1000]}\n"  # Limit to 1000 chars

        if result.stderr:
            prompt += f"\nStderr:\n{result.stderr[:1000]}\n"

        if result.error_message:
            prompt += f"\nError: {result.error_message}\n"

        prompt += "\nProvide:\n"
        prompt += "1. Summary of what happened\n"
        prompt += "2. Root cause if failed\n"
        prompt += "3. Suggested next steps\n"

        response = await self.send_message(prompt)

        return {
            "analysis": response["message"],
            "usage": response["usage"],
        }
