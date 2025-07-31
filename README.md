# Experimental LLM Terminal Agent

An experimental Python project for learning and understanding LLM agent principles through practical implementation. This project demonstrates a simple terminal agent that uses OpenAI API (GPT-4o-mini) with Function Calling to execute shell commands.

## Project Purpose

This is a **learning and experimentation project** focused on understanding core LLM agent concepts:

- Function Calling mechanisms in language models
- Multi-step action planning and execution
- Tool result processing and analysis
- Basic agent architecture without complex abstractions

**Note**: This is experimental code designed for educational purposes, not intended for production use.

## What This Project Demonstrates

### Core LLM Agent Principles

- **Tool/Function Calling**: Defining and exposing tools to the language model
- **Multi-step Execution**: Agent can execute sequences of commands to complete tasks
- **Result Analysis**: Model analyzes command outputs and makes informed decisions
- **Interactive Loop**: Continuous interaction between user requests and agent responses

### Architecture Components

- **get_available_tools()**: Defines the `run_shell_command` tool specification
- **execute_tool()**: Handles actual command execution via `subprocess`
- **process_user_message()**: Main processing loop handling requests and tool execution
- **Interactive Interface**: Terminal-based conversation with the agent

## Features

- Execute any terminal commands: `ls`, `grep`, `find`, `ps`, `cat`, `tail`, `df`, etc.
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
```

2. Install dependencies:
```bash
pip install -e .
```

## Configuration

1. Obtain an OpenAI API key from https://platform.openai.com/api-keys

2. Create a `.env` file with your API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Interactive Mode

Run the agent in interactive terminal mode:

```bash
python main.py
```

Example interactions:
- "Show files in current directory"
- "Find all Python files and count lines of code"
- "Check system memory usage"
- "Search for TODO comments in source files"

### Programmatic Usage

```python
from agent import process_user_message

response = process_user_message("List all running processes")
print(response)
```

## Project Structure

```
llm_agent/
├── agent.py           # Main agent implementation
├── main.py           # Interactive terminal interface
├── tests/
│   └── test_agent.py # Comprehensive test suite
├── pyproject.toml    # Project dependencies
└── README.md         # This file
```

## Technical Implementation

### Tool Definition

The agent exposes a single tool `run_shell_command` with JSON schema specification that the language model can understand and invoke.

### Execution Flow

1. User provides natural language request
2. Model analyzes request and determines required commands
3. Model calls `run_shell_command` tool with appropriate parameters
4. Agent executes command via `subprocess` with safety constraints
5. Results are returned to model for analysis
6. Model provides natural language response to user
7. Process repeats for multi-step tasks

### Safety Measures

- 30-second timeout on command execution
- Limited iteration count (5 max) to prevent infinite loops
- Subprocess isolation
- Error handling and graceful degradation

## Testing

Run the test suite:

```bash
pytest tests/
```

Tests cover:
- Tool definition and execution
- Command success and error scenarios
- Multi-step execution workflows
- API integration with mocking
- Error handling and edge cases

## Learning Objectives

This project helps understand:

1. **Function Calling Architecture**: How to define tools that language models can invoke
2. **Agent Planning**: How models break down complex requests into executable steps
3. **Tool Integration**: Bridging language models with external systems
4. **Iterative Execution**: Managing multi-step workflows
5. **Safety Considerations**: Implementing guardrails for agent systems

## Limitations

- Single tool implementation (shell commands only)
- No persistent memory between sessions
- Limited error recovery mechanisms
- No advanced planning or reasoning strategies
- Basic security model

## Requirements

- Python 3.12+
- OpenAI API key
- Unix-like environment (Linux/macOS)

## Dependencies

- `openai>=1.0.0` - OpenAI API client
- `python-dotenv>=1.0.0` - Environment variable management

## Future Learning Extensions

This basic implementation can be extended to explore:

- Multiple tool types (file operations, web requests, etc.)
- Persistent conversation memory
- Advanced planning algorithms
- Tool composition and chaining
- Error recovery strategies
- Security and sandboxing improvements