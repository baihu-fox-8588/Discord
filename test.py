import asyncio
import os
from dotenv import load_dotenv
from discord_bot import DiscordBot
import signal
import sys
from gemini import cleanup_genai
import logging
from rich.logging import RichHandler

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RichHandler()]
)

# 載入環境變數
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
owner_id = 808972376619483137  # 你的 Discord ID
channel_ID = int(os.getenv('CHANNEL_ID'))
thread_ID = int(os.getenv('THREAD_ID', '0'))  # 新增討論串 ID

# 全局變數用於控制關閉流程
shutdown_event = asyncio.Event()

def handle_shutdown(signum, frame):
    """處理關閉信號"""
    logging.info('接收到關閉信號，正在安全關閉...')
    shutdown_event.set()

async def shutdown():
    """安全關閉程序"""
    logging.info('正在關閉機器人...')
    cleanup_genai()  # 先清理 Gemini 資源
    await asyncio.sleep(1)
    # 強制結束程序
    sys.exit(0)

async def main():
    bot = None
    try:
        # 註冊信號處理器
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        # 創建並啟動 bot
        bot = DiscordBot(token, owner_id)
        logging.info('正在啟動機器人...')
        await bot.start()

    except KeyboardInterrupt:
        logging.info('程式已被使用者中斷')
        
    except Exception as e:
        logging.error(f'發生錯誤：{e}')

    finally:
        if bot:
            logging.info(f'已關閉機器人')
            await bot.close()
            await asyncio.sleep(1)
            await shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logging.info('程式已被使用者中斷')

    finally:
        cleanup_genai()  # 確保在任何情況下都清理 Gemini 資源