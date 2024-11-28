import discord
from discord.ext import commands
import asyncio
import logging
from tqdm import tqdm
from rich.logging import RichHandler
from rich import traceback
from gemini import gemini_ai

# 設定日誌
traceback.install(show_locals=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RichHandler()]
)

# 載入 prompt
with open('prompt.txt', 'r', encoding='utf-8') as f:
    p = f.read()
gemini = gemini_ai(prompt=p)

class DiscordBot:
    """Discord Bot 類別"""
    def __init__(self, token, owner_id=None):
        """初始化 Discord Bot"""
        self.token = token
        self.owner_id = owner_id
        
        # 初始化 AI
        self.ai = gemini_ai()

        # 設定 bot
        intents = discord.Intents.all()
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.is_ready = asyncio.Event()
        
        # 註冊指令和事件
        self.setup_commands()
        
    def setup_commands(self):
        """設定所有指令和事件"""
        
        # 設定事件
        @self.bot.event
        async def setup_hook():
            await self.setup_hook()
            
        @self.bot.event
        async def on_ready():
            await self.on_ready()
            
        @self.bot.event
        async def on_message(message):
            await self.on_message(message)
            await self.bot.process_commands(message)

        @self.bot.event
        async def on_message_delete(message):
            """當訊息被刪除時"""
            if message.author != self.bot.user:  # 忽略機器人自己的訊息
                logging.info(f'訊息被刪除 - 頻道: {message.channel.name} | 作者: {message.author.name} | 內容: {message.content}')

        @self.bot.event
        async def on_message_edit(before, after):
            """當訊息被編輯時"""
            if before.author != self.bot.user:  # 忽略機器人自己的訊息
                logging.info(f'訊息被編輯 - 頻道: {before.channel.name} | 作者: {before.author.name}')
                logging.info(f'原始內容: {before.content}')
                logging.info(f'修改後內容: {after.content}')

        @self.bot.event
        async def on_member_join(member):
            """當新成員加入伺服器時"""
            logging.info(f'新成員加入 - 伺服器: {member.guild.name} | 成員: {member.name}')

        @self.bot.event
        async def on_member_remove(member):
            """當成員離開伺服器時"""
            logging.info(f'成員離開 - 伺服器: {member.guild.name} | 成員: {member.name}')

        @self.bot.event
        async def on_guild_channel_create(channel):
            """當新頻道被創建時"""
            logging.info(f'新頻道創建 - 伺服器: {channel.guild.name} | 頻道: {channel.name}')

        @self.bot.event
        async def on_guild_channel_delete(channel):
            """當頻道被刪除時"""
            logging.info(f'頻道被刪除 - 伺服器: {channel.guild.name} | 頻道: {channel.name}')

        # 註冊斜線指令
        @self.bot.command(name="hello")
        async def hello(ctx):
            """打招呼"""
            await ctx.send(f'{ctx.author.mention} 你好啊！ヾ(•ω•`)o')
            
        @self.bot.command(name="clear")
        async def clear_command(ctx, amount: int = 100):
            """清除訊息"""
            if ctx.author.id != self.owner_id:
                await ctx.send(f'{ctx.author.mention} 只有機器人擁有者可以使用此指令')
                return
            
            try:
                await self.clear(ctx.channel, amount)
                await ctx.send(f'{ctx.author.mention} 已清除訊息！')
            except Exception as e:
                logging.error(f'清除訊息時發生錯誤：{e}')
                await ctx.send(f'{ctx.author.mention} 清除訊息時發生錯誤')
                
        @self.bot.command(name="exit")
        async def exit_command(ctx):
            """退出機器人"""
            if ctx.author.id != self.owner_id:
                await ctx.send("只有機器人擁有者可以使用此指令")
                return
                
            # 發送確認訊息
            confirm_msg = await ctx.send("你要離開我了嗎(｡•́︿•̀｡)(Y/N)")
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() in ['Y', 'N']
            
            try:
                # 等待用戶回應
                msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                
                # 如果用戶確認要退出
                if msg.content.upper() == 'Y':
                    # 先刪除確認訊息
                    try:
                        await confirm_msg.delete()
                        await msg.delete()
                    except:
                        pass
                    # 發送告別訊息並關閉
                    await ctx.send('ヾ(￣▽￣)Bye~Bye~')
                    await self.bot.close()
                else:
                    # 如果用戶取消
                    await ctx.send('已取消退出')
                    try:
                        await confirm_msg.delete()
                        await msg.delete()
                    except:
                        pass
            
            except asyncio.TimeoutError:
                # 如果超時
                await ctx.send('超時未回應，已取消退出')
                try:
                    await confirm_msg.delete()
                except:
                    pass
                
    async def setup_hook(self):
        """當 bot 準備好時會被呼叫"""
        logging.info('Bot setup hook 已執行')
        
    async def on_ready(self):
        """當 bot 準備好時觸發"""
        self.is_ready.set()
        logging.info(f'Bot 已啟動: {self.bot.user.name}')
        
        # 同步斜線指令
        try:
            logging.info('正在同步斜線指令...')
            await self.bot.tree.sync()
            logging.info('斜線指令同步完成！')
        except Exception as e:
            logging.error(f'同步斜線指令時發生錯誤：{e}')
            
    async def start(self):
        """啟動 bot"""
        await self.bot.start(self.token)

    async def close(self):
        """關閉 bot"""
        await self.bot.close()

    async def send_message(self, message: str, user_mention: str = None):
        """發送訊息到指定頻道"""
        await self.is_ready.wait()
        try:
            if user_mention:
                message = f'{user_mention} {message}'
            await self.bot.get_channel(CHANNEL_ID).send(message)
            logging.info(f'已發送訊息：{message}')
        except Exception as e:
            logging.error(f'發送訊息時發生錯誤：{e}')
            raise

    async def clear(self, channel=None, amount=100):
        """清除指定頻道的所有訊息"""
        await self.is_ready.wait()
        
        # 如果沒有指定頻道，使用預設頻道
        channel = channel or self.bot.get_channel(CHANNEL_ID)
        
        try:
            # 取得所有訊息
            messages = []
            async for message in channel.history(limit=amount):
                messages.append(message)
            
            if messages:
                # 使用進度條顯示刪除進度
                with tqdm(total=len(messages), desc="正在清除訊息") as pbar:
                    # 如果訊息數量大於100，使用批量刪除
                    if len(messages) > 1:
                        # Discord 限制一次最多刪除 100 條訊息，且訊息不能超過 14 天
                        chunks = [messages[i:i + 100] for i in range(0, len(messages), 100)]
                        for chunk in chunks:
                            try:
                                await channel.delete_messages(chunk)
                                pbar.update(len(chunk))
                            except discord.errors.HTTPException:
                                # 如果訊息太舊無法批量刪除，就逐條刪除
                                for msg in chunk:
                                    try:
                                        await msg.delete()
                                        pbar.update(1)
                                    except:
                                        continue
                    else:
                        # 如果只有一條訊息，直接刪除
                        await messages[0].delete()
                        pbar.update(1)
                        
                logging.info(f'已清除 {len(messages)} 則訊息')
            else:
                logging.info('沒有需要清除的訊息')
                
        except discord.Forbidden:
            logging.error('沒有權限清除訊息')
            raise
        except Exception as e:
            logging.error(f'清除訊息時發生錯誤：{e}')
            raise

    async def on_message(self, message):
        """處理收到的訊息"""
        # 忽略機器人自己的訊息
        if message.author == self.bot.user:
            return

        # 記錄訊息資訊
        logging.info(f'收到訊息 - 頻道: {message.channel.name} | 作者: {message.author.name} : {message.content}')

        # 檢查是否有提及機器人
        if self.bot.user.mentioned_in(message):
            # 清理消息內容，移除 mention 和額外空格
            content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            
            # 根據不同的命令做出回應
            if '清除' in content or 'clear' in content:
                await self.clear(message.channel)
            elif '退出' in content or 'exit' in content and message.author.id == self.owner_id:
                await message.channel.send(f'{message.author.mention} ヾ(￣▽￣)Bye~Bye~')
                await self.bot.close()
            else:
                try:
                    response = gemini.chat(content)
                    logging.info(f'回覆：{response}')
                    # 在回應前加上 @ 使用者
                    await message.channel.send(f'{message.author.mention} {response}')
                except Exception as e:
                    logging.error(f'生成回覆時發生錯誤：{e}')
                    await message.channel.send(f'{message.author.mention} 抱歉，我現在無法正確回應，請稍後再試。')
