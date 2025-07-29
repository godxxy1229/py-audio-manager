# py-audio-manager
This module manages audio sound effects in Python projects. It supports playing sound effects and providing audio data with low latency. It also prevents audio playback from interrupting during heavy workloads.

## Usage

### 1. Play Sound Effects
```python
from audio_manager import play_sound

# Basic usage
play_sound('AP_Engage')      # Start sound effect
play_sound('AP_Disengage')   # End sound effect
play_sound('NoA_Engage')     # Notification sound effect
play_sound('chime_single')   # Chime sound effect
```

### 2. Get Data for Speech Synthesis
```python
from audio_manager import get_audio_data

# Used in prepare_audio_for_recording
audio_data = get_audio_data('rec_start_voice')
if audio_data:
    # audio_data['data']: numpy array
    # audio_data['fs']: sampling rate
    process_audio(audio_data['data'], audio_data['fs'])
```

### 3. Advanced Usage
```python
from audio_manager import get_audio_manager

# Access AudioManager instance directly
mgr = get_audio_manager()

# Check available sound list
available_sounds = mgr.get_available_sounds()
print(available_sounds)  # ['AP_Engage', 'AP_Disengage', ...]

# Add a new sound
mgr.add_sound('custom_sound', 'path/to/custom.mp3')

# Stop all playing sounds
mgr.stop_all_sounds()
