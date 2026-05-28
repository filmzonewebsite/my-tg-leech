import os
import sys
import time
import asyncio
import aria2p
import shutil
from pyrogram import Client

# ==================== CONFIGS ====================
API_ID = 24071415
API_HASH = "ඔයාගේ_ඇත්තම_API_HASH_එක_මෙතනට_දාන්න"
BOT_TOKEN = "ඔයාගේ_ඇත්තම_BOT_TOKEN_එක_මෙතනට_දාන්න"
# =================================================

TORRENT_FILE_PATH = "download.torrent"
CHAT_ID = os.environ.get("CHAT_ID")

if not os.path.exists(TORRENT_FILE_PATH):
    print("❌ Torrent file not found!")
    sys.exit(1)

app = Client("github_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))

def get_progress_bar(percentage):
    completed_blocks = int(percentage / 10)
    return "█" * completed_blocks + "░" * (10 - completed_blocks)

async def upload_progress(current, total, reply_msg, start_time):
    now = time.time()
    if not hasattr(upload_progress, "last_update"):
        upload_progress.last_update = 0
    if now - upload_progress.last_update < 5:
        return
    upload_progress.last_update = now
    
    percentage = (current / total) * 100
    bar = get_progress_bar(percentage)
    elapsed = now - start_time
    speed = current / elapsed if elapsed > 0 else 0
    speed_str = f"{speed / (1024*1024):.2f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.2f} KB/s"
    
    try:
        await reply_msg.edit(f"⬆️ **Uploading to Telegram...**\n\n📊 **Progress:** [{bar}] {percentage:.1f}%\n⚡ **Speed:** {speed_str}")
    except:
        pass

async def main():
    async with app:
        chat_id = int(CHAT_ID) if CHAT_ID else "me"
        status_msg = await app.send_message(chat_id, "⚡ **GitHub Server Active! Starting Torrent Download...**")
        
        try:
            download = aria2.add_torrent(TORRENT_FILE_PATH)
            gid = download.gid
            
            while True:
                await asyncio.sleep(4)
                download = aria2.get_download(gid)
                
                if download.is_complete:
                    await status_msg.edit("✅ **Download Complete! Uploading to Telegram...**")
                    break
                elif download.has_failed:
                    await status_msg.edit("❌ **Aria2 Torrent Download Failed!**")
                    return
                else:
                    pct = download.progress
                    bar = get_progress_bar(pct)
                    msg = f"⏳ **Downloading via GitHub...**\n\n📝 **Name:** `{download.name}`\n📦 **Size:** {download.total_length_string()}\n📊 **Progress:** [{bar}] {pct:.1f}%\n⚡ **Speed:** {download.download_speed_string()}"
                    try: await status_msg.edit(msg)
                    except: pass
            
            file_path = download.files[0].path
            base_dir = os.path.dirname(file_path)
            actual_path = file_path if os.path.exists(file_path) else base_dir
            
            if os.path.exists(actual_path):
                start_time = time.time()
                if os.path.isdir(actual_path):
                    files = [os.path.join(actual_path, f) for f in os.listdir(actual_path) if os.path.isfile(os.path.join(actual_path, f))]
                    if files:
                        largest_file = max(files, key=os.path.getsize)
                        await app.send_document(chat_id, document=largest_file, caption=f"🔥 **File:** `{download.name}`", progress=upload_progress, progress_args=(status_msg, start_time))
                else:
                    await app.send_document(chat_id, document=actual_path, caption=f"🔥 **File:** `{download.name}`", progress=upload_progress, progress_args=(status_msg, start_time))
                
                await status_msg.delete()
                print("✅ Done!")
                
        except Exception as e:
            await app.send_message(chat_id, f"❌ **Error:** {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
