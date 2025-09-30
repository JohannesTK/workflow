# Quick Start Guide

Get started with workflow automation in 5 minutes!

## Installation

```bash
# Clone or navigate to the project
cd coworker

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install anthropic typer rich pyyaml pydantic aiosqlite
```

## Setup

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Your First Workflow

### 1. Create a workflow

```bash
workflow teach hello-world "Print hello world and the current date"
```

The agent will:
- Generate appropriate code (bash or Python)
- Show you the code for review
- Ask if you want to save it
- Offer to test it immediately

### 2. Run the workflow

```bash
workflow run hello-world
```

### 3. View all workflows

```bash
workflow list
```

### 4. Check execution history

```bash
workflow history hello-world
```

## Real-World Examples

### Example 1: Database Backup

```bash
workflow teach db-backup \
  "Dump postgres database myapp to file, compress it, upload to S3 bucket my-backups"
```

The agent will generate something like:

```bash
#!/bin/bash
set -euo pipefail

echo "Step 1: Dumping database..."
pg_dump -U postgres myapp > /tmp/backup_$(date +%Y%m%d).sql

echo "Step 2: Compressing..."
gzip /tmp/backup_$(date +%Y%m%d).sql

echo "Step 3: Uploading to S3..."
aws s3 cp /tmp/backup_$(date +%Y%m%d).sql.gz s3://my-backups/

echo "✓ Backup completed successfully"
```

### Example 2: Data Pipeline

```bash
workflow teach sales-report \
  "Fetch sales data from https://api.example.com/sales, parse JSON with jq, calculate totals with Python pandas, save to CSV"
```

The agent will generate a Python script with proper error handling:

```python
#!/usr/bin/env python3
import requests
import pandas as pd
import json

def main():
    print("Step 1: Fetching sales data...")
    response = requests.get("https://api.example.com/sales")
    response.raise_for_status()
    data = response.json()

    print("Step 2: Processing data...")
    df = pd.DataFrame(data['sales'])
    totals = df.groupby('region')['amount'].sum()

    print("Step 3: Saving to CSV...")
    totals.to_csv('sales_report.csv')

    print("✓ Report generated successfully")
    return 0

if __name__ == "__main__":
    main()
```

### Example 3: Development Workflow

```bash
workflow teach deploy-staging \
  "Run pytest tests, if they pass build docker image, tag with git commit hash, push to ECR, update ECS service"
```

## Advanced Features

### Interactive Improvement

When a workflow fails, the tool automatically offers to analyze the failure:

```bash
workflow run data-pipeline
# If it fails:
# ✗ Workflow failed!
# Analyze failure and suggest fixes? [Y/n]
```

The reviewer agent will:
- Identify the root cause
- Suggest specific code changes
- Explain why the failure happened

### Manual Improvement

Get improvement suggestions anytime:

```bash
workflow improve my-workflow
```

### View Statistics

```bash
workflow stats db-backup

# Output:
# Total Executions: 45
# Successful: 43
# Failed: 2
# Success Rate: 95.6%
# Avg Duration: 12.3s
```

### Edit Manually

```bash
workflow edit my-workflow
# Opens in $EDITOR
```

### View Code

```bash
workflow show my-workflow
```

## How It Works

The tool uses three specialized AI agents:

1. **Coder Agent** - Generates workflow code from descriptions
2. **Executor Agent** - Runs workflows safely with monitoring
3. **Reviewer Agent** - Analyzes failures and suggests improvements

All workflows are stored as plain files in `~/workflows/`, so you can:
- Version control them with git
- Share them with teammates
- Edit them manually
- Back them up easily

## CLI Reference

```bash
workflow teach <name> <description>  # Create workflow
workflow run <name>                  # Run workflow
workflow list                        # List all workflows
workflow show <name>                 # View workflow details
workflow edit <name>                 # Edit in $EDITOR
workflow delete <name>               # Delete workflow
workflow history [name]              # View execution history
workflow improve <name>              # Get improvement suggestions
workflow stats <name>                # View statistics
```

## Workflow Storage

Workflows are stored in `~/workflows/`:

```
~/workflows/
├── db-backup/
│   ├── config.yaml          # Metadata
│   ├── workflow.sh          # Generated code
│   ├── CLAUDE.md           # Agent memory
│   └── history.jsonl       # Execution log
└── history.db              # SQLite database
```

## Tips

1. **Start simple** - Begin with straightforward workflows and let the agent handle complexity

2. **Review generated code** - Always review what the agent generates before running

3. **Iterate on failures** - Use the reviewer agent to improve workflows based on real failures

4. **Compose workflows** - Break complex tasks into smaller workflows and chain them

5. **Learn from history** - Check `workflow history` to see patterns and improve reliability

## Troubleshooting

### API Key Issues
```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Or set it in ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY=sk-ant-...
```

### Workflow Not Found
```bash
# List all workflows
workflow list

# Check if it exists
ls ~/workflows/
```

### Permission Errors
```bash
# Make sure workflow directory is writable
chmod 755 ~/workflows/
```

## Next Steps

- Explore the `examples/` directory for more complex workflows
- Read the architecture docs to understand the agent system
- Contribute improvements or report issues on GitHub

Happy automating! 🚀
