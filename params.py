import pyaudio

LANG = "EN" # CN for Chinese, EN for English
DEBUG = True

# Model Configuration
WHISP_PATH = "models/whisper-large-v3"
# MODEL_PATH = "models/Yi-1.5-6B-Chat-GGUF/Yi-1.5-6B-Chat.q5_k.gguf" # Or models/yi-chat-6b.Q8_0.gguf
MODEL_PATH = "models/llama2/llama2-13b-chat-INT4.bin"
# Recording Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500
SILENT_CHUNKS = 2 * RATE / CHUNK  # two seconds of silence marks the end of user voice input
MIC_IDX = 0 # Set microphone id. Use tools/list_microphones.py to see a device list.
VOICE_PATH = "recordings/output.wav"
