from ..chatgpt import get_chatgpt_client
from ..gpt3 import get_gpt3_client

FUNC_MAP = {
    "text-davinci-002-render": get_chatgpt_client,
    "text-davinci-003": get_gpt3_client,
    "default": get_chatgpt_client,
}

def get_chat_client(model_name: str):
    if model_name in FUNC_MAP:
        return FUNC_MAP[model_name]()
    else:
        return FUNC_MAP["default"]()

