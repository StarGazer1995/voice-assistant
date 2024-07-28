import time
import wave
import queue
import struct
import threading
import subprocess

import pyaudio
import whisper

from langchain.prompts import PromptTemplate
from langchain_community.llms import LlamaCpp
from langchain.callbacks.base import BaseCallbackHandler, BaseCallbackManager

from webscan.explorer import Explorer, default_config
import logging

LANG = "CN" # CN for Chinese, EN for English
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

def compute_rms(data):
    # Assuming data is in 16-bit samples
    format = "<{}h".format(len(data) // 2)
    ints = struct.unpack(format, data)

    # Calculate RMS
    sum_squares = sum(i ** 2 for i in ints)
    rms = (sum_squares / len(ints)) ** 0.5
    return rms

def record_audio():
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, input_device_index=MIC_IDX, frames_per_buffer=CHUNK)

    silent_chunks = 0
    audio_started = False
    frames = []

    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        rms = compute_rms(data)
        if audio_started:
            if rms < SILENCE_THRESHOLD:
                silent_chunks += 1
                if silent_chunks > SILENT_CHUNKS:
                    break
            else:
                silent_chunks = 0
        elif rms >= SILENCE_THRESHOLD:
            audio_started = True

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # save audio to a WAV file
    with wave.open('recordings/output.wav', 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

class VoiceOutputCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.generated_text = ""
        self.lock = threading.Lock()
        self.speech_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        self.tts_busy = False

    def on_llm_new_token(self, token, **kwargs):
        # Append the token to the generated text
        with self.lock:
            self.generated_text += token

        # Check if the token is the end of a sentence
        if token in ['.', '。', '!', '！', '?', '？']:
            with self.lock:
                # Put the complete sentence in the queue
                self.speech_queue.put(self.generated_text)
                self.generated_text = ""

    def process_queue(self):
        while True:
            # Wait for the next sentence
            text = self.speech_queue.get()
            print("queue: {}".format(text), self.speech_queue.qsize())
            if text is None:
                self.tts_busy = False
                continue
            self.tts_busy = True
            # self.text_to_speech(text)
            self.speech_queue.task_done()
            if self.speech_queue.empty():
                self.tts_busy = False
                print('--------- end of queue-----------')

    def text_to_speech(self, text):
        try:
            if LANG == "CN":
                subprocess.call(["say", "-r", "200", "-v", "TingTing", text])
            else:
                subprocess.call(["say", "-r", "180", "-v", "Karen", text])
        except Exception as e:
            print(f"Error in text-to-speech: {e}")

class Jarvis:
    def __init__(self) -> None:

        FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
        DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
        self.log = logging.getLogger()
        logging.basicConfig(format=FORMAT, encoding="utf-8", level=logging.INFO, datefmt=DATE_FORMAT)
        if DEBUG:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)


        if LANG == "CN":
            prompt_path = "prompts/example-cn.txt"
        else:
            prompt_path = "prompts/example-en.txt"
        with open(prompt_path, 'r', encoding='utf-8') as file:
            template = file.read().strip() # {dialogue}
        self.prompt_template = PromptTemplate(template=template, input_variables=["dialogue"])
        self.explorer = Explorer(logger=self.log)
        self.mic = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            self.log.info(f"Device {i}: {info['name']} (input channels: {info['maxInputChannels']}, output channels: {info['maxOutputChannels']})")

        self.voice_output_handler = VoiceOutputCallbackHandler()

        # Create a callback manager with the voice output handler
        callback_manager = BaseCallbackManager(handlers=[self.voice_output_handler])

        self.llm = LlamaCpp(
            model_path=MODEL_PATH,
            n_gpu_layers=1, # Metal set to 1 is enough.
            n_batch=512,    # Should be between 1 and n_ctx, consider the amount of RAM of your Apple Silicon Chip.
            n_ctx=4096,     # Update the context window size to 4096
            f16_kv=True,    # MUST set to True, otherwise you will run into problem after a couple of calls
            # callback_manager=callback_manager,
            stop=["<|im_end|>"],
            verbose=False,
            top_k=1,
            top_p=0.9
        )
        self.dialogue = ""


    def process_voice(self) -> None:
        if self.voice_output_handler.tts_busy:
            return
        print("Listening...")
        record_audio()
        print("Transcribing...")
        time_ckpt = time.time()
        user_input = whisper.transcribe("recordings/output.wav", path_or_hf_repo=WHISP_PATH)["text"]
        if "新鲜事" in user_input or "新的事" in user_input:
            user_input = self.explorer.access_page(default_config)
            user_input = "\t".join(user_input)
            user_input = "请帮我总结一下面的消息：\n" + user_input

        self.log.info("%s: %s (Time %d ms)" % ("Guest", user_input, (time.time() - time_ckpt) * 1000))
        # TODO: do some de-noising tasks!!!@StarGazer1995
        self.log.info("Generating...")
        self.dialogue += "*Q* {}\n".format(user_input)

        self.prompt = self.prompt_template.format(dialogue=self.dialogue)
        self.log.debug('------------ prompts --------------')
        self.log.debug(self.prompt)
        self.log.debug('--------------end of prompts ------------')
        return

    def process_propmt(self) -> None:

        reply = self.llm(self.prompt, max_tokens=4096)
        self.log.info('-------reply------------')
        self.log.info(reply)
        self.log.info('-------- end of reply ----------')
        time_ckpt = time.time()
        if reply is not None:
            self.voice_output_handler.speech_queue.put(None)
            dialogue += "*A* {}\n".format(reply)
            self.log.info("%s: %s (Time %d ms)" % ("Server", reply.strip(), (time.time() - time_ckpt) * 1000))
        return

def jarvis():
    jarvis = Jarvis()
    try:
        while True:
            if jarvis.voice_output_handler.tts_busy:
                continue
            try:
                jarvis.process_voice()
                jarvis.process_propmt()
            except subprocess.CalledProcessError:
                print("voice recognition failed, please try again")
                continue

    except KeyboardInterrupt:
        pass
    

def main():
    if LANG == "CN":
        prompt_path = "prompts/example-cn.txt"
    else:
        prompt_path = "prompts/example-en.txt"
    with open(prompt_path, 'r', encoding='utf-8') as file:
        template = file.read().strip() # {dialogue}
    prompt_template = PromptTemplate(template=template, input_variables=["dialogue"])
    explorer = Explorer(debug=DEBUG)

    p = pyaudio.PyAudio()

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Device {i}: {info['name']} (input channels: {info['maxInputChannels']}, output channels: {info['maxOutputChannels']})")

    # Create an instance of the VoiceOutputCallbackHandler
    voice_output_handler = VoiceOutputCallbackHandler()

    # Create a callback manager with the voice output handler
    callback_manager = BaseCallbackManager(handlers=[voice_output_handler])

    llm = LlamaCpp(
        model_path=MODEL_PATH,
        n_gpu_layers=1, # Metal set to 1 is enough.
        n_batch=512,    # Should be between 1 and n_ctx, consider the amount of RAM of your Apple Silicon Chip.
        n_ctx=4096,     # Update the context window size to 4096
        f16_kv=True,    # MUST set to True, otherwise you will run into problem after a couple of calls
        # callback_manager=callback_manager,
        stop=["<|im_end|>"],
        verbose=False,
        top_k=1,
        top_p=0.9
    )
    dialogue = ""
    try:
        while True:
            if voice_output_handler.tts_busy:  # Check if TTS is busy
                continue  # Skip to the next iteration if TTS is busy 
            try:
                print("Listening...")
                record_audio()
                print("Transcribing...")
                time_ckpt = time.time()
                user_input = whisper.transcribe("recordings/output.wav", path_or_hf_repo=WHISP_PATH)["text"]
                if "新鲜事" in user_input or "新的事" in user_input:
                    user_input = explorer.access_page(default_config)
                    user_input = "\t".join(user_input)
                    user_input = "请帮我总结一下面的消息：\n" + user_input

                print("%s: %s (Time %d ms)" % ("Guest", user_input, (time.time() - time_ckpt) * 1000))

                time_ckpt = time.time()
                # TODO: do some de-noising tasks!!!@StarGazer1995
                print("Generating...")
                dialogue += "*Q* {}\n".format(user_input)

                prompt = prompt_template.format(dialogue=dialogue)
                print('------------ prompts --------------')
                print(prompt)
                print('--------------end of prompts ------------')
                reply = llm(prompt, max_tokens=4096)
                print('-------reply------------')
                print(reply)
                print('-------- end of reply ----------')
                if reply is not None:
                    voice_output_handler.speech_queue.put(None)
                    dialogue += "*A* {}\n".format(reply)
                    print("%s: %s (Time %d ms)" % ("Server", reply.strip(), (time.time() - time_ckpt) * 1000))
            
            except subprocess.CalledProcessError:
                print("voice recognition failed, please try again")
                continue

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()