# sound_fx.py
import os
import wave
import winsound
import numpy as np

class SoundFX:
    """
    Generates and plays modern, crisp, non-blocking UI audio feedback sounds.
    Uses Win32 PlaySound with SND_ASYNC to guarantee 100% audible, zero-lag sound playback.
    """
    def __init__(self, sounds_dir):
        self.sounds_dir = sounds_dir
        self.sound_paths = {}
        self._generate_sounds()

    def _generate_sounds(self):
        os.makedirs(self.sounds_dir, exist_ok=True)
        sample_rate = 44100

        def save_wav(filename, samples):
            path = os.path.join(self.sounds_dir, filename)
            max_val = np.max(np.abs(samples))
            if max_val > 0:
                samples = samples / max_val * 0.75
            int_samples = (samples * 32767).astype(np.int16)
            with wave.open(path, 'wb') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                f.writeframes(int_samples.tobytes())
            return path

        # 1. Start Sound (Crisp high tap-click sweep: 1500Hz -> 800Hz over 28ms)
        t = np.linspace(0, 0.028, int(sample_rate * 0.028))
        freq = np.linspace(1500, 800, len(t))
        env = np.exp(-t * 120)
        start_samples = np.sin(2 * np.pi * freq * t) * env
        self.sound_paths["start"] = save_wav("start.wav", start_samples)

        # 2. Stop Sound (Crisp low tap-click sweep: 900Hz -> 450Hz over 28ms)
        t = np.linspace(0, 0.028, int(sample_rate * 0.028))
        freq = np.linspace(900, 450, len(t))
        env = np.exp(-t * 120)
        stop_samples = np.sin(2 * np.pi * freq * t) * env
        self.sound_paths["stop"] = save_wav("stop.wav", stop_samples)

        # 3. Success Sound (Harmonic double tick: 1200Hz then 1800Hz)
        t1 = np.linspace(0, 0.02, int(sample_rate * 0.02))
        env1 = np.exp(-t1 * 150)
        s1 = np.sin(2 * np.pi * 1200 * t1) * env1
        t2 = np.linspace(0, 0.025, int(sample_rate * 0.025))
        env2 = np.exp(-t2 * 120)
        s2 = np.sin(2 * np.pi * 1800 * t2) * env2
        silence = np.zeros(int(sample_rate * 0.03))
        success_samples = np.concatenate([s1, silence, s2])
        self.sound_paths["success"] = save_wav("success.wav", success_samples)

        # 4. Error Sound (Soft low bump: 220Hz over 100ms)
        t = np.linspace(0, 0.10, int(sample_rate * 0.10))
        env = np.exp(-t * 30)
        error_samples = np.sin(2 * np.pi * 220 * t) * env
        self.sound_paths["error"] = save_wav("error.wav", error_samples)

    def play(self, sound_name):
        path = self.sound_paths.get(sound_name)
        if path and os.path.exists(path):
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Sound play error: {e}")
