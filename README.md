# LLM Terminal Agent

A modular Python project for learning LLM agent principles through practical implementation. Features unified architecture with multiple interfaces and support for OpenAI, Google Gemini, and LM Studio providers with Function Calling capabilities.

## Project Purpose

This is a **learning and experimentation project** focused on understanding core LLM agent concepts:

- Function Calling mechanisms in language models
- Multi-step action planning and execution
- Tool result processing and analysis
- Provider abstraction and unified interface design
- Clean architecture with separated concerns
- Security considerations for agent systems

**Note**: This is experimental code designed for educational purposes, not intended for production use.

## Architecture

The project follows clean architecture principles with clear separation between business logic and user interfaces:

### Core Components

- **core_agent.py** - Pure agent backend with LLM processing logic
- **chat_interface.py** - Interactive chat frontend
- **shell_interface.py** - Shell-like interface with intelligent command routing
- **main.py** - Unified entry point for all modes

### What This Demonstrates

- **Modular Design**: Clean separation between agent logic and UI frontends
- **Tool/Function Calling**: Defining and exposing tools to language models
- **Multi-step Execution**: Agent can execute sequences of commands to complete tasks
- **Provider Abstraction**: Unified interface for different LLM providers
- **Smart Routing**: Shell mode intelligently routes between direct execution and LLM processing
- **Security Controls**: Safe execution with permission-based software installation

## Features

- **Two Interface Modes**:
  - **Chat Mode**: Traditional interactive conversation with User:/Agent: prompts
  - **Shell Mode**: Standard shell prompt with intelligent command routing
- **Multiple Provider Support**: OpenAI, Google Gemini, and LM Studio APIs
- **Unified Backend**: Same agent logic powers both interfaces
- **Smart Command Detection**: Automatically routes shell commands vs natural language
- **Security Controls**: Prevents automatic software installation without user permission
- **Multi-step Execution**: Agent can run multiple commands to solve complex tasks
- **Result Analysis**: Natural language responses with actual command output
- **Model Customization**: Specify custom models for each provider
- **Debug/Trace Modes**: Verbose output showing iteration steps and token usage
- **Comprehensive Test Coverage**: 45 tests covering all functionality

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

3. Install the CLI tool:
```bash
uv tool install .
```

This makes `cli-agent` available globally.

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

### For LM Studio

1. Download and install LM Studio from https://lmstudio.ai/

2. Load a model in LM Studio and start the local server

3. (Optional) Configure custom base URL if not using default:
```bash
export LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

### Environment File

You can also create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

## Usage

### Chat Mode (Default)

Interactive conversation interface with User:/Agent: style prompts:

```bash
# Using installed CLI tool
cli-agent

# Or run directly
python main.py

# Use different providers
cli-agent --provider gemini
cli-agent --provider lmstudio

# Use custom model
cli-agent --provider openai --model gpt-3.5-turbo

# Enable verbose mode for debugging
cli-agent --verbose --provider gemini
```

### Shell Mode

Shell-like interface with intelligent command routing. Executes shell commands directly, falls back to LLM for natural language:

```bash
# Shell interface with standard prompt
cli-agent --shell

# Use different providers in shell mode
cli-agent --shell --provider gemini
cli-agent --shell --provider lmstudio

# Enable trace mode to see LLM execution details
cli-agent --shell --trace

# Or set environment variable
CLI_AGENT_TRACE=1 cli-agent --shell
```

#### Shell Mode Examples

```bash
# Direct shell commands - executed immediately
anfedoro@MBP4Max:~/project$ ls -la
total 48
drwxr-xr-x  12 user  staff   384 Aug 21 10:30 .
drwxr-xr-x   5 user  staff   160 Aug 21 10:29 ..
-rw-r--r--   1 user  staff  1234 Aug 21 10:30 README.md

# Natural language - processed by LLM
anfedoro@MBP4Max:~/project$ find all python files and count lines
🛠️  Executing command: find . -name "*.py" -type f
🛠️  Executing command: find . -name "*.py" -type f -exec wc -l {} + | tail -1
Total lines across all Python files: 2,847 lines
```

### Command Line Options

```bash
cli-agent --help
```

Options:
- `--provider {openai,gemini,lmstudio}` or `-p`: Choose LLM provider (default: openai)
- `--model MODEL` or `-m`: Specify custom model for the selected provider
- `--shell` or `-s`: Run in shell mode with intelligent command routing
- `--verbose` or `-v`: Show detailed token usage information
- `--trace` or `-t`: Enable trace mode (show LLM execution details)
- `--no-reasoning`: Disable reasoning for faster responses (LM Studio only)
- `--model MODEL` or `-m`: Specify model name for the selected provider
- `--verbose` or `-v`: Show detailed token usage and debug information (chat mode)
- `--shell` or `-s`: Run in shell mode with standard prompt and intelligent routing
- `--trace` or `-t`: Enable trace mode (shell mode only)
- `--no-reasoning`: Disable reasoning process for faster responses (LM Studio)
- `--help` or `-h`: Show help message

### Shell Mode Features

**Intelligent Command Routing:**
- Shell commands executed directly: `ls -la`, `grep pattern *.py`, `git status`
- Natural language processed by LLM: `analyze this code`, `what files are here`

**Standard Shell Experience:**
- Normal shell prompt format: `user@host:path$`
- Tab completion for commands and paths
- Command history navigation

**Silent LLM Mode:**
- No intermediate "Agent is analyzing..." messages
- Clean output like a normal shell
- Enable trace mode to see LLM execution details

### Example Interactions

**Chat Mode:**
```
You: Show files in current directory
🛠️  Executing command: ls -la
🤖 Agent: Here are the files in your current directory:
total 48
drwxr-xr-x  12 user  staff   384 Aug 21 10:30 .
drwxr-xr-x   5 user  staff   160 Aug 21 10:29 ..
-rw-r--r--   1 user  staff  1234 Aug 21 10:30 README.md
...

You: Find all Python files and count lines of code
🛠️  Executing command: find . -name "*.py" -type f -exec wc -l {} +
🤖 Agent: Found Python files with the following line counts:
...
```

**Shell Mode:**
```bash
user@host:project$ ls -la                 # Direct shell execution
total 48
drwxr-xr-x  12 user  staff   384 Aug 21 10:30 .
...

user@host:project$ analyze this code      # LLM processing
🛠️  Executing command: find . -name "*.py" -type f
🛠️  Executing command: head -20 main.py
Based on the code analysis, this appears to be...

user@host:project$ git status            # Direct shell execution  
On branch main
Your branch is up to date with 'origin/main'.
```

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

The new modular architecture provides clean APIs for programmatic use:

```python
from core_agent import AgentConfig, LLMProvider

# Create agent configuration
config = AgentConfig(LLMProvider.OPENAI, model="gpt-4")
config.initialize_client()

# Process messages through core agent
from core_agent import process_user_message
response = process_user_message(
    "List all running processes",
    config.provider,
    config.client,
    config.chat_history
)
print(response)

# Use chat interface programmatically
from chat_interface import handle_chat_message
response = handle_chat_message("show system info", config)

# Use shell interface for smart execution
from shell_interface import smart_execute_with_fallback
is_shell, output = smart_execute_with_fallback("ls -la", config)
```

## Project Structure

```
llm_agent/
├── core_agent.py            # Pure agent backend with LLM logic
├── chat_interface.py        # Interactive chat frontend
├── shell_interface.py       # Shell interface with smart routing  
├── main.py                  # Unified entry point
├── providers/               # Provider modules
│   ├── __init__.py         # Exports function dictionaries
│   ├── functions.py        # Tool definitions and mappings
│   ├── openai.py          # OpenAI-specific implementation
│   ├── gemini.py          # Gemini-specific implementation
│   └── lmstudio.py        # LM Studio-specific implementation
├── input_handler.py        # Enhanced input with history/completion
├── utils.py                # System utilities and context
├── tests/                  # Comprehensive test suite
│   ├── test_agent.py      # Agent backend tests
│   ├── test_shell_interface.py  # Shell interface tests
│   ├── test_input_handler.py    # Input handler tests
│   └── test_utils.py      # Utilities tests
├── pyproject.toml          # Project configuration and dependencies
└── README.md               # This file
```

## Technical Implementation

### Architecture Overview

The project follows clean architecture principles with three main layers:

1. **Core Agent** (`core_agent.py`):
   - Pure business logic for LLM processing
   - Multi-iteration execution with function calling
   - Provider-agnostic message handling
   - Configuration management via `AgentConfig`

2. **Interface Frontends**:
   - **Chat Interface** (`chat_interface.py`): Interactive conversation mode
   - **Shell Interface** (`shell_interface.py`): Shell-like interface with smart routing

3. **Provider Abstraction** (`providers/`):
   - Unified function mapping dictionaries  
   - Provider-specific implementations
   - OpenAI-compatible format for consistency

### Provider Architecture

The agent uses a modular provider system with function mapping dictionaries:

```python
# providers/functions.py
INITIALIZE_CLIENT = {
    "openai": openai.initialize_client,
    "gemini": gemini.initialize_client,
    "lmstudio": lmstudio.initialize_client,
}

SEND_MESSAGE = {
    "openai": openai.send_message,
    "gemini": gemini.send_message,
    "lmstudio": lmstudio.send_message,
}
# ... other function mappings
```

### Execution Flow

**Chat Mode:**
1. User provides input through interactive interface
2. Core agent processes with full LLM iteration logic
3. Function calls executed with visual feedback
4. Response formatted and displayed

**Shell Mode:**
1. Input received via shell-like prompt
2. Smart detection: shell command vs natural language
3. Shell commands executed directly  
4. Natural language routed to core agent (silent mode)
5. Clean output without chat-style formatting

**Core Agent Processing:**
1. Initialize chat history and system context
2. Send message to selected LLM provider
3. Extract function calls if present
4. Execute shell commands via `run_shell_command` tool
5. Add results back to conversation
6. Repeat until task complete (max 10 iterations)

### Safety Measures

- **Installation Controls**: No automatic software installation
- **Command Timeouts**: 30-second execution limits
- **Subprocess Isolation**: Commands run in isolated processes
- **Permission Requests**: User approval required for installations
- **Tool Verification**: Checks tool availability before use
- **Error Handling**: Graceful degradation and error reporting

## Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/ -v
```

**Test Coverage (45 tests):**
- Core agent functionality and multi-iteration logic
- Chat interface and user interaction handling  
- Shell interface with smart command routing
- Provider-specific API integration (mocked)
- Function calling and tool execution
- Error handling and edge cases
- Input handler with readline support
- System utilities and context formatting
- Security controls and permission requests

Tests ensure backward compatibility and verify that both interfaces use the same reliable agent backend.

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

### LM Studio
- **Model**: qwen3-30b-a3b-2507 (default), customizable
- **API**: Local OpenAI-compatible endpoint
- **Environment Variable**: `LM_STUDIO_BASE_URL` (optional, defaults to http://localhost:1234/v1)
- **Requirements**: LM Studio application running locally with a loaded model

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

This modular implementation can be extended to explore:

- **Additional Interfaces**: Web UI, API server, VS Code extension
- **Enhanced Providers**: Anthropic Claude, local models (Ollama)
- **Advanced Tools**: File operations, web requests, database queries
- **Persistent Memory**: Conversation history, learned preferences
- **Smart Routing**: More sophisticated command vs NL detection
- **Security Enhancements**: Sandboxing, granular permissions
- **Performance**: Streaming responses, async execution
- **Agent Orchestration**: Multi-agent collaboration
- **Tool Composition**: Complex multi-step tool chains

## What This Project Teaches

- **Clean Architecture**: Separation of concerns, dependency inversion
- **Provider Patterns**: Abstraction layers, strategy pattern implementation  
- **LLM Integration**: Function calling, multi-iteration logic
- **CLI Design**: Multiple interface modes, user experience
- **Testing Strategy**: Mocking external APIs, comprehensive coverage
- **Security Mindset**: Safe execution, permission controls
- **Modular Design**: Easy extension and maintenance

The codebase serves as a practical example of how to build robust, extensible LLM agent systems with proper architecture and testing.

## Examples

### Chat Mode Examples

**Basic File Operations:**
```
You: Show me all Python files in this directory
🛠️  Executing command: find . -name "*.py" -type f
🤖 Agent: Found the following Python files in your directory:
./core_agent.py
./chat_interface.py
./shell_interface.py
./main.py
...
```

**System Analysis:**
```
You: Check system performance
🛠️  Executing command: top -n 1 -b | head -10
🛠️  Executing command: df -h
🛠️  Executing command: free -m
🤖 Agent: Here's your current system performance:

CPU Usage: [top output]
Disk Usage: [df output]  
Memory Usage: [free output]
```

### Shell Mode Examples

**Direct Commands:**
```bash
user@host:project$ ls -la
total 48
drwxr-xr-x  12 user  staff   384 Aug 21 10:30 .
...

user@host:project$ git status
On branch main
Your branch is up to date with 'origin/main'.
```

**Natural Language Processing:**
```bash
user@host:project$ analyze the code structure
🛠️  Executing command: find . -name "*.py" -type f | head -10
🛠️  Executing command: wc -l *.py
This project has a modular architecture with:
- Core agent backend (core_agent.py)
- Two frontend interfaces (chat_interface.py, shell_interface.py)
- Provider abstraction layer (providers/)
...
```

The agent handles complex, multi-step requests by breaking them down into appropriate command sequences while maintaining security and providing clear, actionable results.
