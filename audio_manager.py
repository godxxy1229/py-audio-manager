 """
Audio Sound Effects Management Module
Reusable audio system for other modules
"""

import os
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import logging
from pathlib import Path


class AudioManager:
    """Audio sound effects management class"""
    
    def __init__(self, sounds_dir="src/sounds"):
        self.sounds_dir = sounds_dir
        self.audio_cache = {}
        self._initialized = False
        
        # Default audio file mapping
        self.default_sounds = {
            'AP_Engage': 'AP_Engage.mp3',
            'AP_Disengage': 'AP_Disengage.mp3',
            'NoA_Engage': 'NoA_Engage.mp3',
            'rec_start_voice': 'rec_start_voice.mp3',
            'rec_stop_voice': 'rec_stop_voice.mp3',
            'chime_single': 'chime_single.mp3',
            'chime_hi_lo': 'chime_hi_lo.mp3'
        }
        
        self.initialize()
    
    def initialize(self):
        """Initialize audio system"""
        if self._initialized:
            return
            
        try:
            # Set optimal latency (balance between performance and stability)
            sd.default.latency = 'low'
            # Larger buffer for CPU-intensive environments (prioritize no dropouts)
            sd.default.blocksize = 2048
            # Optimize audio stream settings
            sd.default.dtype = 'float32'  # consistent data type
            # More flexible latency settings for reliability
            sd.default.latency = ['low', 'high']  # try low latency, fallback to high latency
            
            # Preload audio files
            self._preload_audio_files()
            
            # Warm up sounddevice stream (reduce first-play latency)
            self._warmup_audio_stream()
            
            self._initialized = True
            print("Audio system initialization complete")
            
        except Exception as e:
            logging.error(f"Error during audio system initialization: {e}")
            print(f"Error during audio system initialization: {e}")
    
    def _warmup_audio_stream(self):
        """Warm up the audio stream to eliminate first-play latency"""
        try:
            # Play a very short silence to initialize the stream
            silence = np.zeros((100,), dtype=np.float32)  # 100-sample silence
            sd.play(silence, 22050, blocksize=2048)
            sd.wait()  # wait until done
            print("Audio stream warm-up complete")
        except Exception as e:
            logging.warning(f"Audio stream warm-up failed: {e}")
    
    def _get_resource_path(self, relative_path):
        """Return resource file path (compatible with PyInstaller)"""
        try:
            # When built with PyInstaller
            import sys
            base_path = sys._MEIPASS
        except Exception:
            # Development environment
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    def _preload_audio_files(self):
        """Preload audio files into memory"""
        try:
            # Load default sound files
            for sound_key, filename in self.default_sounds.items():
                file_path = os.path.join(self.sounds_dir, filename)
                resolved_path = self._get_resource_path(file_path)
                
                if os.path.exists(resolved_path):
                    data, fs = sf.read(resolved_path)
                    # Convert mono to stereo
                    if len(data.shape) == 1:
                        data = np.column_stack((data, data))
                    
                    self.audio_cache[sound_key] = {
                        'data': data,
                        'fs': fs
                    }
                else:
                    logging.warning(f"Audio file not found: {resolved_path}")
            
            print(f"Loaded {len(self.audio_cache)} audio files")
            
        except Exception as e:
            logging.error(f"Error loading audio files: {e}")
            print(f"Error loading audio files: {e}")
    
    def add_sound(self, sound_key, file_path):
        """Add a new sound file"""
        try:
            resolved_path = self._get_resource_path(file_path)
            if not os.path.exists(resolved_path):
                logging.error(f"Audio file not found: {resolved_path}")
                return False
                
            data, fs = sf.read(resolved_path)
            
            # Convert mono to stereo
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            
            self.audio_cache[sound_key] = {
                'data': data,
                'fs': fs
            }
            
            logging.info(f"Sound added: {sound_key}")
            return True
            
        except Exception as e:
            logging.error(f"Error adding sound ({sound_key}): {e}")
            return False
    
    def play_sound(self, sound_key):
        """Play sound (non-blocking asynchronous playback)"""
        if sound_key not in self.audio_cache:
            logging.warning(f"Sound key not found: {sound_key}")
            return False
        
        def _play_thread():
            try:
                # Set Windows thread priority for stable playback under CPU load
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetThreadPriority(
                        ctypes.windll.kernel32.GetCurrentThread(), 2  # THREAD_PRIORITY_ABOVE_NORMAL
                    )
                except Exception as e:
                    logging.debug(f"Failed to set Windows thread priority (ignored): {e}")
                
                audio = self.audio_cache[sound_key]
                # Use larger blocksize to prevent dropouts
                sd.play(audio['data'], audio['fs'], blocksize=2048)
            
            except Exception as e:
                logging.error(f"Error playing audio ({sound_key}): {e}")
        
        # Run playback in a high-priority daemon thread
        thread = threading.Thread(
            target=_play_thread, 
            daemon=True, 
            name=f"AudioPlay_{sound_key}"
        )
        thread.start()
        return True
    
    def get_audio_data(self, sound_key):
        """Return audio data for voice synthesis"""
        if sound_key in self.audio_cache:
            return self.audio_cache[sound_key]
        else:
            logging.warning(f"Sound key not found: {sound_key}")
            return None
    
    def get_available_sounds(self):
        """Return list of available sound keys"""
        return list(self.audio_cache.keys())
    
    def stop_all_sounds(self):
        """Stop all sound playback"""
        try:
            sd.stop()
        except Exception as e:
            logging.error(f"Error stopping audio: {e}")

# Global instance (eager initialization for performance)
_audio_manager_instance = AudioManager()

def get_audio_manager():
    """Return the singleton AudioManager instance"""
    return _audio_manager_instance

def play_sound(sound_key):
    """Convenience function to play sound"""
    return get_audio_manager().play_sound(sound_key)

def get_audio_data(sound_key):
    """Convenience function to get audio data"""
    return get_audio_manager().get_audio_data(sound_key)
