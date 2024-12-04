import os
import logging
from openai import OpenAI
from rich.logging import RichHandler
from dotenv import load_dotenv

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RichHandler()]
)

# 設定 OpenAI 的日誌層級為 WARNING，以隱藏 HTTP 請求訊息
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# 載入環境變數
load_dotenv()
xai_api_key = os.getenv('XAI_API_KEY')

if not xai_api_key:
    raise ValueError("未找到 XAI_API_KEY 環境變數")

class Grok:
    def __init__(self, prompt: str = '使用繁體中文進行回覆'):
        self.client = OpenAI(
            api_key=xai_api_key,
            base_url='https://api.x.ai/v1'
        )

        self.messages = [
            {"role": "system", "content": prompt}
        ]

    def chat(self, text: str):
        if not text or not isinstance(text, str):
            logging.error("無效的輸入文本")
            return "抱歉，我無法處理空白或無效的輸入。"
            
        max_retries = 3
        retry_delay = 2  # 每次重試間隔2秒
        
        for attempt in range(max_retries):
            try:
                self.messages.append(
                    {"role": "user", "content": text}
                )

                response = self.client.chat.completions.create(
                    model='grok-beta',
                    messages=self.messages,
                )

                if not response or not response.choices or not response.choices[0].message:
                    raise ValueError("收到無效的回應")
                    
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("收到空的回應內容")

                self.messages.append(
                    {"role": "assistant", "content": content}
                )
                return content

            except Exception as e:
                logging.error(f"Grok API 呼叫失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                return f"抱歉，我遇到了技術問題：{str(e)}"
    
    def get_history(self):
        """獲取歷史記錄"""
        valid_messages = []
        for message in self.messages:
            if not message or 'role' not in message or 'content' not in message:
                logging.warning("發現無效的歷史記錄項目")
                continue
            if not message['content']:
                logging.warning("發現空的歷史記錄內容")
                continue
            valid_messages.append(message)
        return valid_messages

    def cleanup(self):
        """清理資源"""
        try:
            self.messages.clear()
            if hasattr(self, 'client'):
                self.client = None
            logging.info("已關閉 Grok AI")
        except Exception as e:
            logging.error(f"清理資源時發生錯誤: {e}")

if __name__ == '__main__':
    try:
        grok = Grok()

        while True:
            text = input("你:")

            if text == 'exit':
                break

            response = grok.chat(text)
            if response:
                print(f"Grok 回應: {response}")

        history = grok.get_history()

        print("--" * 30)
        print("歷史記錄:")
        for message in history:
            print(f"{message['role']}:\n{message['content']}\n")

    except Exception as e:
        logging.error(f"程式執行錯誤: {e}")