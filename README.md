# workflow - Agent-based CLI Automation

An intelligent CLI tool that helps technical users automate their daily workflows using AI agents.

## Features

- 🤖 **Agent-based architecture** - Orchestrator + specialized subagents (Coder, Executor, Reviewer)
- 📝 **Natural language workflow creation** - Describe what you want, get executable code
- 🔄 **Learn from failures** - Reviewer agent analyzes errors and suggests improvements
- 🔧 **Code-first approach** - All workflows are readable Python/bash scripts
- 🧩 **Composable workflows** - Chain multiple workflows together
- 📊 **Execution history** - Learn from past runs to improve reliability

## Quick Start

```bash
# Install
pip install -e .

# Set up API key
export ANTHROPIC_API_KEY=your_key_here

# Create your first workflow
workflow teach daily-backup "Backup my postgres database to S3"

# Run it
workflow run daily-backup

# View history
workflow history daily-backup
```

## Architecture

```
Orchestrator Agent
├── Coder Agent (generates scripts)
├── Executor Agent (runs workflows safely)
└── Reviewer Agent (analyzes failures, suggests fixes)
```

## Examples

### Data Pipeline
```bash
workflow teach etl-job "Fetch sales data from API, transform with pandas, load to warehouse"
```

### DevOps Workflow
```bash
workflow teach deploy "Run tests, build docker image, push to ECR, update ECS"
```

### System Admin
```bash
workflow teach backup "Tar important directories, encrypt, sync to S3"
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check .
```

## License

MIT
