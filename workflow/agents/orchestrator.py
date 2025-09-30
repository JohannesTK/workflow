"""Main orchestrator agent that coordinates subagents"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from .coder_agent import CoderAgent
from .executor_agent import ExecutorAgent
from .reviewer_agent import ReviewerAgent
from ..storage.workflow_store import WorkflowStore
from ..storage.history_store import HistoryStore
from ..storage.models import WorkflowConfig, WorkflowLanguage, WorkflowStatus


console = Console()


class Orchestrator:
    """Main orchestrator that coordinates workflow operations"""

    def __init__(
        self,
        workflow_store: Optional[WorkflowStore] = None,
        history_store: Optional[HistoryStore] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize orchestrator

        Args:
            workflow_store: Workflow storage (optional)
            history_store: Execution history storage (optional)
            api_key: Anthropic API key (optional, defaults to env var)
        """
        self.workflow_store = workflow_store or WorkflowStore()
        self.history_store = history_store or HistoryStore()

        # Initialize subagents
        self.coder = CoderAgent(api_key=api_key)
        self.executor = ExecutorAgent(api_key=api_key)
        self.reviewer = ReviewerAgent(api_key=api_key)

    async def teach_workflow(
        self,
        name: str,
        description: str,
        language: str = "auto",
        interactive: bool = True,
    ) -> Optional[WorkflowConfig]:
        """Teach a new workflow

        Args:
            name: Workflow name
            description: What the workflow should do
            language: Language preference (auto, bash, python)
            interactive: Whether to ask for confirmation

        Returns:
            WorkflowConfig if successful, None otherwise
        """
        console.print(f"\n[bold blue]Creating workflow:[/] {name}")
        console.print(f"[dim]{description}[/]\n")

        # Check if workflow already exists
        if self.workflow_store.exists(name):
            console.print(f"[yellow]Warning:[/] Workflow '{name}' already exists.")
            if interactive:
                from rich.prompt import Confirm
                if not Confirm.ask("Overwrite?"):
                    return None

        # Generate code using coder agent
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating workflow code...", total=None)

            result = await self.coder.generate_workflow(
                name=name,
                description=description,
                language=language,
            )

            progress.remove_task(task)

        # Extract code from response
        code = self._extract_code_from_response(result["message"])
        detected_language = self._detect_language(code)

        # Show generated code
        console.print(Panel(
            Syntax(code, detected_language, theme="monokai", line_numbers=True),
            title=f"Generated {detected_language.upper()} Code",
            border_style="green",
        ))

        console.print(f"\n[dim]Explanation:[/]")
        # Show explanation (everything except code blocks)
        explanation = self._extract_explanation(result["message"])
        console.print(explanation)

        # Ask for confirmation
        if interactive:
            from rich.prompt import Confirm
            if not Confirm.ask("\n[bold]Save this workflow?[/]", default=True):
                console.print("[yellow]Workflow not saved.[/]")
                return None

        # Save workflow
        workflow = WorkflowConfig(
            name=name,
            description=description,
            language=WorkflowLanguage(detected_language),
            code=code,
        )

        self.workflow_store.save(workflow)
        console.print(f"\n[green]✓[/] Workflow '{name}' saved successfully!")

        # Offer to test
        if interactive:
            from rich.prompt import Confirm
            if Confirm.ask("\n[bold]Test the workflow now?[/]", default=False):
                await self.run_workflow(name, interactive=True)

        return workflow

    async def run_workflow(
        self,
        name: str,
        interactive: bool = True,
    ) -> Optional[bool]:
        """Run a workflow

        Args:
            name: Workflow name
            interactive: Whether to show progress and ask for confirmation

        Returns:
            True if successful, False if failed, None if cancelled
        """
        # Load workflow
        workflow = self.workflow_store.load(name)
        if not workflow:
            console.print(f"[red]Error:[/] Workflow '{name}' not found.")
            return None

        console.print(f"\n[bold blue]Running workflow:[/] {name}")
        console.print(f"[dim]{workflow.description}[/]\n")

        # Validate workflow if interactive
        if interactive:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Validating workflow...", total=None)

                validation = await self.executor.validate_workflow(
                    code=workflow.code,
                    language=workflow.language,
                )

                progress.remove_task(task)

            if not validation["is_safe"]:
                console.print(f"[red]✗ Validation failed:[/]")
                console.print(validation["message"])

                from rich.prompt import Confirm
                if not Confirm.ask("\n[yellow]Run anyway?[/]", default=False):
                    return None

        # Execute workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Executing workflow...", total=None)

            result = await self.executor.execute_workflow(
                workflow_name=name,
                code=workflow.code,
                language=workflow.language,
                timeout=workflow.timeout,
            )

            progress.remove_task(task)

        # Save execution to history
        self.history_store.save_execution(result)

        # Show results
        if result.status == WorkflowStatus.SUCCESS:
            console.print(f"[green]✓ Workflow completed successfully![/]")
            if result.duration:
                console.print(f"[dim]Duration: {result.duration:.2f}s[/]")

            if result.stdout:
                console.print(f"\n[bold]Output:[/]")
                console.print(result.stdout)

            return True

        else:
            console.print(f"[red]✗ Workflow failed![/]")
            if result.duration:
                console.print(f"[dim]Duration: {result.duration:.2f}s[/]")

            if result.stderr:
                console.print(f"\n[bold red]Error output:[/]")
                console.print(result.stderr)

            if result.error_message:
                console.print(f"\n[bold red]Error:[/] {result.error_message}")

            # Offer analysis if interactive
            if interactive:
                from rich.prompt import Confirm
                if Confirm.ask("\n[bold]Analyze failure and suggest fixes?[/]", default=True):
                    await self._analyze_and_fix(name, result, workflow)

            return False

    async def _analyze_and_fix(
        self,
        workflow_name: str,
        result,
        workflow: WorkflowConfig,
    ) -> None:
        """Analyze failure and offer to fix"""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing failure...", total=None)

            analysis = await self.reviewer.analyze_failure(
                result=result,
                code=workflow.code,
                language=workflow.language.value,
            )

            progress.remove_task(task)

        console.print(f"\n[bold cyan]Analysis:[/]")
        console.print(analysis["analysis"])

        # Offer to apply fixes
        from rich.prompt import Confirm
        if Confirm.ask("\n[bold]Apply suggested fixes?[/]", default=True):
            # Extract improved code from analysis
            # (In a real implementation, we'd parse the suggestions more carefully)
            console.print("[yellow]Auto-fix not yet implemented. Please review the suggestions above.[/]")

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from markdown code blocks"""
        import re

        # Find code blocks
        pattern = r"```(?:python|bash|sh)?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # If no code blocks, return the whole response
        return response.strip()

    def _extract_explanation(self, response: str) -> str:
        """Extract explanation (non-code) parts"""
        import re

        # Remove code blocks
        pattern = r"```(?:python|bash|sh)?.*?```"
        explanation = re.sub(pattern, "[code block shown above]", response, flags=re.DOTALL)

        return explanation.strip()

    def _detect_language(self, code: str) -> str:
        """Detect code language"""
        if code.startswith("#!/bin/bash") or code.startswith("#!/bin/sh"):
            return "bash"
        elif code.startswith("#!/usr/bin/env python") or "import " in code[:100]:
            return "python"
        elif "echo " in code or "set -e" in code:
            return "bash"
        else:
            return "python"  # Default
