import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import logging
from rich.logging import RichHandler

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RichHandler()]
)

genai.configure(api_key='AIzaSyAt5lkU9AVAeN6R0B12sNKLKIjKU26_QHE')

class gemini_ai:
    def __init__(self, prompt: str = "使用繁體中文進行回覆", temperature: float = 1, top_p: float = 0.95, top_k: float = 40, max_output_tokens: int = 8192, response_mime_type: str = "text/plain", model_name: str = 'gemini-1.5-flash'):
        
        self.generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": response_mime_type,
        }

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            system_instruction=prompt
        )

        self.history = []

        self.chat_session = self.model.start_chat(
            history=self.history
        )
        logging.info(f'已初始化 Gemini AI，使用模型：{model_name}')

    def chat(self, text: str):
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
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
                logging.info(f'成功生成回應')
                return response.text
                
            except ResourceExhausted as e:
                logging.error(f"API 配額已用完: {e}")
                return "抱歉，API 配額已用完，請稍後再試。"
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"嘗試 {attempt + 1}/{max_retries} 失敗: {e}")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    logging.error(f"在調用 Gemini API 時發生錯誤: {e}")
                    return "抱歉，我現在遇到了一些技術問題，請稍後再試。"
    
    def get_history(self):
        for history in self.history:
            logging.info(f"歷史記錄: {history['parts'][0]}")
