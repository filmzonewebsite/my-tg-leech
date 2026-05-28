import os
import sys
import time
import asyncio
import aria2p
from pyrogram import Client

# GitHub Secrets වලින් දත්ත ලබා ගැනීම
API_ID = int(os.environ.get("24071415"))
API_HASH = os.environ.get("4b584c0d66245e9a467d5e7aa0535cfd")
BOT_TOKEN = os.environ.get("8723336349:AAGQo9f-7UeRECnee2FwtDo1RzV_zjZnZZY")

# Telegram එකෙන් එවපු Torrent File එකේ Path එක (GitHub Action එකෙන් මේකට දත්ත එවයි)
TORRENT_FILE_PATH = "download.torrent"
CHAT_ID = os.environ.get("CHAT_ID") # මේක auto පිරවේවි

if not os.path.exists(TORRENT_FILE_PATH):
    print("❌ Torrent file not found!")
    sys.exit(1)

app = Client("github_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Connect to Aria2
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
        print(f"Uploading: {percentage:.1f}% | Speed: {speed_str}")
    except:
        pass

async def main():
    async with app:
        # 1. මුලින්ම Telegram එකට status එකක් යවනවා වැඩේ පටන් ගත්තා කියලා
        # මෙතනදි ඔයාට මැසේජ් එකක් එවන්න Chat ID එක Actions වලින් ගන්නවා
        chat_id = int(CHAT_ID) if CHAT_ID else "me"
        status_msg = await app.send_message(chat_id, "⚡ **GitHub Server Active! Starting Torrent Download...**")
        
        try:
            # Torrent එක Aria2 එකට දීම
            download = aria2.add_torrent(TORRENT_FILE_PATH)
            gid = download.gid
            
            # Download වෙනකන් බලා සිටීම (Loop)
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
                    msg = f"⏳ **Downloading via GitHub...**\n\n📦 **Size:** {download.total_length_string()}\n📊 **Progress:** [{bar}] {pct:.1f}%\n⚡ **Speed:** {download.download_speed_string()}"
                    try: await status_msg.edit(msg)
                    except: pass
            
            # Uploading Process
            file_path = download.files[0].path
            base_dir = os.path.dirname(file_path)
            actual_path = file_path if os.path.exists(file_path) else base_dir
            
            if os.path.exists(actual_path):
                start_time = time.time()
                if os.path.isdir(actual_path):
                    files = [os.path.join(actual_path, f) for f in os.listdir(actual_path) if os.path.isfile(os.path.join(actual_path, f))]
                    if files:
                        largest_file = max(files, key=os.path.getsize)
                        await app.send_document(chat_id, document=largest_file, caption=f"🔥 **Here is your file:**\n`{download.name}`")
                else:
                    await app.send_document(chat_id, document=actual_path, caption=f"🔥 **Here is your file:**\n`{download.name}`")
                
                await status_msg.delete()
                print("✅ Everything Done Successfully!")
                
        except Exception as e:
            await app.send_message(chat_id, f"❌ **Error Occurred:** {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
