"""
Jarvis — Discord Bot Interface
==============================
Connects the Jarvis AI Agent to Discord.
"""

import os
import asyncio
import discord
from discord.ext import commands

import jarvis_core as core

# ─────────────────────────────────────────────────────────────────────
# 1. SETUP & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

# Ensure the memory system is initialized
core.MEMORY = core.init_memory()
client = core.create_client()

# Discord settings from config.yaml
DISCORD_TOKEN = core.CONFIG.get("discord", {}).get("bot_token", "")
ALLOWED_USER_IDS = core.CONFIG.get("discord", {}).get("allowed_user_ids", [])

if not DISCORD_TOKEN:
    print("❌ Error: Discord bot_token is missing in config.yaml")
    exit(1)

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read user messages

bot = commands.Bot(command_prefix="!", intents=intents)

# Store conversation history per channel/thread
# Format: { channel_id: [ {"role": "system", "content": ...}, ... ] }
conversations = {}

# ─────────────────────────────────────────────────────────────────────
# 2. DISCORD EVENTS
# ─────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"🔒 Allowed User IDs: {ALLOWED_USER_IDS}")
    print("🤖 Jarvis is now online on Discord!")

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # ── Security Check ──────────────────────────────────────────────
    # Only allow specific users to interact with Jarvis (to prevent others from running commands)
    if ALLOWED_USER_IDS and message.author.id not in ALLOWED_USER_IDS:
        print(f"⚠️ Blocked unauthorized user: {message.author} (ID: {message.author.id})")
        return

    # Process standard commands (like !help if we had any)
    await bot.process_commands(message)

    # ── Chat Logic ──────────────────────────────────────────────────
    channel_id = message.channel.id
    user_input = message.content.strip()

    # ── Handle Voice Messages / Audio Attachments ───────────────────
    for attachment in message.attachments:
        # Discord voice messages are usually .ogg files
        if attachment.filename.lower().endswith(('.ogg', '.mp3', '.wav', '.m4a')):
            import os
            audio_path = os.path.join("/tmp", attachment.filename)
            await attachment.save(audio_path)
            
            async with message.channel.typing():
                try:
                    transcription = await asyncio.to_thread(core.transcribe_audio, audio_path)
                    if transcription:
                        user_input = f"{user_input} {transcription}".strip()
                        await message.channel.send(f"🎤 *Transcribed:* \"{transcription}\"")
                except Exception as e:
                    await message.channel.send(f"❌ Failed to transcribe audio: {e}")
                finally:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)

    if not user_input:
        return

    # Initialize conversation history for this channel if it doesn't exist
    if channel_id not in conversations:
        conversations[channel_id] = [{"role": "system", "content": core.SYSTEM_PROMPT}]

    messages = conversations[channel_id]
    messages.append({"role": "user", "content": user_input})

    # Show typing indicator while thinking
    async with message.channel.typing():
        try:
            # Clear the send queue before starting
            core.FILE_SEND_QUEUE.clear()
            
            # chat_turn uses synchronous Ollama and tool calls (like subprocess)
            # We must run it in a thread so it doesn't block the Discord async event loop.
            reply = await asyncio.to_thread(
                core.chat_turn,
                client,
                messages,
                core.DEFAULT_MODEL
            )

            # Send the response back to Discord
            # Discord has a 2000 character limit per message
            if reply:
                # Split reply into chunks of 2000 characters
                for i in range(0, len(reply), 2000):
                    await message.channel.send(reply[i:i+2000])

            # Send any files that were queued by the send_file_to_user tool
            if core.FILE_SEND_QUEUE:
                for filepath in core.FILE_SEND_QUEUE:
                    try:
                        await message.channel.send(file=discord.File(filepath))
                    except Exception as e:
                        await message.channel.send(f"❌ Failed to upload file: {os.path.basename(filepath)}. Error: {e}")

            # Save to Mem0 in a background task (don't block)
            asyncio.create_task(
                asyncio.to_thread(core.save_to_memory, user_input, reply)
            )

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(error_msg)
            await message.channel.send(error_msg)
            messages.pop()  # Remove the failed message from history

# ─────────────────────────────────────────────────────────────────────
# 3. RUN BOT
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
