import os, re, io, asyncio, time, logging
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
try:
    from unprom import deobfuscate as unprom
except Exception:
    unprom=None
load_dotenv()
TOKEN=os.getenv("DISCORD_TOKEN","")
GUILD=os.getenv("GUILD_ID","")
LOG_CHANNEL=os.getenv("LOG_CHANNEL_ID","")
MAX=int(os.getenv("MAX_FILE_MB","5"))*1024*1024
logging.basicConfig(level=logging.INFO)
log=logging.getLogger("lua-bot")
ENGINES=[
("Автоопределение","auto"),("Prometheus / unprom","prometheus"),
("IronBrew v1–v3","ironbrew"),("Luraph v11–v15","luraph"),
("MoonSec V1–V3","moonsec"),("PSU v4.0–v4.5A","psu"),
("MoonVeil v1.4.5","moonveil"),("Hercules v2.0.1","hercules"),
("AztupBrew v2.7.2","aztupbrew"),("77fuscator","77fuscator"),
("Obscura / ObscuraLua","obscura"),("Synapse Xen","synapse"),
("Boronide","boronide"),("wYnFuscate / 25ms","other"),("LuaObfuscator / XFuscator","misc")]
SIGS={
"Luraph":[r"Luraph",r"__lph"],"IronBrew":[r"IronBrew",r"\bIB2\b"],
"MoonSec":[r"MoonSec"],"Prometheus":[r"Prometheus",r"Vmify",r"__PROMETHEUS"],
"PSU":[r"Perth.?s Script Utilities",r"PSU[_ ]?v?4"],"MoonVeil":[r"MoonVeil"],
"Hercules":[r"Hercules"],"AztupBrew":[r"AztupBrew"],"77fuscator":[r"77fuscator"],
"Obscura":[r"ObscuraLua?"],"Synapse Xen":[r"Synapse.?Xen"],
"Boronide":[r"Boronide"],"wYnFuscate":[r"wYnFuscate"],"25ms":[r"25ms"],
"LuaObfuscator":[r"LuaObfuscator",r"Ferib"],"XFuscator":[r"XFuscator"]}
def detect(src):
    found=[n for n,ps in SIGS.items() if any(re.search(p,src,re.I) for p in ps)]
    if not found and (len(re.findall(r"\\[0-9]{2,3}",src))>8 or "loadstring" in src or "string.char" in src):
        found=["Неизвестная / кастомная"]
    return found
def process(src,engine):
    start=time.monotonic()
    if engine=="auto":
        found=detect(src)
        if "Prometheus" in found: engine="prometheus"
        else: return False,"Автоопределение: "+(", ".join(found) if found else "сигнатура не найдена")+". Нет подключённого декодера для этого формата.",None,0
    if engine!="prometheus":
        label=dict(ENGINES).get(engine,engine)
        return False,f"{label}: настоящий декодер пока не подключён. Результат не будет подменён форматированием.",None,0
    if unprom is None: return False,"Движок unprom не установлен. Проверь сборку requirements.txt.",None,0
    try:
        out=unprom(src)
        if not isinstance(out,str) or not out.strip(): return False,"Декодер не вернул исходный код. Возможно, файл повреждён или конфигурация не поддерживается.",None,time.monotonic()-start
        return True,"Prometheus обработан. Реконструкция может быть неполной — проверь результат.",out,time.monotonic()-start
    except Exception as e:
        log.exception("unprom failed")
        return False,f"Ошибка декодера: {type(e).__name__}: {str(e)[:180]}",None,time.monotonic()-start
async def admin_log(bot,msg):
    if not LOG_CHANNEL:return
    try:
        ch=bot.get_channel(int(LOG_CHANNEL))
        if ch: await ch.send(msg[:1900])
    except Exception:log.exception("admin log error")
class EngineSelect(discord.ui.Select):
    def __init__(self,attachment,owner):
        self.attachment,self.owner=attachment,owner
        opts=[discord.SelectOption(label=n,value=v,description="Декодер подключён" if v=="prometheus" else "Модуль пока не реализован",default=v=="auto") for n,v in ENGINES]
        super().__init__(placeholder="Select a deobfuscator…",min_values=1,max_values=1,options=opts)
    async def callback(self,interaction):
        if interaction.user.id!=self.owner:
            return await interaction.response.send_message("Это меню принадлежит другому пользователю.",ephemeral=True)
        await interaction.response.defer()
        name=dict(ENGINES)[self.values[0]]
        msg=await interaction.followup.send(embed=discord.Embed(title="Lua Deobfuscator · Processing",description=f"Файл `{self.attachment.filename}`\nДвижок: **{name}**\n⏳ Анализирую…",color=discord.Color.orange()),wait=True)
        try:
            if self.attachment.size>MAX:
                return await msg.edit(embed=discord.Embed(title="Failed",description=f"Файл превышает лимит {MAX//1048576} МБ.",color=discord.Color.red()))
            raw=await self.attachment.read()
            src=raw.decode("utf-8-sig",errors="replace")
            if not src.strip() or "\x00" in src:
                return await msg.edit(embed=discord.Embed(title="Failed",description="Файл пустой или не является текстовым Lua.",color=discord.Color.red()))
            matches=detect(src)
            await msg.edit(embed=discord.Embed(title="Lua Deobfuscator · Processing",description=f"Файл: `{self.attachment.filename}`\nСигнатуры: {', '.join(matches) if matches else 'не найдены'}\n⚙️ Выполняю статический анализ…",color=discord.Color.blurple()))
            ok,report,out,elapsed=await asyncio.to_thread(process,src,self.values[0])
            if not ok:
                await msg.edit(embed=discord.Embed(title="Deobfuscation failed",description=report,color=discord.Color.red()))
                await admin_log(interaction.client,f"FAILED {interaction.user} · {self.attachment.filename} · {name}")
                return
            data=out.encode("utf-8")
            if len(data)>7*1024*1024:
                return await msg.edit(embed=discord.Embed(title="Failed",description="Результат больше лимита Discord.",color=discord.Color.red()))
            filename=re.sub(r"[^A-Za-z0-9_.-]","_",self.attachment.filename.rsplit(".",1)[0])+".deob.lua"
            f=discord.File(io.BytesIO(data),filename=filename)
            embed=discord.Embed(title="Deobfuscation completed",description=f"Файл: `{self.attachment.filename}`\nДвижок: **{name}**\nВремя: `{elapsed:.2f}s`\n\n{report}",color=discord.Color.green())
            await msg.edit(embed=embed,attachments=[f])
            await admin_log(interaction.client,f"SUCCESS {interaction.user} · {self.attachment.filename} · {name} · {elapsed:.2f}s")
        except Exception:
            log.exception("processing error")
            await msg.edit(embed=discord.Embed(title="Processing error",description="Внутренняя ошибка. Проверь логи Render.",color=discord.Color.red()))
class EngineView(discord.ui.View):
    def __init__(self,att,owner):
        super().__init__(timeout=300);self.add_item(EngineSelect(att,owner))
class Bot(commands.Bot):
    async def setup_hook(self):
        if GUILD:
            g=discord.Object(id=int(GUILD));self.tree.copy_global_to(guild=g);await self.tree.sync(guild=g)
        else:await self.tree.sync()
bot=Bot(command_prefix="!",intents=discord.Intents.default())
@bot.event
async def on_ready():log.info("Online as %s",bot.user)
@bot.tree.command(name="deobfuscate",description="Загрузить Lua-файл и выбрать движок")
async def deobfuscate(interaction:discord.Interaction,file:discord.Attachment):
    if not file.filename.lower().endswith((".lua",".luau",".txt")) or file.size>MAX:
        return await interaction.response.send_message(f"Нужен .lua/.luau/.txt файл до {MAX//1048576} МБ.",ephemeral=True)
    embed=discord.Embed(title="Lua Deobfuscator",description=f"Файл `{file.filename}` получен.\nВыбери деобфускатор в меню.",color=discord.Color.blurple())
    embed.add_field(name="Реально подключено",value="Prometheus / unprom" if unprom else "Prometheus: ошибка установки зависимости",inline=False)
    embed.set_footer(text="Остальные движки появятся после реализации и тестирования.")
    await interaction.response.send_message(embed=embed,view=EngineView(file,interaction.user.id))
@bot.tree.command(name="detect",description="Определить вероятный обфускатор")
async def detect_cmd(interaction:discord.Interaction,file:discord.Attachment):
    if not file.filename.lower().endswith((".lua",".luau",".txt")) or file.size>MAX:
        return await interaction.response.send_message("Нужен Lua/TXT файл допустимого размера.",ephemeral=True)
    src=(await file.read()).decode("utf-8-sig",errors="replace");found=detect(src)
    await interaction.response.send_message("Возможные совпадения: "+(", ".join(found) if found else "не найдены")+". Это эвристика, не гарантия.",ephemeral=True)
@bot.tree.command(name="engines",description="Список движков и статус поддержки")
async def engines_cmd(interaction:discord.Interaction):
    lines=[f"• **{n}** — "+("✅ подключён" if v=="prometheus" and unprom else ("⚠️ установка не удалась" if v=="prometheus" else "🧩 в плане")) for n,v in ENGINES]
    await interaction.response.send_message("\n".join(lines),ephemeral=True)
@bot.tree.command(name="ping",description="Проверить бота")
async def ping(interaction:discord.Interaction):
    await interaction.response.send_message(f"🟢 Online · {round(bot.latency*1000)} ms",ephemeral=True)
if not TOKEN:raise RuntimeError("Set DISCORD_TOKEN in environment variables")
bot.run(TOKEN)
