import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, Shield, Mic, MicOff, CloudRain, ShieldAlert, Cpu, HardDrive, MessageSquare, Trash2, FileText, StopCircle, Menu } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import VoiceInterface from './VoiceInterface.jsx';
import './index.css';

const API_BASE = 'http://localhost:8000';

const SystemDial = ({ label, value }) => {
  const radius = 80;
  const innerRadius = 64;
  const outerRadius = 96;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <div className="system-dial" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minHeight: 0, justifyContent: 'center', width: '100%' }}>
      <div style={{ position: 'relative', height: '100%', maxHeight: '200px', minHeight: '100px', aspectRatio: '1/1' }}>
        <svg viewBox="0 0 240 240" style={{ width: '100%', height: '100%', filter: 'drop-shadow(0 0 10px var(--color-cyan))' }}>
          {/* Outer dashed tech ring */}
          <circle cx="120" cy="120" r={outerRadius} fill="none" stroke="rgba(0, 240, 255, 0.4)" strokeWidth="2" strokeDasharray="8 8" />
          
          {/* Inner solid ring background */}
          <circle cx="120" cy="120" r={innerRadius} fill="none" stroke="rgba(0, 240, 255, 0.1)" strokeWidth="4" />
          
          {/* Background track for main value */}
          <circle cx="120" cy="120" r={radius} fill="none" stroke="rgba(0, 240, 255, 0.1)" strokeWidth="16" />
          
          {/* Animated Value Ring */}
          <circle 
            cx="120" 
            cy="120" 
            r={radius} 
            fill="none" 
            stroke="var(--color-cyan)" 
            strokeWidth="16"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="butt"
            style={{ transition: 'stroke-dashoffset 1s ease-in-out', transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
          />
          
          {/* Crosshair decorative elements */}
          <line x1="120" y1="12" x2="120" y2="24" stroke="var(--color-cyan)" strokeWidth="3" opacity="0.6" />
          <line x1="120" y1="216" x2="120" y2="228" stroke="var(--color-cyan)" strokeWidth="3" opacity="0.6" />
          <line x1="12" y1="120" x2="24" y2="120" stroke="var(--color-cyan)" strokeWidth="3" opacity="0.6" />
          <line x1="216" y1="120" x2="228" y2="120" stroke="var(--color-cyan)" strokeWidth="3" opacity="0.6" />
          
          <text x="120" y="132" fill="var(--color-cyan)" fontSize="40" fontFamily="var(--font-hud)" fontWeight="bold" textAnchor="middle">{Math.round(value)}%</text>
        </svg>
      </div>
      <div className="dial-label" style={{ 
        color: 'var(--color-orange)', 
        fontSize: '1.2rem', 
        marginTop: '5px', 
        letterSpacing: '3px',
        fontFamily: 'var(--font-mono)'
      }}>{label}</div>
    </div>
  );
};

const NotesArchive = ({ notes, fetchNotes }) => {
  const [newNote, setNewNote] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState('');

  const handleCreate = async () => {
    if (!newNote.trim()) return;
    await fetch(`${API_BASE}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newNote })
    });
    setNewNote('');
    fetchNotes();
  };

  const handleUpdate = async (id) => {
    if (!editContent.trim()) return;
    await fetch(`${API_BASE}/notes/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: editContent })
    });
    setEditingId(null);
    fetchNotes();
  };

  const handleDelete = async (id) => {
    await fetch(`${API_BASE}/notes/${id}`, { method: 'DELETE' });
    fetchNotes();
  };

  return (
    <div className="notes-archive" style={{
      position: 'absolute', top: '80px', left: '20px', right: '20px', bottom: '80px',
      padding: '30px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px',
      background: 'rgba(5, 10, 15, 0.85)', border: '1px solid var(--color-panel-border)',
      backdropFilter: 'blur(10px)', clipPath: 'polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px)'
    }}>
      <h2 style={{ color: 'var(--color-cyan)', fontFamily: 'var(--font-hud)', letterSpacing: '3px', textShadow: '0 0 10px var(--color-cyan)' }}>NOTES ARCHIVE</h2>
      
      {/* Create Note Input */}
      <div style={{ background: 'rgba(0, 240, 255, 0.05)', border: '1px solid var(--color-cyan-dim)', padding: '15px' }}>
        <textarea 
          value={newNote} 
          onChange={e => setNewNote(e.target.value)} 
          placeholder="ENTER NEW ARCHIVE ENTRY..."
          style={{ width: '100%', minHeight: '80px', background: 'transparent', border: 'none', color: 'var(--color-cyan)', fontFamily: 'var(--font-mono)', outline: 'none', resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
          <button className="angled-btn active" onClick={handleCreate}>SAVE ENTRY</button>
        </div>
      </div>

      {/* Notes Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
        {notes.map(n => (
          <div key={n.id} style={{
            background: 'rgba(0, 240, 255, 0.02)',
            border: '1px solid var(--color-cyan-dim)',
            borderTop: '3px solid var(--color-cyan)',
            padding: '15px',
            fontFamily: 'var(--font-mono)',
            position: 'relative',
            minHeight: '150px'
          }}>
            <div style={{ color: 'var(--color-orange)', fontSize: '0.8rem', marginBottom: '10px' }}>
              {new Date(n.updated_at).toLocaleString()}
            </div>
            
            {editingId === n.id ? (
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <textarea 
                  value={editContent} 
                  onChange={e => setEditContent(e.target.value)}
                  style={{ flex: 1, width: '100%', minHeight: '100px', background: 'rgba(0,0,0,0.5)', border: '1px solid var(--color-cyan)', color: 'var(--color-cyan)', fontFamily: 'var(--font-mono)', outline: 'none', resize: 'vertical' }}
                />
                <div style={{ display: 'flex', gap: '10px', marginTop: '10px', justifyContent: 'flex-end' }}>
                  <button onClick={() => setEditingId(null)} style={{ background: 'none', color: 'var(--color-cyan)', border: '1px solid var(--color-cyan)', cursor: 'pointer', padding: '5px 10px' }}>CANCEL</button>
                  <button onClick={() => handleUpdate(n.id)} style={{ background: 'var(--color-cyan)', color: '#000', border: 'none', cursor: 'pointer', padding: '5px 10px', fontWeight: 'bold' }}>SAVE</button>
                </div>
              </div>
            ) : (
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div style={{ whiteSpace: 'pre-wrap', color: 'var(--color-cyan)', marginBottom: '40px', fontSize: '0.95rem', flex: 1 }}>{n.content}</div>
                <div style={{ position: 'absolute', bottom: '15px', right: '15px', display: 'flex', gap: '10px' }}>
                  <button onClick={() => { setEditingId(n.id); setEditContent(n.content); }} style={{ background: 'none', border: 'none', color: 'var(--color-cyan)', cursor: 'pointer' }}><FileText size={16} /></button>
                  <button onClick={() => handleDelete(n.id)} style={{ background: 'none', border: 'none', color: 'var(--color-orange)', cursor: 'pointer' }}><Trash2 size={16} /></button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const DataVault = () => {
  const [query, setQuery] = useState('');
  const [fileType, setFileType] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(`${API_BASE}/api/files/search?query=${encodeURIComponent(query)}&file_type=${encodeURIComponent(fileType)}`);
      const data = await res.json();
      if (data.status === 'success') {
        setResults(data.files || []);
      } else {
        setResults([]);
      }
    } catch (e) {
      console.error(e);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="notes-archive" style={{
      position: 'absolute', top: '80px', left: '20px', right: '20px', bottom: '80px',
      padding: '30px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px',
      background: 'rgba(5, 10, 15, 0.85)', border: '1px solid var(--color-panel-border)',
      backdropFilter: 'blur(10px)', clipPath: 'polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px)'
    }}>
      <h2 style={{ color: 'var(--color-cyan)', fontFamily: 'var(--font-hud)', letterSpacing: '3px', textShadow: '0 0 10px var(--color-cyan)' }}>DATA VAULT</h2>
      
      <div style={{ display: 'flex', gap: '15px', background: 'rgba(0, 240, 255, 0.05)', border: '1px solid var(--color-cyan-dim)', padding: '15px', alignItems: 'center' }}>
        <input 
          type="text" 
          value={query} 
          onChange={e => setQuery(e.target.value)} 
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="ENTER SEARCH QUERY..."
          style={{ flex: 1, background: 'transparent', border: 'none', color: 'var(--color-cyan)', fontFamily: 'var(--font-mono)', outline: 'none', fontSize: '1.1rem' }}
        />
        <select 
          value={fileType} 
          onChange={e => setFileType(e.target.value)}
          style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid var(--color-cyan)', color: 'var(--color-cyan)', fontFamily: 'var(--font-mono)', padding: '5px', outline: 'none' }}
        >
          <option value="">ALL FILES</option>
          <option value="code">CODE</option>
          <option value="document">DOCUMENT</option>
          <option value="pdf">PDF</option>
          <option value="image">IMAGE</option>
        </select>
        <button className="angled-btn active" onClick={handleSearch} disabled={loading}>
          {loading ? 'SCANNING...' : 'SCAN'}
        </button>
      </div>

      {searched && results.length === 0 && !loading && (
        <div style={{ textAlign: 'center', color: 'var(--color-orange)', marginTop: '40px', fontFamily: 'var(--font-mono)' }}>
          NO RECORDS FOUND
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
        {results.map((f, i) => (
          <div key={i} style={{
            background: 'rgba(0, 240, 255, 0.02)',
            border: '1px solid var(--color-cyan-dim)',
            borderTop: '3px solid var(--color-cyan)',
            padding: '15px',
            fontFamily: 'var(--font-mono)',
            position: 'relative',
            display: 'flex', flexDirection: 'column'
          }}>
            <div style={{ color: 'var(--color-cyan)', fontWeight: 'bold', wordBreak: 'break-all', marginBottom: '5px' }}>{f.name}</div>
            <div style={{ color: 'var(--color-orange)', fontSize: '0.8rem', marginBottom: '15px', wordBreak: 'break-all' }}>{f.path}</div>
            {f.size_kb && <div style={{ color: 'var(--color-cyan-dim)', fontSize: '0.8rem', position: 'absolute', top: '15px', right: '15px' }}>{f.size_kb} KB</div>}
            
            {f.content_preview && (
              <div style={{ 
                background: 'rgba(0,0,0,0.4)', padding: '10px', fontSize: '0.8rem', color: 'var(--color-cyan-dim)', 
                maxHeight: '150px', overflowY: 'auto', border: '1px solid rgba(0, 240, 255, 0.1)', whiteSpace: 'pre-wrap'
              }}>
                {f.content_preview}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const NeuralCore = () => {
  const [memories, setMemories] = useState([]);
  const [status, setStatus] = useState('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const fetchMemories = async () => {
      try {
        const res = await fetch(`${API_BASE}/memory`);
        const data = await res.json();
        if (data.status === 'success') {
          setMemories(data.results || []);
          setStatus('online');
        } else if (data.status === 'offline') {
          setStatus('offline');
          setErrorMsg(data.message);
        } else {
          setStatus('error');
          setErrorMsg(data.message || 'UNKNOWN ERROR');
        }
      } catch (e) {
        setStatus('error');
        setErrorMsg('CONNECTION FAILED');
      }
    };
    fetchMemories();
  }, []);

  return (
    <div className="notes-archive" style={{
      position: 'absolute', top: '80px', left: '20px', right: '20px', bottom: '80px',
      padding: '30px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px',
      background: 'rgba(5, 10, 15, 0.85)', border: '1px solid var(--color-panel-border)',
      backdropFilter: 'blur(10px)', clipPath: 'polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px)'
    }}>
      <h2 style={{ color: 'var(--color-cyan)', fontFamily: 'var(--font-hud)', letterSpacing: '3px', textShadow: '0 0 10px var(--color-cyan)' }}>NEURAL CORE</h2>
      
      {status === 'loading' && <div style={{ color: 'var(--color-cyan)', fontFamily: 'var(--font-mono)' }}>CONNECTING TO NEURAL NET...</div>}
      
      {status === 'offline' && (
        <div style={{ textAlign: 'center', color: 'var(--color-orange)', marginTop: '10%' }}>
          <ShieldAlert size={64} style={{ margin: '0 auto 20px', filter: 'drop-shadow(0 0 10px var(--color-orange))' }} />
          <h2 style={{ fontFamily: 'var(--font-hud)', letterSpacing: '3px' }}>NEURAL LINK SEVERED</h2>
          <p style={{ fontFamily: 'var(--font-mono)' }}>{errorMsg}</p>
        </div>
      )}

      {status === 'error' && (
        <div style={{ textAlign: 'center', color: 'red', marginTop: '10%' }}>
          <ShieldAlert size={64} style={{ margin: '0 auto 20px' }} />
          <h2 style={{ fontFamily: 'var(--font-hud)', letterSpacing: '3px' }}>SYSTEM ERROR</h2>
          <p style={{ fontFamily: 'var(--font-mono)' }}>{errorMsg}</p>
        </div>
      )}

      {status === 'online' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '20px', padding: '20px' }}>
          {memories.length === 0 ? (
             <div style={{ color: 'var(--color-cyan-dim)', fontFamily: 'var(--font-mono)' }}>NO MEMORIES EXTRACTED YET.</div>
          ) : (
            memories.map((m, i) => {
              const text = typeof m === 'object' ? (m.memory || m.text || JSON.stringify(m)) : m;
              return (
                <div key={i} style={{
                  background: 'rgba(0, 240, 255, 0.05)',
                  border: '1px solid rgba(0, 240, 255, 0.3)',
                  borderRadius: '50%',
                  width: '100%',
                  aspectRatio: '1/1',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '20px',
                  textAlign: 'center',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-cyan)',
                  boxShadow: '0 0 20px rgba(0, 240, 255, 0.1) inset',
                  animation: `pulse ${2 + Math.random()}s infinite alternate`
                }}>
                  <span style={{ fontSize: '0.85rem', textShadow: '0 0 5px var(--color-cyan)' }}>{text}</span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

const RateLimitTimer = ({ content }) => {
  const match = content.match(/\[RATE_LIMIT_TIMER:\s*(\d+)\]/);
  const initialSeconds = match ? parseInt(match[1]) : 60;
  const [sec, setSec] = useState(initialSeconds);

  useEffect(() => {
    if (sec <= 0) return;
    const timer = setInterval(() => setSec(s => s - 1), 1000);
    return () => clearInterval(timer);
  }, [sec]);

  const prefix = content.replace(/\[RATE_LIMIT_TIMER:\s*\d+\]/, '').trim();

  return (
    <div>
      <ReactMarkdown>{prefix}</ReactMarkdown>
      <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(255, 140, 0, 0.1)', border: '1px solid var(--color-orange)', color: 'var(--color-orange)', fontFamily: 'var(--font-mono)' }}>
        {sec > 0 ? `⚠️ RATE LIMIT DETECTED. RESTORING IN: ${sec} SECONDS...` : `✅ LIMIT RESTORED. READY.`}
      </div>
    </div>
  );
};

function App() {
  const [activeTab, setActiveTab] = useState('os');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  
  const [notes, setNotes] = useState([]);
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  const [sysStats, setSysStats] = useState({ cpu: 0, ram: 0, gpu: 0, diskUsed: 0, diskTotal: 0 });

  const [time, setTime] = useState('');
  const [date, setDate] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    fetchNotes();
    fetchChats();
    
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/system_metrics`);
        const data = await res.json();
        if (data.status === 'success') {
          setSysStats({
             cpu: data.cpu_percent,
             ram: data.ram_percent,
             gpu: data.gpu_percent || 0,
             diskUsed: data.disk_used_gb,
             diskTotal: data.disk_total_gb
          });
        }
      } catch (e) {}
    };
    fetchStats();
    
    const statTimer = setInterval(fetchStats, 2000);
    
    const timer = setInterval(() => {
      const now = new Date();
      setTime(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      setDate(now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' }));
    }, 1000);
    return () => {
      clearInterval(timer);
      clearInterval(statTimer);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${API_BASE}/notes`);
      const data = await res.json();
      if (data.status === 'success') setNotes(data.notes || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchChats = async () => {
    try {
      const res = await fetch(`${API_BASE}/chats`);
      const data = await res.json();
      if (data.status === 'success') setChatSessions(data.chats || []);
    } catch (e) {
      console.error(e);
    }
  };

  const createNewChat = () => {
    setMessages([]);
    setActiveChatId(null);
  };

  const loadChat = (chat) => {
    setMessages(chat.messages);
    setActiveChatId(chat.id);
  };

  const deleteChat = async (e, id) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/chats/${id}`, { method: 'DELETE' });
      if (activeChatId === id) createNewChat();
      fetchChats();
    } catch (err) {}
  };

  const saveChat = async (updatedMessages, chatIdToSave = activeChatId) => {
    try {
      const res = await fetch(`${API_BASE}/chats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: chatIdToSave, messages: updatedMessages })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setActiveChatId(data.chat.id);
        fetchChats();
        return data.chat.id;
      }
    } catch (e) {
      console.error(e);
    }
    return chatIdToSave;
  };

  const toggleRecording = async () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      alert("Your browser does not support real-time speech recognition. Please use Chrome or Edge.");
      return;
    }

    if (isRecording) {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      mediaRecorderRef.current = recognition;
      let finalString = "";

      recognition.onstart = () => {
        setIsRecording(true);
        setInput('');
      };

      recognition.onresult = (event) => {
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          interimTranscript += event.results[i][0].transcript;
        }
        setInput(interimTranscript);
        finalString = interimTranscript;
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
        if (finalString.trim()) {
          handleSendMessage(finalString);
        }
      };

      recognition.start();
    }
  };

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsTyping(false);
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Generation stopped by user.' }]);
    }
  };

  const handleSendMessage = async (textOverride) => {
    const textToSend = typeof textOverride === 'string' ? textOverride : input;
    if (!textToSend.trim()) return;
    const newUserMsg = { role: 'user', content: textToSend };
    const updatedMessages = [...messages, newUserMsg];
    setMessages(updatedMessages);
    setInput('');
    setIsTyping(true);

    const currentId = await saveChat(updatedMessages);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: updatedMessages }),
        signal: controller.signal
      });
      const data = await res.json();
      if (data.status === 'success') {
        setMessages(data.messages);
        await saveChat(data.messages, currentId);
        fetchNotes();
      } else {
        setMessages([...updatedMessages, { role: 'assistant', content: `❌ Error: ${data.message}` }]);
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        console.log('Generation aborted');
      } else {
        setMessages([...updatedMessages, { role: 'assistant', content: `❌ Connection error.` }]);
      }
    } finally {
      setIsTyping(false);
    }
  };

  const handleApproveCommand = async (instruction) => {
    setIsTyping(true);
    try {
      const res = await fetch(`${API_BASE}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction })
      });
      const data = await res.json();
      const resultText = `[System] Command executed.\nExit Code: ${data.exit_code}\nOutput:\n\`\`\`\n${data.stdout}\n\`\`\`\nError:\n\`\`\`\n${data.stderr}\n\`\`\``;
      
      const updatedMessages = [...messages, { role: 'user', content: resultText }];
      setMessages(updatedMessages);

      const chatRes = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: updatedMessages })
      });
      const chatData = await chatRes.json();
      if (chatData.status === 'success') {
         setMessages(chatData.messages);
         saveChat(chatData.messages);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsTyping(false);
    }
  };

  const displayMessages = [];
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.role === 'user' || msg.role === 'assistant') {
      if (msg.content) displayMessages.push({ ...msg, index: i });
    } else if (msg.role === 'tool') {
      try {
        const parsed = JSON.parse(msg.content);
        if (parsed.status === 'approval_required') {
          displayMessages.push({ role: 'system', content: parsed.message, instruction: parsed.instruction, index: i });
        }
      } catch (e) { }
    }
  }

  return (
    <div className="hud-container">
      {/* Top Bar */}
      <div className="top-bar">
        <button 
          onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
          style={{ background: 'none', border: 'none', color: 'var(--color-cyan)', cursor: 'pointer', marginRight: '15px', display: 'flex', alignItems: 'center' }}
        >
          <Menu size={24} />
        </button>
        <div className={`top-tab ${activeTab === 'os' ? 'active' : ''}`} onClick={() => setActiveTab('os')}>S.H.I.E.L.D OS</div>
        <div className={`top-tab ${activeTab === 'notes' ? 'active' : ''}`} onClick={() => setActiveTab('notes')}>NOTES ARCHIVE</div>
        <div className={`top-tab ${activeTab === 'data_vault' ? 'active' : ''}`} onClick={() => setActiveTab('data_vault')}>DATA VAULT</div>
        <div className={`top-tab ${activeTab === 'voice' ? 'active' : ''}`} onClick={() => setActiveTab('voice')}>VOICE INTERFACE</div>
        <div className="top-date-time">
          <span className="time-display">{time || '00:00'}</span>
          <span className="date-display">{date || 'INITIALIZING...'}</span>
        </div>
      </div>

      {activeTab === 'os' && (
        <>
          {/* Left Panel: Chat History */}
          <div className={`left-panel ${isSidebarOpen ? 'open' : 'closed'}`}>
            <div className="profile-badge">
              <div className="profile-avatar"><img src="/logo.png" alt="Jarvis" style={{ width: '100%', height: '100%', objectFit: 'contain', borderRadius: '50%' }} /></div>
              <div className="profile-info">
                <h3>AGENT: STARK</h3>
                <p>ACCESS: LEVEL 10</p>
              </div>
            </div>
            <div className="left-buttons-list" style={{ overflowY: 'auto', paddingRight: '5px' }}>
              <button className="angled-btn active" onClick={createNewChat} style={{ marginBottom: '10px' }}>
                + NEW CHAT
              </button>
              {chatSessions.map(c => (
                <div 
                  key={c.id} 
                  className={`angled-btn ${activeChatId === c.id ? 'active' : ''}`}
                  onClick={() => loadChat(c)}
                  style={{ justifyContent: 'space-between' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <MessageSquare size={14} />
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {c.title}
                    </span>
                  </div>
                  <button onClick={(e) => deleteChat(e, c.id)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Right Panel: Notes & Diagnostics */}
          <div className="right-panel" style={{ position: 'absolute', right: '20px', top: '80px', bottom: '120px', width: '320px', display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly', alignItems: 'center' }}>
            <SystemDial label="RAM USAGE" value={sysStats.ram} />
            <SystemDial label="CPU LOAD" value={sysStats.cpu} />
            <SystemDial label="GPU LOAD" value={sysStats.gpu} />
          </div>

          {/* Center Console */}
          <div className={`center-console ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
            <div className="reactor-bg">
              <div className="reactor-core"></div>
              <div className="reactor-inner"></div>
            </div>
            
            <div className="chat-panel">
              <div className="chat-header">
                <img src="/logo.png" alt="Jarvis" className="custom-logo" />
                <h2 className="chat-title">J.A.R.V.I.S. INTERFACE</h2>
              </div>
              
              <div className="chat-log">
                {displayMessages.length === 0 && (
                  <div style={{ textAlign: 'center', color: 'var(--color-cyan)', marginTop: '20%' }}>
                    <ShieldAlert size={48} style={{ margin: '0 auto 15px' }} />
                    <h3 style={{ fontFamily: 'var(--font-hud)', fontSize: '1.5rem', letterSpacing: '2px' }}>SYSTEM ONLINE</h3>
                    <p style={{ fontFamily: 'var(--font-mono)' }}>Awaiting commands, sir.</p>
                  </div>
                )}
                {displayMessages.map((msg, i) => (
                  <div key={i} className={`message ${msg.role}`}>
                    {msg.role === 'system' ? (
                      <div className="system-prompt">
                        <div className="prompt-title">⚠️ SYSTEM OVERRIDE REQUESTED</div>
                        <code>{msg.instruction}</code>
                        <button className="approve-btn" onClick={() => handleApproveCommand(msg.instruction)}>
                          EXECUTE
                        </button>
                      </div>
                    ) : Array.isArray(msg.content) ? (
                      <div className="vision-message-content">
                        {msg.content.map((part, pIdx) => {
                          if (part.type === 'text') {
                            return <ReactMarkdown key={pIdx}>{part.text}</ReactMarkdown>;
                          }
                          if (part.type === 'image_url') {
                            return (
                              <img 
                                key={pIdx} 
                                src={part.image_url.url} 
                                alt="Screen Context" 
                                style={{ maxWidth: '100%', maxHeight: '200px', objectFit: 'contain', borderRadius: '8px', marginTop: '10px', border: '1px solid var(--color-cyan-dim)' }} 
                              />
                            );
                          }
                          return null;
                        })}
                      </div>
                    ) : typeof msg.content === 'string' && msg.content.includes('[RATE_LIMIT_TIMER:') ? (
                      <RateLimitTimer content={msg.content} />
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>
                ))}
                {isTyping && <div className="message bot"><span className="typing-text">Processing...</span></div>}
                <div ref={messagesEndRef} />
              </div>

              <div className="chat-input-area">
                <textarea
                  className="chat-input"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
                  placeholder="ENTER COMMAND OR PRESS MIC..."
                  disabled={isTyping}
                />
                <button className={`chat-btn ${isRecording ? 'recording' : ''}`} onClick={toggleRecording} disabled={isTyping}>
                  {isRecording ? <Mic size={20} /> : <MicOff size={20} />}
                </button>
                {isTyping ? (
                  <button className="chat-btn" onClick={stopGeneration} style={{ color: 'var(--color-orange)', borderColor: 'var(--color-orange)' }}>
                    <StopCircle size={20} />
                  </button>
                ) : (
                  <button className="chat-btn" onClick={handleSendMessage} disabled={!input.trim()}>
                    <Send size={20} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'notes' && (
        <NotesArchive notes={notes} fetchNotes={fetchNotes} />
      )}

      {activeTab === 'data_vault' && (
        <DataVault />
      )}

      {activeTab === 'voice' && (
        <VoiceInterface />
      )}

      {/* Bottom Bar */}
      <div className="bottom-bar">
        <div className="bottom-stats">
          <div className="stat-row"><HardDrive size={14} /> C: <span className="stat-val">{sysStats.diskUsed} GB / {sysStats.diskTotal} GB</span></div>
          <div className="stat-row"><Cpu size={14} /> SYS CORE: <span className="stat-val">{sysStats.cpu}% LOAD</span></div>
        </div>
        <div className="bottom-status">Currently power level is at 100 percent and holding steady.</div>
        <div className="bottom-stats">
          <div className="stat-row">IP: <span className="stat-val">202.164.156.130</span></div>
        </div>
      </div>
    </div>
  );
}

export default App;
