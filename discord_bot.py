import os
import logging
import discord
from discord.ext import commands
import asyncio
from gemini import gemini_ai
from grok import Grok
import time
import aiohttp
from discord import app_commands
from rich.logging import RichHandler
from rich import traceback
from tqdm import tqdm
import requests
from city_names import CITY_NAMES  # 導入城市名稱對照表
import datetime

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
    def __init__(self, token, owner_id = None, model: str = 'Gemini', wait: bool = False):
        """初始化 Discord Bot"""
        self.token = token
        self.owner_id = owner_id
        self.wait = wait
        
        # 城市名稱對照表
        self.CITY_NAMES = CITY_NAMES  # 設置城市名稱對照表
        
        # 初始化 AI
        with open('E:/project/Discord/prompt/千雪.md', 'r', encoding='utf-8') as f:
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
            try:
                await self.bot.tree.sync()
                logging.info("已同步斜線指令")
            except Exception as e:
                logging.error(f"同步斜線指令時發生錯誤：{e}")
            await self.setup_hook()
            
        @self.bot.event
        async def on_ready():
            await self.on_ready()
            
        # 註冊斜線指令
        @self.bot.tree.command(name="ping", description="檢查機器人延遲")
        async def ping(interaction: discord.Interaction):
            """測量各種延遲的平均值（10次測量）"""
            await interaction.response.defer()
            
            # 初始化延遲列表
            bot_latencies = []
            api_latencies = []
            ws_latencies = []
            
            # 進行10次測量
            for _ in range(10):
                # Bot 回應延遲
                before = time.monotonic()
                bot_latency = (time.monotonic() - before) * 1000
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
            
            await interaction.followup.send(embed=embed)

        @self.bot.tree.command(name="exit", description="關閉機器人")
        async def exit_command(interaction: discord.Interaction):
            """關閉機器人"""
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("只有機器人擁有者可以使用此指令", ephemeral=True)
                return
            
            await interaction.response.send_message(f"掰掰啦 ~ 寶寶 ~", ephemeral=True)
            await self.close()

        @self.bot.tree.command(name="clear", description="清除指定數量的訊息")
        @app_commands.describe(amount="要清除的訊息數量（1-100）")
        async def clear(interaction: discord.Interaction, amount: int = 10):
            """清除訊息"""
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("只有機器人擁有者可以使用此指令", ephemeral=True)
                return
            
            if not 0 < amount <= 100:
                await interaction.response.send_message("清除數量必須在 1 到 100 之間", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                deleted = await interaction.channel.purge(limit=amount)
                await interaction.followup.send(f"已清除 {len(deleted)} 條訊息", ephemeral=True)
            except Exception as e:
                logging.error(f'清除訊息時發生錯誤：{e}')
                await interaction.followup.send("清除訊息時發生錯誤", ephemeral=True)

        @self.bot.tree.command(name="royoo", description="關心指定使用者今天女裝了嗎")
        @app_commands.describe(
            amount="要詢問的次數（預設10次）",
            user="要關心的使用者（預設為 Royoo）"
        )
        async def royoo(
            interaction: discord.Interaction,
            amount: int = 10,  # 預設為10次
            user: discord.Member = None  # 預設為 None，後面會改為 Royoo 的 ID
        ):
            """關心指定使用者今天女裝了嗎"""
            # 檢查次數是否在合理範圍內
            if not 0 < amount <= 100:
                await interaction.response.send_message(
                    "詢問次數必須在 1 到 100 之間",
                    ephemeral=True
                )
                return

            # 立即回應互動以避免超時
            await interaction.response.send_message(
                "正在發送關心訊息...",
                ephemeral=True
            )

            try:
                # 設定目標討論串
                target_thread_id = 1311094222656639018
                guild = interaction.guild
                
                # 獲取討論串
                try:
                    target_thread = await guild.fetch_channel(target_thread_id)
                    logging.info(f"找到討論串: {target_thread.name}")
                except discord.NotFound:
                    await interaction.edit_original_response(
                        content="找不到指定的討論串"
                    )
                    return
                except discord.Forbidden:
                    await interaction.edit_original_response(
                        content="我沒有權限訪問討論串"
                    )
                    return

                # 檢查是否為有效的討論串或文字頻道
                if not isinstance(target_thread, (discord.Thread, discord.TextChannel)):
                    await interaction.edit_original_response(
                        content="目標不是有效的討論串或文字頻道"
                    )
                    return

                # 檢查發送訊息的權限
                if not target_thread.permissions_for(guild.me).send_messages:
                    await interaction.edit_original_response(
                        content="我沒有在討論串中發送訊息的權限"
                    )
                    return

                # 設定要 @ 的使用者
                default_user_id = 1076840902200393759  # Royoo 的 ID
                if user is None:
                    user_mention = f"<@{default_user_id}>"
                else:
                    user_mention = user.mention

                # 發送訊息
                sent_count = 0
                for i in range(amount):
                    try:
                        await target_thread.send(f"每日關心 {user_mention} 今天女裝了嗎？")
                        sent_count += 1
                        logging.info(f"成功發送第 {sent_count}/{amount} 條訊息")
                        
                        # 如果不是最後一條訊息，則等待一下
                        if i < amount - 1:
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logging.error(f"發送第 {sent_count + 1} 條訊息時發生錯誤: {e}")
                        break

                # 更新結果訊息
                if sent_count == amount:
                    await interaction.edit_original_response(
                        content=f"✅ 已發送完成！共發送 {sent_count} 次關心訊息 ❤️"
                    )
                else:
                    await interaction.edit_original_response(
                        content=f"⚠️ 發送過程中出現錯誤，僅發送了 {sent_count}/{amount} 次訊息"
                    )

            except Exception as e:
                logging.error(f"執行指令時發生錯誤: {e}")
                await interaction.edit_original_response(
                    content=f"❌ 執行指令時發生錯誤: {str(e)}"
                )

        @self.bot.tree.command(name="info", description="顯示伺服器和機器人資訊")
        async def info(interaction: discord.Interaction):
            """顯示伺服器和機器人資訊"""
            guild = interaction.guild
            bot_member = guild.get_member(self.bot.user.id)
            
            embed = discord.Embed(title=f"{guild.name} 伺服器資訊", color=discord.Color.blue())
            
            # 伺服器資訊
            embed.add_field(
                name="📊 伺服器資訊",
                value=f"🏷️ 伺服器 ID：{guild.id}\n"
                      f"👑 擁有者：{guild.owner.mention}\n"
                      f"📅 創建時間：<t:{int(guild.created_at.timestamp())}:R>\n"
                      f"👥 成員數：{guild.member_count}",
                inline=False
            )
            
            # 頻道資訊
            channels = guild.channels
            text_channels = len([c for c in channels if isinstance(c, discord.TextChannel)])
            voice_channels = len([c for c in channels if isinstance(c, discord.VoiceChannel)])
            categories = len([c for c in channels if isinstance(c, discord.CategoryChannel)])
            
            embed.add_field(
                name="📝 頻道統計",
                value=f"💭 文字頻道：{text_channels}\n"
                      f"🔊 語音頻道：{voice_channels}\n"
                      f"📁 類別數：{categories}",
                inline=True
            )
            
            # 機器人資訊
            embed.add_field(
                name="🤖 機器人資訊",
                value=f"🏷️ 名稱：{self.bot.user.name}\n"
                      f"📅 加入時間：<t:{int(bot_member.joined_at.timestamp())}:R>\n"
                      f"⚡ 延遲：{round(self.bot.latency * 1000)}ms",
                inline=True
            )
            
            # 設置伺服器圖標
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(name="help", description="顯示所有可用的指令")
        async def help(interaction: discord.Interaction):
            """顯示所有可用的指令"""
            embed = discord.Embed(
                title="📚 指令幫助",
                description="以下是所有可用的斜線指令：",
                color=discord.Color.blue()
            )
            
            commands = {
                "ping": "檢查機器人延遲",
                "clear": "清除指定數量的訊息 (管理員專用)",
                "info": "顯示伺服器和機器人資訊",
                "help": "顯示此幫助訊息",
                "exit": "關閉機器人 (管理員專用)",
                "Royoo": "每日關心 Royoo 今天女裝了嗎",
                "weather": "查詢指定地點的天氣預報"
            }
            
            for cmd, desc in commands.items():
                embed.add_field(
                    name=f"/{cmd}",
                    value=desc,
                    inline=False
                )
            
            embed.set_footer(text="提示：輸入 / 可以看到所有可用的指令")
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(name="weather", description="查詢指定地點的天氣預報")
        async def weather(interaction: discord.Interaction, location: str = "新北市"):
            """查詢天氣預報
            
            Args:
                location (str, optional): 要查詢的地點（城市名稱）。預設為新北市。
                支援台灣縣市及世界主要城市，例如：
                - 台灣：台北、新北、高雄等
                - 日本：東京、大阪、京都等
                - 美國：紐約、洛杉磯等
                - 亞洲：首爾、北京、香港等
                - 歐洲：倫敦、巴黎等
            """
            try:
                # 轉換城市名稱
                if location in self.CITY_NAMES:
                    city_name = self.CITY_NAMES[location]
                else:
                    await interaction.response.send_message(f"抱歉，找不到 {location} 的天氣資訊。請確認城市名稱是否正確。", ephemeral=True)
                    return
                
                # OpenWeatherMap API設置
                api_key = "5f11c065acc703865b9351406ac35562"
                base_url = "http://api.openweathermap.org/data/2.5"
                
                # 天氣圖標對照表
                WEATHER_ICONS = {
                    "Clear": "☀️",
                    "Clouds": "☁️",
                    "Rain": "🌧️",
                    "Drizzle": "🌦️",
                    "Thunderstorm": "⛈️",
                    "Snow": "🌨️",
                    "Mist": "🌫️",
                    "Smoke": "🌫️",
                    "Haze": "🌫️",
                    "Dust": "🌫️",
                    "Fog": "🌫️",
                    "Sand": "🌫️",
                    "Ash": "🌫️",
                    "Squall": "🌪️",
                    "Tornado": "🌪️"
                }

                # 發送當前天氣API請求
                current_params = {
                    "q": city_name,
                    "appid": api_key,
                    "units": "metric",  # 使用攝氏溫度
                    "lang": "zh_tw"     # 使用繁體中文
                }
                
                # 發送未來天氣預報API請求
                forecast_params = {
                    "q": city_name,
                    "appid": api_key,
                    "units": "metric",
                    "lang": "zh_tw"
                }

                try:
                    # 獲取當前天氣
                    current_response = requests.get(f"{base_url}/weather", params=current_params)
                    current_data = current_response.json()
                    
                    # 獲取未來天氣預報
                    forecast_response = requests.get(f"{base_url}/forecast", params=forecast_params)
                    forecast_data = forecast_response.json()

                    if current_response.status_code == 200:
                        # 獲取當前天氣圖標
                        current_icon = WEATHER_ICONS.get(current_data['weather'][0]['main'], "🌈")
                        
                        # 創建 Embed
                        embed = discord.Embed(
                            title=f"{current_icon} {location} 天氣預報",
                            color=discord.Color.blue(),
                            timestamp=datetime.datetime.now()
                        )

                        # 當前天氣資訊（使用表格格式和動態寬度）
                        current_weather = (
                            f"```\n天氣狀況    當前溫度    體感溫度    濕度    風速\n"  # 天氣狀況4個中文=8個空格
                            f"{WEATHER_ICONS.get(current_data['weather'][0]['main'], '🌈')} {current_data['weather'][0]['description']:<4}"  # 多雲2個中文=4個空格
                            f"{current_data['main']['temp']:>6.1f} °C  "
                            f"{current_data['main']['feels_like']:>6.1f} °C  "
                            f"{current_data['main']['humidity']:>4}%   "  # 濕度右對齊
                            f"{current_data['wind']['speed']:>4.1f} m/s\n```"
                        )
                        embed.add_field(name="📍 當前天氣", value=current_weather, inline=False)

                        # 處理未來天氣預報
                        if forecast_response.status_code == 200:
                            # 按照日期分組預報數據
                            daily_forecasts = {}
                            today = datetime.datetime.now().strftime('%m/%d')
                            for item in forecast_data['list']:
                                date = datetime.datetime.fromtimestamp(item['dt']).strftime('%m/%d')
                                # 跳過當天的預報
                                if date == today:
                                    continue
                                if date not in daily_forecasts:
                                    daily_forecasts[date] = {
                                        'temps': [],
                                        'weather': item['weather'][0]['description'],
                                        'weather_main': item['weather'][0]['main'],
                                        'pop': item.get('pop', 0)
                                    }
                                daily_forecasts[date]['temps'].append(item['main']['temp'])

                            # 只取前7天
                            dates = list(daily_forecasts.keys())[:7]
                            
                            # 生成預報表格
                            forecast_text = "```\n日期      最高溫度      最低溫度      降雨率     天氣狀況\n"  # 考慮中文字元寬度
                            for date in dates:
                                max_temp = max(daily_forecasts[date]['temps'])
                                min_temp = min(daily_forecasts[date]['temps'])
                                pop = int(daily_forecasts[date]['pop'] * 100)
                                weather_icon = WEATHER_ICONS.get(daily_forecasts[date]['weather_main'], "🌈")
                                
                                # 格式化每個字段，確保對齊
                                forecast_text += (
                                    f"{date:<6} "  # 日期佔6個字元加1空格
                                    f"{max_temp:>7.1f} °C  "  # 溫度右移一格
                                    f"{min_temp:>7.1f} °C  "  # 溫度右移一格
                                    f"{pop:>7}%     "  # 降雨機率右移一格
                                    f"{weather_icon} {daily_forecasts[date]['weather']:<}\n"  # 天氣狀況左對齊
                                )
                            forecast_text += "```"
                            
                            embed.add_field(name="🗓️ 未來天氣預報", value=forecast_text, inline=False)
                            
                            # 添加天氣圖標說明
                            icons_text = " ".join([f"{icon} {desc}" for desc, icon in WEATHER_ICONS.items()])
                            embed.set_footer(text=f"天氣圖標說明：{icons_text}")
                        
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message(f"抱歉，無法獲取 {location} 的天氣資訊。", ephemeral=True)
                except Exception as e:
                    print(f"Error: {e}")
                    await interaction.response.send_message(f"抱歉，獲取天氣資訊時發生錯誤。", ephemeral=True)
            except Exception as e:
                logging.error(f'執行天氣指令時發生錯誤：{e}')
                await interaction.response.send_message("執行指令時發生錯誤", ephemeral=True)

        # 註冊其他事件
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

    async def process_message_queue(self):
        """處理訊息佇列"""
        self.processing = True
        while True:
            try:
                # 從佇列中取出訊息
                message = await self.message_queue.get()
                
                try:
                    # 調用 AI API，並加入使用者名稱
                    user_message = f"[{message.author.display_name}]: {message.content}"
                    response = self.ai.chat(user_message)
                    logging.info(f'回覆：{response}')

                    # 等待 5 秒
                    if self.wait:
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
