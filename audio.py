# audio.py
import os
import queue
import threading
import sounddevice as sd
import soundfile as sf

import numpy as np

class AudioRecorder:
    def __init__(self, filename="temp_recording.wav", samplerate=16000, channels=1):
        self.filename = filename
        self.samplerate = samplerate
        self.channels = channels
        self.q = queue.Queue()
        self.recording = False
        self.current_volume = 0.0
        self.stream = None
        self.writer_thread = None
        self.lock = threading.Lock()
        
        # Start background stream and keep mic open in standby for instant capture
        self._init_stream()

    def _init_stream(self):
        """Initialize continuous InputStream in standby mode for instant recording."""
        try:
            if self.stream is not None:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
            self.stream = sd.InputStream(
                samplerate=self.samplerate, 
                channels=self.channels, 
                callback=self._callback
            )
            self.stream.start()
            print("Audio input stream initialized in standby mode.")
        except Exception as e:
            print(f"Error initializing audio stream: {e}")

    def _callback(self, indata, frames, time_info, status):
        """Called for each audio block by sounddevice (runs on audio driver thread)."""
        if status:
            print(f"SoundDevice status warning: {status}")
            
        if indata.size > 0:
            self.current_volume = float(np.max(np.abs(indata)))
            if self.recording:
                self.q.put(indata.copy())
        else:
            self.current_volume = 0.0

    def get_volume(self):
        """Return the current peak audio level (0.0 to 1.0)."""
        return self.current_volume if self.recording else 0.0

    def start(self):
        """Start audio recording immediately (0ms latency, standby stream)."""
        with self.lock:
            if self.recording:
                return False
                
            if self.stream is None or not self.stream.active:
                print("Re-initializing audio stream...")
                self._init_stream()
                
            dirname = os.path.dirname(self.filename)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)
                
            # Drain any stale frames
            while not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break
                    
            self.recording = True
            self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
            self.writer_thread.start()
            return True

    def _write_loop(self):
        """Background thread that writes audio frames from queue to WAV file."""
        try:
            with sf.SoundFile(self.filename, mode='w', samplerate=self.samplerate, channels=self.channels) as file:
                while self.recording or not self.q.empty():
                    try:
                        data = self.q.get(timeout=0.05)
                        file.write(data)
                    except queue.Empty:
                        continue
        except Exception as e:
            print(f"Error writing audio file: {e}")
            self.recording = False

    def stop(self):
        """Stop audio recording and return the saved WAV file path."""
        with self.lock:
            if not self.recording:
                return None
                
            self.recording = False
            if self.writer_thread and self.writer_thread.is_alive():
                self.writer_thread.join(timeout=2.0)
            self.writer_thread = None
            
        if os.path.exists(self.filename) and os.path.getsize(self.filename) > 44:
            return self.filename
        return None

    def close(self):
        """Close audio stream when exiting app."""
        self.recording = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

