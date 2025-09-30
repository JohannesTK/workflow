# Architecture

This document explains the architecture of the workflow automation tool.

## Overview

The tool uses an **agent-based architecture** inspired by Claude Agent SDK and CoAct, where specialized AI agents work together to create, execute, and improve workflows.

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Interface (Typer)                 │
│  teach | run | list | improve | history | stats        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Orchestrator Agent                         │
│  • Coordinates workflow lifecycle                       │
│  • Manages conversation flow                            │
│  • Delegates to specialized subagents                   │
└──┬──────────────┬──────────────┬────────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌────────────┐ ┌──────────────┐ ┌────────────────┐
│ Coder      │ │ Executor     │ │ Reviewer       │
│ Agent      │ │ Agent        │ │ Agent          │
│            │ │              │ │                │
│ Generates  │ │ Runs code    │ │ Analyzes       │
│ workflow   │ │ safely       │ │ failures       │
│ code       │ │              │ │ Suggests fixes │
└────────────┘ └──────────────┘ └────────────────┘
      │              │                  │
      └──────────────┴──────────────────┘
                     │
        ┌────────────▼────────────────────────────┐
        │          Tool Layer                     │
        │  • BashExecutor                         │
        │  • PythonExecutor                       │
        │  • Safe sandboxed execution             │
        └─────────────┬───────────────────────────┘
                      │
        ┌─────────────▼───────────────────────────┐
        │       Storage Layer                     │
        │  • WorkflowStore (YAML + code files)    │
        │  • HistoryStore (SQLite)                │
        │  • Agent memory (CLAUDE.md)             │
        └─────────────────────────────────────────┘
```

## Core Components

### 1. Agents

All agents inherit from `BaseAgent` which provides:
- Claude API integration
- Conversation history management
- Tool use support
- Streaming capabilities

#### Orchestrator Agent

**Location**: `workflow/agents/orchestrator.py`

**Responsibilities**:
- Entry point for all workflow operations
- Coordinates between specialized agents
- Manages user interaction flow
- Handles workflow lifecycle (create, run, analyze)

**Key Methods**:
- `teach_workflow()` - Create new workflow
- `run_workflow()` - Execute workflow
- `_analyze_and_fix()` - Analyze failures

#### Coder Agent

**Location**: `workflow/agents/coder_agent.py`

**System Prompt**: Specialized for generating clean, safe, well-documented code

**Responsibilities**:
- Generate workflow code from natural language
- Choose appropriate language (bash vs Python)
- Add error handling and logging
- Provide code explanations
- Improve existing code

**Key Methods**:
- `generate_workflow()` - Generate new workflow code
- `improve_workflow()` - Improve based on feedback
- `explain_code()` - Explain what code does

**Code Generation Guidelines**:
- Always include error handling
- Add progress indicators
- Use standard tools when possible
- Make code idempotent
- Avoid dangerous commands
- Include helpful comments

#### Executor Agent

**Location**: `workflow/agents/executor_agent.py`

**System Prompt**: Specialized for safe execution and monitoring

**Responsibilities**:
- Validate workflow code before execution
- Execute bash and Python workflows
- Capture all output (stdout/stderr)
- Monitor execution time
- Detect failures early
- Provide execution analysis

**Key Methods**:
- `execute_workflow()` - Run workflow
- `validate_workflow()` - Safety check
- `analyze_execution()` - Provide insights

**Safety Features**:
- Command blocklist (rm -rf /, sudo, etc.)
- Execution timeouts
- Output sanitization
- Error capture

#### Reviewer Agent

**Location**: `workflow/agents/reviewer_agent.py`

**System Prompt**: Specialized for debugging and improvement

**Responsibilities**:
- Analyze workflow failures
- Identify root causes
- Recognize failure patterns
- Suggest specific fixes
- Provide code improvements
- Learn from execution history

**Key Methods**:
- `analyze_failure()` - Debug single failure
- `identify_patterns()` - Find recurring issues
- `suggest_improvements()` - General recommendations
- `compare_executions()` - Compare success vs failure

**Pattern Recognition**:
- Timeout errors
- Network issues
- Permission errors
- Missing dependencies
- API errors
- Rate limiting

### 2. Tools

**Location**: `workflow/tools/`

Tools provide the execution layer for workflows.

#### BashExecutor

**Features**:
- Async subprocess execution
- Configurable timeouts
- Command allowlist/blocklist
- Environment variable support
- Working directory support

**Safety**:
```python
denied_commands = [
    "rm -rf /",
    "sudo rm",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # fork bomb
]
```

#### PythonExecutor

**Features**:
- Temporary file execution
- Package installation support
- Timeout handling
- Output capture

### 3. Storage

**Location**: `workflow/storage/`

#### WorkflowStore

**Storage format**:
```
~/workflows/
├── workflow-name/
│   ├── config.yaml      # Metadata (name, description, language, etc.)
│   ├── workflow.sh      # Executable code
│   └── CLAUDE.md        # Agent memory/notes
```

**Key Methods**:
- `save()` - Save workflow to disk
- `load()` - Load workflow from disk
- `list_workflows()` - Get all workflows
- `delete()` - Remove workflow
- `update_memory()` - Update agent memory

**Benefits**:
- Version control friendly (plain files)
- Human-readable
- Easy to share
- Direct editing possible

#### HistoryStore

**Storage format**: SQLite database at `~/workflows/history.db`

**Schema**:
```sql
CREATE TABLE executions (
    id INTEGER PRIMARY KEY,
    workflow_name TEXT,
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration REAL,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    error_message TEXT
)
```

**Key Methods**:
- `save_execution()` - Record execution
- `get_executions()` - Query history
- `get_failure_patterns()` - Analyze patterns
- `get_stats()` - Calculate statistics

**Pattern Detection**:
Automatically groups similar errors:
- Timeouts
- Network errors
- Permission errors
- Missing dependencies
- Rate limiting
- Authentication errors

### 4. Data Models

**Location**: `workflow/storage/models.py`

Key models built with Pydantic:

```python
class WorkflowConfig:
    name: str
    description: str
    language: WorkflowLanguage  # BASH or PYTHON
    code: str
    created_at: datetime
    timeout: int
    env_vars: Dict[str, str]

class ExecutionResult:
    workflow_name: str
    status: WorkflowStatus
    started_at: datetime
    duration: float
    stdout: str
    stderr: str
    error_message: str

class FailurePattern:
    pattern_type: str
    count: int
    last_seen: datetime
    error_messages: List[str]
    suggested_fixes: List[str]
```

## Data Flow

### Teaching a Workflow

```
User: "workflow teach backup 'Backup DB to S3'"
  │
  ▼
Orchestrator: Initialize
  │
  ▼
Coder Agent: Generate code
  • Parse description
  • Choose language (bash/python)
  • Generate code with error handling
  • Add progress logging
  │
  ▼
Orchestrator: Show code to user
  │
  ▼
User: Approve? (y/n)
  │
  ▼
WorkflowStore: Save to ~/workflows/backup/
  • config.yaml
  • workflow.sh
  • CLAUDE.md
```

### Running a Workflow

```
User: "workflow run backup"
  │
  ▼
Orchestrator: Load workflow
  │
  ▼
Executor Agent: Validate code
  • Check for dangerous commands
  • Verify dependencies
  │
  ▼
User: Looks safe? (y/n)
  │
  ▼
BashExecutor/PythonExecutor: Execute
  • Run in subprocess
  • Capture output
  • Monitor timing
  │
  ▼
HistoryStore: Save execution result
  │
  ▼
Orchestrator: Show results
  │
  ▼ (if failed)
Reviewer Agent: Analyze failure
  • Parse errors
  • Identify root cause
  • Suggest fixes
  │
  ▼
Orchestrator: Offer to apply fixes
```

### Improving a Workflow

```
User: "workflow improve backup"
  │
  ▼
HistoryStore: Get failure patterns
  │
  ▼
Reviewer Agent: Analyze patterns
  • Group similar errors
  • Identify systemic issues
  • Generate improvements
  │
  ▼
Coder Agent: Apply fixes
  • Update code
  • Add retry logic
  • Improve error handling
  │
  ▼
WorkflowStore: Save updated workflow
```

## Key Design Decisions

### 1. Code-First Approach

**Why**: Inspired by CoAct research showing code generation is more reliable than UI automation

**Benefits**:
- User can read and understand workflows
- Direct editing possible
- Version control friendly
- Debuggable with standard tools
- No brittleness from UI changes

### 2. Agent-Based Architecture

**Why**: Separation of concerns, specialized expertise

**Benefits**:
- Each agent focuses on one task
- Clear responsibilities
- Easier to improve individual components
- Follows Claude Agent SDK patterns

### 3. Learning from History

**Why**: OSWorld research showed agents need to learn from failures

**Implementation**:
- SQLite database tracks all executions
- Pattern detection identifies recurring issues
- Reviewer agent suggests proactive improvements

**Benefits**:
- Workflows become more reliable over time
- Proactive error prevention
- Data-driven improvements

### 4. Interactive by Default

**Why**: Trust and transparency for users

**Features**:
- Show generated code before saving
- Confirm before execution
- Offer analysis after failures
- Allow manual editing

**Benefits**:
- User stays in control
- Learning opportunity
- Safety
- Trust building

## Extension Points

### 1. Custom Tools via MCP

Future: Add Model Context Protocol (MCP) support for custom tools:

```python
# Example: AWS tools MCP server
class AWSToolsServer(MCPServer):
    def get_tools(self):
        return [
            EC2Tool(),
            S3Tool(),
            LambdaTool(),
        ]
```

### 2. Workflow Composition

Future: Chain workflows together:

```bash
workflow compose weekly-report \
  --steps fetch-data,analyze,generate-pdf,email
```

### 3. Scheduling Integration

Future: Integrate with cron or systemd timers:

```bash
workflow schedule backup "0 2 * * *"
```

### 4. Remote Execution

Future: Execute workflows on remote servers:

```bash
workflow run deploy --remote production-server
```

## Performance Considerations

### Token Usage

- Agents maintain conversation history
- History grows with workflow complexity
- Consider context window limits
- Future: Implement context compression

### Execution Safety

- All code runs in subprocesses
- Timeouts prevent infinite loops
- Command blocklist prevents dangerous operations
- No direct system access

### Storage Efficiency

- Workflows are plain text files (minimal storage)
- SQLite for history (efficient queries)
- Execution output limited to prevent bloat

## Security Considerations

### Input Validation

- User descriptions validated
- Generated code reviewed
- Command blocklist enforced

### Sandboxing

- Code runs in subprocesses
- No shell expansion of user input
- Environment variable isolation

### Secrets Management

- API keys from environment variables
- No secrets in workflow files
- Future: Integrate with secret managers

## Testing Strategy

### Unit Tests

- Test individual agents
- Test tool execution
- Test storage operations

### Integration Tests

- End-to-end workflow creation
- Execution and error handling
- Pattern detection

### Example Test

```python
async def test_workflow_creation():
    orch = Orchestrator()
    workflow = await orch.teach_workflow(
        name="test",
        description="Echo hello",
        interactive=False
    )
    assert workflow is not None
    assert "echo" in workflow.code.lower()
```

## Future Enhancements

1. **Multi-step workflows** - Built-in step management
2. **Parallel execution** - Run multiple workflows simultaneously
3. **Workflow marketplace** - Share workflows with community
4. **Web UI** - Alternative to CLI
5. **Workflow visualization** - Diagram generation
6. **Better debugging** - Step-through execution
7. **Cloud execution** - Run workflows in containers
8. **Monitoring** - Real-time execution dashboards

## References

- [OSWorld Research](https://xlang.ai/blog/osworld-verified) - Benchmarking computer use agents
- [CoAct Paper](https://arxiv.org/pdf/2508.03923) - Code-first agent approach
- [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview) - Agent framework patterns
- [Anthropic API Docs](https://docs.anthropic.com/) - Claude API reference
