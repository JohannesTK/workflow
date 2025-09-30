"""CLI interface for workflow automation tool"""

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .agents.orchestrator import Orchestrator
from .storage.workflow_store import WorkflowStore
from .storage.history_store import HistoryStore
from .storage.models import WorkflowStatus


app = typer.Typer(
    name="workflow",
    help="Agent-based CLI automation tool for technical users",
    add_completion=False,
)

console = Console()


def get_orchestrator() -> Orchestrator:
    """Get orchestrator instance"""
    return Orchestrator()


@app.command()
def teach(
    name: str = typer.Argument(..., help="Workflow name"),
    description: str = typer.Argument(..., help="What the workflow should do"),
    language: str = typer.Option("auto", "--lang", "-l", help="Language (auto/bash/python)"),
    non_interactive: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
):
    """Create a new workflow by describing what it should do"""

    async def _teach():
        orch = get_orchestrator()
        await orch.teach_workflow(
            name=name,
            description=description,
            language=language,
            interactive=not non_interactive,
        )

    asyncio.run(_teach())


@app.command()
def run(
    name: str = typer.Argument(..., help="Workflow name"),
    non_interactive: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
):
    """Run a workflow"""

    async def _run():
        orch = get_orchestrator()
        await orch.run_workflow(
            name=name,
            interactive=not non_interactive,
        )

    asyncio.run(_run())


@app.command()
def list():
    """List all workflows"""
    store = WorkflowStore()
    workflows = store.list_workflows()

    if not workflows:
        console.print("[yellow]No workflows found.[/]")
        console.print("\nCreate one with: [bold]workflow teach <name> <description>[/]")
        return

    table = Table(title="Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Language", style="green")

    for wf_name in workflows:
        wf = store.load(wf_name)
        if wf:
            table.add_row(
                wf.name,
                wf.description[:50] + "..." if len(wf.description) > 50 else wf.description,
                wf.language.value,
            )

    console.print(table)


@app.command()
def show(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Show workflow details and code"""
    store = WorkflowStore()
    workflow = store.load(name)

    if not workflow:
        console.print(f"[red]Error:[/] Workflow '{name}' not found.")
        raise typer.Exit(1)

    # Show details
    console.print(Panel(
        f"[bold]Name:[/] {workflow.name}\n"
        f"[bold]Description:[/] {workflow.description}\n"
        f"[bold]Language:[/] {workflow.language.value}\n"
        f"[bold]Created:[/] {workflow.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"[bold]Timeout:[/] {workflow.timeout}s",
        title="Workflow Details",
        border_style="blue",
    ))

    # Show code
    console.print(f"\n[bold]Code:[/]")
    console.print(Panel(
        Syntax(workflow.code, workflow.language.value, theme="monokai", line_numbers=True),
        border_style="green",
    ))


@app.command()
def history(
    name: Optional[str] = typer.Argument(None, help="Workflow name (optional)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of executions to show"),
    failed_only: bool = typer.Option(False, "--failed", "-f", help="Show only failed executions"),
):
    """Show execution history"""
    store = HistoryStore()

    status_filter = WorkflowStatus.FAILED if failed_only else None
    executions = store.get_executions(
        workflow_name=name,
        status=status_filter,
        limit=limit,
    )

    if not executions:
        console.print("[yellow]No execution history found.[/]")
        return

    table = Table(title=f"Execution History{' for ' + name if name else ''}")
    table.add_column("Workflow", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Started At", style="white")
    table.add_column("Duration", style="green")

    for exe in executions:
        status_style = "green" if exe.status == WorkflowStatus.SUCCESS else "red"
        table.add_row(
            exe.workflow_name,
            f"[{status_style}]{exe.status.value}[/]",
            exe.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            f"{exe.duration:.2f}s" if exe.duration else "N/A",
        )

    console.print(table)

    # Show stats if for specific workflow
    if name:
        stats = store.get_stats(name)
        console.print(f"\n[bold]Statistics:[/]")
        console.print(f"  Total executions: {stats['total_executions']}")
        console.print(f"  Successful: {stats['successful']}")
        console.print(f"  Failed: {stats['failed']}")
        console.print(f"  Success rate: {stats['success_rate']:.1f}%")
        console.print(f"  Avg duration: {stats['avg_duration']:.2f}s")


@app.command()
def delete(
    name: str = typer.Argument(..., help="Workflow name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a workflow"""
    store = WorkflowStore()

    if not store.exists(name):
        console.print(f"[red]Error:[/] Workflow '{name}' not found.")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm
        if not Confirm.ask(f"[bold red]Delete workflow '{name}'?[/]"):
            console.print("[yellow]Cancelled.[/]")
            return

    store.delete(name)
    console.print(f"[green]✓[/] Workflow '{name}' deleted.")


@app.command()
def edit(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Edit workflow code in your default editor"""
    import os
    import subprocess

    store = WorkflowStore()
    workflow = store.load(name)

    if not workflow:
        console.print(f"[red]Error:[/] Workflow '{name}' not found.")
        raise typer.Exit(1)

    # Get code file path
    ext = "sh" if workflow.language.value == "bash" else "py"
    code_path = store._get_code_path(name, workflow.language)

    # Open in editor
    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(code_path)])

    # Reload workflow to show changes
    updated = store.load(name)
    if updated and updated.code != workflow.code:
        console.print(f"[green]✓[/] Workflow '{name}' updated.")
    else:
        console.print("[dim]No changes made.[/]")


@app.command()
def improve(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Analyze workflow and suggest improvements"""

    async def _improve():
        orch = get_orchestrator()
        store = WorkflowStore()
        history_store = HistoryStore()

        workflow = store.load(name)
        if not workflow:
            console.print(f"[red]Error:[/] Workflow '{name}' not found.")
            return

        # Get failure patterns
        patterns = history_store.get_failure_patterns(name)

        if patterns:
            console.print(f"\n[bold yellow]Found {len(patterns)} failure patterns:[/]")
            for p in patterns:
                console.print(f"  • {p.pattern_type}: {p.count} occurrences")

            analysis = await orch.reviewer.identify_patterns(
                patterns=patterns,
                code=workflow.code,
                language=workflow.language.value,
            )

            console.print(f"\n[bold cyan]Analysis:[/]")
            console.print(analysis["analysis"])
        else:
            # General improvement suggestions
            suggestions = await orch.reviewer.suggest_improvements(
                code=workflow.code,
                language=workflow.language.value,
            )

            console.print(f"\n[bold cyan]Improvement Suggestions:[/]")
            console.print(suggestions["suggestions"])

    asyncio.run(_improve())


@app.command()
def stats(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Show workflow statistics"""
    store = HistoryStore()

    if not WorkflowStore().exists(name):
        console.print(f"[red]Error:[/] Workflow '{name}' not found.")
        raise typer.Exit(1)

    stats = store.get_stats(name)

    panel = Panel(
        f"[bold]Total Executions:[/] {stats['total_executions']}\n"
        f"[bold]Successful:[/] [green]{stats['successful']}[/]\n"
        f"[bold]Failed:[/] [red]{stats['failed']}[/]\n"
        f"[bold]Success Rate:[/] {stats['success_rate']:.1f}%\n"
        f"[bold]Avg Duration:[/] {stats['avg_duration']:.2f}s",
        title=f"Statistics for '{name}'",
        border_style="blue",
    )

    console.print(panel)


@app.callback()
def main():
    """
    workflow - Agent-based CLI automation tool

    Create, run, and manage automated workflows using AI agents.
    """
    pass


if __name__ == "__main__":
    app()
