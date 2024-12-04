import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import logging
import os
from rich.logging import RichHandler
from dotenv import load_dotenv
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

# 載入環境變數
load_dotenv()
API_KEYS = [
    os.getenv('GEMINI_API_KEY_1'),
    os.getenv('GEMINI_API_KEY_2'),
    os.getenv('GEMINI_API_KEY_3')
]

# 過濾掉無效的 API keys
API_KEYS = [key for key in API_KEYS if key is not None]

if not API_KEYS:
    raise ValueError("沒有找到有效的 Gemini API Keys，請檢查環境變數設置")

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
        """初始化 Gemini API"""
        try:
            if self.current_api_key_index >= len(API_KEYS):
                raise ValueError("所有 API Keys 都已用盡")
            
            current_key = API_KEYS[self.current_api_key_index]
            if not current_key:
                raise ValueError(f"API Key {self.current_api_key_index + 1} 無效")
            
            genai.configure(api_key=current_key)
            logging.info(f'使用 API Key {self.current_api_key_index + 1}')
        except Exception as e:
            logging.error(f"初始化 Gemini API 時發生錯誤: {e}")
            raise

    def _rotate_api_key(self):
        self.current_api_key_index = (self.current_api_key_index + 1) % len(API_KEYS)
        self._initialize_with_current_key()

    def _create_model(self, model_name, prompt):
        return genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            system_instruction=prompt
        )

    def get_history(self):
        """獲取歷史記錄並計算總 token 數量"""
        total_tokens = 0
        for entry in self.history:
            if not entry or 'parts' not in entry or not entry['parts']:
                logging.warning("發現無效的歷史記錄項目")
                continue
                
            content = entry['parts'][0]
            if not content:
                logging.warning("發現空的歷史記錄內容")
                continue
                
            logging.info(f"歷史記錄: {content}")
            try:
                tokens = self.model.count_tokens(content).total_tokens
                total_tokens += tokens
            except Exception as e:
                logging.error(f"計算 token 時發生錯誤: {e}")
                
        logging.info(f"歷史記錄總 token 數量: {total_tokens}")
        return total_tokens

    def chat(self, text: str):
        if not text or not isinstance(text, str):
            logging.error("無效的輸入文本")
            return "抱歉，我無法處理空白或無效的輸入。"
            
        max_retries = 9
        retry_sets = 2  # 嘗試兩組，每組9次
        retry_delay = 2  # 每次重試間隔2秒
        set_delay = 5   # 每組重試間隔5秒
        
        for set_attempt in range(retry_sets):
            for attempt in range(max_retries):
                try:
                    # 計算輸入文本的 token 數量
                    input_token_count = self.model.count_tokens(text).total_tokens
                    logging.info(f"輸入文本的 token 數量: {input_token_count}")
                    
                    response = self.chat_session.send_message(text)
                    if not response or not response.text:
                        raise ValueError("收到空的回應")
                    
                    # 計算回應文本的 token 數量
                    output_token_count = self.model.count_tokens(response.text).total_tokens
                    logging.info(f"回應文本的 token 數量: {output_token_count}")
                    logging.info(f"本次對話總 token 數量: {input_token_count + output_token_count}")
                    
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
                    current_attempt = set_attempt * max_retries + attempt + 1
                    total_attempts = max_retries * retry_sets
                    
                    if current_attempt < total_attempts:
                        logging.warning(f"嘗試 {current_attempt}/{total_attempts} 失敗: {e}")
                        import time
                        
                        # 如果完成一組9次嘗試，等待5秒
                        if attempt == max_retries - 1 and set_attempt < retry_sets - 1:
                            logging.info(f"完成第 {set_attempt + 1} 組嘗試，等待 {set_delay} 秒後繼續...")
                            time.sleep(set_delay)
                        else:
                            time.sleep(retry_delay)
                        continue
                    else:
                        logging.error(f"在調用 Gemini API 時發生錯誤: {e}")
                        return "抱歉，我現在遇到了一些技術問題，請稍後再試。"
    
    def cleanup(self):
        """清理資源並關閉連接"""
        try:
            if hasattr(self, 'chat_session'):
                self.chat_session = None
            if hasattr(self, 'model'):
                self.model = None
            logging.info("已關閉 Gemini AI")
        except Exception as e:
            logging.error(f"清理 Gemini 資源時發生錯誤: {e}")
