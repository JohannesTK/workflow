"""Reviewer agent for analyzing failures and suggesting improvements"""

from typing import List, Optional
from .base_agent import BaseAgent
from ..storage.models import ExecutionResult, FailurePattern


REVIEWER_SYSTEM_PROMPT = """You are a workflow debugging and improvement specialist.

Your role is to analyze workflow failures, identify root causes, and suggest practical improvements.

Expertise:
- Error message interpretation
- Common failure pattern recognition
- Root cause analysis
- Solution recommendation
- Code improvement suggestions

When analyzing failures:
1. Parse error messages carefully
2. Identify the root cause (not just symptoms)
3. Look for patterns across multiple failures
4. Consider environmental factors (network, permissions, dependencies)
5. Suggest specific, actionable fixes

When suggesting improvements:
- Provide concrete code changes
- Explain why the change will help
- Prioritize reliability and error handling
- Consider edge cases
- Add validation and retries where appropriate

Common failure patterns to recognize:
- Network issues (timeouts, connection refused, DNS)
- Authentication/permission errors
- Missing dependencies or tools
- Rate limiting
- Resource exhaustion
- Data format mismatches
- API changes

Always provide:
1. Root cause explanation
2. Specific code changes (show diff or new code)
3. Rationale for the fix
4. Confidence level (high/medium/low)"""


class ReviewerAgent(BaseAgent):
    """Agent specialized in analyzing failures and suggesting improvements"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="reviewer",
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            api_key=api_key,
        )

    async def analyze_failure(
        self,
        result: ExecutionResult,
        code: str,
        language: str,
    ) -> dict:
        """Analyze a workflow failure

        Args:
            result: Failed execution result
            code: Workflow code that failed
            language: Code language

        Returns:
            Dict with analysis and suggested fixes
        """
        prompt = "Analyze this workflow failure:\n\n"
        prompt += f"Workflow: {result.workflow_name}\n"
        prompt += f"Duration: {result.duration:.2f}s\n" if result.duration else ""
        prompt += f"Exit code: {result.exit_code}\n" if result.exit_code else ""

        if result.stdout:
            prompt += f"\nStdout:\n```\n{result.stdout[:2000]}\n```\n"

        if result.stderr:
            prompt += f"\nStderr:\n```\n{result.stderr[:2000]}\n```\n"

        if result.error_message:
            prompt += f"\nError message: {result.error_message}\n"

        prompt += f"\nWorkflow code:\n```{language}\n{code}\n```\n"

        prompt += "\nProvide:\n"
        prompt += "1. Root cause of the failure\n"
        prompt += "2. Specific code changes to fix it\n"
        prompt += "3. Additional improvements to prevent similar issues\n"
        prompt += "4. Confidence level in the fix\n"

        response = await self.send_message(prompt)

        return {
            "analysis": response["message"],
            "usage": response["usage"],
        }

    async def identify_patterns(
        self,
        patterns: List[FailurePattern],
        code: str,
        language: str,
    ) -> dict:
        """Analyze failure patterns and suggest proactive improvements

        Args:
            patterns: Identified failure patterns
            code: Current workflow code
            language: Code language

        Returns:
            Dict with pattern analysis and suggested improvements
        """
        if not patterns:
            return {
                "analysis": "No recurring failure patterns found.",
                "suggestions": [],
            }

        prompt = "Analyze these recurring failure patterns:\n\n"

        for i, pattern in enumerate(patterns, 1):
            prompt += f"{i}. {pattern.pattern_type} (occurred {pattern.count} times)\n"
            prompt += f"   Last seen: {pattern.last_seen}\n"
            if pattern.error_messages:
                prompt += f"   Example: {pattern.error_messages[0][:200]}\n"
            prompt += "\n"

        prompt += f"\nCurrent workflow code:\n```{language}\n{code}\n```\n"

        prompt += "\nProvide:\n"
        prompt += "1. Which patterns indicate systemic issues vs. transient problems\n"
        prompt += "2. Proactive improvements to prevent these failures\n"
        prompt += "3. Prioritized list of code changes\n"
        prompt += "4. Risk assessment of each suggested change\n"

        response = await self.send_message(prompt)

        return {
            "analysis": response["message"],
            "usage": response["usage"],
        }

    async def suggest_improvements(
        self,
        code: str,
        language: str,
        execution_history: Optional[str] = None,
    ) -> dict:
        """Suggest general improvements to workflow

        Args:
            code: Workflow code
            language: Code language
            execution_history: Summary of past executions

        Returns:
            Dict with improvement suggestions
        """
        prompt = f"Review this {language} workflow and suggest improvements:\n\n"
        prompt += f"```{language}\n{code}\n```\n"

        if execution_history:
            prompt += f"\nExecution history:\n{execution_history}\n"

        prompt += "\nSuggest improvements for:\n"
        prompt += "1. Error handling and resilience\n"
        prompt += "2. Code clarity and maintainability\n"
        prompt += "3. Performance optimizations\n"
        prompt += "4. Security considerations\n"
        prompt += "5. Logging and observability\n"

        prompt += "\nFor each suggestion, provide:\n"
        prompt += "- What to change and why\n"
        prompt += "- Code example\n"
        prompt += "- Expected impact\n"

        response = await self.send_message(prompt)

        return {
            "suggestions": response["message"],
            "usage": response["usage"],
        }

    async def compare_executions(
        self,
        success_result: ExecutionResult,
        failure_result: ExecutionResult,
        code: str,
    ) -> dict:
        """Compare successful and failed executions to find differences

        Args:
            success_result: Successful execution
            failure_result: Failed execution
            code: Workflow code

        Returns:
            Dict with comparison insights
        """
        prompt = "Compare these two executions to understand why one failed:\n\n"

        prompt += "SUCCESSFUL EXECUTION:\n"
        prompt += f"Duration: {success_result.duration:.2f}s\n" if success_result.duration else ""
        prompt += f"Output:\n{success_result.stdout[:1000] if success_result.stdout else 'N/A'}\n\n"

        prompt += "FAILED EXECUTION:\n"
        prompt += f"Duration: {failure_result.duration:.2f}s\n" if failure_result.duration else ""
        prompt += f"Output:\n{failure_result.stdout[:1000] if failure_result.stdout else 'N/A'}\n"
        prompt += f"Error:\n{failure_result.stderr[:1000] if failure_result.stderr else 'N/A'}\n\n"

        prompt += "Identify:\n"
        prompt += "1. What changed between executions\n"
        prompt += "2. Possible environmental factors\n"
        prompt += "3. How to make workflow more resilient\n"

        response = await self.send_message(prompt)

        return {
            "comparison": response["message"],
            "usage": response["usage"],
        }
