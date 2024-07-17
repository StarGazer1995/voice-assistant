from llama_cpp import llama_model_quantize, GGML_TYPE_Q4_0

def main():
    res=llama_model_quantize("/Users/gongzhao/workspace/garage_toys/applications/voice_assistant/models/Qwen-14B/qwen-14b-f16.gguf",
                              "/Users/gongzhao/workspace/garage_toys/applications/voice_assistant/models/Qwen-14B/qwen-14b-int4.bin",
                                GGML_TYPE_Q4_0)
    if res == 0:
        print("quantize successes")
    else:
        print("process fail")

if __name__ == "__main__":
    main()