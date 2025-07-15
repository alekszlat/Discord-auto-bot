import json
import asyncio
import discord
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ─── Paths & Globals ─────────────────────────────────────────────────────────
CONFIG_PATH            = "config.json"
SCHEDULER_PATH         = "scheduler.json"
USERS_ID_LIST_PATH     = "users-id-list.json"
MAIN_LOOP              = None

# Write PID for external management (optional)
with open("bot.pid", "w") as f:
    f.write(str(os.getpid()))

# ─── Load Bot Configuration ───────────────────────────────────────────────────
with open(CONFIG_PATH, "r") as f:
    base_cfg = json.load(f)

TOKEN               = base_cfg["token"]
DEFAULT_CHANNEL     = int(base_cfg.get("default_channel_id", 0))
BOT_LOGS_CHANNEL    = int(base_cfg.get("bot_logs_channel_id", 0))
ADMIN_USER_ID       = int(base_cfg.get("admin_user_id", 0))
TIMEZONE            = base_cfg.get("timezone", "UTC")

# ─── Discord Client & Scheduler Setup ────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


# ─── User ID List Helpers ────────────────────────────────────────────────────
def load_users_id_list():
    """Read and return the list of users from disk, or empty list if missing."""
    if not os.path.isfile(USERS_ID_LIST_PATH):
        return []
    with open(USERS_ID_LIST_PATH, "r") as f:
        cfg = json.load(f)
    return cfg.get("users", [])

def save_users_id_list(users):
    """Write the current users list back to disk."""
    with open(USERS_ID_LIST_PATH, "w") as f:
        json.dump({"users": users}, f, indent=4)

def reload_users():
    """Reload the in-memory users list from disk."""
    global users_id_list
    try:
        users_id_list = load_users_id_list()
    except Exception:
        users_id_list = []

# Initialize users list on startup
users_id_list = load_users_id_list()


# ─── Job Helpers ─────────────────────────────────────────────────────────────
def load_jobs():
    """Read and return the list of scheduled jobs from disk, or empty list if missing."""
    if not os.path.isfile(SCHEDULER_PATH):
        return []
    with open(SCHEDULER_PATH, "r") as f:
        cfg = json.load(f)
    return cfg.get("jobs", [])

def save_jobs(jobs):
    """Write the current jobs list back to disk."""
    with open(SCHEDULER_PATH, "w") as f:
        json.dump({"jobs": jobs}, f, indent=4)

# In-memory jobs list
jobs_list = load_jobs()


# ─── Scheduling Logic ─────────────────────────────────────────────────────────
async def send_scheduled_message(user_id: int, message: str):
    """Fetch the user and DM them the scheduled message."""
    user = await client.fetch_user(user_id)
    information = f"Scheduled message for {user.name} (ID: {user_id})"
    if not user:
        return
    try:
        await user.send(f"📅 {information}\n\n{message}")
        if BOT_LOGS_CHANNEL:
            log_ch = client.get_channel(BOT_LOGS_CHANNEL)
            if log_ch:
                await log_ch.send(f"📮 Sent scheduled message to {user.name} (ID: {user_id}).")
    except Exception:
        pass  # Silently ignore send failures

def add_job_to_scheduler(job):
    """Add a single job to the APScheduler instance."""
    trigger = CronTrigger.from_crontab(job["cron"], timezone=TIMEZONE)
    scheduler.add_job(
        send_scheduled_message,
        trigger=trigger,
        args=[int(job["user_id"]), job["message"]],
        id=job["id"],
        replace_existing=True
    )

def load_scheduler_and_reschedule():
    """Reload all jobs from disk and reschedule them."""
    try:
        with open(SCHEDULER_PATH, "r") as f:
            cfg = json.load(f)
        scheduler.remove_all_jobs()
        for job in cfg.get("jobs", []):
            add_job_to_scheduler(job)
    except Exception:
        pass  # On error, skip reload


# ─── Watchdog Handler ─────────────────────────────────────────────────────────
class SchedulerChangeHandler(FileSystemEventHandler):
    """Watches config files and triggers reloads on change."""
    def __init__(self, loop):
        super().__init__()
        self.loop = loop

    def process(self, event):
        path = event.src_path
        if path.endswith(SCHEDULER_PATH):
            self.loop.call_soon_threadsafe(
                asyncio.create_task,
                asyncio.to_thread(load_scheduler_and_reschedule)
            )
        elif path.endswith(USERS_ID_LIST_PATH):
            self.loop.call_soon_threadsafe(
                asyncio.create_task,
                asyncio.to_thread(reload_users)
            )

    on_modified = process
    on_created  = process
    on_moved    = process


# ─── Utility ─────────────────────────────────────────────────────────────────
def unique_job_id(user_id):
    """Generate a simple unique job ID based on user and timestamp."""
    import time
    return f"user{user_id}_{int(time.time())}"


# ─── Discord Event Handlers ──────────────────────────────────────────────────
@client.event
async def on_ready():
    """Called when the bot logs in and is ready."""
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()

    # Optional startup ping
    if DEFAULT_CHANNEL:
        ch = client.get_channel(DEFAULT_CHANNEL)
        if ch:
            await ch.send("🤖 Bot is now online!")

    # Schedule existing jobs
    load_scheduler_and_reschedule()
    scheduler.start()

    # Start watching both JSON files for live reloads
    observer = Observer()
    handler  = SchedulerChangeHandler(MAIN_LOOP)
    observer.schedule(handler, path=".", recursive=False)
    observer.daemon = True
    observer.start()


@client.event
async def on_message(message):
    """Handle incoming messages: DMs, user management, and scheduling commands."""
    # Ignore messages from the bot itself
    if message.author.id == client.user.id:
        return

    # ─ User List Commands ─────────────────────────────────────────────────────
    content = message.content.strip()
    if content.startswith("!users"):
        if not users_id_list:
            await message.channel.send("No users in the list.")
        else:
            lines = [f"{i+1}. {u['name']} (ID: {u['id']})"
                     for i, u in enumerate(users_id_list)]
            await message.channel.send("**User ID List:**\n" + "\n".join(lines))
        return

    if content.startswith("!addUser"):
        uid = message.author.id
        if uid not in {u["id"] for u in users_id_list}:
            users_id_list.append({"id": uid, "name": str(message.author)})
            save_users_id_list(users_id_list)
            await message.channel.send(f"Added {message.author} to the user list.")
        else:
            await message.channel.send("You are already in the list.")
        return

    if content.startswith("!removeUser"):
        uid = message.author.id
        if uid in {u["id"] for u in users_id_list}:
            users_id_list[:] = [u for u in users_id_list if u["id"] != uid]
            save_users_id_list(users_id_list)
            await message.channel.send(f"Removed {message.author} from the user list.")
        else:
            await message.channel.send("You are not in the list.")
        return

    # ─ Scheduling Command ─────────────────────────────────────────────────────
    if content.startswith("!schedule"):
        parts = content.split()
        # Need at least: command + 5 cron tokens + 1+ message tokens + user_id
        if len(parts) < 8:
            return await message.channel.send(
                "Usage: `!schedule <cron> <message> <user_id>`\n"
                "Example: `!schedule 0 9 * * * Good morning! 123456789012345678`"
            )

        # Extract cron (first 5 tokens) and target user ID (last token)
        cron_expr = " ".join(parts[1:6])
        try:
            target_user_id = int(parts[-1])
        except ValueError:
            return await message.channel.send("Invalid user ID; must be numeric.")

        # Join the message text between cron and user_id
        msg_text = " ".join(parts[6:-1])

        # Build and schedule the job
        job = {
            "id":        unique_job_id(message.author.id),
            "cron":      cron_expr,
            "user_id":   target_user_id,
            "message":   msg_text
        }
        jobs_list.append(job)
        add_job_to_scheduler(job)
        save_jobs(jobs_list)

        await message.channel.send(
            f"Scheduled! I will DM <@{target_user_id}> with:\n`{msg_text}`\nat `{cron_expr}`"
        )
        return

    # ─ Answer Text Command ─────────────────────────────────────────────────────
    if content.startswith("!answerText"):
        parts = content.split()
        if len(parts) < 3:
            return await message.channel.send(
                "Usage: `!answerText <text> <user_id>`\n"
                "Example: `!answerText Hello there! 123456789012345678`"
            )

        # Extract the answer text and the target user ID
        answer_text    = " ".join(parts[1:-1])
        try:
            target_user_id = int(parts[-1])
        except ValueError:
            return await message.channel.send("Invalid user ID; must be numeric.")

        # Check the ID is in your list
        if target_user_id not in {u["id"] for u in users_id_list}:
            return await message.channel.send("User not found in the list.")

        # **Fetch** the user object, then send
        try:
            user = await client.fetch_user(target_user_id)
            await user.send(f"Message from {message.author.name}: {answer_text}")
            await message.channel.send(f"✅ Sent your message to {user.name}.")
        except Exception as e:
            await message.channel.send(f"❌ Could not send DM: {e}")
    # ─ Help Command ───────────────────────────────────────────────────────────
    if content.startswith("!help"):
        help_text = (
            "`!schedule <cron> <message> <user_id>` - Schedule a DM.\n"
            " !answerText <text> <user_id>- Set the bot's answer text.\n"                
            "`!users` - Show user list.\n"
            "`!addUser` - Add yourself to the user list.\n"
            "`!removeUser` - Remove yourself from the user list.\n"
        )
        await message.channel.send(help_text)
        return


# ─── Bot Entry Point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    client.run(TOKEN)

