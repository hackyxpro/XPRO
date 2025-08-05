import telebot
import os
import json
from uuid import uuid4
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# === CONFIG ===
BOT_TOKEN = "7853004642:AAFreF83_Pc5lBRE2MPF3rhUC_KGJpCgZsY"
ADMIN_ID = 6684769651
CHANNEL_URL = "https://t.me/+iOn8K6DHhMk3ODA1"
FILES_PATH = "files.json"
USERS_PATH = "users.json"

bot = telebot.TeleBot(BOT_TOKEN)

# === UTIL FUNCTIONS (storage, delete, export, etc.) ===
def load_json(path):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump({}, f)
    with open(path, 'r') as f:
        return json.load(f)
def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
def add_user(uid):
    users = load_json(USERS_PATH)
    if str(uid) not in users:
        users[str(uid)] = True
        save_json(USERS_PATH, users)
def get_user_count():
    return len(load_json(USERS_PATH))
def save_file(ftype, fid, owner, cap):
    db = load_json(FILES_PATH)
    key = str(uuid4())
    db[key] = {"type": ftype, "file_id": fid, "owner": owner, "caption": cap or ""}
    save_json(FILES_PATH, db)
    return key
def get_file(key): return load_json(FILES_PATH).get(key)
def delete_user_file(owner, key):
    db = load_json(FILES_PATH)
    if key in db and db[key]["owner"] == owner:
        del db[key]; save_json(FILES_PATH, db); return True
    return False
def get_user_files(uid):
    db = load_json(FILES_PATH)
    return {k: v for k, v in db.items() if v["owner"] == uid}
def join_markup():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
    return kb
def admin_markup():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("📣 Broadcast", callback_data="broadcast"),
           InlineKeyboardButton("👥 Users", callback_data="users"),
           InlineKeyboardButton("📤 Export", callback_data="export"))
    return kb

# === BOT HANDLERS ===
@bot.message_handler(commands=["start"])
def cmd_start(m):
    add_user(m.from_user.id)
    args = m.text.split()
    if len(args) > 1 and args[1].startswith("dl_"):
        key = args[1][3:]; f = get_file(key)
        if f:
            try:
                cap = f.get("caption", "")
                if f["type"]=="photo": bot.send_photo(m.chat.id, f["file_id"], caption=cap)
                elif f["type"]=="video": bot.send_video(m.chat.id, f["file_id"], caption=cap)
                else: bot.send_document(m.chat.id, f["file_id"], caption=cap)
            except: bot.send_message(m.chat.id, "❌ Failed to send")
        else: bot.send_message(m.chat.id, "❌ File not found")
        return
    bot.send_message(m.chat.id,
        "👋 Welcome!\nSend any media to get a share link.\nUse /myfiles for list.",
        reply_markup=join_markup())

@bot.message_handler(commands=["myfiles"])
def cmd_myfiles(m):
    lst = get_user_files(m.from_user.id)
    if not lst:
        bot.send_message(m.chat.id, "📭 No uploads yet.")
    else:
        txt = "🗂 Your files:\n"
        for k,v in lst.items():
            preview = f"📝 {v['caption'][:30]}..." if v['caption'] else "📁 No title"
            txt += f"{preview}\n/start dl_{k}\n/delete {k}\n\n"
        bot.send_message(m.chat.id, txt)

@bot.message_handler(commands=["delete"])
def cmd_delete(m):
    parts = m.text.split()
    if len(parts)!=2:
        bot.send_message(m.chat.id, "Usage: /delete <file_id>")
        return
    ok = delete_user_file(m.from_user.id, parts[1])
    bot.send_message(m.chat.id,
        "✅ Deleted." if ok else "❌ Cannot delete.")

@bot.message_handler(commands=["admin"])
def cmd_admin(m):
    if m.from_user.id == ADMIN_ID:
        bot.send_message(m.chat.id, "⚙️ Admin Panel", reply_markup=admin_markup())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    if c.message.chat.id != ADMIN_ID: return
    if c.data=="broadcast":
        msg = bot.send_message(c.message.chat.id, "📣 Now send broadcast:")
        bot.register_next_step_handler(msg, handle_broadcast)
    elif c.data=="users":
        bot.send_message(c.message.chat.id, f"👥 {get_user_count()} users")
    elif c.data=="export":
        export_all(c.message.chat.id)

def handle_broadcast(m):
    us = load_json(USERS_PATH); cnt = 0
    for uid in us:
        try:
            if m.content_type=="text":
                bot.send_message(uid, m.text)
            elif m.content_type=="photo":
                bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption or "")
            elif m.content_type=="video":
                bot.send_video(uid, m.video.file_id, caption=m.caption or "")
            elif m.content_type=="document":
                bot.send_document(uid, m.document.file_id, caption=m.caption or "")
            cnt+=1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Sent to {cnt} users")

def export_all(admin_chat):
    us = load_json(USERS_PATH); fs = load_json(FILES_PATH)
    with open("users_export.txt","w") as f:
        f.write(f"Users: {len(us)}\n"+ "\n".join(us.keys()))
    lines=[]
    for k,v in fs.items():
        cap=v.get("caption","").replace("\n"," ")[:50]
        link=f"https://t.me/{bot.get_me().username}?start=dl_{k}"
        lines.append(f"ID:{k} Type:{v['type']} Owner:{v['owner']} Cap:{cap} Link:{link}")
    with open("files_export.txt","w", encoding="utf8") as f:
        f.write("\n".join(lines))
    bot.send_document(admin_chat, open("users_export.txt","rb"), caption="Users list")
    bot.send_document(admin_chat, open("files_export.txt","rb"), caption="Files list")

@bot.message_handler(content_types=["photo","video","document"])
def handle_media(m):
    add_user(m.from_user.id)
    if m.photo:
        fid = m.photo[-1].file_id; ftype="photo"
    elif m.video:
        fid = m.video.file_id; ftype="video"
    else:
        fid = m.document.file_id; ftype="document"
    cap = m.caption or ""
    key = save_file(ftype, fid, m.from_user.id, cap)
    bot.reply_to(m, f"✅ Saved!\nLink: https://t.me/{bot.get_me().username}?start=dl_{key}")

# === KEEP‑ALIVE WEB SERVER ===
app = Flask('')
@app.route('/')
def home(): return "I'm alive!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# === START BOT ===
bot.infinity_polling()
