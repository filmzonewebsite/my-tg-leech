import os
import sys
import time
import asyncio
import aria2p
import requests
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ==================== CONFIGS ====================
BOT_TOKEN = "8723336349:AAGQo9f-7UeRECnee2FwtDo1RzV_zjZnZZY"
GH_TOKEN = "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"
GH_REPO = "filmzonewebsite/my-tg-leech"
# =================================================

TORRENT_FILE_PATH = "download.torrent"
CHAT_ID = os.environ.get("CHAT_ID")
RUNNING_IN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"

bot = Bot(token=BOT_TOKEN)

def get_progress_bar(percentage):
    pct = min(max(percentage, 0), 100)
    completed_blocks = int(pct / 10)
    return "█" * completed_blocks + "░" * (10 - completed_blocks)

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

async def start_cmd(update, context):
    await update.message.reply_text("👋 මට Torrent Magnet ලින්ක් එකක් එවන්න, නැත්නම් .torrent ෆයිල් එකක් අප්ලෝඩ් කරන්න!")

async def handle_message(update, context):
    m = update.message
    text = m.text or ""
    
    if text.startswith("magnet:") or text.startswith("http"):
        reply = await m.reply_text("🔄 GitHub Server එක පණගන්වමින්... කරුණාකර රැඳී සිටින්න...")
        if trigger_github_action(m.chat_id, text):
            await reply.edit_text("🚀 GitHub Server එක සාර්ථකව පණගැන්වුණා! ටික වෙලාවකින් ඩවුන්ලෝඩ් එක පටන් ගනීවි.")
        else:
            await reply.edit_text("❌ GitHub Server එක පණගන්වන්න බැරි වුණා. Tokens පරීක්ෂා කරන්න.")

async def handle_document(update, context):
    m = update.message
    if m.document and m.document.file_name.endswith(".torrent"):
        reply = await m.reply_text("📦 Torrent ෆයිල් එක හඳුනාගත්තා! GitHub සර්වර් එක ලෑස්ති කරමින්...")
        file = await context.bot.get_file(m.document.file_id)
        file_bytes = await file.download_as_bytearray()
        torrent_content = file_bytes.hex()
        
        if trigger_github_action(m.chat_id, f"hex:{torrent_content}"):
            await reply.edit_text("🚀 GitHub Server එක පණගැන්වුණා! ටොරන්ට් ෆයිල් එක බාන්න සූදානම් කරමින් පවතී...")
        else:
            await reply.edit_text("❌ Server එක පණගැන්වීම අසාර්ථකයි.")

# --- GitHub Server එක ඇතුළේ දිවෙන කොටස ---
async def run_github_download():
    aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))
    chat_id = int(CHAT_ID)
    status_msg = await bot.send_message(chat_id, "⚡ **GitHub Server Active! Starting Torrent Leech...**")
    
    try:
        await asyncio.sleep(3)
        downloads = aria2.get_downloads()
        if not downloads:
            await bot.edit_message_text("❌ Torrent එක ඇතුළත් කිරීමට නොහැකි වුණා!", chat_id, status_msg.message_id)
            return
        download = downloads[0]
        gid = download.gid
        
        last_edit_time = 0
        while True:
            await asyncio.sleep(4)
            download = aria2.get_download(gid)
            if download.is_complete:
                await bot.edit_message_text("✅ **Download Complete! Uploading to Telegram...**", chat_id, status_msg.message_id)
                break
            elif download.has_failed:
                await bot.edit_message_text("❌ **Aria2 Download Failed!**", chat_id, status_msg.message_id)
                return
            else:
                now = time.time()
                if now - last_edit_time >= 5:
                    pct = download.progress
                    bar = get_progress_bar(pct)
                    msg = f"⏳ **Downloading via GitHub...**\n\n📝 **Name:** `{download.name}`\n📦 **Size:** {download.total_length_string()}\n📊 **Progress:** [{bar}] {pct:.1f}%\n⚡ **Speed:** {download.download_speed_string()}"
                    try:
                        await bot.edit_message_text(msg, chat_id, status_msg.message_id)
                        last_edit_time = now
                    except: pass
        
        file_path = download.files[0].path
        actual_path = file_path if os.path.exists(file_path) else os.path.dirname(file_path)
        
        if os.path.exists(actual_path):
            if os.path.isdir(actual_path):
                files = [os.path.join(actual_path, f) for f in os.listdir(actual_path) if os.path.isfile(os.path.join(actual_path, f))]
                actual_path = max(files, key=os.path.getsize)
            
            with open(actual_path, 'rb') as doc:
                await bot.send_document(chat_id, document=doc, caption=f"🔥 **File:** `{download.name}`")
            await bot.delete_message(chat_id, status_msg.message_id)
            
    except Exception as e:
        await bot.send_message(chat_id, f"❌ **Error:** {str(e)}")

if __name__ == "__main__":
    if RUNNING_IN_GITHUB:
        asyncio.run(run_github_download())
    else:
        print("🤖 Bot is listening to Telegram Messages...")
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        app.run_polling()
