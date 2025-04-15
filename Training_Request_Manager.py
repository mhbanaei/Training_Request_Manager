import discord
from discord.ext import commands
import datetime
import json
import os

# ================= تنظیمات اولیه =================
BOT_TOKEN = "YourToken"  # توکن بات خودتون را جایگزین کنید
ALLOWED_ROLE_ID = YourToken           # آی‌دی نقش مجاز برای استفاده از فرمان /amozesh
CHANNEL_ID = YourToken                # آی‌دی چنلی که امبد (برای همه گزینه‌ها) در آن ارسال می‌شود
LOG_CHANNEL_ID = YourToken            # آی‌دی چنل لاگ برای ثبت تایید درخواست
REVIEWER_ROLE_ID = YourToken          # آی‌دی نقش مجاز برای تایید درخواست

PROGRESS_FILE = "user_progress.json"
PENDING_ACCEPT_FILE = "pending_accept_requests.json"
PENDING_COMPLETION_FILE = "pending_completion_requests.json"

# -------------------- توابع ذخیره و بارگذاری وضعیت کاربران --------------------
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            else:
                data = json.loads(content)
        for uid, progress in data.items():
            if progress.get("last_time") is not None:
                progress["last_time"] = datetime.datetime.fromisoformat(progress["last_time"])
        return data
    return {}

def save_progress():
    data = {}
    for uid, progress in user_progress.items():
        progress_copy = progress.copy()
        if progress_copy.get("last_time") is not None:
            progress_copy["last_time"] = progress_copy["last_time"].isoformat()
        data[uid] = progress_copy
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# -------------------- توابع ذخیره و بارگذاری درخواست‌های در حال انتظار تایید --------------------
def load_pending_accept():
    if os.path.exists(PENDING_ACCEPT_FILE):
        with open(PENDING_ACCEPT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            else:
                return json.loads(content)
    return {}

def save_pending_accept(data):
    with open(PENDING_ACCEPT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# -------------------- توابع ذخیره و بارگذاری درخواست‌های در حال انتظار تکمیل --------------------
def load_pending_completion():
    if os.path.exists(PENDING_COMPLETION_FILE):
        with open(PENDING_COMPLETION_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            else:
                return json.loads(content)
    return {}

def save_pending_completion(data):
    with open(PENDING_COMPLETION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# -------------------- متغیرهای سراسری --------------------
user_progress = load_progress()
pending_accept_requests = load_pending_accept()
pending_completion_requests = load_pending_completion()
teacher_cooldown = {}  # دیکشنری برای ذخیره زمان آخرین تایید هر مربی

# متون پیش‌فرض برای هر گزینه
default_texts = {
    1: "جلسه آکادمی Z-01",
    2: "جلسه آکادمی Z-02",
    3: "جلسه آکادمی Z-03",
    4: "جلسه آکادمی Z-04",
    5: "جلسه آکادمی Z-05",
}

# ================= تعریف ویو دکمه‌های انتخاب گزینه =================
class OptionSelectionView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        progress = user_progress.get(str(user_id), {"last_option": 0, "last_time": None, "accepted": True})
        expected_option = progress["last_option"] + 1
        pending = not progress.get("accepted", True)
        for i in range(1, 6):
            button = OptionButton(option_number=i)
            if pending:
                button.disabled = True
            else:
                button.disabled = (i != expected_option)
            self.add_item(button)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("این دکمه برای شما نیست.", ephemeral=True)
            return False
        return True

class OptionButton(discord.ui.Button):
    def __init__(self, option_number: int):
        super().__init__(style=discord.ButtonStyle.primary, label=f"Z-0{option_number}", custom_id=f"option_{option_number}")
        self.option_number = option_number
    
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.datetime.now()
        
        progress = user_progress.get(str(user_id), {"last_option": 0, "last_time": None, "accepted": True})
        expected_option = progress["last_option"] + 1
        
        if self.option_number != expected_option:
            await interaction.response.send_message(
                f"لطفاً گزینه‌ها را به ترتیب انتخاب کنید. گزینه بعدی باید Z-0{expected_option} باشد.",
                ephemeral=True
            )
            return
        
        if progress["last_option"] > 0 and not progress["accepted"]:
            await interaction.response.send_message(
                "درخواست قبلی شما هنوز توسط مربی تایید نشده است.",
                ephemeral=True
            )
            return
        
        if progress["accepted"] and progress["last_time"] is not None:
            elapsed = (now - progress["last_time"]).total_seconds()
            if elapsed < 24 * 3600:
                remaining = 24 * 3600 - elapsed
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                await interaction.response.send_message(
                    f"لطفاً {hours} ساعت و {minutes} دقیقه صبر کنید تا بتوانید گزینه بعدی را انتخاب کنید.",
                    ephemeral=True
                )
                return
        
        progress["last_option"] = self.option_number
        progress["accepted"] = False  # در انتظار تایید
        user_progress[str(user_id)] = progress
        save_progress()
        
        self.disabled = True
        parent_view: OptionSelectionView = self.view
        if self.option_number < 5:
            for child in parent_view.children:
                if isinstance(child, OptionButton) and child.option_number == self.option_number + 1:
                    child.disabled = False
                    break
        
        await interaction.response.edit_message(view=parent_view)
        
        tracking_number = now.strftime("%H%M%m%d%Y")
        embed = discord.Embed(title="درخواست آموزش", color=discord.Color.blue(), timestamp=now)
        embed.add_field(name="کاربر", value=f"<@{user_id}>", inline=False)
        embed.add_field(name="شماره پیگیری", value=tracking_number, inline=False)
        embed.add_field(name="تاریخ و زمان درخواست", value=now.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="جلسه انتخاب شده", value=default_texts.get(self.option_number, f"جلسه Z-0{self.option_number}"), inline=False)
            
        channel = interaction.client.get_channel(CHANNEL_ID)
        if channel is not None:
            accept_view = AcceptRequestView(requester_id=user_id, embed_data=embed)
            sent_message = await channel.send(embed=embed, view=accept_view)
            accept_view.sent_message = sent_message
            interaction.client.add_view(accept_view)
            pending_accept_requests[str(user_id)] = embed.to_dict()
            save_pending_accept(pending_accept_requests)
        else:
            print(f"چنل با آی‌دی {CHANNEL_ID} پیدا نشد.")

# ================= تعریف مدال جهت دریافت توضیحات =================
class DescriptionModal(discord.ui.Modal, title="توضیحات پذیرش"):
    description = discord.ui.TextInput(
        label="توضیحات", 
        style=discord.TextStyle.long, 
        placeholder="لطفاً توضیحات خود را وارد کنید...", 
        required=True
    )
    
    def __init__(self, requester_id: int, embed_data: discord.Embed, approval_message: discord.Message):
        super().__init__()
        self.requester_id = requester_id
        self.embed_data = embed_data
        self.approval_message = approval_message
    
    async def on_submit(self, interaction: discord.Interaction):
        approver = interaction.user
        
        # برای DM به کاربر
        dm_embed = discord.Embed.from_dict(self.embed_data.to_dict())
        dm_embed.title = "درخواست جلسه آکادمی شما تایید شد"
        dm_embed.add_field(name="توضیحات", value=self.description.value, inline=False)
        dm_embed.add_field(name="تایید کننده", value=f"<@{approver.id}>", inline=False)
        
        requester = interaction.client.get_user(self.requester_id)
        if requester is not None:
            try:
                await requester.send(embed=dm_embed)
            except Exception as e:
                print(f"امکان ارسال DM به کاربر {self.requester_id} وجود ندارد: {e}")
        
        # ساخت امبد جدید برای لاگ بر اساس امبد اولیه (بدون تغییر در قالب اصلی)
        log_embed = discord.Embed.from_dict(self.embed_data.to_dict())
        log_embed.title = "جلسه تایید شده توسط مربی"
        # حذف هر فیلدی با نام "تایید کننده" اگر وجود داشته باشد
        new_fields = [field for field in log_embed.to_dict().get("fields", []) if field.get("name") != "تایید کننده"]
        log_embed.clear_fields()
        for field in new_fields:
            log_embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))
        log_embed.add_field(name="تایید کننده", value=f"<@{approver.id}>", inline=False)
        
        complete_view = CompleteTrainingView(requester_id=self.requester_id, approver_id=approver.id, embed_data=log_embed)
        
        # حذف پیام اولیه از کانال اصلی و ارسال پیام جدید در چنل لاگ
        try:
            await self.approval_message.delete()
        except Exception as e:
            print(f"خطا در حذف پیام اولیه: {e}")
        
        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel is not None:
            new_message = await log_channel.send(embed=log_embed, view=complete_view)
            pending_completion_requests[str(self.requester_id)] = {
                "embed": log_embed.to_dict(),
                "approver_id": approver.id,
                "message_id": new_message.id
            }
            save_pending_completion(pending_completion_requests)
        else:
            print(f"چنل لاگ با آی‌دی {LOG_CHANNEL_ID} پیدا نشد.")
        
        teacher_cooldown[approver.id] = datetime.datetime.now()
        
        if str(self.requester_id) in pending_accept_requests:
            del pending_accept_requests[str(self.requester_id)]
            save_pending_accept(pending_accept_requests)
        
        await interaction.response.send_message("درخواست تایید شد. لطفاً دکمه «تکمیل آموزش» را برای نهایی کردن کلیک کنید.", ephemeral=True)

# ================= تعریف ویو دکمه تایید درخواست =================
class AcceptRequestView(discord.ui.View):
    def __init__(self, requester_id: int, embed_data: discord.Embed):
        super().__init__(timeout=None)
        self.requester_id = requester_id
        self.embed_data = embed_data
        self.sent_message = None
        self.add_item(AcceptButton(requester_id=requester_id, embed_data=embed_data))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if REVIEWER_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("شما اجازه‌ی قبول درخواست را ندارید.", ephemeral=True)
            return False
        return True

class AcceptButton(discord.ui.Button):
    def __init__(self, requester_id: int, embed_data: discord.Embed):
        super().__init__(style=discord.ButtonStyle.success, label="قبول درخواست", custom_id=f"accept_{requester_id}")
        self.requester_id = requester_id
        self.embed_data = embed_data
    
    async def callback(self, interaction: discord.Interaction):
        now = datetime.datetime.now()
        teacher_id = interaction.user.id
        last_approval = teacher_cooldown.get(teacher_id)
        if last_approval is not None:
            elapsed = (now - last_approval).total_seconds()
            if elapsed < 2 * 3600:
                remaining = 2 * 3600 - elapsed
                minutes = int(remaining / 60)
                seconds = int(remaining % 60)
                await interaction.response.send_message(
                    f"لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید تا بتوانید درخواست بعدی را تایید کنید.",
                    ephemeral=True
                )
                return
        
        self.disabled = True
        modal = DescriptionModal(
            requester_id=self.requester_id,
            embed_data=self.embed_data,
            approval_message=self.view.sent_message
        )
        await interaction.response.send_modal(modal)

# ================= تعریف ویو و دکمه تکمیل آموزش =================
class CompleteTrainingView(discord.ui.View):
    def __init__(self, requester_id: int, approver_id: int, embed_data: discord.Embed):
        super().__init__(timeout=None)
        self.requester_id = requester_id
        self.approver_id = approver_id
        self.embed_data = embed_data
        self.add_item(CompleteTrainingButton(requester_id=requester_id, approver_id=approver_id, embed_data=embed_data))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.approver_id:
            await interaction.response.send_message("این دکمه فقط برای تایید کننده است.", ephemeral=True)
            return False
        return True

class CompleteTrainingButton(discord.ui.Button):
    def __init__(self, requester_id: int, approver_id: int, embed_data: discord.Embed):
        super().__init__(style=discord.ButtonStyle.secondary, label="تکمیل آموزش", custom_id=f"complete_{requester_id}_{approver_id}")
        self.requester_id = requester_id
        self.approver_id = approver_id
        self.embed_data = embed_data

    async def callback(self, interaction: discord.Interaction):
        now = datetime.datetime.now()
        if interaction.user.id != self.approver_id:
            await interaction.response.send_message("شما اجازه‌ی این عملیات را ندارید.", ephemeral=True)
            return
        
        progress = user_progress.get(str(self.requester_id), {"last_option": 0, "last_time": None, "accepted": False})
        progress["accepted"] = True
        progress["last_time"] = now
        user_progress[str(self.requester_id)] = progress
        save_progress()
        
        if str(self.requester_id) in pending_completion_requests:
            del pending_completion_requests[str(self.requester_id)]
            save_pending_completion(pending_completion_requests)
        
        # ساخت امبد نهایی بدون فیلد تایید کننده و با اضافه کردن تکمیل کننده
        final_embed = discord.Embed.from_dict(self.embed_data.to_dict())
        final_embed.title = "جلسه تکمیل شده توسط مربی"
        fields = [field for field in final_embed.to_dict().get("fields", []) if field.get("name") not in ["تایید کننده", "تکمیل کننده"]]
        final_embed.clear_fields()
        for field in fields:
            final_embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))
        final_embed.add_field(name="تکمیل کننده", value=f"<@{interaction.user.id}>", inline=False)
        
        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel is not None:
            try:
                await log_channel.send(embed=final_embed)
            except Exception as e:
                print(f"خطا در ارسال پیام به چنل لاگ: {e}")
        else:
            print(f"چنل لاگ با آی‌دی {LOG_CHANNEL_ID} پیدا نشد.")
        
        try:
            await interaction.message.delete()
        except Exception as e:
            print(f"خطا در حذف پیام لاگ: {e}")
        
        await interaction.response.send_message("تکمیل آموزش انجام شد.", ephemeral=True)

# ================= تنظیمات بات =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    for user_id in user_progress.keys():
        bot.add_view(OptionSelectionView(int(user_id)))
    for requester_id, embed_dict in pending_accept_requests.items():
        embed = discord.Embed.from_dict(embed_dict)
        bot.add_view(AcceptRequestView(requester_id=int(requester_id), embed_data=embed))
    # بازیابی ویوهای تکمیل آموزش پس از ریستارت
    for requester_id, info in pending_completion_requests.items():
        embed = discord.Embed.from_dict(info["embed"])
        approver_id = info["approver_id"]
        view = CompleteTrainingView(requester_id=int(requester_id), approver_id=approver_id, embed_data=embed)
        bot.add_view(view)

@bot.tree.command(name="amozesh", description="ارسال درخواست آموزش")
async def amozesh(interaction: discord.Interaction):
    user_id = interaction.user.id
    if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("شما اجازه‌ی استفاده از این فرمان را ندارید.", ephemeral=True)
        return

    progress = user_progress.get(str(user_id), {"last_option": 0, "last_time": None, "accepted": True})
    if not progress.get("accepted", True):
        await interaction.response.send_message(
            "درخواست قبلی شما هنوز در انتظار تایید است. لطفاً پس از تایید درخواست قبلی از دستور مجدد استفاده کنید.",
            ephemeral=True
        )
        return
    
    view = OptionSelectionView(user_id=user_id)
    try:
        await interaction.user.send("لطفاً جلسه آموزشی خود را انتخاب کنید:", view=view)
        await interaction.response.send_message("یک پیام خصوصی برای شما ارسال شد.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("امکان ارسال پیام خصوصی به شما وجود ندارد. لطفاً تنظیمات دایرکت خود را بررسی کنید.", ephemeral=True)

bot.run(BOT_TOKEN)
