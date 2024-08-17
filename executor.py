from langchain.prompts import PromptTemplate
from webscan.explorer import Explorer, default_config
from params import *
import logging
import whisper

class BasicExecutor:
    def __init__(self, promt_path, logger=None, debug_mode=False) -> None:

        if logger is None:
            FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
            DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
            self.log = logging.getLogger()
            logging.basicConfig(format=FORMAT, encoding="utf-8", level=logging.INFO, datefmt=DATE_FORMAT)
        else:
            self.log = logger

        if DEBUG:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)
        self.explorer = Explorer(logger=logger, debug=debug_mode)
    

    def process_voice(self) -> PromptTemplate:
        user_input = whisper.transcribe(VOICE_PATH, path_or_hf_repo=WHISP_PATH)["text"]
        if "新鲜事" in user_input or "新的事" in user_input:
            user_input = self.explorer.access_page(default_config)
            user_input = "\t".join(user_input)
            user_input = "请帮我总结一下面的消息：\n" + user_input
        return user_input
    
    def process_voice_debug(self) -> PromptTemplate:
        user_input = "Generate a cpp project that prints 'Hello World' in the screen. Also, tell me how to compile the project on a Mac"
        return user_input
