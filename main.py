from rubpy.bot import BotClient, filters
from rubpy.bot.models import Update
import sys
import os

sys.path.insert(0, "src")

import functions

bot = BotClient('BBJHFF0JWMVEHNITSEGCDTEAJXGLGDUXNLQICROYLFZIZEZQAEAIGJHIAZIYAIQH')

allow_users = [
    'u0JhYdw00da5ebb60d1d224b2d259c72',
]

@bot.on_update(filters.commands('start'))
async def handle_start(c: BotClient, update: Update):
    if update.new_message:
        if update.new_message.sender_id in allow_users: # Checking if the users is one of the allowed users
            await update.reply("Hello And Welcome to this Bot\n\nAvailable Commands\n/dl [link] -> Download a Url\n/webpage [link] -> Save a webpage and send the file")

@bot.on_update(filters.commands('dl'))
async def handle_dl(c: BotClient, update: Update):
    if update.new_message:
        if update.new_message.sender_id in allow_users: # Checking if the users is one of the allowed users
            await update.reply("We recieve your requests and gonna start trying to download it")
            
            url = update.new_message.text.replace("/dl ","")
            download_path = functions.download_file(url)
            
            await update.reply("Downloading Finished, Start Uploading")

            try:
                code = functions.rar_compress(filepath=download_path,output_dir=download_path+"-rar-dir")
            except:
                await update.reply(str(sys.exc_info()[0])[:1024])

            rar_files = os.listdir(download_path+"-rar-dir")
            
            for file in rar_files:
                print(f"Uploading... {file}")
                message_id = await bot.send_file(chat_id=update.chat_id,file=f"{download_path}-rar-dir/{file}",text="Text")
                print(f"{file} Uploaded.")
                os.remove(f"{download_path}-rar-dir/{file}")
            os.rmdir(f"{download_path}-rar-dir")

@bot.on_update(filters.commands('webpage'))
async def handle_webpage(c: BotClient, update: Update):
    if update.new_message:
        if update.new_message.sender_id in allow_users: # Checking if the users is one of the allowed users
            await update.reply("We recieve your requests and gonna start trying to archive it")
            
            url = update.new_message.text.replace("/webpage ","")
            download_path = functions.save_single_html(url)
            
            await update.reply("Archiving Finished, Start Uploading")

            try:
                code = functions.rar_compress(filepath=download_path,output_dir=download_path+"-rar-dir")
            except:
                await update.reply(str(sys.exc_info()[0])[:1024])

            rar_files = os.listdir(download_path+"-rar-dir")
            
            for file in rar_files:
                print(f"Uploading... {file}")
                message_id = await bot.send_file(chat_id=update.chat_id,file=f"{download_path}-rar-dir/{file}",text="Text")
                print(f"{file} Uploaded.")
                os.remove(f"{download_path}-rar-dir/{file}")
            os.rmdir(f"{download_path}-rar-dir")

if __name__ == "__main__":
    bot.run()