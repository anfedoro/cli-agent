# CLI Agent

A modular Python project for learning LLM agent principles through practical implementation. Features unified architecture with multiple interfaces and support for OpenAI, Google Gemini, and LM Studio providers with Function Calling capabilities.

## Project Purpose

This is a **learning and experimentation project** focused on understanding core LLM agent concepts:

- Function Calling mechanisms in language models
- Multi-step action planning and execution
- Tool result processing and analysis
- Provider abstraction and unified interface design
- Clean architecture with separated concerns
- Security considerations for agent systems
- Configuration management through natural language

**Note**: This is experimental code designed for educational purposes, not intended for production use.

## Key Features

### 🎯 Smart Configuration Management
- **Natural Language Configuration**: Tell the agent "change default mode to shell" or "set the prompt indicator to a robot emoji"
- **Persistent Settings**: Configuration automatically saved to `~/.cliagent/settings.json`
- **Dynamic Defaults**: Command-line arguments use your saved preferences as defaults

### 🐚 Enhanced Shell Experience  
- **Visual Agent Indicator**: Shell prompt shows ⭐ (configurable) when in agent mode
- **Universal Tab Completion**: Path completion works everywhere, not just specific commands
- **Smart Directory Handling**: Built-in `cd` and `pwd` commands that actually change directories
- **Preserve Location**: Optionally return to starting directory when exiting (configurable)

### 🏗️ Clean Architecture
- **Centralized Tools**: All LLM tools defined once in core agent, not duplicated across providers
- **Provider Focus**: Providers only handle API communication, agent controls all tool definitions
- **Unified Interface**: Same backend powers both chat and shell modes

## Architecture

The project follows clean architecture principles with clear separation between business logic and user interfaces:

### Core Components

- **agent/core_agent.py** - Pure agent backend with LLM processing logic and centralized tool definitions
- **interface/chat_interface.py** - Interactive chat frontend  
- **interface/shell_interface.py** - Shell-like interface with intelligent command routing
- **agent/config.py** - Configuration management with natural language updates
- **input_handler/** - Enhanced input handling with universal tab completion
- **main.py** - Unified entry point for all modes

### What This Demonstrates

- **Modular Design**: Clean separation between agent logic and UI frontends
- **Tool/Function Calling**: Centralized tool definitions exposed to all LLM providers
- **Multi-step Execution**: Agent can execute sequences of commands to complete tasks
- **Provider Abstraction**: Unified interface for different LLM providers, providers only handle API calls
- **Smart Configuration**: Natural language configuration changes through LLM function calls
- **Enhanced Shell UX**: Visual indicators, universal tab completion, proper directory handling
- **Smart Routing**: Shell mode intelligently routes between direct execution and LLM processing
- **Security Controls**: Safe execution with permission-based software installation

## Features

- **Two Interface Modes**:
  - **Chat Mode**: Traditional interactive conversation with User:/Agent: prompts
  - **Shell Mode**: Standard shell prompt with intelligent command routing and visual agent indicator
- **Multiple Provider Support**: OpenAI, Google Gemini, and LM Studio APIs
- **Unified Backend**: Same agent logic powers both interfaces
- **Smart Command Detection**: Automatically routes shell commands vs natural language
- **Natural Language Configuration**: Change settings by talking to the agent
- **Enhanced Shell Experience**: 
  - Visual prompt indicator (⭐) when in agent mode
  - Universal tab completion for paths and commands
  - Proper `cd`/`pwd` built-in commands
  - Optional directory restoration on exit
- **Centralized Tool Architecture**: All tools defined once in core agent, not duplicated per provider
- **Security Controls**: Prevents automatic software installation without user permission
- **Multi-step Execution**: Agent can run multiple commands to solve complex tasks
- **Result Analysis**: Natural language responses with actual command output
- **Model Customization**: Specify custom models for each provider
- **Debug/Trace Modes**: Verbose output showing iteration steps and token usage
- **Persistent Configuration**: Settings saved to `~/.cliagent/settings.json`
- **Comprehensive Test Coverage**: 45 tests covering all functionality

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cli-agent
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

The agent creates a configuration directory at `~/.cliagent/` with persistent settings:

- **settings.json** - User preferences and defaults
- **history.txt** - Command history for shell mode

### Initial Setup

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

### Smart Configuration Management

The agent includes a powerful configuration system that can be updated through natural language:

**Example Configuration Commands:**
```bash
# In chat or shell mode, just tell the agent what you want:
"Change the default mode to shell"
"Set the prompt indicator to a robot emoji"  
"Make OpenAI the default provider"
"Set default model to gpt-4"
"Turn off directory restoration"
"Change the prompt indicator to a star"
```

**Configuration Options:**
- `default_provider`: "openai", "gemini", or "lmstudio"
- `default_model`: Model name (provider-specific, e.g., "gpt-4", "gemini-pro")
- `default_mode`: "chat" or "shell" 
- `agent_prompt_indicator`: Symbol shown in shell prompt (⭐, 🤖, etc.)
- `preserve_initial_location`: Return to starting directory on exit (true/false)
- `completion_enabled`: Enable tab completion (true/false)
- `history_length`: Number of commands to keep in history

**Manual Configuration:**
Settings are stored in `~/.cliagent/settings.json` and can be edited directly:
```json
{
  "version": "0.3.1",
  "default_provider": "openai",
  "default_model": null,
  "default_mode": "shell",
  "agent_prompt_indicator": "⭐",
  "preserve_initial_location": true,
  "completion_enabled": true,
  "history_length": 1000
}
```

## Usage

The CLI agent automatically uses your saved configuration as defaults for all arguments.

### Chat Mode

Interactive conversation interface with User:/Agent: style prompts:

```bash
# Using installed CLI tool (uses your default mode from config)
cli-agent

# Force chat mode
cli-agent --mode chat

# Use different providers (or set as default via config)
cli-agent --provider gemini
cli-agent --provider lmstudio

# Use custom model (or set as default via config)
cli-agent --provider openai --model gpt-4

# Enable verbose mode for debugging
cli-agent --verbose --provider gemini
```

### Shell Mode

Shell-like interface with intelligent command routing and visual agent indicator:

```bash
# Shell interface with enhanced prompt  
cli-agent --mode shell

# Use different providers in shell mode
cli-agent --mode shell --provider gemini

# Enable trace mode to see LLM execution details
cli-agent --mode shell --trace

# Don't restore initial directory on exit
cli-agent --mode shell --no-restore

# Or set environment variable for trace
CLI_AGENT_TRACE=1 cli-agent --mode shell
```

#### Enhanced Shell Features

**Visual Agent Indicator:**
```bash
⭐ user@host:~/project$  # Agent mode (indicator configurable)
user@host:~/project$   # Regular shell
```

**Universal Tab Completion:**
- Works with all commands and paths
- No need for specific command lists
- Supports both GNU readline and macOS libedit

**Smart Directory Handling:**
```bash
⭐ user@host:~/project$ cd /tmp
⭐ user@host:/tmp$ pwd
/tmp
⭐ user@host:/tmp$ exit  # Returns to ~/project if preserve_initial_location=true
```

#### Shell Mode Examples

```bash
# Direct shell commands - executed immediately  
⭐ user@host:~/project$ ls -la
total 48
drwxr-xr-x  12 user  staff   384 Aug 21 10:30 .
drwxr-xr-x   5 user  staff   160 Aug 21 10:29 ..
-rw-r--r--   1 user  staff  1234 Aug 21 10:30 README.md

# Natural language - processed by LLM
⭐ user@host:~/project$ find all python files and count lines
🛠️  Executing command: find . -name "*.py" -type f
🛠️  Executing command: find . -name "*.py" -type f -exec wc -l {} + | tail -1
Total lines across all Python files: 2,847 lines

# Configuration through natural language
⭐ user@host:~/project$ change the prompt indicator to a robot emoji
Configuration updated successfully!
Applied changes: {'agent_prompt_indicator': '🤖'}

🤖 user@host:~/project$ set default mode to chat  
Configuration updated successfully!
Applied changes: {'default_mode': 'chat'}
```

### Command Line Options

```bash
cli-agent --help
```

Options:
- `--provider {openai,gemini,lmstudio}` or `-p`: Choose LLM provider (default: from config)
- `--model MODEL` or `-m`: Specify custom model for the selected provider (default: from config)
- `--mode {chat,shell}`: Choose interface mode (default: from config)
- `--verbose` or `-v`: Show detailed token usage information
- `--trace` or `-t`: Enable trace mode (show LLM execution details, shell mode only)
- `--no-reasoning`: Disable reasoning for faster responses (LM Studio only)
- `--no-restore`: Don't restore initial directory on exit (shell mode only)
- `--help` or `-h`: Show help message

**Note**: All defaults are read from your `~/.cliagent/settings.json` configuration.

### Shell Mode Features

**Intelligent Command Routing:**
- Shell commands executed directly: `ls -la`, `grep pattern *.py`, `git status`
- Natural language processed by LLM: `analyze this code`, `what files are here`

**Enhanced Shell Experience:**
- Visual agent indicator: Configurable symbol (⭐, 🤖, etc.) shows agent mode
- Universal tab completion: Works with all commands and file paths
- Proper built-in commands: `cd` and `pwd` actually change the working directory
- Directory preservation: Optional return to starting directory on exit

**Silent LLM Mode:**
- No intermediate "Agent is analyzing..." messages
- Clean output like a normal shell
- Enable trace mode to see LLM execution details

**Natural Language Configuration:**
- Change settings on the fly: "set default provider to gemini"
- Persistent across sessions: Settings saved automatically
- No need to edit config files manually

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
⭐ user@host:project$ ls -la                    # Direct shell execution
total 48
drwxr-xr-x  12 user  staff   384 Aug 21 10:30 .
...

⭐ user@host:project$ analyze this code         # LLM processing
🛠️  Executing command: find . -name "*.py" -type f
🛠️  Executing command: head -20 main.py
Based on the code analysis, this appears to be...

⭐ user@host:project$ git status              # Direct shell execution  
On branch main
Your branch is up to date with 'origin/main'.

⭐ user@host:project$ change default mode to chat  # Configuration update
Configuration updated successfully!
Applied changes: {'default_mode': 'chat'}
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
from agent.core_agent import LLMProvider, process_user_message

# Create configuration
from agent.config import load_settings
settings = load_settings()

# Process messages through core agent
from agent.core_agent import process_message_with_functions
response = process_message_with_functions(
    "List all running processes",
    LLMProvider.OPENAI,
    history=[]
)
print(response)

# Use configuration management
from agent.config import update_configuration
result = update_configuration({
    'default_provider': 'gemini',
    'agent_prompt_indicator': '🚀'
})
print(result['message'])

# Use chat interface programmatically
from interface.chat_interface import chat_main

# Use shell interface for smart execution  
from interface.shell_interface import smart_execute_with_fallback
is_shell, output = smart_execute_with_fallback("ls -la")
```

## Project Structure

```
cli-agent/
├── agent/                   # Core agent logic
│   ├── __init__.py         # Agent module exports
│   ├── core_agent.py       # Pure agent backend with centralized tools
│   ├── config.py           # Configuration management with LLM updates
│   └── utils.py            # System utilities and shell prompt generation
├── interface/              # User interface frontends
│   ├── chat_interface.py   # Interactive chat frontend
│   └── shell_interface.py  # Shell interface with smart routing
├── input_handler/          # Enhanced input handling
│   └── input_handler.py    # Universal tab completion and history
├── providers/              # Provider modules (API communication only)
│   ├── __init__.py         # Exports function dictionaries
│   ├── functions.py        # Tool definitions and mappings
│   ├── openai.py          # OpenAI-specific implementation
│   ├── gemini.py          # Gemini-specific implementation
│   └── lmstudio.py        # LM Studio-specific implementation
├── main.py                 # Unified entry point with config-based defaults
├── tests/                  # Comprehensive test suite
│   ├── test_agent.py      # Agent backend tests
│   ├── test_input_handler.py    # Input handler tests
│   └── test_utils.py      # Utilities tests
├── pyproject.toml          # Project configuration and dependencies
└── README.md               # This file
```

## Technical Implementation

### Architecture Overview

The project follows clean architecture principles with clear separation of concerns:

1. **Core Agent** (`agent/core_agent.py`):
   - Pure business logic for LLM processing
   - Multi-iteration execution with function calling
   - Centralized tool definitions (used by all providers)
   - Provider-agnostic message handling

2. **Configuration Management** (`agent/config.py`):
   - Persistent settings in `~/.cliagent/settings.json`
   - Natural language configuration updates via LLM
   - Default value management for CLI arguments

3. **Interface Frontends**:
   - **Chat Interface** (`interface/chat_interface.py`): Interactive conversation mode
   - **Shell Interface** (`interface/shell_interface.py`): Enhanced shell with visual indicators

4. **Provider Abstraction** (`providers/`):
   - Providers only handle API communication
   - Unified function mapping dictionaries  
   - Tools defined centrally in core agent, not duplicated per provider
   - OpenAI-compatible format for consistency

5. **Enhanced Input** (`input_handler/`):
   - Universal tab completion (works with all commands)
   - Cross-platform readline/libedit support
   - Command history management

### Provider Architecture

The agent uses a modular provider system where providers focus solely on API communication:

```python
# agent/core_agent.py - Centralized tool definitions
def get_agent_tools() -> List[Dict[str, Any]]:
    """All LLM tools defined once, used by all providers."""
    return [
        {
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "description": "Execute shell command...",
                # ... tool definition
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "update_agent_configuration",
                "description": "Update CLI agent settings...",
                # ... tool definition
            }
        }
    ]

# providers/openai.py - Provider only handles API
def get_available_tools() -> List[Dict[str, Any]]:
    """Return centralized tool definitions."""
    from agent.core_agent import get_agent_tools
    return get_agent_tools()
```

**Key Benefits:**
- No tool duplication across providers
- Single source of truth for all LLM capabilities  
- Providers focus only on API communication
- Easy to add new tools (define once, works everywhere)

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
2. Send message to selected LLM provider with centralized tools
3. Extract function calls if present
4. Execute tools via centralized `execute_tool()` function:
   - `run_shell_command`: Execute shell commands
   - `update_agent_configuration`: Modify persistent settings via natural language
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
def get_available_tools() -> List[Dict[str, Any]]:
    """Return centralized tool definitions."""
    from agent.core_agent import get_agent_tools
    return get_agent_tools()

def initialize_client() -> Any:
    """Initialize client for your provider."""
    api_key = os.getenv("YOUR_PROVIDER_API_KEY")
    if not api_key:
        raise ValueError("YOUR_PROVIDER_API_KEY environment variable not found.")
    return YourProviderClient(api_key=api_key)

# ... other required functions (send_message, extract_function_calls, etc.)
```

**Important**: Don't duplicate tool definitions! Use `get_agent_tools()` from core agent.

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

GET_AVAILABLE_TOOLS = {
    "openai": openai.get_available_tools,
    "gemini": gemini.get_available_tools,
    "your_provider": your_provider.get_available_tools,  # Add this
}

# Add to all other function dictionaries...
```

Tools are automatically available since your provider uses `get_agent_tools()`.

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
2. **Provider Abstraction**: Building unified interfaces for different APIs where providers focus on communication
3. **Centralized Tool Management**: Single source of truth for all LLM capabilities
4. **Configuration Management**: Persistent settings with natural language updates
5. **Enhanced User Experience**: Visual indicators, universal tab completion, smart command routing
6. **Security in AI Systems**: Implementing safeguards for agent systems
7. **Modular Design**: Creating extensible architectures with clear separation of concerns
8. **Agent Planning**: How models break down complex requests into executable steps
9. **Tool Integration**: Bridging language models with external systems
10. **Iterative Execution**: Managing multi-step workflows
11. **Natural Language Interfaces**: Configuration and control through conversation

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
- **Advanced Tools**: File operations, web requests, database queries, code execution
- **Persistent Memory**: Conversation history, learned preferences, user context
- **Smart Routing**: More sophisticated command vs NL detection
- **Enhanced Configuration**: Plugin system, custom tool definitions
- **Security Enhancements**: Sandboxing, granular permissions, audit logging
- **Performance**: Streaming responses, async execution, caching
- **Agent Orchestration**: Multi-agent collaboration
- **Tool Composition**: Complex multi-step tool chains
- **Natural Language APIs**: Voice interfaces, conversational configuration

## What This Project Teaches

- **Clean Architecture**: Separation of concerns, dependency inversion, centralized logic
- **Provider Patterns**: Abstraction layers where providers focus solely on API communication  
- **LLM Integration**: Function calling, multi-iteration logic, centralized tool definitions
- **Enhanced UX Design**: Visual indicators, universal input handling, natural language configuration
- **Configuration Management**: Persistent settings, natural language updates, default management
- **CLI Design**: Multiple interface modes, dynamic defaults from configuration
- **Testing Strategy**: Mocking external APIs, comprehensive coverage
- **Security Mindset**: Safe execution, permission controls
- **Modular Design**: Easy extension and maintenance, single responsibility principle

The codebase serves as a practical example of how to build robust, extensible LLM agent systems with proper architecture, user experience, and natural language configuration capabilities.

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
