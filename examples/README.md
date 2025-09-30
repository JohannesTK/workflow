# Workflow Examples

This directory contains examples of using the workflow automation tool.

## Quick Start

1. Install the tool:
```bash
pip install -e ..
```

2. Set your API key:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

3. Create a workflow:
```bash
workflow teach daily-backup "Backup important files to external drive"
```

4. Run it:
```bash
workflow run daily-backup
```

## Example Workflows

### Data Processing
```bash
workflow teach data-pipeline "Fetch data from API, transform with jq, save to CSV"
```

### System Administration
```bash
workflow teach cleanup "Find and delete log files older than 30 days"
```

### Development
```bash
workflow teach deploy "Run tests, build docker image, push to registry"
```

### Reporting
```bash
workflow teach weekly-report "Query database, generate charts, send email"
```

## Testing

Run the simple test:
```bash
python examples/simple_test.py
```

## Tips

- Use `workflow list` to see all workflows
- Use `workflow history <name>` to see execution history
- Use `workflow improve <name>` to get AI-powered improvement suggestions
- Edit workflows directly with `workflow edit <name>`
