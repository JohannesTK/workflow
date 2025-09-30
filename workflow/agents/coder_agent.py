"""Coder agent for generating workflow code"""

from typing import Optional
from .base_agent import BaseAgent


CODER_SYSTEM_PROMPT = """You are a workflow code generation specialist for technical users.

Your role is to generate executable bash or Python scripts based on user descriptions.

Guidelines:
- Write clean, well-commented code
- Include comprehensive error handling (try/except for Python, || exit for bash)
- Add progress logging so users can see what's happening
- Use standard CLI tools when possible (curl, jq, awk, sed, psql, aws, etc.)
- Prefer Python for complex logic, data processing, and API calls
- Prefer bash for simple command pipelines and file operations
- Validate inputs and check prerequisites
- Make scripts idempotent when possible
- Never use dangerous commands (rm -rf /, sudo without context, etc.)

Code structure for Python workflows:
```python
#!/usr/bin/env python3
\"\"\"
Workflow: {name}
Description: {description}
\"\"\"

import subprocess
import sys
from pathlib import Path

def main():
    \"\"\"Main workflow execution\"\"\"
    print("Step 1: ...")
    # Implementation

    print("Step 2: ...")
    # Implementation

    print("✓ Workflow completed successfully")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
```

Code structure for bash workflows:
```bash
#!/bin/bash
# Workflow: {name}
# Description: {description}

set -euo pipefail  # Exit on error, undefined vars, pipe failures

echo "Step 1: ..."
# Implementation

echo "Step 2: ..."
# Implementation

echo "✓ Workflow completed successfully"
```

When generating code:
1. Ask clarifying questions if the user's description is ambiguous
2. Show the generated code with explanation
3. Explain what each major section does
4. Mention any prerequisites (packages, tools, environment variables)
5. Suggest testing the workflow in a safe environment first

Always prioritize user control and safety."""


class CoderAgent(BaseAgent):
    """Agent specialized in generating workflow code"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="coder",
            system_prompt=CODER_SYSTEM_PROMPT,
            api_key=api_key,
        )

    async def generate_workflow(
        self,
        name: str,
        description: str,
        language: str = "auto",
        additional_context: Optional[str] = None,
    ) -> dict:
        """Generate workflow code

        Args:
            name: Workflow name
            description: What the workflow should do
            language: "python", "bash", or "auto" to let agent decide
            additional_context: Extra context or requirements

        Returns:
            Dict with:
                - code: Generated code
                - language: Chosen language
                - explanation: Explanation of the code
                - prerequisites: Required tools/packages
        """
        # Build prompt
        prompt = f"Generate a workflow script:\n\n"
        prompt += f"Name: {name}\n"
        prompt += f"Description: {description}\n"

        if language != "auto":
            prompt += f"Language: {language}\n"
        else:
            prompt += "Language: Choose the most appropriate (bash or Python)\n"

        if additional_context:
            prompt += f"\nAdditional context:\n{additional_context}\n"

        prompt += "\nGenerate the complete, executable code with detailed comments."

        # Get response from Claude
        response = await self.send_message(prompt)

        return {
            "message": response["message"],
            "usage": response["usage"],
        }

    async def improve_workflow(
        self,
        code: str,
        language: str,
        issues: list[str],
        execution_history: Optional[str] = None,
    ) -> dict:
        """Improve existing workflow code based on feedback

        Args:
            code: Current workflow code
            language: Code language
            issues: List of issues to fix
            execution_history: Recent execution history/errors

        Returns:
            Dict with improved code and explanation
        """
        prompt = "Improve this workflow code:\n\n"
        prompt += f"```{language}\n{code}\n```\n\n"
        prompt += "Issues to address:\n"
        for i, issue in enumerate(issues, 1):
            prompt += f"{i}. {issue}\n"

        if execution_history:
            prompt += f"\nRecent execution history:\n{execution_history}\n"

        prompt += "\nProvide the complete improved code with explanation of changes."

        response = await self.send_message(prompt)

        return {
            "message": response["message"],
            "usage": response["usage"],
        }

    async def explain_code(self, code: str, language: str) -> dict:
        """Explain what a workflow code does

        Args:
            code: Code to explain
            language: Code language

        Returns:
            Dict with explanation
        """
        prompt = f"Explain what this {language} workflow does:\n\n"
        prompt += f"```{language}\n{code}\n```\n\n"
        prompt += "Provide a clear, step-by-step explanation."

        response = await self.send_message(prompt)

        return {
            "message": response["message"],
            "usage": response["usage"],
        }
