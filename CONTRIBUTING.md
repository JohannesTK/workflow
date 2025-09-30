# Contributing to workflow

Thanks for your interest in improving the workflow automation tool!

## Development Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd coworker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e ".[dev]"
```

4. Set up your API key:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Project Structure

```
workflow/
├── agents/          # AI agents (orchestrator, coder, executor, reviewer)
├── tools/           # Execution tools (bash, python executors)
├── storage/         # Persistence layer (workflows, history)
└── cli.py           # CLI interface
```

## Making Changes

### Adding a New Agent

1. Create file in `workflow/agents/`
2. Inherit from `BaseAgent`
3. Define system prompt
4. Implement key methods
5. Add to orchestrator

Example:
```python
from .base_agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, api_key=None):
        super().__init__(
            name="my_agent",
            system_prompt="You are...",
            api_key=api_key
        )

    async def my_method(self, input: str) -> dict:
        response = await self.send_message(input)
        return {"result": response["message"]}
```

### Adding a New Tool

1. Create file in `workflow/tools/`
2. Inherit from `Tool`
3. Implement `execute()` and `get_input_schema()`

Example:
```python
from .base import Tool, ToolResult

class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="What this tool does"
        )

    async def execute(self, **kwargs) -> ToolResult:
        # Implementation
        return ToolResult(
            success=True,
            output="result"
        )

    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
```

### Adding a CLI Command

1. Add function to `workflow/cli.py`
2. Decorate with `@app.command()`
3. Use Typer for arguments and options

Example:
```python
@app.command()
def mycommand(
    arg: str = typer.Argument(..., help="Description"),
    option: bool = typer.Option(False, "--flag", help="Description"),
):
    """Command description"""
    # Implementation
```

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Format with Black: `black .`
- Lint with Ruff: `ruff check .`

## Testing

### Run Tests
```bash
pytest
```

### Write Tests
```python
# tests/test_agents.py
import pytest
from workflow.agents import CoderAgent

@pytest.mark.asyncio
async def test_coder_generates_code():
    coder = CoderAgent()
    result = await coder.generate_workflow(
        name="test",
        description="Print hello"
    )
    assert "print" in result["message"].lower()
```

## Documentation

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for technical changes
- Add examples to examples/ directory
- Update QUICKSTART.md for new features

## Commit Guidelines

Use conventional commits:
```
feat: Add workflow composition feature
fix: Handle timeout errors in executor
docs: Update quickstart guide
refactor: Simplify coder agent logic
test: Add integration tests for orchestrator
```

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Add tests
4. Update documentation
5. Run linters and tests
6. Submit PR with description

## Ideas for Contributions

### High Priority
- [ ] Add automated tests (unit + integration)
- [ ] Improve error messages
- [ ] Add workflow templates
- [ ] Better pattern detection algorithms
- [ ] Performance optimizations

### Medium Priority
- [ ] Workflow composition (chain workflows)
- [ ] Scheduling integration
- [ ] MCP server support
- [ ] Remote execution
- [ ] Workflow marketplace

### Nice to Have
- [ ] Web UI
- [ ] Workflow visualization
- [ ] Step debugging
- [ ] Cloud execution
- [ ] Monitoring dashboard

## Questions?

Open an issue or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
