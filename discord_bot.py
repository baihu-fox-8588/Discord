import discord
from discord.ext import commands
import asyncio
import logging
import os
from tqdm import tqdm
from rich.logging import RichHandler
from rich import traceback
from gemini import gemini_ai
from grok import Grok
import time
import aiohttp

# 設置環境變數以抑制 gRPC 警告
os.environ['GRPC_PYTHON_LOG_LEVEL'] = '0'
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# 設定日誌
traceback.install(show_locals=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RichHandler()]
)


class DiscordBot:
    """Discord Bot 類別"""
    def __init__(self, token, owner_id = None, model: str = 'Gemini'):
        """初始化 Discord Bot"""
        self.token = token
        self.owner_id = owner_id
        
        # 初始化 AI
        with open('./prompt/特斯拉.txt', 'r', encoding='utf-8') as f:
            p = f.read()
        
        if model.lower() == 'gemini':
            self.ai = gemini_ai(prompt=p)

        elif model.lower() == 'grok':
            self.ai = Grok(prompt=p)

        else:
            logging.warning(f"未知模型：{model}")
            self.ai = gemini_ai(prompt=p)

        # 設定 bot
        intents = discord.Intents.all()
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.is_ready = asyncio.Event()
        
        # 初始化訊息佇列
        self.message_queue = asyncio.Queue()
        self.processing = False
        
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
                logging.debug(f'訊息被編輯 - 頻道: {before.channel.name} | 作者: {before.author.name}')

        @self.bot.event
        async def on_member_join(member):
            """當新成員加入伺服器時"""
            logging.debug(f'新成員加入 - {member.name}')

        @self.bot.event
        async def on_member_remove(member):
            """當成員離開伺服器時"""
            logging.debug(f'成員離開 - {member.name}')

        @self.bot.event
        async def on_guild_channel_create(channel):
            """當新頻道被創建時"""
            logging.debug(f'新頻道創建 - {channel.name}')

        @self.bot.event
        async def on_guild_channel_delete(channel):
            """當頻道被刪除時"""
            logging.debug(f'頻道被刪除 - {channel.name}')

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
                
        @self.bot.command(name="token_test")
        async def token_test(ctx, message_count: int = 100, *, test_message: str = "這是一個測試訊息"):
            """測試不同數量歷史訊息的 token 消耗"""
            if message_count <= 0 or message_count > 100:
                await ctx.send("訊息數量必須在 1 到 100 之間")
                return
                
            # 創建測試用的 AI 實例
            try:
                with open('./prompt/特斯拉.txt', 'r', encoding='utf-8') as f:
                    p = f.read()
            except FileNotFoundError:
                p = "使用繁體中文進行回覆"
                logging.warning("找不到 prompt 文件，使用預設 prompt")
                
            test_ai = gemini_ai(prompt=p)
            
            # 準備進度訊息
            progress_msg = await ctx.send("正在進行測試，請稍候...")
            
            # 準備測試結果
            results = []
            base_tokens = None
            
            try:
                # 第一次測試（無歷史訊息）
                input_tokens = test_ai.model.count_tokens(test_message).total_tokens
                response = test_ai.chat(test_message)
                response_tokens = test_ai.model.count_tokens(response).total_tokens
                base_tokens = input_tokens + response_tokens
                
                results.append({
                    'history_count': 0,
                    'total_tokens': base_tokens,
                    'increase': 0,
                    'percentage': 0
                })
                
                # 測試不同數量的歷史訊息
                test_intervals = [1, 5, 10, 20, 50, 75, 100]  # 測試的歷史訊息數量點
                test_intervals = [x for x in test_intervals if x <= message_count]
                
                for target_count in test_intervals:
                    if target_count <= len(test_ai.history) // 2:
                        continue
                        
                    # 添加更多歷史訊息直到達到目標數量
                    while len(test_ai.history) // 2 < target_count:
                        test_ai.chat(f"這是第 {len(test_ai.history)//2 + 1} 條測試訊息")
                    
                    # 計算當前的 token 消耗
                    history_tokens = sum(test_ai.model.count_tokens(h['parts'][0]).total_tokens 
                                       for h in test_ai.history)
                    current_input_tokens = test_ai.model.count_tokens(test_message).total_tokens
                    current_response = test_ai.chat(test_message)
                    current_response_tokens = test_ai.model.count_tokens(current_response).total_tokens
                    
                    total_tokens = current_input_tokens + current_response_tokens + history_tokens
                    increase = total_tokens - base_tokens
                    percentage = ((total_tokens / base_tokens) - 1) * 100
                    
                    results.append({
                        'history_count': target_count,
                        'total_tokens': total_tokens,
                        'increase': increase,
                        'percentage': percentage
                    })
                    
                    # 更新進度
                    await progress_msg.edit(content=f"測試進度: {target_count}/{message_count} 條歷史訊息")
                
                # 創建結果報告
                embed = discord.Embed(
                    title="Token 消耗量測試報告",
                    description=f"測試訊息: {test_message}",
                    color=discord.Color.blue()
                )
                
                # 基準數據
                embed.add_field(
                    name="基準 (無歷史訊息)",
                    value=f"總 Token: {base_tokens}",
                    inline=False
                )
                
                # 各個測試點的數據
                for result in results[1:]:  # 跳過基準數據
                    embed.add_field(
                        name=f"歷史訊息數: {result['history_count']}",
                        value=f"總 Token: {result['total_tokens']}\n"
                              f"增加量: {result['increase']}\n"
                              f"增加比例: {result['percentage']:.2f}%",
                        inline=True
                    )
                
                # 刪除進度訊息並發送結果
                await progress_msg.delete()
                await ctx.send(embed=embed)
                
            except Exception as e:
                await progress_msg.edit(content=f"測試過程中發生錯誤: {str(e)}")
            
        @self.bot.command(name="ping")
        async def ping(ctx):
            """測量各種延遲的平均值（10次測量）"""
            msg = await ctx.send("正在測量延遲中...")
            
            # 初始化延遲列表
            bot_latencies = []
            api_latencies = []
            ws_latencies = []
            
            # 進行10次測量
            for _ in range(10):
                # Bot 回應延遲
                before = time.monotonic()
                tmp_msg = await ctx.send(".")
                bot_latency = (time.monotonic() - before) * 1000
                await tmp_msg.delete()
                bot_latencies.append(bot_latency)
                
                # API 延遲
                api_before = time.monotonic()
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://discord.com/api/v10/gateway') as resp:
                        api_latency = (time.monotonic() - api_before) * 1000
                api_latencies.append(api_latency)
                
                # WebSocket 延遲
                ws_latencies.append(self.bot.latency * 1000)
                
                # 短暫延遲以避免速率限制
                await asyncio.sleep(0.5)
            
            # 計算平均值
            avg_bot = round(sum(bot_latencies) / len(bot_latencies))
            avg_api = round(sum(api_latencies) / len(api_latencies))
            avg_ws = round(sum(ws_latencies) / len(ws_latencies))
            avg_total = round((avg_bot + avg_api + avg_ws) / 3)
            
            # 建立嵌入式訊息
            embed = discord.Embed(title="延遲測試報告", color=discord.Color.blue())
            
            # 使用 embed.description 顯示延遲資訊
            embed.description = (
                f"**Bot 回應延遲**：{avg_bot}ms\n"
                f"**API 延遲**：{avg_api}ms\n"
                f"**網路延遲**：{avg_ws}ms\n"
                f"**平均延遲**：{avg_total}ms"
            )
            
            await msg.edit(content=None, embed=embed)
            
        @self.bot.command(name="exit")
        async def exit_command(ctx):
            """退出機器人"""
            # 檢查是否為機器人擁有者
            if ctx.author.id != self.owner_id:
                await ctx.send(f"{ctx.author.mention} 抱歉，只有機器人擁有者才能使用此指令！")
                return
            
            # 發送確認訊息
            confirm_msg = await ctx.send("你要離開我了嗎(｡•́︿•̀｡)(Y/N)")
            
            def check(m):
                # 確保只有原始發送者可以回應，且必須在同一個頻道
                return (m.author.id == self.owner_id and 
                        m.channel == ctx.channel and 
                        m.content.upper() in ['Y', 'N'])
            
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
                    await ctx.send('下次見啦！ヾ(￣▽￣)Bye~Bye~')
                    logging.info(f'機器人被擁有者 {ctx.author.name} 關閉')
                    await self.bot.close()
                else:
                    # 如果用戶取消
                    await ctx.send('已取消關閉機器人')
                    try:
                        await confirm_msg.delete()
                        await msg.delete()
                    except:
                        pass
            
            except asyncio.TimeoutError:
                # 如果超時
                await ctx.send('超過 30 秒未回應，已自動取消關閉')
                try:
                    await confirm_msg.delete()
                except:
                    pass
            
    async def process_message_queue(self):
        """處理訊息佇列"""
        self.processing = True
        while True:
            try:
                # 從佇列中取出訊息
                message = await self.message_queue.get()
                
                try:
                    # 調用 Gemini API
                    response = self.ai.chat(message.content)
                    logging.info(f'回覆：{response}')

                    # 等待 5 秒
                    logging.info('等待 5 秒後發送回覆...')
                    await asyncio.sleep(5)
                    
                    # 發送回覆到原始頻道
                    await message.channel.send(f'{message.author.mention} {response}')
                    
                except Exception as e:
                    logging.error(f'處理訊息時發生錯誤：{e}')
                    await message.channel.send(f'{message.author.mention} 抱歉，我現在無法正確回應，請稍後再試。')
                
                finally:
                    # 標記任務完成
                    self.message_queue.task_done()
                    # 等待一小段時間再處理下一條訊息
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logging.error(f'佇列處理器發生錯誤：{e}')
                await asyncio.sleep(5)  # 發生錯誤時等待較長時間

    async def setup_hook(self):
        """當 bot 準備好時會被呼叫"""
        logging.info('Bot setup hook 已執行')
        # 啟動訊息佇列處理器
        asyncio.create_task(self.process_message_queue())
        
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
        try:
            # 停止處理新的訊息
            self.processing = False
            
            # 等待所有佇列中的訊息處理完成
            if hasattr(self, 'message_queue'):
                if not self.message_queue.empty():
                    await self.message_queue.join()
            
            # 關閉 Gemini 的聊天會話
            if hasattr(self, 'ai'):
                self.ai.cleanup()
                await asyncio.sleep(1)  # 給予時間清理
            
            # 關閉 Discord bot
            await self.bot.close()
            
        except Exception as e:
            logging.error(f"關閉時發生錯誤: {e}")

    async def send_message(self, channel, message: str, user_mention: str = None):
        """發送訊息到指定頻道"""
        await self.is_ready.wait()
        try:
            if not channel:
                raise ValueError("未提供有效的頻道")
                
            if user_mention:
                message = f'{user_mention} {message}'
            await channel.send(message)
            logging.info(f'已發送訊息到頻道 {channel.name}：{message}')
        except Exception as e:
            logging.error(f'發送訊息時發生錯誤：{e}')
            raise

    async def clear(self, channel, amount=100):
        """清除指定頻道的所有訊息"""
        await self.is_ready.wait()
        
        try:
            if not channel:
                raise ValueError("未提供有效的頻道")
            
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
                # 將訊息加入佇列
                await self.message_queue.put(message)
