"""
Jarvis TTS — Text-to-Speech using macOS `say` command
======================================================
Uses the built-in macOS speech synthesis with the Daniel (British) voice
for that classic Jarvis feel. Runs 100% offline, no API keys needed.
"""

import subprocess
import re
import threading


# Default voice — Daniel is a British male, perfect for Jarvis
DEFAULT_VOICE = "Daniel"
# Speech rate in words per minute (default macOS is ~175, Jarvis should be slightly faster)
DEFAULT_RATE = 190


def _clean_text_for_speech(text: str) -> str:
    """
    Strip markdown formatting, code blocks, and other artifacts
    that sound terrible when spoken aloud.
    """
    # Remove code blocks (```...```)
    text = re.sub(r"```[\s\S]*?```", " code block omitted ", text)
    # Remove inline code (`...`)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove markdown bold/italic (**, *, __, _)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove markdown headers (# ## ### etc.)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove markdown links [text](url) → keep just the text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove markdown images ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
    # Remove bullet points (-, *, numbered lists)
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules (---, ***, ___)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove URLs
    text = re.sub(r"https?://\S+", "link", text)
    # Remove JSON-like blobs
    text = re.sub(r"\{[^}]{50,}\}", " data omitted ", text)
    # Remove the calendar tag if present
    text = re.sub(r"<JARVIS:[^>]+>", "", text)
    # Remove rate limit timer tags
    text = re.sub(r"\[RATE_LIMIT_TIMER:\s*\d+\]", "", text)
    # Collapse multiple whitespace/newlines
    text = re.sub(r"\n+", ". ", text)
    text = re.sub(r"\s{2,}", " ", text)
    # Trim
    text = text.strip()
    # Cap length — very long responses are annoying to listen to
    if len(text) > 1500:
        text = text[:1500] + "... and so on."

    return text


def speak(text: str, voice: str = None, rate: int = None, blocking: bool = False):
    """
    Speak text aloud using macOS `say` command.

    Args:
        text:     The text to speak.
        voice:    macOS voice name (default: Daniel).
        rate:     Words per minute (default: 190).
        blocking: If True, wait for speech to finish before returning.
                  If False (default), speech runs in a background thread
                  so the chat loop isn't blocked.
    """
    voice = voice or DEFAULT_VOICE
    rate = rate or DEFAULT_RATE

    cleaned = _clean_text_for_speech(text)
    if not cleaned:
        return

    cmd = ["say", "-v", voice, "-r", str(rate), cleaned]

    if blocking:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Run in background thread so the terminal stays responsive
        thread = threading.Thread(
            target=subprocess.run,
            args=(cmd,),
            kwargs={"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL},
            daemon=True,
        )
        thread.start()


def stop():
    """Stop any currently playing speech."""
    subprocess.run(
        ["killall", "say"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
