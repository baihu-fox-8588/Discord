import asyncio
import os
from dotenv import load_dotenv
from discord_bot import DiscordBot

# 載入環境變數
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
owner_id = 808972376619483137  # 你的 Discord ID
channel_ID = int(os.getenv('CHANNEL_ID'))
thread_ID = int(os.getenv('THREAD_ID', '0'))  # 新增討論串 ID

async def main():
    bot = None
    try:
        # 創建並啟動 bot
        bot = DiscordBot(token, owner_id)
        await bot.start()

    except KeyboardInterrupt:
        print('程式已被使用者中斷')
    except Exception as e:
        print(f'發生錯誤：{e}')
    finally:
        if bot:
            await bot.close()

async def 女裝():
    try:
        bot = DiscordBot(token, owner_id)
        
        # 在一個新的事件迴圈中運行 bot
        bot_task = asyncio.create_task(bot.start())
        
        # 等待頻道準備好
        await bot.is_ready.wait()
        
        # 取得指定的頻道或討論串
        if thread_ID:
            channel = await bot.bot.fetch_channel(thread_ID)
            if not channel:
                print(f'無法找到指定的討論串 ID: {thread_ID}')
                return
        else:
            channel = bot.bot.get_channel(channel_ID)
            if not channel:
                print(f'無法找到指定的頻道 ID: {channel_ID}')
                return
        
        # 發送訊息
        for _ in range(10):
            await channel.send('每日關心 <@1076840902200393759> 今天女裝了嗎？')
            await asyncio.sleep(0.5)  # 每次發送訊息的間隔時間為 0.5 秒

        # 關閉 bot
        await bot.close()
        await bot_task

    except KeyboardInterrupt:
        print('程式已被使用者中斷')
    except Exception as e:
        print(f'發生錯誤：{e}')
        
    finally:
        if 'bot' in locals():
            await bot.close()

if __name__ == '__main__':
    asyncio.run(main())