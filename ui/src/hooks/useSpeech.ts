import { useEffect, useRef, useCallback } from 'react';
import { useJarvisStore } from '../store/jarvisStore';

const PRE_STARTER_FILES = Array.from({ length: 10 }, (_, i) => `starter_${i + 1}`);

class TTSPlayer {
  private queue: string[] = [];
  private playing = false;
  private stopped = false;
  private audio: HTMLAudioElement;
  private loopId = 0;
  public enabled = true;
  
  onPlaybackComplete?: () => void;
  onStateChange?: (isPlaying: boolean) => void;

  constructor() {
    this.audio = document.createElement('audio');
    this.audio.preload = 'auto';
  }

  unlock() {
    const silentWav = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
    this.audio.src = silentWav;
    const p = this.audio.play();
    if (p) p.catch(() => {});
    
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        const g = ctx.createGain();
        g.gain.value = 0;
        const o = ctx.createOscillator();
        o.connect(g);
        g.connect(ctx.destination);
        o.start(0);
        o.stop(ctx.currentTime + 0.001);
        setTimeout(() => ctx.close(), 200);
      }
    } catch (_) {}
  }

  enqueue(base64Audio: string) {
    if (this.stopped) return;
    this.queue.push(base64Audio);
    if (!this.playing) {
      this.playLoop();
    }
  }

  stop() {
    this.stopped = true;
    this.audio.pause();
    this.audio.removeAttribute('src');
    this.audio.load();
    this.queue = [];
    this.playing = false;
    this.onStateChange?.(false);
    this.onPlaybackComplete?.();
  }

  reset() {
    this.stop();
    this.stopped = false;
    this.loopId += 1;
  }

  private async playLoop() {
    if (this.playing) return;
    this.playing = true;
    this.loopId += 1;
    const currentLoopId = this.loopId;
    this.onStateChange?.(true);

    while (this.queue.length > 0) {
      if (this.stopped || currentLoopId !== this.loopId) break;
      const b64 = this.queue.shift();
      if (b64) {
        try {
          await this.playB64(b64);
        } catch (e) {
          console.warn('TTS segment error:', e);
        }
      }
    }

    if (currentLoopId !== this.loopId) {
      this.playing = false;
      return;
    }
    this.playing = false;
    this.onStateChange?.(false);
    this.onPlaybackComplete?.();
  }

  private playB64(b64: string): Promise<void> {
    return new Promise((resolve) => {
      this.audio.src = 'data:audio/mp3;base64,' + b64;
      const done = () => {
        resolve();
      };
      this.audio.onended = done;
      this.audio.onerror = done;
      const p = this.audio.play();
      if (p) p.catch(done);
    });
  }

  public isCurrentlyPlaying() {
    return this.playing;
  }
}

class PreStarterPlayer {
  private audio: HTMLAudioElement;
  private cache: Record<string, string> = {};

  constructor() {
    this.audio = document.createElement('audio');
    this.audio.preload = 'auto';
  }

  async preload() {
    for (const file of PRE_STARTER_FILES) {
      try {
        const r = await fetch(`/app/audio/${file}.mp3`);
        if (!r.ok) continue;
        const blob = await r.blob();
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve((reader.result as string || '').split(',')[1] || '');
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        if (base64) {
          this.cache[file] = base64;
        }
      } catch (_) {}
    }
  }

  play(onComplete?: () => void) {
    const loadedKeys = Object.keys(this.cache);
    if (loadedKeys.length === 0) {
      onComplete?.();
      return;
    }
    const file = loadedKeys[Math.floor(Math.random() * loadedKeys.length)];
    const base64 = this.cache[file];
    if (!base64) {
      onComplete?.();
      return;
    }
    this.audio.src = 'data:audio/mp3;base64,' + base64;
    this.audio.currentTime = 0;
    let fired = false;
    const done = () => {
      if (fired) return;
      fired = true;
      this.audio.onended = null;
      this.audio.onerror = null;
      onComplete?.();
    };
    this.audio.onended = done;
    this.audio.onerror = done;
    const p = this.audio.play();
    if (p) p.catch(done);
  }
}

// Singletons for players
const ttsPlayerInstance = new TTSPlayer();
const preStarterPlayerInstance = new PreStarterPlayer();

// Preload audio files as early as possible
if (typeof window !== 'undefined') {
  preStarterPlayerInstance.preload();
}

export function useSpeech(onTranscriptReceived?: (text: string) => void) {
  const {
    isListening,
    isSpeaking,
    ttsSpeaking,
    autoListenMode,
    settings,
    isStreaming,
    setIsListening,
    setIsSpeaking,
    setTtsSpeaking,
    setIsOrbActive,
    setAutoListenMode,
    setSpeechWidget,
    addActivity,
  } = useJarvisStore();

  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const vadRAFRef = useRef<number | null>(null);
  const silenceTimerRef = useRef<any>(null);
  const isSpeakingRef = useRef<boolean>(false);

  // Define restart function
  const maybeRestartListening = useCallback(() => {
    if (!useJarvisStore.getState().autoListenMode) return;
    if (useJarvisStore.getState().isStreaming) return;

    const ttsActive = ttsPlayerInstance.isCurrentlyPlaying() || ttsPlayerInstance['queue'].length > 0;
    if (ttsActive && !useJarvisStore.getState().settings.voiceInterrupt) return;

    const delay = ttsActive ? 150 : 700;
    setTimeout(() => {
      const state = useJarvisStore.getState();
      if (state.autoListenMode && !state.isStreaming && !state.isListening) {
        startListening();
      }
    }, delay);
  }, []);

  // Set callbacks on tts player
  useEffect(() => {
    ttsPlayerInstance.onStateChange = (isPlaying) => {
      setTtsSpeaking(isPlaying);
      setIsOrbActive(isPlaying || useJarvisStore.getState().isListening);
    };

    ttsPlayerInstance.onPlaybackComplete = () => {
      maybeRestartListening();
    };

    return () => {
      ttsPlayerInstance.onStateChange = undefined;
      ttsPlayerInstance.onPlaybackComplete = undefined;
    };
  }, [setTtsSpeaking, setIsOrbActive, maybeRestartListening]);

  const processSTT = async (blob: Blob) => {
    setSpeechWidget(true, 'Thinking...');
    addActivity('Processing Speech to Text...', 'thinking');

    const formData = new FormData();
    const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
    formData.append('file', blob, `audio.${mimeType === 'audio/webm' ? 'webm' : 'mp4'}`);

    try {
      const res = await fetch(`/stt`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.text && data.text.trim()) {
        const text = data.text.trim();
        addActivity(`Speech Transcribed: "${text}"`, 'execution');
        onTranscriptReceived?.(text);
      } else {
        setSpeechWidget(true, 'Could not hear clearly.');
        addActivity('Speech transcription completed with empty results.', 'status');
        setTimeout(() => {
          if (!useJarvisStore.getState().isListening) {
            setSpeechWidget(false);
          }
        }, 2000);
      }
    } catch (e: any) {
      console.error('STT Error:', e);
      setSpeechWidget(true, 'Audio processing error.');
      addActivity(`STT Processing failed: ${e.message}`, 'error');
      setTimeout(() => {
        if (!useJarvisStore.getState().isListening) {
          setSpeechWidget(false);
        }
      }, 2000);
    }
  };

  const monitorVAD = (analyser: AnalyserNode) => {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const checkSilence = () => {
      if (!useJarvisStore.getState().isListening) return;

      analyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
      const average = sum / dataArray.length;

      const VOLUME_THRESHOLD = 3; // very sensitive, matched to legacy script.js

      if (average > VOLUME_THRESHOLD) {
        if (!isSpeakingRef.current) {
          isSpeakingRef.current = true;
          setIsSpeaking(true);
          setSpeechWidget(true, 'Hearing you...');
          
          // Interrupt TTS if enabled
          if (useJarvisStore.getState().settings.voiceInterrupt && ttsPlayerInstance.isCurrentlyPlaying()) {
            ttsPlayerInstance.stop();
            addActivity('Speech interrupted playback', 'status');
          }
        }
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
      } else {
        if (isSpeakingRef.current && !silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            // Silence detected -> stop recording & send
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
              mediaRecorderRef.current.stop();
            }
            stopListeningInternal(true); // stop recording tracks
          }, 1200); // 1200ms of silence triggers capture, matching script.js
        }
      }
      vadRAFRef.current = requestAnimationFrame(checkSilence);
    };

    checkSilence();
  };

  const stopListeningInternal = (sendAudio = false) => {
    if (vadRAFRef.current) {
      cancelAnimationFrame(vadRAFRef.current);
      vadRAFRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      if (!sendAudio) {
        // Discard chunks by overriding handler
        mediaRecorderRef.current.onstop = null;
      }
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    setIsListening(false);
    isSpeakingRef.current = false;
    setIsSpeaking(false);
    setSpeechWidget(false);
    setIsOrbActive(ttsPlayerInstance.isCurrentlyPlaying());
  };

  const startListening = async () => {
    if (useJarvisStore.getState().isStreaming || useJarvisStore.getState().isListening) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;
      setIsListening(true);
      setIsOrbActive(true);
      setSpeechWidget(true, 'Listening...');
      addActivity('Microphone stream started. VAD active.', 'status');

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioContextClass();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      analyser.minDecibels = -60;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const hasChunks = audioChunksRef.current.length > 0;
        const wasSpeaking = isSpeakingRef.current;
        const chunks = audioChunksRef.current;
        audioChunksRef.current = [];
        
        isSpeakingRef.current = false;
        setIsSpeaking(false);

        if (hasChunks && wasSpeaking) {
          const audioBlob = new Blob(chunks, { type: mimeType });
          await processSTT(audioBlob);
        } else {
          maybeRestartListening();
        }
      };

      mediaRecorder.start(100);
      monitorVAD(analyser);
    } catch (err: any) {
      setIsListening(false);
      setSpeechWidget(false);
      setIsOrbActive(ttsPlayerInstance.isCurrentlyPlaying());
      addActivity(`Failed to start mic input: ${err.message}`, 'error');
      
      if (useJarvisStore.getState().autoListenMode) {
        setAutoListenMode(false);
      }
    }
  };

  const stopListening = () => {
    stopListeningInternal(false);
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const toggleAutoListen = () => {
    const newVal = !autoListenMode;
    setAutoListenMode(newVal);
    addActivity(`Auto-Listen mode set to ${newVal}`, 'status');
    if (newVal && !isListening && !isStreaming) {
      startListening();
    } else if (!newVal && isListening) {
      stopListening();
    }
  };

  const playThinkingSound = () => {
    if (settings.thinkingSounds) {
      preStarterPlayerInstance.play();
    }
  };

  const unlockAudioContext = () => {
    ttsPlayerInstance.unlock();
  };

  return {
    isListening,
    isSpeaking,
    ttsSpeaking,
    autoListenMode,
    ttsPlayer: ttsPlayerInstance,
    startListening,
    stopListening,
    toggleListening,
    toggleAutoListen,
    playThinkingSound,
    unlockAudioContext,
  };
}
