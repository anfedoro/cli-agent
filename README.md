# LLM Terminal Agent - OpenAI Only

A simple Python project demonstrating LLM agent principles through practical implementation. This terminal agent uses OpenAI API (GPT-4o-mini) with Function Calling to execute shell commands safely.

## Project Purpose

This is a **learning and experimentation project** focused on understanding core LLM agent concepts:

- Function Calling mechanisms in OpenAI models
- Multi-step action planning and execution
- Tool result processing and analysis
- Basic agent architecture

**Note**: This is experimental code designed for educational purposes, not intended for production use.

## Features

- Execute terminal commands: `ls`, `grep`, `find`, `ps`, `cat`, `tail`, `df`, etc.
- Multi-step command execution (agent can run multiple commands to solve complex tasks)
- Result analysis with natural language responses
- Interactive terminal mode
- Command execution timeouts (30 seconds) for safety
- Comprehensive test coverage

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd llm_agent
git checkout openai-only
```

2. Install dependencies:
```bash
uv sync
# or with pip:
pip install -e .
```

## Configuration

1. Obtain an OpenAI API key from https://platform.openai.com/api-keys

2. Set the environment variable:
```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

Or create a `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Interactive Mode

```bash
python main.py
```

For debug information:
```bash
python main.py --verbose
```

### Example Interactions

- "Show files in current directory"
- "Find all Python files and count lines of code"
- "Check system memory usage"
- "Search for TODO comments in source files"

### Programmatic Usage

```python
import os
from agent import process_user_message
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = "your_key"
client = OpenAI()

response = process_user_message("List all running processes", client)
print(response)
```

## Technical Implementation

### Tool Definition

The agent exposes a single tool `run_shell_command` with JSON schema specification that OpenAI models can understand and invoke.

### Execution Flow

1. User provides natural language request
2. OpenAI model analyzes request and determines required commands
3. Model calls `run_shell_command` tool with appropriate parameters
4. Agent executes command via `subprocess` with safety constraints
5. Results are returned to model for analysis
6. Model provides natural language response to user
7. Process repeats for multi-step tasks

### Safety Measures

- Limited iteration count (5 max) to prevent infinite loops
- Subprocess isolation with 30-second timeouts
- Error handling and graceful degradation

## Testing

```bash
python -m pytest tests/ -v
```

Tests cover:
- Tool definition and execution
- Command success and error scenarios
- Multi-step execution workflows
- API integration with mocking
- Error handling and edge cases

## Requirements

- Python 3.12+
- OpenAI API key
- Unix-like environment (Linux/macOS)

## Dependencies

- `openai>=1.0.0` - OpenAI API client
- `python-dotenv>=1.0.0` - Environment variable management

## Limitations

- Single provider (OpenAI only)
- Single tool implementation (shell commands only)
- No persistent memory between sessions
- Limited error recovery mechanisms
- Basic security model

## Learning Objectives

This project helps understand:

1. **Function Calling Architecture**: How to define tools that OpenAI models can invoke
2. **Agent Planning**: How models break down complex requests into executable steps
3. **Tool Integration**: Bridging language models with external systems
4. **Iterative Execution**: Managing multi-step workflows
5. **Safety Considerations**: Implementing guardrails for agent systems

## Future Extensions

This basic implementation can be extended to explore:

- Multiple tool types (file operations, web requests, etc.)
- Persistent conversation memory
- Advanced planning algorithms
- Tool composition and chaining
- Error recovery strategies
- Enhanced security measures

---

For multi-provider support (OpenAI + Gemini), see the `main` branch.