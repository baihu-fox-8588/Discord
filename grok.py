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
        try:
            self.messages.append(
                {"role": "user", "content": text}
            )

            response = self.client.chat.completions.create (
                model='grok-beta',
                messages=self.messages,
            )

            self.messages.append(
                {"role": "assistant", "content": response.choices[0].message.content}
            )
            return response.choices[0].message.content

        except Exception as e:
            logging.error(f"Grok API 呼叫失敗: {e}")
            return str(e)
    
    def get_history(self):
        return self.messages

    async def cleanup(self):
        """清理資源"""
        pass

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