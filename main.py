import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os
from datetime import datetime, date
import random

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Data storage
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_guild_data(guild_id):
    data = load_data()
    guild_id = str(guild_id)
    if guild_id not in data:
        data[guild_id] = {
            "invites": {},
            "normal_prizes": ["جائزة 1", "جائزة 2", "جائزة 3", "جائزة 4", "جائزة 5"],
            "vip_prizes": ["جائزة VIP 1", "جائزة VIP 2", "جائزة VIP 3", "جائزة VIP 4", "جائزة VIP 5"],
            "settings": {
                "spin_cost_normal": 1,
                "spin_cost_vip": 5,
                "bot_avatar_url": None,
                "streaming_status": "الدوران والفوز!",
                "invite_log_channel": None,
                "daily_spin_limit": 10,
            },
            "spin_results": [],
            "daily_spins": {}
        }
        save_data(data)
    return data

def get_daily_spins(guild_id, user_id):
    data = get_guild_data(guild_id)
    guild_id = str(guild_id)
    user_id = str(user_id)
    
    if user_id not in data[guild_id]["daily_spins"]:
        data[guild_id]["daily_spins"][user_id] = {"date": str(date.today()), "count": 0}
        save_data(data)
    
    today = str(date.today())
    if data[guild_id]["daily_spins"][user_id]["date"] != today:
        data[guild_id]["daily_spins"][user_id] = {"date": today, "count": 0}
        save_data(data)
    
    return data[guild_id]["daily_spins"][user_id]["count"]

def increment_daily_spins(guild_id, user_id):
    data = get_guild_data(guild_id)
    guild_id = str(guild_id)
    user_id = str(user_id)
    
    today = str(date.today())
    if user_id not in data[guild_id]["daily_spins"] or data[guild_id]["daily_spins"][user_id]["date"] != today:
        data[guild_id]["daily_spins"][user_id] = {"date": today, "count": 0}
    
    data[guild_id]["daily_spins"][user_id]["count"] += 1
    save_data(data)

def get_guild_specific(guild_id, key):
    data = get_guild_data(guild_id)
    guild_id = str(guild_id)
    return data[guild_id].get(key, {})

def set_guild_specific(guild_id, key, value):
    data = get_guild_data(guild_id)
    guild_id = str(guild_id)
    data[guild_id][key] = value
    save_data(data)

def is_ticket_channel(channel):
    """Check if a channel is a ticket channel"""
    if not channel:
        return False
    
    channel_name = channel.name.lower()
    if "ticket" in channel_name or "تذكرة" in channel_name:
        return True
    
    if channel.category and ("ticket" in channel.category.name.lower() or "تذاكر" in channel.category.name.lower()):
        return True
    
    return False

@bot.event
async def on_ready():
    print(f"✅ Bot is ready as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

@bot.event
async def on_member_join(member):
    """Track invites when a new member joins"""
    if member.bot:
        return
    
    try:
        guild_id = str(member.guild.id)
        data = get_guild_data(guild_id)
        
        invites_before = data[guild_id].get("invites_cache", {})
        invites_after = {}
        
        for invite in await member.guild.invites():
            invites_after[invite.code] = invite.uses
        
        inviter_id = None
        for code, uses in invites_after.items():
            before_uses = invites_before.get(code, 0)
            if uses > before_uses:
                try:
                    invite_obj = await bot.fetch_invite(code)
                    if invite_obj.inviter:
                        inviter_id = str(invite_obj.inviter.id)
                    break
                except:
                    pass
        
        if inviter_id:
            if inviter_id not in data[guild_id]["invites"]:
                data[guild_id]["invites"][inviter_id] = {"normal": 0, "vip": 0}
            data[guild_id]["invites"][inviter_id]["normal"] += 1
        
        data[guild_id]["invites_cache"] = invites_after
        save_data(data)
    except Exception as e:
        print(f"Error tracking invite: {e}")

# Admin Commands
@bot.tree.command(name="add-invites", description="إضافة دعوات لمستخدم")
@app_commands.describe(user="المستخدم", count="عدد الدعوات")
async def add_invites(interaction: discord.Interaction, user: discord.User, count: int):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    user_id = str(user.id)
    
    if user_id not in data[guild_id]["invites"]:
        data[guild_id]["invites"][user_id] = {"normal": 0, "vip": 0}
    
    data[guild_id]["invites"][user_id]["normal"] += count
    save_data(data)
    
    embed = discord.Embed(title="✅ تمت إضافة الدعوات", color=discord.Color.green())
    embed.add_field(name="المستخدم", value=f"{user.mention}", inline=False)
    embed.add_field(name="تمت الإضافة", value=f"+{count} دعوات", inline=False)
    embed.add_field(name="إجمالي الدعوات العادية", value=data[guild_id]["invites"][user_id]["normal"], inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove-invites", description="حذف دعوات من مستخدم")
@app_commands.describe(user="المستخدم", count="عدد الدعوات")
async def remove_invites(interaction: discord.Interaction, user: discord.User, count: int):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    user_id = str(user.id)
    
    if user_id not in data[guild_id]["invites"]:
        data[guild_id]["invites"][user_id] = {"normal": 0, "vip": 0}
    
    data[guild_id]["invites"][user_id]["normal"] = max(0, data[guild_id]["invites"][user_id]["normal"] - count)
    save_data(data)
    
    embed = discord.Embed(title="✅ تم حذف الدعوات", color=discord.Color.red())
    embed.add_field(name="المستخدم", value=f"{user.mention}", inline=False)
    embed.add_field(name="تم الحذف", value=f"-{count} دعوات", inline=False)
    embed.add_field(name="الدعوات المتبقية", value=data[guild_id]["invites"][user_id]["normal"], inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set-invite-log", description="تعيين قناة سجل الدعوات")
@app_commands.describe(channel="القناة")
async def set_invite_log(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    data[guild_id]["settings"]["invite_log_channel"] = channel.id
    save_data(data)
    
    embed = discord.Embed(title="✅ تم تعيين قناة السجل", color=discord.Color.green())
    embed.add_field(name="القناة", value=f"{channel.mention}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set-normal-prizes", description="تعيين الجوائز العادية")
@app_commands.describe(
    prize1="الجائزة الأولى",
    prize2="الجائزة الثانية",
    prize3="الجائزة الثالثة",
    prize4="الجائزة الرابعة",
    prize5="الجائزة الخامسة"
)
async def set_normal_prizes(interaction: discord.Interaction, prize1: str, prize2: str, prize3: str, prize4: str, prize5: str):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    prizes = [p for p in [prize1, prize2, prize3, prize4, prize5] if p.strip()]
    data[guild_id]["normal_prizes"] = prizes
    save_data(data)
    
    embed = discord.Embed(title="✅ تم تحديث الجوائز العادية", color=discord.Color.blue())
    embed.add_field(name="الجوائز", value="\n".join(prizes), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set-vip-prizes", description="تعيين جوائز VIP")
@app_commands.describe(
    prize1="الجائزة الأولى",
    prize2="الجائزة الثانية",
    prize3="الجائزة الثالثة",
    prize4="الجائزة الرابعة",
    prize5="الجائزة الخامسة"
)
async def set_vip_prizes(interaction: discord.Interaction, prize1: str, prize2: str, prize3: str, prize4: str, prize5: str):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    prizes = [p for p in [prize1, prize2, prize3, prize4, prize5] if p.strip()]
    data[guild_id]["vip_prizes"] = prizes
    save_data(data)
    
    embed = discord.Embed(title="✅ تم تحديث جوائز VIP", color=discord.Color.gold())
    embed.add_field(name="الجوائز", value="\n".join(prizes), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spin-settings", description="عرض إعدادات الدوران")
async def spin_settings(interaction: discord.Interaction):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    settings = data[guild_id]["settings"]
    
    embed = discord.Embed(title="⚙️ إعدادات الدوران", color=discord.Color.purple())
    
    embed.add_field(name="━━━━━━━━ الجوائز العادية ━━━━━━━━", value="", inline=False)
    embed.add_field(name="عدد الجوائز", value=f"**{len(data[guild_id]['normal_prizes'])} جوائز**", inline=False)
    if data[guild_id]['normal_prizes']:
        prizes_list = "\n".join([f"• {i+1}. {p}" for i, p in enumerate(data[guild_id]['normal_prizes'])])
        embed.add_field(name="الجوائز", value=prizes_list, inline=False)
    
    embed.add_field(name="━━━━━━━━ جوائز VIP ━━━━━━━━", value="", inline=False)
    embed.add_field(name="عدد الجوائز", value=f"**{len(data[guild_id]['vip_prizes'])} جوائز**", inline=False)
    if data[guild_id]['vip_prizes']:
        prizes_list = "\n".join([f"• {i+1}. {p}" for i, p in enumerate(data[guild_id]['vip_prizes'])])
        embed.add_field(name="الجوائز", value=prizes_list, inline=False)
    
    embed.add_field(name="━━━━━━━━ الإعدادات العامة ━━━━━━━━", value="", inline=False)
    embed.add_field(name="الحد اليومي للسحب", value=f"**{settings['daily_spin_limit']}** مرات/يوم", inline=True)
    embed.add_field(name="حالة البث", value=f"_{settings['streaming_status']}_", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set-spin-invites", description="تعيين تكلفة الدوران")
@app_commands.describe(spin_type="normal أو vip", cost="التكلفة")
async def set_spin_invites(interaction: discord.Interaction, spin_type: str, cost: int):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    
    if spin_type.lower() == "normal":
        data[guild_id]["settings"]["spin_cost_normal"] = cost
    elif spin_type.lower() == "vip":
        data[guild_id]["settings"]["spin_cost_vip"] = cost
    else:
        await interaction.response.send_message("❌ اختر normal أو vip", ephemeral=True)
        return
    
    save_data(data)
    
    embed = discord.Embed(title="✅ تم تحديث التكلفة", color=discord.Color.green())
    embed.add_field(name="نوع الدوران", value=spin_type, inline=False)
    embed.add_field(name="التكلفة الجديدة", value=cost, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spin-results", description="عرض نتائج الدورانات الأخيرة")
async def spin_results(interaction: discord.Interaction):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    
    if not data[guild_id]["spin_results"]:
        await interaction.response.send_message("❌ لا توجد نتائج دورانات حتى الآن", ephemeral=True)
        return
    
    embed = discord.Embed(title="📊 نتائج الدورانات الأخيرة", color=discord.Color.blue())
    for result in data[guild_id]["spin_results"][-10:]:
        embed.add_field(
            name=f"{result['user']} - {result['type']}",
            value=f"الجائزة: {result['prize']}\nالوقت: {result['time']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bot-avatar", description="تعيين صورة البوت")
@app_commands.describe(url="رابط الصورة")
async def bot_avatar(interaction: discord.Interaction, url: str):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    data[guild_id]["settings"]["bot_avatar_url"] = url
    save_data(data)
    
    embed = discord.Embed(title="✅ تم تحديث الصورة", color=discord.Color.green())
    embed.add_field(name="الرابط", value=url, inline=False)
    embed.set_thumbnail(url=url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set-streaming", description="تعيين حالة البث")
@app_commands.describe(status="حالة البث")
async def set_streaming(interaction: discord.Interaction, status: str):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ أنت تحتاج صلاحيات المسؤول", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    data[guild_id]["settings"]["streaming_status"] = status
    save_data(data)
    
    await bot.change_presence(activity=discord.Streaming(name=status, url="https://www.twitch.tv/discord"))
    
    embed = discord.Embed(title="✅ تم تحديث حالة البث", color=discord.Color.green())
    embed.add_field(name="الحالة الجديدة", value=status, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set-daily-limit", description="تحديد عدد السحب اليومي للأعضاء (أدمن فقط)")
@app_commands.describe(limit="عدد مرات السحب اليومية")
async def set_daily_limit(interaction: discord.Interaction, limit: int):
    if not interaction.user.guild_permissions or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ هذا الأمر حصري للمسؤولين فقط!", ephemeral=True)
        return
    
    if limit < 1:
        await interaction.response.send_message("❌ الحد الأدنى هو 1", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    data[guild_id]["settings"]["daily_spin_limit"] = limit
    save_data(data)
    
    embed = discord.Embed(title="✅ تم تحديد السحب اليومي", color=discord.Color.green())
    embed.add_field(name="الحد اليومي الجديد", value=f"{limit} مرات", inline=False)
    embed.add_field(name="📝 ملاحظة", value="سيتم إعادة تعيين العداد كل يوم عند منتصف الليل", inline=False)
    await interaction.response.send_message(embed=embed)

# User Commands
@bot.command(name="invites", description="عرض عدد دعواتك")
async def check_invites(ctx):
    guild_id = str(ctx.guild.id)
    data = get_guild_data(guild_id)
    user_id = str(ctx.author.id)
    invites = data[guild_id]["invites"].get(user_id, {"normal": 0, "vip": 0})
    
    total_invites = invites["normal"] + invites["vip"]
    
    embed = discord.Embed(title="📊 دعواتك", color=discord.Color.blue())
    embed.add_field(name="عدد الدعوات", value=f"**{total_invites}**", inline=False)
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

class SpinView(View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
    
    async def perform_spin(self, interaction: discord.Interaction, spin_type: str):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        user_name = interaction.user.mention
        
        data = load_data()
        guild_id_str = str(guild_id)
        
        if guild_id_str not in data:
            data = get_guild_data(guild_id)
            guild_id_str = str(guild_id)
        
        today = str(date.today())
        
        if user_id not in data[guild_id_str]["daily_spins"]:
            data[guild_id_str]["daily_spins"][user_id] = {"date": today, "count": 0}
        elif data[guild_id_str]["daily_spins"][user_id]["date"] != today:
            data[guild_id_str]["daily_spins"][user_id] = {"date": today, "count": 0}
        
        daily_spins = data[guild_id_str]["daily_spins"][user_id]["count"]
        daily_limit = data[guild_id_str]["settings"]["daily_spin_limit"]
        
        if daily_spins >= daily_limit:
            embed = discord.Embed(title="❌ لقد وصلت للحد اليومي", color=discord.Color.red())
            embed.add_field(name="السحب المتبقي اليوم", value="0", inline=False)
            embed.add_field(name="الحد اليومي", value=f"{daily_limit}", inline=False)
            embed.add_field(name="⏰ التوقيت", value="سيعود العداد صفر غداً", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if spin_type == "normal":
            prizes = data[guild_id_str]["normal_prizes"]
            if not prizes:
                await interaction.response.send_message("❌ لا توجد جوائز متاحة!", ephemeral=True)
                return
            
            prize = random.choice(prizes)
            
        elif spin_type == "vip":
            prizes = data[guild_id_str]["vip_prizes"]
            if not prizes:
                await interaction.response.send_message("❌ لا توجد جوائز VIP متاحة!", ephemeral=True)
                return
            
            prize = random.choice(prizes)
        
        data[guild_id_str]["daily_spins"][user_id]["count"] += 1
        
        result = {
            "user": user_name,
            "type": spin_type,
            "prize": prize,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data[guild_id_str]["spin_results"].append(result)
        if len(data[guild_id_str]["spin_results"]) > 100:
            data[guild_id_str]["spin_results"] = data[guild_id_str]["spin_results"][-100:]
        
        save_data(data)
        
        daily_spins = data[guild_id_str]["daily_spins"][user_id]["count"]
        spins_remaining = daily_limit - daily_spins
        
        embed = discord.Embed(title="🎉 نتيجة الدوران!", color=discord.Color.gold())
        embed.add_field(name="👤 المستخدم", value=user_name, inline=False)
        embed.add_field(name="🎯 نوع الدوران", value="عادي" if spin_type == "normal" else "VIP", inline=False)
        embed.add_field(name="🎁 الجائزة", value=prize, inline=False)
        embed.add_field(name="🎫 السحب المتبقي اليوم", value=f"{spins_remaining}/{daily_limit}", inline=False)
        await interaction.response.send_message(embed=embed)
    
    @discord.ui.button(label="🎯 عادي", style=discord.ButtonStyle.green)
    async def normal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.perform_spin(interaction, "normal")
    
    @discord.ui.button(label="👑 VIP", style=discord.ButtonStyle.blurple)
    async def vip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.perform_spin(interaction, "vip")

@bot.command(name="spin", description="دوران العجلة!")
async def spin(ctx):
    if not is_ticket_channel(ctx.channel):
        embed = discord.Embed(title="❌ لا يمكن استخدام هذا الأمر هنا", color=discord.Color.red())
        embed.description = "هذا الأمر متاح فقط داخل التذاكر"
        embed.add_field(name="📍 أين تستخدمه؟", value="استخدم الأمر فقط في قنوات التذاكر", inline=False)
        embed.add_field(name="💡 مثال", value="القنوات التي تحتوي على 'ticket' في اسمها", inline=False)
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(title="🎮 اختر نوع الدوران", color=discord.Color.purple())
    embed.description = "اضغط على الزر المطلوب للدوران"
    embed.add_field(name="🎯 عادي", value="دوران عادي", inline=True)
    embed.add_field(name="👑 VIP", value="دوران VIP", inline=True)
    
    view = SpinView(ctx)
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="prizes", description="عرض الجوائز المتاحة")
async def view_prizes(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    data = get_guild_data(guild_id)
    
    embed = discord.Embed(title="🎁 الجوائز المتاحة", color=discord.Color.purple())
    
    if data[guild_id]["normal_prizes"]:
        embed.add_field(name="الجوائز العادية", value="\n".join(data[guild_id]["normal_prizes"]), inline=False)
    else:
        embed.add_field(name="الجوائز العادية", value="لم يتم تعيين جوائز", inline=False)
    
    if data[guild_id]["vip_prizes"]:
        embed.add_field(name="جوائز VIP", value="\n".join(data[guild_id]["vip_prizes"]), inline=False)
    else:
        embed.add_field(name="جوائز VIP", value="لم يتم تعيين جوائز", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

class MainHelpView(View):
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="👑 أوامر الأونر", style=discord.ButtonStyle.blurple)
    async def admin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="👑 أوامر المسؤول", color=discord.Color.red(), description="الأوامر المتاحة للمسؤولين فقط")
        embed.add_field(name="━━━━━━━━ إدارة الدعوات ━━━━━━━━", value="", inline=False)
        embed.add_field(name="/add-invites", value="إضافة دعوات لمستخدم", inline=False)
        embed.add_field(name="/remove-invites", value="حذف دعوات من مستخدم", inline=False)
        embed.add_field(name="/set-invite-log", value="تعيين قناة سجل الدعوات", inline=False)
        embed.add_field(name="━━━━━━━━ إدارة الجوائز ━━━━━━━━", value="", inline=False)
        embed.add_field(name="/set-normal-prizes", value="تعيين الجوائز العادية (5 جوائز)", inline=False)
        embed.add_field(name="/set-vip-prizes", value="تعيين جوائز VIP (5 جوائز)", inline=False)
        embed.add_field(name="━━━━━━━━ إعدادات الدوران ━━━━━━━━", value="", inline=False)
        embed.add_field(name="/spin-settings", value="عرض إعدادات الدوران الكاملة", inline=False)
        embed.add_field(name="/set-spin-invites", value="تعيين تكلفة الدوران (عادي/VIP)", inline=False)
        embed.add_field(name="/set-daily-limit", value="تحديد عدد مرات السحب اليومي", inline=False)
        embed.add_field(name="/spin-results", value="عرض آخر 10 نتائج دورانات", inline=False)
        embed.add_field(name="━━━━━━━━ إعدادات البوت ━━━━━━━━", value="", inline=False)
        embed.add_field(name="/bot-avatar", value="تعيين صورة البوت (رابط صورة)", inline=False)
        embed.add_field(name="/set-streaming", value="تعيين حالة البث للبوت", inline=False)
        view = BackHelpView()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📚 أوامر عامة", style=discord.ButtonStyle.green)
    async def user_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📚 الأوامر العامة", color=discord.Color.green(), description="الأوامر المتاحة للجميع")
        embed.add_field(name="━━━━━━━━ أوامر الدوران ━━━━━━━━", value="", inline=False)
        embed.add_field(name="!invites", value="عرض عدد دعواتك (عادي و VIP)", inline=False)
        embed.add_field(name="!spin", value="دوران العجلة مع اختيار النوع (عادي/VIP)", inline=False)
        embed.add_field(name="/prizes", value="عرض جميع الجوائز المتاحة", inline=False)
        embed.add_field(name="━━━━━━━━ معلومات ودعم ━━━━━━━━", value="", inline=False)
        embed.add_field(name="/help", value="عرض قائمة المساعدة هذه", inline=False)
        embed.add_field(name="/support", value="الحصول على الدعم والمساعدة", inline=False)
        embed.add_field(name="/join-voice", value="الانضمام لقناة صوتية", inline=False)
        embed.add_field(name="━━━━━━━━ معلومات إضافية ━━━━━━━━", value="", inline=False)
        embed.add_field(name="💡 ملاحظات مهمة", value="• لكل عضو حد يومي للسحب\n• كل سحب يكلف دعوات\n• النتائج تظهر في القناة للجميع", inline=False)
        view = BackHelpView()
        await interaction.response.edit_message(embed=embed, view=view)

class BackHelpView(View):
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.gray)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📖 قائمة المساعدة الرئيسية", color=discord.Color.blue())
        embed.description = "اختر فئة الأوامر التي تريد معرفة المزيد عنها"
        view = MainHelpView()
        await interaction.response.edit_message(embed=embed, view=view)

@bot.tree.command(name="help", description="قائمة المساعدة")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 قائمة المساعدة الرئيسية", color=discord.Color.blue())
    embed.description = "اختر فئة الأوامر التي تريد معرفة المزيد عنها"
    view = MainHelpView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="support", description="الحصول على الدعم")
async def support_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📞 الدعم", color=discord.Color.green())
    embed.add_field(name="هل تحتاج مساعدة؟", value="تواصل مع مسؤولي السيرفر", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="about", description="معلومات عن البوت")
async def about_command(interaction: discord.Interaction):
    embed = discord.Embed(title="ℹ️ معلومات البوت", color=discord.Color.blurple())
    embed.add_field(name="🤖 اسم البوت", value=f"{bot.user.name}", inline=False)
    embed.add_field(name="👨‍💻 Developer", value="**Mujahid**", inline=False)
    embed.add_field(name="📝 الوصف", value="نظام إدارة متقدم للعجلة والجوائز مع تتبع الدعوات", inline=False)
    embed.add_field(name="⚙️ الميزات", value="• نظام دوران العجلة\n• تتبع تلقائي للدعوات\n• إدارة الجوائز\n• حد يومي للسحب\n• دعم صوتي", inline=False)
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="join-voice", description="الانضمام لقناة صوتية")
@app_commands.describe(channel="قناة صوتية")
async def join_voice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    try:
        await interaction.response.defer()
        
        vc = await channel.connect(self_deaf=True, self_mute=True)
        
        embed = discord.Embed(
            title="✅ تم الاتصال بنجاح",
            color=discord.Color.green(),
            description="تم الانضمام لقناة الصوت بنجاح"
        )
        embed.add_field(name="📍 القناة", value=channel.mention, inline=True)
        embed.add_field(name="🔇 حالة الميكروفون", value="مقفل", inline=True)
        embed.add_field(name="🔊 حالة السماعات", value="مقفلة", inline=True)
        embed.add_field(name="⏱️ الحالة", value="متصل بشكل دائم", inline=False)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_footer(text=f"تم بواسطة {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ حدث خطأ",
            color=discord.Color.red(),
            description=f"فشل الاتصال بقناة الصوت"
        )
        embed.add_field(name="🔍 التفاصيل", value=f"```{str(e)}```", inline=False)
        embed.add_field(name="💡 التلميح", value="تأكد من أن البوت لديه صلاحيات الاتصال بقنوات الصوت", inline=False)
        
        try:
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(f"❌ خطأ: {str(e)}")

# Run the bot
if __name__ == "__main__":
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set")
        exit(1)
    bot.run(bot_token)
