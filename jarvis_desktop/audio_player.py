"""
jarvis_desktop/audio_player.py — In-Memory Persistent Audio Player Queue

Keeps sounddevice OutputStream initialized once at startup.
Streams incoming PCM/MP3 audio bytes directly from memory without writing temporary files to disk.
Supports instant stop() for full-duplex barge-in interruption.
"""

import io
import queue
import threading
import logging
import time
from typing import Optional

logger = logging.getLogger("JARVIS.AudioPlayer")

class PersistentAudioPlayer:
    """
    In-memory persistent audio stream player.
    """
    
    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.stop_requested = False
        self.stream = None
        self.playing = False
        self._lock = threading.Lock()

    def start(self):
        """Initialize sounddevice output stream."""
        try:
            import sounddevice as sd
            self.stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=1024,
                callback=self._stream_callback
            )
            self.stream.start()
            self.playing = True
            logger.info("[AUDIO-PLAYER] OutputStream initialized (%dHz, %dch)", self.sample_rate, self.channels)
        except Exception as e:
            logger.warning("[AUDIO-PLAYER] sounddevice OutputStream init failed: %s (will use PyGame memory fallback)", e)

    def _stream_callback(self, outdata, frames, time_info, status):
        """Callback to feed sounddevice output buffer directly from in-memory queue."""
        bytes_needed = len(outdata)
        out_buf = bytearray()
        
        while len(out_buf) < bytes_needed and not self.stop_requested:
            try:
                chunk = self.audio_queue.get_nowait()
                out_buf.extend(chunk)
            except queue.Empty:
                break

        if self.stop_requested:
            out_buf.clear()
            self.audio_queue = queue.Queue()
            self.stop_requested = False

        if len(out_buf) < bytes_needed:
            # Pad with silence
            out_buf.extend(b'\x00' * (bytes_needed - len(out_buf)))
            
        outdata[:] = bytes(out_buf[:bytes_needed])

    def play_bytes(self, pcm_data: bytes):
        """Enqueue PCM bytes into memory playback queue."""
        if not pcm_data:
            return
        self.stop_requested = False
        self.audio_queue.put(pcm_data)

    def stop(self):
        """Instant stop / clear queue for barge-in interruption."""
        with self._lock:
            self.stop_requested = True
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
        logger.info("[AUDIO-PLAYER] Playback interrupted and cleared.")

    def close(self):
        """Close output stream."""
        self.stop()
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
