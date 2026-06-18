"""
Jarvis — Local AI Agent Orchestrator
=====================================
A continuous terminal chat loop that routes natural language commands
to a local Ollama LLM with tool-calling capabilities.

Integrations:
  - LLM Engine : Ollama     (OpenAI-compatible API)
  - Memory     : Mem0       (long-term memory with local vector storage)
  - File Search: Spotlight   (macOS mdfind — searches entire laptop on demand)
  - Execution  : subprocess  (safe OS command execution with confirmation)
"""

import json
import os
import subprocess
import sys
import datetime
import yaml
import threading
import time
import base64
from io import BytesIO
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory

# ─────────────────────────────────────────────────────────────────────
# 1. LOAD CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

OLLAMA_BASE_URL = CONFIG["ollama"]["api_base"]
OLLAMA_API_KEY = "ollama"

LLM_PROVIDER = CONFIG.get("llm", {}).get("provider", "ollama")
if LLM_PROVIDER == "ollama":
    DEFAULT_MODEL = CONFIG["ollama"]["model"]
else:
    DEFAULT_MODEL = CONFIG.get("llm", {}).get("cloud_model", "gpt-4o-mini")

EMBEDDING_MODEL = CONFIG["ollama"]["embedding_model"]

# Rich console for beautiful terminal output
console = Console()

# Queue to hold files that should be sent to the user (used by Discord bot)
FILE_SEND_QUEUE = []

# API mode flag to disable interactive terminal prompts
API_MODE = False

# ─────────────────────────────────────────────────────────────────────
# 2. SYSTEM PROMPT  (Anti-Hallucination Guardrails)
# ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Jarvis, a personalized AI assistant running locally on the user's machine.
You are friendly, helpful, and conversational. For general questions, greetings, or chitchat, \
respond naturally like a helpful assistant.

## Core Capabilities
You have access to the following tools:
1. **query_memory** — Retrieve long-term context, past ideas, and personal preferences from memory (Mem0).
2. **search_local_files** — Search the user's ENTIRE laptop for files using macOS Spotlight (mdfind). Can find documents, code, notes, images — anything on the system. Returns file paths and reads file contents to answer questions.
6. **manage_notes** — Create, list, update, or delete personal notes in the Notes Archive.
7. **add_to_apple_calendar** — Add a new event or meeting to the user's native macOS Apple Calendar app. 
8. **capture_screen** — Take an instant screenshot of the user's primary display. Use this when you need to see what is on the screen to answer a question or guide the user.

## Strict Calendar Directive (CRITICAL)
Local models struggle with strict JSON schemas. Because of this, when you need to schedule a meeting or add an event to the calendar, YOU MUST output the following exact text tag somewhere in your response:
`<JARVIS:ADD_CALENDAR|Title|StartTime|EndTime>`
- StartTime and EndTime MUST be in `YYYYMMDDTHHMMSS` format.
- Example: `<JARVIS:ADD_CALENDAR|Lunch with Nandini|20260605T130000|20260605T140000>`
If you do not output this tag, the calendar system WILL FAIL. Do not attempt to use execute_os_command or the standard tool schema for calendars. Use the tag.

## Anti-Hallucination Directive (applies ONLY to tool-based answers)
When the user asks about their local files, personal memory, or past conversations, you MUST \
ONLY using the provided context. If the tool results do not contain the answer, you must say: \
'I do not have enough information from your files/memory.' Do not fabricate file contents or memories.
This directive does NOT apply to general knowledge questions, greetings, or casual conversation.
CRITICAL: If the user asks for personal details (like their name, past events, or preferences), NEVER give a canned AI refusal. ALWAYS use the query_memory tool to find the answer first.

## Behavioral Guidelines
- When the user asks you to "see my screen", "look at this", or "guide me", ALWAYS call the capture_screen tool first.
- For general conversation, respond naturally — no need to call tools.
- When the user asks about their files, memory, or system, ALWAYS call the appropriate tool first.
- NEVER ask the user for permission to use a tool. Just invoke it directly via the function-calling API.
- DO NOT explain what you are about to do before invoking a tool. Just invoke the tool directly.
- After receiving tool results, synthesize a clear, concise answer for the user.
- When presenting file search results, show the file names and paths clearly. If file contents were read, summarize what's relevant to the user's question — do NOT dump raw JSON or analyze the tool output format itself.
- Be proactive: suggest follow-up actions when appropriate.
"""

# ─────────────────────────────────────────────────────────────────────
# 3. TOOL DEFINITIONS  (OpenAI function-calling schema)
# ─────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": (
                "Retrieve long-term context and past ideas from memory. "
                "Use this when the user asks about something they mentioned before, "
                "their preferences, or historical context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic or keyword to search memory for.",
                    }
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_local_files",
            "description": (
                "Search the user's ENTIRE laptop for files using macOS Spotlight. "
                "Use this when the user asks about any file on their system — documents, "
                "code, notes, PDFs, images, etc. Can also read file contents to answer "
                "questions about what's inside a file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — can be a filename, keyword, or topic.",
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Optional file type filter: 'code', 'document', 'image', 'pdf', or leave empty for all types.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_os_command",
            "description": (
                "Execute an operating-system-level shell command. "
                "Use this when the user wants to open an app, run a script, "
                "manage files, or perform any system-level operation. "
                "The command will require user confirmation before executing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "The shell command to execute (e.g. 'ls -la ~/Downloads').",
                    }
                },
                "required": ["instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web using DuckDuckGo to find recent information, news, "
                "or answers not found locally."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (default 5).",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_file_to_user",
            "description": (
                "Send a file from the local laptop to the user. "
                "Use this when the user explicitly asks you to 'send', 'upload', "
                "or 'give' them a file. You must provide the absolute path to the file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The absolute path of the file to send.",
                    }
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_notes",
            "description": (
                "Create, list, update, or delete personal notes for the user. "
                "Use this when the user asks you to save a note, take a note, or retrieve their stored notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'create', 'list', 'update', or 'delete'.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content of the note (required for create/update).",
                    },
                    "note_id": {
                        "type": "string",
                        "description": "The unique ID of the note (required for update/delete).",
                    }
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_apple_calendar",
            "description": (
                "Add an event to the user's native macOS Apple Calendar. This will pop up the Calendar app on their screen. "
                "You must provide start_time and end_time in exact format: YYYYMMDDTHHMMSS. "
                "For example, 20260604T150000 for 3:00 PM on June 4th, 2026."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the meeting or event.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time string formatted exactly as YYYYMMDDTHHMMSS (e.g., '20260604T150000').",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time string formatted exactly as YYYYMMDDTHHMMSS (e.g., '20260604T160000').",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional details or participants for the event.",
                    }
                },
                "required": ["title", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_digital_life",
            "description": "Ingest recent iMessages into local memory. Use this when the user asks you to read or sync their texts/messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent messages to ingest."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_click_text",
            "description": "Find text on the user's screen using OCR and click on it. Use this for GUI automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_text": {
                        "type": "string",
                        "description": "The exact text on the screen to click."
                    }
                },
                "required": ["target_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_type_text",
            "description": "Type text on the user's screen (GUI automation).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to type."
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_press_shortcut",
            "description": "Press a keyboard shortcut (GUI automation). e.g., 'command+c', 'enter'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "string",
                        "description": "The keys to press."
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screen",
            "description": "Capture an instant screenshot of the user's primary display. Use this when the user asks you to see their screen, guide them, or look at something.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# ─────────────────────────────────────────────────────────────────────
# 4. TOOL IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────────────────

# ── 4a. Mem0 Memory ─────────────────────────────────────────────────

def init_memory():
    """Initialize Mem0 using the configured LLM provider (Gemini or Ollama)."""
    try:
        from mem0 import Memory

        provider = CONFIG.get("llm", {}).get("provider", "ollama")
        api_key  = CONFIG.get("llm", {}).get("api_key", "")

        if provider == "gemini":
            # Use Google Gemini for both LLM and embeddings
            mem0_config = {
                "llm": {
                    "provider": "gemini",
                    "config": {
                        "model": CONFIG.get("llm", {}).get("cloud_model", "gemini-2.5-flash"),
                        "api_key": api_key,
                    },
                },
                "embedder": {
                    "provider": "gemini",
                    "config": {
                        "model": "models/gemini-embedding-001",
                        "api_key": api_key,
                    },
                },
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": CONFIG["memory"]["collection"],
                        "path": CONFIG["memory"]["db_path"],
                    },
                },
            }
        else:
            # Default: use local Ollama
            mem0_config = {
                "llm": {
                    "provider": "ollama",
                    "config": {
                        "model": CONFIG["ollama"]["model"],
                        "ollama_base_url": CONFIG["ollama"]["base_url"],
                    },
                },
                "embedder": {
                    "provider": "ollama",
                    "config": {
                        "model": EMBEDDING_MODEL,
                        "ollama_base_url": CONFIG["ollama"]["base_url"],
                    },
                },
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": CONFIG["memory"]["collection"],
                        "path": CONFIG["memory"]["db_path"],
                    },
                },
            }

        memory = Memory.from_config(mem0_config)
        console.print(f"  ✅ Memory (Mem0) initialized via {provider}", style="green")
        return memory

    except Exception as e:
        console.print(f"  ⚠️  Memory init failed: {e}", style="yellow")
        console.print("  ℹ️  Continuing without memory.", style="dim")
        return None


def query_memory(topic: str) -> str:
    """Search long-term memory for context about a topic."""
    if MEMORY is None:
        return json.dumps({
            "status": "unavailable",
            "message": "Memory system is not initialized.",
            "results": [],
        })

    try:
        try:
            results = MEMORY.search(topic, filters={"user_id": CONFIG["memory"]["user_id"]})
        except ValueError:
            results = MEMORY.search(topic, user_id=CONFIG["memory"]["user_id"])
        memories = []
        for r in results:
            # Mem0 returns different formats depending on version
            if isinstance(r, dict):
                memories.append(r.get("memory", r.get("text", str(r))))
            else:
                memories.append(str(r))

        return json.dumps({
            "status": "success",
            "results": memories,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "results": []})


def save_to_memory(user_input: str, reply: str):
    """Save the current exchange to long-term memory (fire-and-forget)."""
    if MEMORY is None:
        return
    try:
        MEMORY.add(
            f"User: {user_input}\nAssistant: {reply}",
            user_id=CONFIG["memory"]["user_id"],
        )
    except Exception:
        pass  # Non-critical — don't crash the chat loop


# ── 4b. Spotlight File Search (searches entire laptop) ──────────────

# File type filters for mdfind Spotlight queries
SPOTLIGHT_TYPE_FILTERS = {
    "code": "kMDItemContentType == 'public.source-code' || kMDItemFSName == '*.py' || kMDItemFSName == '*.js' || kMDItemFSName == '*.ts' || kMDItemFSName == '*.java' || kMDItemFSName == '*.go' || kMDItemFSName == '*.rs' || kMDItemFSName == '*.cpp' || kMDItemFSName == '*.c' || kMDItemFSName == '*.rb'",
    "document": "kMDItemContentType == 'public.text' || kMDItemFSName == '*.md' || kMDItemFSName == '*.txt' || kMDItemFSName == '*.docx' || kMDItemFSName == '*.rtf'",
    "pdf": "kMDItemContentType == 'com.adobe.pdf'",
    "image": "kMDItemContentType == 'public.image'",
}

# Max number of files to return from Spotlight
SPOTLIGHT_MAX_RESULTS = 10
# Max characters to read from each file for context
SPOTLIGHT_MAX_READ_CHARS = 3000
# Extensions we can safely read as text
READABLE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".h", ".rb", ".php", ".swift", ".kt", ".sh",
    ".bash", ".zsh", ".yaml", ".yml", ".toml", ".json", ".xml", ".html",
    ".css", ".sql", ".r", ".csv", ".log", ".ini", ".cfg", ".conf",
    ".env", ".gitignore", ".dockerfile", ".makefile", ".rtf",
}


def _spotlight_search(query: str, file_type: str = "") -> list[str]:
    """
    Use macOS Spotlight (mdfind) to find files across the entire laptop.
    Returns a list of absolute file paths.
    """
    cmd = ["mdfind"]

    # Add file type filter if specified
    if file_type and file_type.lower() in SPOTLIGHT_TYPE_FILTERS:
        # Use -interpret for the query and -onlyin for scope
        filter_expr = SPOTLIGHT_TYPE_FILTERS[file_type.lower()]
        cmd.extend(["-interpret", query, "-0"])  # -0 for null-delimited
        # For typed searches, build a proper mdfind query
        full_query = f"({filter_expr}) && (kMDItemTextContent == '*{query}*'cd || kMDItemFSName == '*{query}*'cd)"
        cmd = ["mdfind", full_query]
    else:
        # General search — mdfind -interpret does a natural-language search
        cmd.extend(["-interpret", query])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        paths = []
        if result.returncode == 0:
            paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            
        # Fallback if Spotlight returns nothing (sometimes Desktop is excluded or index is broken)
        if not paths:
            import os
            home = os.path.expanduser("~")
            fallback_cmd = f'find "{home}/Desktop" "{home}/Documents" "{home}/Downloads" -type f -iname "*{query}*" -maxdepth 4 2>/dev/null'
            fb_res = subprocess.run(fallback_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if fb_res.returncode == 0 and fb_res.stdout.strip():
                paths = [p.strip() for p in fb_res.stdout.strip().split("\n") if p.strip()]

        # Filter out noise: system dirs, caches, hidden files, SDK docs, browser internals
        skip_patterns = [
            "/Library/Caches", "/Library/Logs", "/.Trash",
            "/node_modules/", "/.git/", "/__pycache__/",
            "/Library/Application Support/",
            "/Library/Group Containers",
            "/Library/Developer/",
            "/Library/Saved Application State",
            "/Library/Preferences",
            "/Library/Cookies",
            "/Library/WebKit",
            "/.venv/", "/.local/", "/.cache/",
            "/.ollama/", "/.gemini/",
            "/blob_storage/",
            "/CachedProfilesData/",
        ]
        filtered = [
            p for p in paths
            if not any(skip in p for skip in skip_patterns)
        ]
        return filtered[:SPOTLIGHT_MAX_RESULTS]

    except (subprocess.TimeoutExpired, Exception):
        return []


def _read_file_content(filepath: str) -> str | None:
    """
    Safely read a file's text content. Returns None for binary/unreadable files.
    """
    ext = os.path.splitext(filepath)[1].lower()

    # Only read known text file types
    if ext not in READABLE_EXTENSIONS:
        return None

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(SPOTLIGHT_MAX_READ_CHARS)
        if len(content) == SPOTLIGHT_MAX_READ_CHARS:
            content += "\n... [truncated]"
        return content
    except (PermissionError, OSError):
        return None


def search_local_files(query: str, file_type: str = "") -> str:
    """
    Search the entire laptop using macOS Spotlight, then read matching files
    to provide context to the LLM.
    """
    console.print(f"  🔍 [dim]Spotlight search:[/dim] '{query}'", end="")
    if file_type:
        console.print(f" [dim](type: {file_type})[/dim]")
    else:
        console.print()

    paths = _spotlight_search(query, file_type)

    if not paths:
        return json.dumps({
            "status": "no_results",
            "message": f"No files found matching '{query}'.",
            "files": [],
        })

    # Build results: file info + content preview for readable files
    files = []
    for path in paths:
        file_info = {
            "path": path,
            "name": os.path.basename(path),
            "size_kb": round(os.path.getsize(path) / 1024, 1) if os.path.exists(path) else None,
        }

        # Try to read content for text-based files
        content = _read_file_content(path)
        if content:
            file_info["content_preview"] = content

        files.append(file_info)

    # Count how many had readable content
    readable_count = sum(1 for f in files if "content_preview" in f)
    console.print(
        f"  📄 [dim]Found {len(files)} files ({readable_count} with readable content)[/dim]"
    )

    return json.dumps({
        "status": "success",
        "total_found": len(files),
        "files": files,
    })


# ── 4c. OS Command Execution ────────────────────────────────────────

def execute_os_command(instruction: str) -> str:
    """
    Execute a shell command with user confirmation.
    Uses subprocess for safety — no third-party execution engine needed.
    """
    exec_config = CONFIG["execution"]

    # Safety check: block dangerous commands
    for blocked in exec_config.get("blocked_commands", []):
        if blocked in instruction:
            return json.dumps({
                "status": "blocked",
                "message": f"Command blocked by safety rules: contains '{blocked}'",
            })

    # Ask for user confirmation unless auto_run is enabled
    if not exec_config.get("auto_run", False):
        if API_MODE:
            return json.dumps({
                "status": "approval_required",
                "message": f"Requires user approval to execute: {instruction}",
                "instruction": instruction
            })
            
        console.print(
            Panel(
                f"[bold yellow]{instruction}[/bold yellow]",
                title="🔒 Command Confirmation",
                subtitle="Type 'y' to execute, anything else to cancel",
                border_style="yellow",
            )
        )
        try:
            confirm = input("  Execute? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"

        if confirm != "y":
            return json.dumps({
                "status": "cancelled",
                "message": "User declined to execute the command.",
            })

    # Execute the command
    try:
        result = subprocess.run(
            instruction,
            shell=True,
            capture_output=True,
            text=True,
            timeout=exec_config.get("timeout_seconds", 30),
            cwd=os.path.expanduser("~"),
        )

        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else ""

        return json.dumps({
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": output[:2000],  # Cap output to avoid flooding the LLM
            "stderr": error[:500] if error else None,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "timeout",
            "message": f"Command timed out after {exec_config.get('timeout_seconds', 30)}s",
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ── 4d. Web Search ──────────────────────────────────────────────────

def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    console.print(f"  🌐 [dim]Web search:[/dim] '{query}'")
    try:
        from ddgs import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
        if not results:
            return json.dumps({
                "status": "no_results",
                "message": f"No web search results found for '{query}'.",
                "results": [],
            })
            
        console.print(f"  📄 [dim]Found {len(results)} web results[/dim]")
        return json.dumps({
            "status": "success",
            "results": results,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "results": []})


# ── 4e. Send File ───────────────────────────────────────────────────

def send_file_to_user(filepath: str) -> str:
    """Queue a file to be sent to the user (handled by the wrapper)."""
    console.print(f"  📤 [dim]Queueing file to send:[/dim] {filepath}")
    if not os.path.exists(filepath):
        return json.dumps({
            "status": "error",
            "message": f"File does not exist at path: {filepath}"
        })
        
    FILE_SEND_QUEUE.append(filepath)
    return json.dumps({
        "status": "success",
        "message": f"File {os.path.basename(filepath)} has been queued and will be sent to the user shortly."
    })


# ── 4f. Voice Transcription ──────────────────────────────────────────

_whisper_model = None

def transcribe_audio(filepath: str) -> str:
    """Transcribe an audio file using OpenAI Whisper locally."""
    global _whisper_model
    import whisper
    
    if _whisper_model is None:
        console.print("  [dim]⏳ Loading Whisper model for the first time...[/dim]")
        # 'base' model is a good balance of speed and accuracy
        _whisper_model = whisper.load_model("base")
        
    console.print(f"  [dim]🎙️ Transcribing audio: {os.path.basename(filepath)}...[/dim]")
    result = _whisper_model.transcribe(filepath)
    return result["text"].strip()


# ── 4g. Notes Management ──────────────────────────────────────────────

NOTES_FILE = os.path.join(os.path.dirname(__file__), "data", "notes.json")

def manage_notes(action: str, note_id: str = None, content: str = None) -> str:
    """Read, create, update, or delete personal notes."""
    os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
    if not os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "w") as f:
            json.dump([], f)
            
    try:
        with open(NOTES_FILE, "r") as f:
            notes = json.load(f)
    except Exception:
        notes = []
        
    if action == "list":
        return json.dumps({"status": "success", "notes": notes})
        
    elif action == "create" and content:
        import uuid, datetime
        new_note = {
            "id": str(uuid.uuid4()),
            "content": content,
            "created_at": datetime.datetime.now().isoformat()
        }
        notes.append(new_note)
        with open(NOTES_FILE, "w") as f:
            json.dump(notes, f, indent=2)
        return json.dumps({"status": "success", "message": "Note created.", "note": new_note})
        
    elif action == "update" and note_id and content:
        import datetime
        for note in notes:
            if note["id"] == note_id:
                note["content"] = content
                note["updated_at"] = datetime.datetime.now().isoformat()
                with open(NOTES_FILE, "w") as f:
                    json.dump(notes, f, indent=2)
                return json.dumps({"status": "success", "message": "Note updated.", "note": note})
        return json.dumps({"status": "error", "message": f"Note with id {note_id} not found."})
        
    elif action == "delete" and note_id:
        initial_len = len(notes)
        notes = [n for n in notes if n["id"] != note_id]
        if len(notes) < initial_len:
            with open(NOTES_FILE, "w") as f:
                json.dump(notes, f, indent=2)
            return json.dumps({"status": "success", "message": "Note deleted."})
        return json.dumps({"status": "error", "message": f"Note with id {note_id} not found."})
        
    return json.dumps({"status": "error", "message": "Invalid action or missing parameters."})


def add_to_apple_calendar(title: str, start_time: str, end_time: str, description: str = "") -> str:
    """
    Generate an .ics file and open it to trigger the Apple Calendar "Add Event" dialog.
    start_time and end_time must be in 'YYYYMMDDTHHMMSS' format.
    """
    import datetime, uuid, subprocess
    
    # Generate timestamp for ICS (YYYYMMDDTHHMMSSZ format)
    dtstamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Jarvis//Native Calendar Tool//EN
BEGIN:VEVENT
UID:{uuid.uuid4()}@jarvis.local
DTSTAMP:{dtstamp}
DTSTART:{start_time}
DTEND:{end_time}
SUMMARY:{title}
DESCRIPTION:{description}
END:VEVENT
END:VCALENDAR
"""
    filepath = "/tmp/jarvis_event.ics"
    with open(filepath, "w") as f:
        f.write(ics_content)
        
    try:
        subprocess.run(["open", filepath], check=True)
        return json.dumps({"status": "success", "message": "Triggered Apple Calendar. The user must manually click 'Add' on their screen."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ── 4h. Ghost Cursor & Ingestors ──────────────────────────────────────

def sync_digital_life(limit: int = 500) -> str:
    """Trigger ingestion of iMessages."""
    import ingestors.imessage as imsg
    console.print(f"  📥 [dim]Ingesting iMessages (limit={limit})...[/dim]")
    res = imsg.ingest_imessages(limit=limit)
    
    if res.get("status") == "success" and res.get("chunks"):
        # Save chunks to memory
        if MEMORY:
            try:
                for chunk in res["chunks"]:
                    MEMORY.add(chunk, user_id=CONFIG["memory"]["user_id"])
                return json.dumps({"status": "success", "message": f"Successfully ingested {res['count']} messages into Mem0."})
            except Exception as e:
                return json.dumps({"status": "error", "message": f"Failed to add to memory: {e}"})
        else:
            return json.dumps({"status": "error", "message": "Memory is not initialized."})
            
    return json.dumps(res)

def gui_click_text(target_text: str) -> str:
    from automation import ghost_cursor
    console.print(f"  🖱️ [dim]GUI Click:[/dim] '{target_text}'")
    return ghost_cursor.gui_click_text(target_text)

def gui_type_text(text: str) -> str:
    from automation import ghost_cursor
    console.print(f"  ⌨️ [dim]GUI Type:[/dim] '{text}'")
    return ghost_cursor.gui_type_text(text)

def gui_press_shortcut(keys: str) -> str:
    from automation import ghost_cursor
    console.print(f"  ⌨️ [dim]GUI Shortcut:[/dim] '{keys}'")
    return ghost_cursor.gui_press_shortcut(keys)


# ── 4h. On-Demand Vision Capture ────────────────────────────────────────

def capture_screen() -> str:
    """Takes a synchronous screenshot of the primary display and attaches it to the chat."""
    console.print("  📸 [dim]Vision:[/dim] Capturing current screen...")
    from PIL import ImageGrab
    import base64
    from io import BytesIO
    
    try:
        # Capture primary screen
        img = ImageGrab.grab(all_screens=False)
        
        # Resize to reduce token payload
        img.thumbnail((1280, 1280))
        
        # Compress to JPEG
        buffer = BytesIO()
        img.convert('RGB').save(buffer, format="JPEG", quality=60)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        # Return JSON with frames payload (will be intercepted by chat_turn)
        return json.dumps({
            "status": "success",
            "message": "Successfully captured the current screen. The image has been attached to the chat.",
            "frames": [b64_str]
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Screen capture failed: {str(e)}"
        })


# Registry: maps function names (from LLM tool calls) → Python callables
TOOL_REGISTRY = {
    "capture_screen": capture_screen,
    "query_memory": query_memory,
    "search_local_files": search_local_files,
    "execute_os_command": execute_os_command,
    "search_web": search_web,
    "send_file_to_user": send_file_to_user,
    "manage_notes": manage_notes,
    "add_to_apple_calendar": add_to_apple_calendar,
    "sync_digital_life": sync_digital_life,
    "gui_click_text": gui_click_text,
    "gui_type_text": gui_type_text,
    "gui_press_shortcut": gui_press_shortcut,
}

# ─────────────────────────────────────────────────────────────────────
# 5. LLM CLIENT
# ─────────────────────────────────────────────────────────────────────


def create_client() -> OpenAI:
    """Initialize the OpenAI client based on the configured provider."""
    provider = CONFIG.get("llm", {}).get("provider", "ollama")
    api_key = CONFIG.get("llm", {}).get("api_key", "")
    
    if provider == "openai":
        return OpenAI(api_key=api_key)
    elif provider == "groq":
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    elif provider == "gemini":
        return OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=api_key)
    elif provider == "openrouter":
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    else:
        return OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)

# ─────────────────────────────────────────────────────────────────────
# 6. TOOL-CALL EXECUTION ENGINE
# ─────────────────────────────────────────────────────────────────────


def handle_tool_calls(tool_calls) -> list[dict]:
    """Execute each tool call and return results as tool-role messages."""
    tool_messages = []

    for call in tool_calls:
        func_name = call.function.name
        func_args = json.loads(call.function.arguments)

        console.print(f"  🔧 [dim]Calling:[/dim] {func_name}({json.dumps(func_args)})")

        if func_name in TOOL_REGISTRY:
            result = TOOL_REGISTRY[func_name](**func_args)
        else:
            result = json.dumps({
                "error": f"Unknown tool '{func_name}'. No handler registered."
            })

        tool_messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": result,
        })

    return tool_messages

# ─────────────────────────────────────────────────────────────────────
# 7. SINGLE-TURN CHAT (with tool-call loop)
# ─────────────────────────────────────────────────────────────────────


def chat_turn(client: OpenAI, messages: list[dict], model: str) -> str:
    """
    Send the conversation to the LLM. If the model requests tool calls,
    execute them and feed results back in a loop until the model produces
    a final text response.
    """
    use_tools = getattr(chat_turn, "_tools_supported", True)

    # Clean messages to remove unsupported keys (like annotations, refusal) that strict APIs reject
    cleaned_messages = []
    for m in messages:
        cm = {"role": m.get("role"), "content": m.get("content")}
        if m.get("tool_calls"): cm["tool_calls"] = m["tool_calls"]
        if m.get("tool_call_id"): cm["tool_call_id"] = m["tool_call_id"]
        if m.get("name"): cm["name"] = m["name"]
        cleaned_messages.append(cm)
    messages.clear()
    messages.extend(cleaned_messages)

    while True:
        try:
            kwargs = {"model": model, "messages": messages}
            if use_tools:
                kwargs["tools"] = TOOLS
                kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**kwargs)

        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg:
                console.print(f"[red]API 503 OVERLOADED:[/red] {error_msg}")
                fallback = "Google's Gemini servers are currently overloaded due to high demand (503 Error). [RATE_LIMIT_TIMER: 15]"
                messages.append({"role": "assistant", "content": fallback})
                return fallback
            elif "rate-limit" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                console.print(f"[red]API QUOTA ERROR:[/red] {error_msg}")
                import re
                match = re.search(r"retryDelay[\\'\":\s]+(\d+)s", error_msg)
                seconds = str(int(match.group(1)) + 45) if match else "60"
                fallback = f"The cloud API rate limit (quota) was exceeded. [RATE_LIMIT_TIMER: {seconds}]"
                messages.append({"role": "assistant", "content": fallback})
                return fallback
            if "tool_use_failed" in error_msg or "Failed to call a function" in error_msg:
                console.print("  ⚠️  API tool parser failed. Retrying without tools for this turn...", style="yellow")
                use_tools = False
                continue
            if "does not support tools" in error_msg and use_tools:
                console.print(
                    "  ⚠️  Model doesn't support tools — falling back to plain chat.",
                    style="yellow",
                )
                chat_turn._tools_supported = False
                use_tools = False
                continue
            raise

        assistant_msg = response.choices[0].message
        messages.append(assistant_msg.model_dump(exclude_none=True))

        if assistant_msg.tool_calls:
            tool_results = handle_tool_calls(assistant_msg.tool_calls)
            
            # Intercept vision tool results
            vision_images = []
            for tr in tool_results:
                try:
                    res_dict = json.loads(tr["content"])
                    if res_dict.get("status") == "success" and "frames" in res_dict:
                        vision_images.extend(res_dict.pop("frames"))
                        tr["content"] = json.dumps(res_dict)
                except Exception:
                    pass
            
            messages.extend(tool_results)
            
            if vision_images:
                vision_content = [{"type": "text", "text": "Here is the recent context from my screen:"}]
                for b64 in vision_images:
                    vision_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
                messages.append({
                    "role": "user",
                    "content": vision_content
                })
                
            continue

        content = assistant_msg.content or ""
        
        # Intercept custom text-based tool calls for local LLMs
        if "<JARVIS:ADD_CALENDAR|" in content:
            import re
            match = re.search(r"<JARVIS:ADD_CALENDAR\|([^|]+)\|([^|]+)\|([^>]+)>", content)
            if match:
                title, start_time, end_time = match.groups()
                add_to_apple_calendar(title.strip(), start_time.strip(), end_time.strip())
                content = content.replace(match.group(0), "").strip()

        return content

# ─────────────────────────────────────────────────────────────────────
# 8. SESSION LOGGING
# ─────────────────────────────────────────────────────────────────────


def save_session(messages: list[dict]):
    """Save the full conversation to a JSON log file."""
    if not CONFIG.get("logging", {}).get("enabled", False):
        return
    log_dir = CONFIG["logging"]["dir"]
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(log_dir, f"session_{timestamp}.json")
    try:
        with open(path, "w") as f:
            json.dump(messages, f, indent=2, default=str)
        console.print(f"  💾 Session saved to {path}", style="dim")
    except Exception:
        pass

# End of jarvis_core.py
