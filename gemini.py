import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import logging
import os
from rich.logging import RichHandler
import atexit

# 設置環境變數以抑制 gRPC 警告
os.environ['GRPC_PYTHON_LOG_LEVEL'] = '0'
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RichHandler()]
)

# API keys list
API_KEYS = [
    'AIzaSyAt5lkU9AVAeN6R0B12sNKLKIjKU26_QHE',
    'AIzaSyBDRyKIvpsXKYVyc1DlXv7OQK3zSDNoNTQ',
    'AIzaSyCv_CLB_OITWQkHywYUV4TdXOsRMa--q9A'
]

def cleanup_genai():
    """清理 Gemini AI 的全局資源"""
    try:
        if hasattr(genai, '_client'):
            if hasattr(genai._client, '_channel'):
                genai._client._channel.close()
            genai._client = None
    except Exception as e:
        logging.error(f"清理 Gemini AI 全局資源時發生錯誤: {e}")

# 註冊程序退出時的清理函數
atexit.register(cleanup_genai)

class gemini_ai:
    def __init__(self, prompt: str = "使用繁體中文進行回覆", temperature: float = 1, top_p: float = 0.95, top_k: float = 40, max_output_tokens: int = 8192, response_mime_type: str = "text/plain", model_name: str = 'gemini-1.5-flash'):
        self.current_api_key_index = 0
        self._initialize_with_current_key()
        
        self.generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": response_mime_type,
        }

        self.model = self._create_model(model_name, prompt)
        self.history = []
        self.chat_session = self.model.start_chat(history=self.history)
        logging.info(f'已初始化 Gemini AI，使用模型：{model_name}')

    def _initialize_with_current_key(self):
        genai.configure(api_key=API_KEYS[self.current_api_key_index])
        logging.info(f'使用 API Key {self.current_api_key_index + 1}')

    def _rotate_api_key(self):
        self.current_api_key_index = (self.current_api_key_index + 1) % len(API_KEYS)
        self._initialize_with_current_key()

    def _create_model(self, model_name, prompt):
        return genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            system_instruction=prompt
        )

    def chat(self, text: str):
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries * len(API_KEYS)):
            try:
                response = self.chat_session.send_message(text)
                self.history.append(
                    {
                        'role':'user',
                        'parts':[text],
                    }                
                )
                self.history.append(
                    {
                        'role':'model',
                        'parts':[response.text]
                    }
                )
                return response.text
                
            except ResourceExhausted as e:
                logging.error(f"API 配額已用完: {e}")
                self._rotate_api_key()
                
            except Exception as e:
                if attempt < max_retries * len(API_KEYS) - 1:
                    logging.warning(f"嘗試 {attempt + 1}/{max_retries * len(API_KEYS)} 失敗: {e}")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    logging.error(f"在調用 Gemini API 時發生錯誤: {e}")
                    return "抱歉，我現在遇到了一些技術問題，請稍後再試。"
    
    def get_history(self):
        for history in self.history:
            logging.info(f"歷史記錄: {history['parts'][0]}")

    def cleanup(self):
        """清理資源並關閉連接"""
        try:
            if hasattr(self, 'chat_session'):
                self.chat_session = None
            if hasattr(self, 'model'):
                self.model = None
        except Exception as e:
            logging.error(f"清理 Gemini 資源時發生錯誤: {e}")
