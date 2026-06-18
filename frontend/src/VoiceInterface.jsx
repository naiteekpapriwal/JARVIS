import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, MicOff } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const VoiceInterface = () => {
  const [status, setStatus] = useState('idle');
  const [userTranscript, setUserTranscript] = useState('');
  const [jarvisReply, setJarvisReply] = useState('');
  const [amplitude, setAmplitude] = useState(0);
  const [messages, setMessages] = useState([]);

  const recognitionRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const sourceRef = useRef(null);

  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (audioContextRef.current) audioContextRef.current.close();
      if (recognitionRef.current) recognitionRef.current.abort();
    };
  }, []);

  const startAmplitudeLoop = useCallback(() => {
    if (!analyserRef.current) return;
    const data = new Uint8Array(analyserRef.current.fftSize);
    const loop = () => {
      analyserRef.current.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / data.length);
      setAmplitude(Math.min(rms * 4, 1));
      animFrameRef.current = requestAnimationFrame(loop);
    };
    loop();
  }, []);

  const stopAmplitudeLoop = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    setAmplitude(0);
  }, []);

  const playTTS = useCallback(async (text) => {
    setStatus('speaking');
    try {
      const res = await fetch(`${API_BASE}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!res.ok) throw new Error('TTS failed');
      const arrayBuffer = await res.arrayBuffer();

      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioContextRef.current;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyser);
      analyser.connect(ctx.destination);
      sourceRef.current = source;

      source.onended = () => {
        stopAmplitudeLoop();
        setStatus('idle');
      };

      source.start(0);
      startAmplitudeLoop();
    } catch (err) {
      console.error('TTS playback error:', err);
      setStatus('idle');
    }
  }, [startAmplitudeLoop, stopAmplitudeLoop]);

  const sendToJarvis = useCallback(async (text) => {
    setStatus('processing');
    setUserTranscript(text);
    setJarvisReply('');

    const updatedMessages = [...messages, { role: 'user', content: text }];
    setMessages(updatedMessages);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: updatedMessages })
      });
      const data = await res.json();

      if (data.status === 'success') {
        const reply = data.reply || '';
        setJarvisReply(reply);
        setMessages(data.messages || updatedMessages);
        if (reply.trim()) {
          await playTTS(reply);
        } else {
          setStatus('idle');
        }
      } else {
        setJarvisReply('Error: ' + (data.message || 'Unknown error'));
        setStatus('idle');
      }
    } catch (err) {
      setJarvisReply('Connection error.');
      setStatus('idle');
    }
  }, [messages, playTTS]);

  const toggleMic = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition not supported. Use Chrome or Edge.');
      return;
    }

    if (status === 'listening') {
      if (recognitionRef.current) recognitionRef.current.stop();
      setStatus('idle');
      return;
    }

    if (sourceRef.current) {
      try { sourceRef.current.stop(); } catch (e) {}
      stopAmplitudeLoop();
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    let finalText = '';

    recognition.onstart = () => {
      setStatus('listening');
      setUserTranscript('');
      setJarvisReply('');
    };

    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setUserTranscript(transcript);
      finalText = transcript;
    };

    recognition.onerror = (event) => {
      console.error('Speech error:', event.error);
      setStatus('idle');
    };

    recognition.onend = () => {
      if (finalText.trim()) {
        sendToJarvis(finalText.trim());
      } else {
        setStatus('idle');
      }
    };

    recognition.start();
  }, [status, sendToJarvis, stopAmplitudeLoop]);

  // ── Computed ──
  const isActive = status === 'speaking';
  const isListening = status === 'listening';
  const glowStr = isActive ? 6 + amplitude * 15 : isListening ? 5 : 3;
  const coreGlow = isActive ? 0.4 + amplitude * 0.5 : isListening ? 0.35 : 0.12;

  const statusText = {
    idle: 'AWAITING COMMAND...',
    listening: '🎤  LISTENING...',
    processing: 'PROCESSING...',
    speaking: 'SPEAKING...',
  }[status];

  // Ring config — radii as percentage of the 600-unit viewBox
  const rings = [
    { r: 245, sw: 2,   da: '20 8 5 8',  spd: 55, dir: 1,  op: 0.3  },
    { r: 210, sw: 2.5, da: '3 6',       spd: 40, dir: -1, op: 0.45 },
    { r: 175, sw: 3,   da: '35 5 8 5',  spd: 28, dir: 1,  op: 0.55 },
    { r: 140, sw: 1.5, da: '2 7',       spd: 50, dir: -1, op: 0.35 },
    { r: 105, sw: 4,   da: 'none',      spd: 0,  dir: 1,  op: 0.85 },
  ];

  return (
    <div className="vi-root">
      {/* Full-screen SVG — rings are the background */}
      <svg className="vi-svg" viewBox="0 0 600 600" preserveAspectRatio="xMidYMid meet">
        <defs>
          <filter id="vi-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={glowStr} result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="vi-core-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="12" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Subtle radial backdrop */}
        <circle cx="300" cy="300" r="260" fill="none" stroke="rgba(0,240,255,0.02)" strokeWidth="180" />

        {/* Decorative tick marks around ring 3 */}
        {Array.from({ length: 36 }).map((_, i) => {
          const a = (i * 10 * Math.PI) / 180;
          return (
            <line key={`t${i}`}
              x1={300 + 172 * Math.cos(a)} y1={300 + 172 * Math.sin(a)}
              x2={300 + 180 * Math.cos(a)} y2={300 + 180 * Math.sin(a)}
              stroke="rgba(0,240,255,0.2)" strokeWidth="1.2"
            />
          );
        })}

        {/* Binary dots around ring 2 */}
        {Array.from({ length: 48 }).map((_, i) => {
          const a = (i * 7.5 * Math.PI) / 180;
          return (
            <circle key={`d${i}`}
              cx={300 + 212 * Math.cos(a)} cy={300 + 212 * Math.sin(a)}
              r={isActive ? 1.8 + amplitude : 1.2}
              fill={i % 3 ? 'rgba(0,240,255,0.45)' : 'rgba(0,240,255,0.1)'}
            />
          );
        })}

        {/* 5 rotating rings */}
        {rings.map((ring, i) => {
          const sm = isActive ? Math.max(0.2, 1 - amplitude * 0.6) : isListening ? 0.7 : 1;
          const dur = ring.spd > 0 ? ring.spd * sm : 0;
          const sc = isActive ? 1 + amplitude * 0.02 * (i + 1) : 1;
          return (
            <circle key={i} cx="300" cy="300" r={ring.r}
              fill="none" stroke="var(--color-cyan)"
              strokeWidth={ring.sw + (isActive ? amplitude * 1.5 : 0)}
              strokeDasharray={ring.da} opacity={ring.op + (isActive ? amplitude * 0.25 : 0)}
              filter="url(#vi-glow)"
              style={{
                transformOrigin: '300px 300px',
                transform: `scale(${sc})`,
                animation: dur > 0 ? `voice-ring-spin ${dur}s linear infinite ${ring.dir < 0 ? 'reverse' : 'normal'}` : 'none',
                transition: 'stroke-width 0.15s, opacity 0.15s, transform 0.15s',
              }}
            />
          );
        })}

        {/* Crosshairs */}
        <line x1="300" y1="45" x2="300" y2="60" stroke="var(--color-cyan)" strokeWidth="1.5" opacity="0.25" />
        <line x1="300" y1="540" x2="300" y2="555" stroke="var(--color-cyan)" strokeWidth="1.5" opacity="0.25" />
        <line x1="45" y1="300" x2="60" y2="300" stroke="var(--color-cyan)" strokeWidth="1.5" opacity="0.25" />
        <line x1="540" y1="300" x2="555" y2="300" stroke="var(--color-cyan)" strokeWidth="1.5" opacity="0.25" />

        {/* Core */}
        <circle cx="300" cy="300" r="60" fill={`rgba(0,240,255,${coreGlow * 0.12})`}
          stroke="rgba(0,240,255,0.5)" strokeWidth={1.5 + (isActive ? amplitude * 2 : 0)}
          filter="url(#vi-core-glow)" style={{ transition: 'all 0.15s' }} />
        <circle cx="300" cy="300" r="42" fill={`rgba(0,240,255,${coreGlow * 0.2})`}
          style={{ transition: 'fill 0.15s' }} />

        {/* Center text */}
        <text x="300" y="296" textAnchor="middle" dominantBaseline="middle"
          fill="var(--color-cyan)" fontFamily="var(--font-hud)" fontSize="16"
          letterSpacing="6" filter="url(#vi-glow)">
          J.A.R.V.I.S.
        </text>
        <text x="300" y="314" textAnchor="middle" dominantBaseline="middle"
          fill="rgba(0,240,255,0.4)" fontFamily="var(--font-mono)" fontSize="7" letterSpacing="3">
          VOICE INTERFACE v2.0
        </text>
      </svg>

      {/* Overlay: transcript */}
      <div className="vi-overlay">
        {(userTranscript || jarvisReply) && (
          <div className="vi-transcript">
            {userTranscript && (
              <div className="vi-line vi-user"><span className="vi-label">YOU:</span> {userTranscript}</div>
            )}
            {jarvisReply && (
              <div className="vi-line vi-jarvis">
                <span className="vi-label">JARVIS:</span> {jarvisReply.length > 180 ? jarvisReply.slice(0, 180) + '…' : jarvisReply}
              </div>
            )}
          </div>
        )}

        {/* Status */}
        <div className={`vi-status ${status}`}>{statusText}</div>

        {/* Mic */}
        <button className={`vi-mic ${status === 'listening' ? 'active' : ''} ${status === 'processing' ? 'disabled' : ''}`}
          onClick={toggleMic} disabled={status === 'processing'}>
          {status === 'listening' ? <Mic size={28} /> : <MicOff size={28} />}
          {status === 'listening' && <span className="vi-mic-pulse" />}
          {status === 'listening' && <span className="vi-mic-pulse d2" />}
        </button>
      </div>
    </div>
  );
};

export default VoiceInterface;
