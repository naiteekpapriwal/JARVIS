import sqlite3
import os
import datetime
import json
from collections import defaultdict

def ingest_imessages(limit=500):
    """
    Connects to the macOS iMessage database, extracts recent messages,
    and returns them as formatted context chunks.
    Requires Full Disk Access for the Python/Terminal environment.
    """
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    
    if not os.path.exists(db_path):
        return {"status": "error", "message": f"iMessage database not found at {db_path}."}
        
    try:
        # Connect in read-only mode to prevent locking issues
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Query to get messages joined with handles
        query = """
        SELECT 
            m.text, 
            m.is_from_me, 
            h.id as phone_number,
            m.date
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.text IS NOT NULL
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"status": "success", "message": "No messages found.", "count": 0, "chunks": []}
            
        # Group messages by contact/conversation
        conversations = defaultdict(list)
        
        for text, is_from_me, phone_number, msg_date in rows:
            # macOS chat.db absolute time starts from Jan 1, 2001
            mac_epoch_offset = 978307200
            try:
                # the date is sometimes in nanoseconds on newer macOS versions, sometimes seconds
                if len(str(msg_date)) > 11:
                    timestamp = (msg_date / 1000000000) + mac_epoch_offset
                else:
                    timestamp = msg_date + mac_epoch_offset
                dt = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = "Unknown Date"
                
            sender = "Me" if is_from_me else (phone_number if phone_number else "Unknown")
            conversations[sender].append(f"[{dt}] {sender}: {text}")
            
        # Format into chunks for Memory
        chunks = []
        for contact, messages in conversations.items():
            # Reverse to chronological order for the chunk
            messages.reverse()
            # Limit chunk size slightly to avoid huge blocks
            chunk_text = f"iMessage Conversation with {contact}:\n" + "\n".join(messages[-50:])
            chunks.append(chunk_text)
            
        return {"status": "success", "message": f"Extracted {len(rows)} messages across {len(conversations)} contacts.", "count": len(rows), "chunks": chunks}
        
    except sqlite3.OperationalError as e:
        return {"status": "error", "message": f"Database error (you may need to grant Full Disk Access): {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

