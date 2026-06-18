"""
Jarvis — Local AI Agent (CLI Interface)
=====================================
A continuous terminal chat loop that routes natural language commands
to a local Ollama LLM with tool-calling capabilities.
"""

import os
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

import jarvis_core as core
import tts

def record_audio_until_enter():
    import sounddevice as sd
    import numpy as np
    import scipy.io.wavfile as wav
    import queue
    import sys
    
    q = queue.Queue()
    
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    samplerate = 16000
    channels = 1
    
    core.console.print("  [bold red]🎤 Recording...[/bold red] (Press [bold]Enter[/bold] to stop)")
    
    stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback)
    with stream:
        input()  # Wait for Enter
        
    core.console.print("  [dim]Processing audio...[/dim]")
    
    audio_data = []
    while not q.empty():
        audio_data.append(q.get())
    
    if not audio_data:
        return None
        
    audio_np = np.concatenate(audio_data, axis=0)
    
    filepath = "/tmp/jarvis_voice.wav"
    wav.write(filepath, samplerate, audio_np)
    return filepath

def main():
    """Continuous terminal chat loop with rich formatting."""
    # ── Startup banner ──────────────────────────────────────────────
    core.console.print()
    core.console.print(
        Panel(
            Text.from_markup(
                f"[bold bright_cyan]🤖 JARVIS — Local AI Agent (CLI)[/bold bright_cyan]\n"
                f"[dim]Model  : {core.DEFAULT_MODEL}[/dim]\n"
                f"[dim]Server : {core.CONFIG['ollama']['base_url']}[/dim]"
            ),
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )

    # ── Initialize subsystems ───────────────────────────────────────
    core.console.print("  Initializing subsystems...", style="dim")
    core.MEMORY = core.init_memory()
    core.console.print("  ✅ File search (Spotlight) ready — searches entire laptop", style="green")
    core.console.print()

    client = core.create_client()

    # Conversation history (persists within session)
    messages: list[dict] = [{"role": "system", "content": core.SYSTEM_PROMPT}]

    # Input history (persists across sessions via file)
    os.makedirs(".jarvis", exist_ok=True)
    history = FileHistory(".jarvis/input_history")

    core.console.print(
        "  [dim]Type[/dim] [bold]exit[/bold] [dim]or[/dim] [bold]quit[/bold] "
        "[dim]to end the session.[/dim]\n"
    )

    # Track whether TTS is enabled (loaded from config)
    tts_enabled = core.CONFIG.get("tts", {}).get("enabled", True)
    tts_voice = core.CONFIG.get("tts", {}).get("voice", "Daniel")
    tts_rate = core.CONFIG.get("tts", {}).get("rate", 190)

    while True:
        # ── Get user input ──────────────────────────────────────────
        try:
            # Stop any ongoing speech when user starts typing
            tts.stop()
            user_input = prompt("You ➜  ", history=history).strip()
        except (EOFError, KeyboardInterrupt):
            core.console.print("\n  👋 Session ended. Goodbye!\n", style="bold")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            core.save_session(messages)
            core.console.print("\n  👋 Session ended. Goodbye!\n", style="bold")
            break

        # ── Special command: help ────────────────────────────────────
        if user_input.lower() == "/help":
            core.console.print(
                Panel(
                    "[bold]Commands:[/bold]\n"
                    "  /help  — Show this help\n"
                    "  /voice — Record audio using your microphone\n"
                    "  /mute  — Mute Jarvis voice\n"
                    "  /unmute — Unmute Jarvis voice\n"
                    "  exit   — End session\n\n"
                    "[bold]Capabilities:[/bold]\n"
                    "  🧠 Memory — I remember things across sessions\n"
                    "  🔍 File Search — I can find any file on your laptop\n"
                    "  🌐 Web Search — I can search the web for information\n"
                    "  ⚡ OS Commands — I can run shell commands (with your approval)\n"
                    "  🔊 Voice — Jarvis speaks responses using Daniel voice",
                    title="Help",
                    border_style="bright_cyan",
                ),
            )
            continue

        # ── Special command: mute/unmute ─────────────────────────────
        if user_input.lower() == "/mute":
            tts_enabled = False
            tts.stop()
            core.console.print("  🔇 [dim]Voice muted.[/dim]")
            continue

        if user_input.lower() == "/unmute":
            tts_enabled = True
            core.console.print("  🔊 [dim]Voice unmuted.[/dim]")
            continue

        # ── Special command: voice ───────────────────────────────────
        if user_input.lower() == "/v" or user_input.lower() == "/voice":
            try:
                audio_path = record_audio_until_enter()
                if not audio_path:
                    continue
                transcription = core.transcribe_audio(audio_path)
                if not transcription:
                    core.console.print("  [yellow]No speech detected.[/yellow]")
                    continue
                core.console.print(f"  [cyan]You:[/cyan] {transcription}")
                user_input = transcription
            except Exception as e:
                core.console.print(f"  ❌ Error recording audio: {e}", style="bold red")
                continue

        # ── Send to LLM ────────────────────────────────────────────
        messages.append({"role": "user", "content": user_input})

        try:
            with core.console.status("[bold cyan]Thinking...", spinner="dots"):
                reply = core.chat_turn(client, messages, core.DEFAULT_MODEL)

            # Render response as markdown
            core.console.print()
            core.console.print(
                Panel(
                    Markdown(reply) if reply else Text("(empty response)"),
                    title="[bold bright_cyan]Jarvis[/bold bright_cyan]",
                    border_style="bright_cyan",
                    padding=(1, 2),
                )
            )
            core.console.print()

            # Speak the reply aloud
            if tts_enabled and reply:
                tts.speak(reply, voice=tts_voice, rate=tts_rate)

            # Save to memory in the background
            core.save_to_memory(user_input, reply)

        except Exception as e:
            core.console.print(f"\n  ❌ Error: {e}\n", style="bold red")
            messages.pop()  # Remove failed user message

if __name__ == "__main__":
    main()
