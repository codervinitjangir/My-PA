import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Mic, MicOff, Volume2, VolumeX, Camera, Loader2 } from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';
import { useSpeech } from '../hooks/useSpeech';
import { TaskCard } from '../components/TaskCard';
import { cn } from '../lib/utils';
import { DashboardWidgets } from '../widgets/DashboardWidgets';

export const ChatPage: React.FC = () => {
  const {
    messages,
    isStreaming,
    currentMode,
    sessionId,
    settings,
    isListening,
    ttsSpeaking,
    autoListenMode,
    speechWidgetVisible,
    speechWidgetText,
    isCameraActive,
    camVisionMode,
    captureFrameFn,
    addChatMessage,
    updateChatMessage,
    setIsStreaming,
    setSessionId,
    setSearchResults,
    setSearchResultsVisible,
    addActivity,
    setActivityPanelOpen,
    setCameraActive,
  } = useJarvisStore();

  const [inputVal, setInputVal] = useState('');
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [ttsEnabled, setTtsEnabled] = useState(true);

  // Initialize Speech hooks
  const handleTranscript = useCallback((text: string) => {
    sendMessage(text);
  }, []);

  const {
    startListening,
    stopListening,
    toggleAutoListen,
    playThinkingSound,
    unlockAudioContext,
    ttsPlayer,
  } = useSpeech(handleTranscript);

  // Disable TTS on toggle
  const toggleTts = () => {
    const newVal = !ttsEnabled;
    setTtsEnabled(newVal);
    if (ttsPlayer) {
      ttsPlayer.enabled = newVal;
      if (!newVal) ttsPlayer.stop();
    }
    addActivity(`Text-to-Speech set to ${newVal}`, 'status');
  };

  // Auto scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Sync TTS enabled state
  useEffect(() => {
    if (ttsPlayer) {
      ttsPlayer.enabled = ttsEnabled;
    }
  }, [ttsEnabled, ttsPlayer]);

  // Auto resize input area
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(200, textarea.scrollHeight)}px`;
    }
  }, [inputVal]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming) {
        sendMessage();
      }
    }
  };

  // Helper to determine camera vision requirement
  const isCameraQuery = (text: string): boolean => {
    const patterns = [
      /what\s+(can|do)\s+you\s+see/i,
      /can\s+you\s+see/i,
      /describe\s+(what\s+you\s+see|this|the\s+image)/i,
      /what('s|s)\s+in\s+(this\s+)?(picture|image)/i,
      /what\s+do\s+i\s+look\s+like/i,
      /what\s+(am\s+i\s+)?holding/i,
      /show\s+me\s+what\s+you\s+see/i,
    ];
    const t = text.trim().toLowerCase();
    return patterns.some((p) => p.test(t)) || (t.includes('see') && (t.includes('what') || t.includes('describe')));
  };

  // Main Send Message Pipeline
  const sendMessage = async (textOverride?: string) => {
    let text = (textOverride || inputVal).trim();
    const isVisionOn = camVisionMode || isCameraQuery(text) || (isCameraActive && text);

    if (isVisionOn && !text) {
      text = 'What do you see?';
    }

    if (!text || isStreaming) return;

    // Reset speech states
    if (isListening) {
      stopListening();
    }

    addActivity(`Input Received: "${text}"`, 'status');

    // 1. Vision & Frame Capture
    let imgBase64: string | null = null;
    if (isVisionOn) {
      // Auto turn on camera if not already active
      if (!isCameraActive) {
        setCameraActive(true);
        addActivity('Activating camera pipeline for vision request...', 'status');
        // Wait 1.5s for camera stream initialization
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }

      // Capture frame
      if (captureFrameFn) {
        imgBase64 = await captureFrameFn();
        if (!imgBase64) {
          addActivity('Vision camera frame not ready yet', 'error');
        }
      }
    }

    setInputVal('');
    addChatMessage({
      role: 'user',
      text,
      images: imgBase64 ? [`data:image/jpeg;base64,${imgBase64}`] : undefined,
    });

    setIsStreaming(true);
    const assistantMsgId = addChatMessage({
      role: 'assistant',
      text: '',
      isStreaming: true,
    });

    // Reset TTS and play thinking sounds
    if (ttsPlayer) {
      ttsPlayer.reset();
      unlockAudioContext();
    }
    if (settings.thinkingSounds) {
      playThinkingSound();
    }

    const CAM_BYPASS_TOKEN = 'TTCAMTOKENTT';
    const messageToSend = imgBase64 ? `${text} ${CAM_BYPASS_TOKEN}` : text;
    
    // Choose endpoint based on current mode
    // (backend unified classify-and-execute endpoint)
    const endpoint = '/chat/jarvis/stream';

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min timeout

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageToSend,
          session_id: sessionId,
          tts: ttsEnabled && !!ttsPlayer,
          imgbase64: imgBase64 || null,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      if (!res.body) throw new Error('No stream response body');
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = '';
      let fullResponse = '';
      let streamDone = false;

      // Handle response actions or tasks
      let attachedTasks: any[] = [];

      while (!streamDone) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split('\n\n');
        sseBuffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.session_id) {
              setSessionId(data.session_id);
            }

            // Stream chunk
            if ('chunk' in data) {
              fullResponse += data.chunk || '';
              updateChatMessage(assistantMsgId, {
                text: fullResponse,
              });
              scrollToBottom();
            }

            // Play voice segment
            if (data.audio && ttsPlayer && ttsEnabled) {
              ttsPlayer.enqueue(data.audio);
            }

            // Activity panel data
            if (data.activity) {
              addActivity(data.activity.text || data.activity, data.activity.type || 'status');
              if (settings.autoOpenActivity) {
                setActivityPanelOpen(true);
              }
            }

            // Search results payload
            if (data.search_results) {
              setSearchResults(data.search_results);
              if (settings.autoOpenSearchResults) {
                setSearchResultsVisible(true);
              }
            }

            // Action triggers
            if (data.actions) {
              handleActions(data.actions, assistantMsgId);
            }

            // Background tasks
            if (data.background_tasks) {
              attachedTasks = [...attachedTasks, ...data.background_tasks];
              updateChatMessage(assistantMsgId, {
                backgroundTasks: attachedTasks,
              });
            }

            if (data.error) throw new Error(data.error);
            if (data.done) {
              streamDone = true;
              break;
            }
          } catch (parseErr: any) {
            if (parseErr.message && !parseErr.message.includes('JSON')) {
              throw parseErr;
            }
          }
        }
        if (streamDone) break;
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      let errMsg = 'Something went wrong. Please try again.';
      if (err.name === 'AbortError') {
        errMsg = 'Request timed out.';
      } else if (err.message) {
        errMsg = err.message;
      }
      updateChatMessage(assistantMsgId, {
        text: `Error: ${errMsg}`,
      });
    } finally {
      clearTimeout(timeoutId);
      setIsStreaming(false);
      updateChatMessage(assistantMsgId, {
        isStreaming: false,
      });
      // Restart auto-listen if active
      if (autoListenMode) {
        startListening();
      }
    }
  };

  // Custom Actions Handler for Streaming JSON
  const handleActions = (actions: any, msgId: string) => {
    if (!actions) return;

    // Web Open/Play URLs
    const urls = [
      ...(actions.wopens || []),
      ...(actions.plays || []),
      ...(actions.googlesearches || []),
      ...(actions.youtubesearches || []),
    ];

    urls.forEach((url) => {
      if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
        try {
          window.open(url, '_blank', 'noopener');
          addActivity(`Action: opened URL "${url}"`, 'tool');
        } catch (_) {}
      }
    });

    // Content writing text chunks
    if (actions.contents && actions.contents.length > 0) {
      addActivity(`Action: wrote document chunk`, 'tool');
    }

    // Image attachments
    if (actions.images && actions.images.length > 0) {
      updateChatMessage(msgId, {
        images: actions.images,
      });
    }

    // Camera action commands
    if (actions.cam) {
      if (actions.cam.action === 'open') {
        setCameraActive(true);
      } else if (actions.cam.action === 'close') {
        setCameraActive(false);
      } else if (actions.cam.action === 'open_and_capture') {
        const resendMsg = actions.cam.resend_message || 'What do you see?';
        (async () => {
          setCameraActive(true);
          await new Promise((resolve) => setTimeout(resolve, 2000));
          if (captureFrameFn) {
            const frame = await captureFrameFn();
            if (frame) {
              sendMessage(resendMsg);
            }
          }
        })();
      }
    }
  };

  // Text formatter helper for clean UI formatting
  const formatText = (text: string) => {
    if (!text) return null;

    // Simple markdown code block parser
    const parts = text.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const code = part.slice(3, -3).replace(/^[a-zA-Z]+\n/, ''); // Strip lang identifier
        return (
          <pre key={index} className="my-2 p-3 rounded-lg bg-zinc-900 border border-zinc-800/80 font-mono text-[11px] overflow-x-auto text-zinc-300 select-text">
            <code>{code}</code>
          </pre>
        );
      }

      // Inline code blocks `` `code` `` and Bold text `**bold**`
      const inlineParts = part.split(/(\*\*.*?\*\*|`.*?`)/g);

      return (
        <span key={index} className="whitespace-pre-line leading-relaxed font-sans">
          {inlineParts.map((subPart, subIdx) => {
            if (subPart.startsWith('**') && subPart.endsWith('**')) {
              return <strong key={subIdx} className="font-bold text-zinc-100">{subPart.slice(2, -2)}</strong>;
            }
            if (subPart.startsWith('`') && subPart.endsWith('`')) {
              return (
                <code key={subIdx} className="px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800/60 font-mono text-[10px] text-emerald-400 mx-0.5 select-text">
                  {subPart.slice(1, -1)}
                </code>
              );
            }
            return subPart;
          })}
        </span>
      );
    });
  };

  return (
    <div className="flex-1 w-full max-w-4xl h-[70vh] flex flex-col bg-zinc-950/40 backdrop-blur-md border border-zinc-900/60 rounded-3xl overflow-hidden shadow-2xl relative">
      {/* Welcome Dashboard when Empty */}
      {messages.length === 0 ? (
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          <DashboardWidgets onSendMessage={sendMessage} />
        </div>
      ) : (
        /* Messages History viewport */
        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex flex-col max-w-[85%] rounded-2xl p-4 text-xs select-text shadow-sm border",
                msg.role === 'user'
                  ? "ml-auto bg-emerald-500/10 border-emerald-500/20 text-zinc-200 rounded-tr-none"
                  : "mr-auto bg-zinc-900/35 border-zinc-800/40 text-zinc-300 rounded-tl-none"
              )}
            >
              {/* Message Meta Info */}
              <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-mono mb-1 font-semibold">
                {msg.role === 'user' ? 'BOSS' : 'JARVIS OS'}
              </span>

              {/* Message Content */}
              <div className="space-y-2">
                {msg.text ? (
                  formatText(msg.text)
                ) : (
                  msg.isStreaming && (
                    <span className="text-zinc-500 animate-pulse font-mono">Stream typing...</span>
                  )
                )}
              </div>

              {/* Attached Vision/Action Images */}
              {msg.images && msg.images.length > 0 && (
                <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-zinc-850">
                  {msg.images.map((img, i) => (
                    <img
                      key={i}
                      src={img}
                      alt="Context capture"
                      className="max-h-48 w-full object-cover rounded-lg border border-zinc-800"
                    />
                  ))}
                </div>
              )}

              {/* Background executing task cards */}
              {msg.backgroundTasks && msg.backgroundTasks.length > 0 && (
                <div className="space-y-1.5 mt-3 pt-3 border-t border-zinc-850">
                  {msg.backgroundTasks.map((t, idx) => (
                    <TaskCard
                      key={idx}
                      taskId={t.task_id}
                      type={t.type}
                      label={t.label}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
          {/* Scroll bottom helper */}
          <div ref={chatBottomRef} />
        </div>
      )}

      {/* Mic Status overlay banner */}
      {speechWidgetVisible && (
        <div className="absolute top-4 left-4 z-30 px-3 py-1.5 rounded-full bg-zinc-900/80 backdrop-blur border border-zinc-800/60 flex items-center gap-2 text-[10px] text-zinc-400 font-mono shadow-md animate-fade-in">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
          <span>{speechWidgetText}</span>
        </div>
      )}

      {/* Input bar footer wrapper */}
      <div className="p-4 border-t border-zinc-900 bg-zinc-950/70 backdrop-blur-md flex flex-col gap-2">
        <div className="flex gap-2">
          {/* Text Area Input */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Jarvis anything..."
            className="flex-1 bg-zinc-900/40 border border-zinc-900 hover:border-zinc-850 focus:border-zinc-800 rounded-xl px-4 py-3 text-xs outline-none text-zinc-200 placeholder:text-zinc-500 resize-none max-h-[140px] custom-scrollbar transition-all"
            disabled={isStreaming}
          />

          {/* Action circular buttons */}
          <div className="flex items-end gap-1.5 pb-1">
            {/* Cam Toggle Button */}
            {currentMode === 'jarvis' && (
              <button
                onClick={() => setCameraActive(!isCameraActive)}
                className={cn(
                  "p-2.5 rounded-xl border transition-all duration-200",
                  isCameraActive
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : "bg-zinc-900/30 text-zinc-500 border-zinc-900 hover:text-zinc-300 hover:border-zinc-800"
                )}
                title="Camera frame preview for vision"
                disabled={isStreaming}
              >
                <Camera size={15} />
              </button>
            )}

            {/* Microphone Auto-listen Toggle Button */}
            <button
              onClick={toggleAutoListen}
              className={cn(
                "p-2.5 rounded-xl border transition-all duration-200",
                autoListenMode
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-zinc-900/30 text-zinc-500 border-zinc-900 hover:text-zinc-300 hover:border-zinc-800",
                isListening && "animate-pulse"
              )}
              title={autoListenMode ? "Disable Speech Auto-listen" : "Enable Speech Auto-listen"}
              disabled={isStreaming}
            >
              {autoListenMode ? <Mic size={15} /> : <MicOff size={15} />}
            </button>

            {/* TTS Toggle Button */}
            <button
              onClick={toggleTts}
              className={cn(
                "p-2.5 rounded-xl border transition-all duration-200",
                ttsEnabled
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-zinc-900/30 text-zinc-500 border-zinc-900 hover:text-zinc-300 hover:border-zinc-800",
                ttsSpeaking && "animate-bounce"
              )}
              title={ttsEnabled ? "Disable text-to-speech voice" : "Enable text-to-speech voice"}
            >
              {ttsEnabled ? <Volume2 size={15} /> : <VolumeX size={15} />}
            </button>

            {/* Send Button */}
            <button
              onClick={() => sendMessage()}
              disabled={isStreaming || !inputVal.trim()}
              className={cn(
                "p-2.5 rounded-xl border transition-all duration-200",
                inputVal.trim() && !isStreaming
                  ? "bg-emerald-500 text-white border-emerald-400 hover:bg-emerald-400 shadow-md"
                  : "bg-zinc-900/30 text-zinc-600 border-zinc-900 cursor-not-allowed"
              )}
            >
              {isStreaming ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <Send size={15} />
              )}
            </button>
          </div>
        </div>

        {/* Char count / Meta */}
        <div className="flex justify-between items-center px-1 text-[9px] text-zinc-500 font-mono font-medium">
          <span>Mode: Unified Agentic Core</span>
          {inputVal.length > 50 && (
            <span>{inputVal.length.toLocaleString()} / 32,000</span>
          )}
        </div>
      </div>
    </div>
  );
};
