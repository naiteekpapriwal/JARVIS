from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import subprocess
import os
import uuid
from datetime import datetime
import psutil

import jarvis_core as core

app = FastAPI(title="Jarvis Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core subsystems
core.API_MODE = True
client = core.create_client()
core.MEMORY = core.init_memory()

class ChatRequest(BaseModel):
    messages: list[dict]

class CommandRequest(BaseModel):
    instruction: str

from fastapi import BackgroundTasks

@app.post("/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    messages = req.messages
    # ensure system prompt is present
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": core.SYSTEM_PROMPT})
        
    try:
        reply = core.chat_turn(client, messages, core.DEFAULT_MODEL)
        
        # Check if there's any file queued to send
        files_to_send = list(core.FILE_SEND_QUEUE)
        core.FILE_SEND_QUEUE.clear()
        
        # Save to memory in background if it's a real user message
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if last_user_msg:
            background_tasks.add_task(core.save_to_memory, last_user_msg, reply)
            
        return {
            "status": "success",
            "reply": reply,
            "messages": messages,
            "files_to_send": files_to_send
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/execute")
async def execute_command(req: CommandRequest):
    """Execute a command that was approved by the UI."""
    try:
        result = subprocess.run(
            req.instruction,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.expanduser("~")
        )
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/notes")
async def get_notes():
    res = core.manage_notes("list")
    return json.loads(res)

class NoteRequest(BaseModel):
    content: str

@app.post("/notes")
async def create_note(req: NoteRequest):
    res = core.manage_notes("create", content=req.content)
    return json.loads(res)

@app.put("/notes/{note_id}")
async def update_note(note_id: str, req: NoteRequest):
    res = core.manage_notes("update", note_id=note_id, content=req.content)
    return json.loads(res)

@app.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    res = core.manage_notes("delete", note_id=note_id)
    return json.loads(res)



CHATS_FILE = "data/chats.json"

def load_chats():
    if not os.path.exists(CHATS_FILE):
        return []
    try:
        with open(CHATS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_chats(chats):
    os.makedirs("data", exist_ok=True)
    with open(CHATS_FILE, "w") as f:
        json.dump(chats, f, indent=4)

from typing import Optional

class ChatSessionRequest(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    messages: list

@app.get("/chats")
async def get_chats():
    return {"status": "success", "chats": load_chats()}

@app.post("/chats")
async def save_chat_session(req: ChatSessionRequest):
    chats = load_chats()
    chat_id = req.id if req.id else str(uuid.uuid4())
    title = req.title if req.title else "New Chat"
    
    if len(req.messages) > 1 and title == "New Chat":
        first_user = next((m["content"] for m in req.messages if m["role"] == "user"), None)
        if first_user:
            title = first_user[:30] + "..." if len(first_user) > 30 else first_user

    session = {
        "id": chat_id,
        "title": title,
        "messages": req.messages,
        "updated_at": datetime.now().isoformat()
    }
    
    updated = False
    for i, c in enumerate(chats):
        if c.get("id") == chat_id:
            chats[i] = session
            updated = True
            break
            
    if not updated:
        chats.append(session)
        
    chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    save_chats(chats)
    
    return {"status": "success", "chat": session}

@app.delete("/chats/{chat_id}")
async def delete_chat_session(chat_id: str):
    chats = load_chats()
    chats = [c for c in chats if c.get("id") != chat_id]
    save_chats(chats)
    return {"status": "success"}

import base64
class VoiceRequest(BaseModel):
    audio_base64: str

@app.post("/voice")
async def process_voice(req: VoiceRequest):
    try:
        # Decode base64 to temp file
        audio_data = base64.b64decode(req.audio_base64)
        temp_path = "/tmp/jarvis_web_voice.webm"
        with open(temp_path, "wb") as f:
            f.write(audio_data)
        
        # Transcribe
        transcription = core.transcribe_audio(temp_path)
        return {"status": "success", "text": transcription}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_gpu_usage():
    try:
        res = subprocess.run(['ioreg', '-l'], capture_output=True, text=True)
        import re
        match = re.search(r'"Device Utilization %"=([0-9]+)', res.stdout)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 0

@app.get("/system_metrics")
async def get_system_metrics():
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/')
        gpu = get_gpu_usage()
        
        return {
            "status": "success",
            "cpu_percent": cpu,
            "ram_percent": ram,
            "gpu_percent": gpu,
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/files/search")
async def search_files(query: str, file_type: str = ""):
    res = core.search_local_files(query, file_type)
    return json.loads(res)

@app.get("/memory")
async def get_memory():
    if core.MEMORY is None:
        return {"status": "offline", "message": "Memory offline. Start Ollama."}
    try:
        try:
            results = core.MEMORY.get_all(filters={"user_id": core.CONFIG["memory"]["user_id"]})
        except ValueError:
            results = core.MEMORY.get_all(user_id=core.CONFIG["memory"]["user_id"])
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
