import os
import sys
import time
import asyncio
import aria2p
import shutil
import json
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# ==================== CONFIGS ====================
API_ID = 24071415
API_HASH = "4b584c0d66245e9a467d5e7aa0535cfd"
BOT_TOKEN = "8723336349:AAGQo9f-7UeRECnee2FwtDo1RzV_zjZnZZY"
GH_TOKEN = "ඔයා_පියවර_1දී_ගත්තු_ghp_ලින්ක්_එක"
GH_REPO = "ඔයාගේ_github_username_එක/repository_නම" # උදා: sadesha/my-tg-leech
# =================================================

TORRENT_FILE_PATH = "download.torrent"
CHAT_ID = os.environ.get("CHAT_ID")
RUNNING_IN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"

app = Client("github_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def get_progress_bar(percentage):
    return "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))

# GitHub Workflow එක ටෙලිග්‍රෑම් එකෙන් active කරන Function එක
def trigger_github_action(chat_id, torrent_data):
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/torrent.yml/dispatches"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "ref": "main",
        "inputs": {
            "chat_id": str(chat_id),
            "torrent_url": torrent_data
        }
    }
    res = requests.post(url, headers=headers, json=data)
    return res.status_code == 204

async def upload_progress(current, total, reply_msg, start_time):
    now = time.time()
    if not hasattr(upload_progress, "last_update"): upload_progress.last_update = 0
    if now - upload_progress.last_update < 5: return
    upload_progress.last_update = now
    
    pct = (current / total) * 100
    bar = get_progress_bar(pct)
    elapsed = now - start_time
    speed = current / elapsed if elapsed > 0 else 0
    speed_str = f"{speed / (1024*1024):.2f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.2f} KB/s"
    try: await reply_msg.edit(f"⬆️ **Uploading to Telegram...**\n\n📊 **Progress:** [{bar}] {pct:.1f}%\n⚡ **Speed:** {speed_str}")
    except: pass

# --- ටෙලිග්‍රෑම් එකෙන් මැසේජ් බාරගන්නා කොටස ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(c, m):
    await m.reply_text("👋 මට Torrent Magnet ලින්ක් එකක් එවන්න, නැත්නම් .torrent ෆයිල් එකක් අප්ලෝඩ් කරන්න!")

@app.on_message(filters.text & filters.private)
async def handle_text(c, m):
    if m.text.startswith("magnet:") or m.text.startswith("http"):
        reply = await m.reply_text("🔄 GitHub Server එක පණගන්වමින්... කරුණාකර රැඳී සිටින්න...")
        if trigger_github_action(m.chat.id, m.text):
            await reply.edit("🚀 GitHub Server එක සාර්ථකව පණගැන්වුණා! ටික වෙලාවකින් ඩවුන්ලෝඩ් එක පටන් ගනීවි.")
        else:
            await reply.edit("❌ GitHub Server එක පණගන්වන්න බැරි වුණා. Configs පරීක්ෂා කරන්න.")

@app.on_message(filters.document & filters.private)
async def handle_doc(c, m):
    if m.document.file_name.endswith(".torrent"):
        reply = await m.reply_text("📦 Torrent ෆයිල් එක හඳුනාගත්තා! GitHub සර්වර් එක ලෑස්ති කරමින්...")
        # පහසුව සඳහා ටොරන්ට් ෆයිල් එකේ දත්ත කෙලින්ම text එකක් විදිහට පාස් කරමු
        file_bytes = await m.download(in_memory=True)
        torrent_content = file_bytes.getvalue().hex() # hex එකක් විදිහට යවමු
        
        if trigger_github_action(m.chat.id, f"hex:{torrent_content}"):
            await reply.edit("🚀 GitHub Server එක පණගැන්වුණා! ටොරන්ට් ෆයිල් එක බාන්න සූදානම් කරමින් පවතී...")
        else:
            await reply.edit("❌ Server එක පණගැන්වීම අසාර්ථකයි.")

# --- GitHub එක ඇතුළේ ඩවුන්ලෝඩ් එක සිද්ධ වෙන කොටස ---
async def run_github_download():
    aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))
    async with app:
        chat_id = int(CHAT_ID)
        status_msg = await app.send_message(chat_id, "⚡ **GitHub Server Active! Starting Torrent Leech...**")
        
        try:
            download = aria2.get_all_downloads()[0]
            gid = download.gid
            
            while True:
                await asyncio.sleep(4)
                download = aria2.get_download(gid)
                if download.is_complete:
                    await status_msg.edit("✅ **Download Complete! Uploading to Telegram...**")
                    break
                elif download.has_failed:
                    await status_msg.edit("❌ **Aria2 Download Failed!**")
                    return
                else:
                    pct = download.progress
                    bar = get_progress_bar(pct)
                    msg = f"⏳ **Downloading via GitHub...**\n\n📝 **Name:** `{download.name}`\n📦 **Size:** {download.total_length_string()}\n📊 **Progress:** [{bar}] {pct:.1f}%\n⚡ **Speed:** {download.download_speed_string()}"
                    try: await status_msg.edit(msg)
                    except: pass
            
            file_path = download.files[0].path
            actual_path = file_path if os.path.exists(file_path) else os.path.dirname(file_path)
            
            if os.path.exists(actual_path):
                start_time = time.time()
                if os.path.isdir(actual_path):
                    files = [os.path.join(actual_path, f) for f in os.listdir(actual_path) if os.path.isfile(os.path.join(actual_path, f))]
                    largest_file = max(files, key=os.path.getsize)
                    await app.send_document(chat_id, document=largest_file, caption=f"🔥 **File:** `{download.name}`", progress=upload_progress, progress_args=(status_msg, start_time))
                else:
                    await app.send_document(chat_id, document=actual_path, caption=f"🔥 **File:** `{download.name}`", progress=upload_progress, progress_args=(status_msg, start_time))
                await status_msg.delete()
        except Exception as e:
            await app.send_message(chat_id, f"❌ **Error:** {str(e)}")

if __name__ == "__main__":
    if RUNNING_IN_GITHUB:
        asyncio.run(run_github_download())
    else:
        print("🤖 Bot is listening to Telegram Messages locally/externally...")
        app.run()
        
