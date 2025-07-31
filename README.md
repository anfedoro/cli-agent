# LLM Terminal Agent

An experimental Python project for learning and understanding LLM agent principles through practical implementation. This terminal agent supports multiple LLM providers (OpenAI and Google Gemini) with unified Function Calling to execute shell commands safely.

## Project Purpose

This is a **learning and experimentation project** focused on understanding core LLM agent concepts:

- Function Calling mechanisms in language models
- Multi-step action planning and execution
- Tool result processing and analysis
- Provider abstraction and unified interface design
- Security considerations for agent systems

**Note**: This is experimental code designed for educational purposes, not intended for production use.

## What This Project Demonstrates

### Core LLM Agent Principles

- **Tool/Function Calling**: Defining and exposing tools to language models
- **Multi-step Execution**: Agent can execute sequences of commands to complete tasks
- **Result Analysis**: Model analyzes command outputs and makes informed decisions
- **Interactive Loop**: Continuous interaction between user requests and agent responses
- **Provider Abstraction**: Unified interface for different LLM providers
- **Security Controls**: Safe execution with permission-based software installation

### Architecture Components

- **Modular Provider System**: Clean separation of provider-specific implementations
- **Function Mapping Dictionaries**: Elegant dispatch system for provider functions
- **Unified Tool Interface**: Same tools work across all providers
- **Security Layer**: Built-in safeguards against unauthorized software installation
- **Interactive CLI**: Terminal-based conversation with provider selection

## Features

- **Multiple Provider Support**: Choose between OpenAI and Google Gemini APIs
- **Unified API Interface**: Both providers use OpenAI-compatible format for consistency
- **Security Controls**: Prevents automatic software installation without user permission
- **Execute terminal commands**: `ls`, `grep`, `find`, `ps`, `cat`, `tail`, `df`, etc.
- **Multi-step command execution**: Agent can run multiple commands to solve complex tasks
- **Result analysis**: Natural language responses with actual command output
- **Interactive terminal mode**: Real-time conversation with provider selection
- **Model customization**: Specify custom models for each provider
- **Debug mode**: Verbose output showing iteration steps and token usage
- **Command execution timeouts**: 30-second safety limits
- **Comprehensive test coverage**: Full test suite for both providers

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd llm_agent
```

2. Install dependencies:
```bash
uv sync --extra dev
```

or with pip:
```bash
pip install -e .[dev]
```

## Configuration

### For OpenAI

1. Obtain an OpenAI API key from https://platform.openai.com/api-keys

2. Set the environment variable:
```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

### For Google Gemini

1. Obtain a Gemini API key from https://aistudio.google.com/app/apikey

2. Set the environment variable:
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
```

### Environment File

You can also create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

### Basic Usage

```bash
# Use OpenAI (default)
python main.py

# Use Gemini
python main.py --provider gemini

# Use custom model
python main.py --provider openai --model gpt-3.5-turbo

# Enable verbose mode for debugging
python main.py --verbose --provider gemini
```

### Command Line Options

```bash
python main.py --help
```

Options:
- `--provider {openai,gemini}` or `-p`: Choose LLM provider (default: openai)
- `--model MODEL` or `-m`: Specify model name for the selected provider
- `--verbose` or `-v`: Show detailed token usage and debug information
- `--help` or `-h`: Show help message

### Example Interactions

- "Show files in current directory"
- "Find all Python files and count lines of code"
- "Check system memory usage"
- "Search for TODO comments in source files"
- "Analyze disk usage by directory"

### Security Features

The agent includes built-in security controls:

- **Permission-based installation**: Agent asks before installing any software
- **Tool verification**: Checks if required tools are available before use
- **No automatic installations**: Commands like `pip install`, `apt install`, etc. require user permission
- **Safe command execution**: 30-second timeouts and subprocess isolation

Example of security in action:
```
User: use tokei to analyze code
Agent: It seems tokei is not installed. To complete this task, I need to install tokei. May I proceed with the installation?
```

### Programmatic Usage

```python
import os
from agent import LLMProvider, initialize_client, process_user_message

# Using OpenAI
os.environ["OPENAI_API_KEY"] = "your_key"
client = initialize_client(LLMProvider.OPENAI)
response = process_user_message(
    "List all running processes",
    LLMProvider.OPENAI,
    client
)
print(response)

# Using Gemini
os.environ["GEMINI_API_KEY"] = "your_key"
client = initialize_client(LLMProvider.GEMINI)
response = process_user_message(
    "List all running processes",
    LLMProvider.GEMINI,
    client
)
print(response)
```

## Project Structure

```
llm_agent/
├── providers/                 # Provider modules
│   ├── __init__.py           # Exports function dictionaries
│   ├── functions.py          # Function mapping dictionaries
│   ├── openai.py            # OpenAI-specific implementation
│   └── gemini.py            # Gemini-specific implementation
├── agent.py                  # Main agent logic and unified interface
├── main.py                  # CLI interface with argument parsing
├── tests/
│   └── test_agent.py        # Comprehensive test suite
├── pyproject.toml           # Project dependencies and configuration
└── README.md                # This file
```

## Technical Implementation

### Provider Architecture

The agent uses a modular provider system with function mapping dictionaries:

```python
# providers/functions.py
INITIALIZE_CLIENT = {
    "openai": openai.initialize_client,
    "gemini": gemini.initialize_client,
}

SEND_MESSAGE = {
    "openai": openai.send_message,
    "gemini": gemini.send_message,
}
# ... other function mappings
```

### Unified API Interface

Both providers use OpenAI-compatible format:
- **OpenAI**: Native OpenAI API
- **Gemini**: Google's OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`)

### Tool Definition

Both providers expose the same `run_shell_command` tool with identical schemas, ensuring consistent behavior across providers.

### Execution Flow

1. User provides natural language request and selects provider
2. Agent checks if required tools are available
3. If tools are missing, agent asks permission before installation
4. Model analyzes request and determines required commands
5. Model calls `run_shell_command` tool with appropriate parameters
6. Agent executes command via `subprocess` with safety constraints
7. Results are returned to model in provider-specific format
8. Model provides natural language response with actual command output
9. Process repeats for multi-step tasks

### Safety Measures

- **Installation Controls**: No automatic software installation
- **Command Timeouts**: 30-second execution limits
- **Subprocess Isolation**: Commands run in isolated processes
- **Permission Requests**: User approval required for installations
- **Tool Verification**: Checks tool availability before use
- **Error Handling**: Graceful degradation and error reporting

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Tests cover:
- Tool definition and execution for both providers
- Command success and error scenarios
- Multi-step execution workflows
- Provider-specific API integration with mocking
- Error handling and edge cases
- Security controls and permission requests
- Unified interface functionality

## Adding New Providers

The modular architecture makes it easy to add new LLM providers. Here's how:

### Step 1: Create Provider Module

Create a new file `providers/your_provider.py`:

```python
import os
from typing import Any, Dict, List
from openai import OpenAI  # or your provider's client

def initialize_client() -> Any:
    """Initialize client for your provider."""
    api_key = os.getenv("YOUR_PROVIDER_API_KEY")
    if not api_key:
        raise ValueError("YOUR_PROVIDER_API_KEY environment variable not found.")
    return YourProviderClient(api_key=api_key)

def get_available_tools() -> List[Dict[str, Any]]:
    """Return tool definitions in OpenAI format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "description": "Execute shell command in terminal and return execution result",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute, e.g. 'ls -la /tmp'",
                        }
                    },
                    "required": ["command"],
                },
            },
        }
    ]

def get_display_name() -> str:
    """Get display name for this provider."""
    return "Your Provider Name"

def send_message(client, messages, model_name=None):
    """Send message to your provider's API."""
    # Implement API call logic
    pass

def extract_function_calls(response):
    """Extract function calls from response."""
    # Implement function call extraction
    pass

def add_function_result_to_messages(messages, response, function_results):
    """Add function results to message history."""
    # Implement result addition logic
    pass

def extract_usage_info(response):
    """Extract token usage information."""
    # Return dict with prompt_tokens, completion_tokens, total_tokens
    pass

def get_response_text(response):
    """Extract response text."""
    # Return the text content from response
    pass
```

### Step 2: Add to Enum

Add your provider to the enum in `agent.py`:

```python
class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    YOUR_PROVIDER = "your_provider"  # Add this line
```

### Step 3: Update Function Mappings

Add your provider to each dictionary in `providers/functions.py`:

```python
from . import gemini, openai, your_provider  # Add import

INITIALIZE_CLIENT = {
    "openai": openai.initialize_client,
    "gemini": gemini.initialize_client,
    "your_provider": your_provider.initialize_client,  # Add this
}

GET_AVAILABLE_TOOLS = {
    "openai": openai.get_available_tools,
    "gemini": gemini.get_available_tools,
    "your_provider": your_provider.get_available_tools,  # Add this
}

# Add to all other function dictionaries...
```

### Step 4: Update CLI Options

Add your provider to the choices in `main.py`:

```python
parser.add_argument(
    "--provider", "-p",
    choices=["openai", "gemini", "your_provider"],  # Add here
    default="openai",
    help="LLM provider to use (default: openai)"
)
```


That's it! The agent will automatically work with your new provider through the unified interface.

## Learning Objectives

This project helps understand:

1. **Function Calling Architecture**: How to define tools that language models can invoke
2. **Provider Abstraction**: Building unified interfaces for different APIs
3. **Security in AI Systems**: Implementing safeguards for agent systems
4. **Modular Design**: Creating extensible architectures
5. **Agent Planning**: How models break down complex requests into executable steps
6. **Tool Integration**: Bridging language models with external systems
7. **Iterative Execution**: Managing multi-step workflows

## Supported Providers

### OpenAI
- **Model**: gpt-4o-mini (default), customizable
- **API**: Native OpenAI Chat Completions with Function Calling
- **Environment Variable**: `OPENAI_API_KEY`

### Google Gemini
- **Model**: gemini-2.0-flash-exp (default), customizable
- **API**: Google's OpenAI-compatible endpoint
- **Environment Variable**: `GEMINI_API_KEY`

## Limitations

- Single tool implementation (shell commands only)
- No persistent memory between sessions
- Basic security model (permission-based)
- Limited error recovery mechanisms
- No advanced planning or reasoning strategies

## Requirements

- Python 3.12+
- OpenAI API key and/or Gemini API key
- Unix-like environment (Linux/macOS)

## Dependencies

- `openai>=1.0.0` - OpenAI API client (used by both providers)
- `google-generativeai>=0.3.0` - Google Gemini API client (for native API if needed)
- `python-dotenv>=1.0.0` - Environment variable management

## Future Learning Extensions

This basic implementation can be extended to explore:

- Additional LLM providers (Anthropic Claude, local models, etc.)
- Multiple tool types (file operations, web requests, database queries)
- Persistent conversation memory
- Advanced planning algorithms
- Tool composition and chaining
- Enhanced security models (sandboxing, permission levels)
- Error recovery strategies
- Provider-specific optimization strategies
- Streaming responses
- Async execution

## Examples

### Basic File Operations
```
User: Show me all Python files in this directory
Agent: [Executes: find . -name "*.py"]
```

### System Analysis
```
User: Check system performance
Agent: [Executes: top, df -h, free -m]
```

### Code Analysis
```
User: Count lines of code in this project
Agent: I need to use a code analysis tool. May I install 'cloc' to complete this task?
```

### Multi-step Tasks
```
User: Find large files and show disk usage
Agent: [Executes: find . -size +10M, du -sh *, df -h]
```

The agent handles complex, multi-step requests by breaking them down into appropriate command sequences while maintaining security and providing clear, actionable results.
