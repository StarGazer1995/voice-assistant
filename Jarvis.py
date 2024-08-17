import time
import subprocess

import pyaudio

from langchain.prompts import PromptTemplate
from langchain_community.llms import LlamaCpp
from langchain.callbacks.base import BaseCallbackManager

from webscan.explorer import Explorer, default_config
import logging
from params import *
from voice_handler import VoiceOutputCallbackHandler, record_audio
from executor import BasicExecutor

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

        self.mic = pyaudio.PyAudio()        
        for i in range(self.mic.get_device_count()):
            info = self.mic.get_device_info_by_index(i)
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
            callback_manager=callback_manager,
            stop=["<|im_end|>"],
            verbose=False,
            top_k=1,
            top_p=0.9
        )

        self.executer = BasicExecutor(promt_path=prompt_path, logger=logging.getLogger(), )
        self.dialogue = ""


    def process_voice(self) -> None:
        if self.voice_output_handler.tts_busy:
            return
        print("Listening...")
        record_audio()
        print("Transcribing...")
        time_ckpt = time.time()
        user_input = self.executer.process_voice()

        self.log.info("%s: %s (Time %d ms)" % ("Guest", user_input, (time.time() - time_ckpt) * 1000))
        # # TODO: do some de-noising tasks!!!@StarGazer1995
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
            self.dialogue += "*A* {}\n".format(reply)
            self.log.info("%s: %s (Time %d ms)" % ("Server", reply.strip(), (time.time() - time_ckpt) * 1000))
        return

class JarvisDebug(Jarvis):
    def process_voice(self) -> None:
        if self.voice_output_handler.tts_busy:
            return
        self.log.info("This is the debug version of Jarvis")
        print("Transcribing...")
        user_input = self.executer.process_voice_debug()
        self.dialogue += "*Q* {}\n".format(user_input)

        self.prompt = self.prompt_template.format(dialogue=self.dialogue)
        self.log.debug('------------ prompts --------------')
        self.log.debug(self.prompt)
        self.log.debug('--------------end of prompts ------------')
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

def jarvis_run_once():
    jarvis = JarvisDebug()
    jarvis.process_voice()
    jarvis.process_propmt()
    return 

if __name__ == '__main__':
    jarvis_run_once()
