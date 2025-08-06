import json, os, requests, logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ------------ CONFIG ------------
BOT_TOKEN = "7853004642:AAFrR1gGwlxdn7m2VNA3UhVBnrIdBrfatYQ"
API_URL = "https://numinfoapi.zerovault.workers.dev/search/mobile?value="
ADMIN_USERNAME = "@XPRO_BEASTY_BOT"
ADMINS = [6684769651]
BOT_USERNAME = "OSINT_XPRO_BOT"
USER_DATA_FILE = "users.json"

# ------------ LOGGING ------------
logging.basicConfig(level=logging.INFO)

# ------------ INIT BOT ------------
bot = TeleBot(BOT_TOKEN)
admin_states = {}

# ------------ USER DATABASE ------------
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_user(uid, username=None, full_name=None):
    data = load_user_data()
    key = str(uid)
    if key not in data:
        data[key] = {
            "credits": 3,
            "referral": None,
            "ref_count": 0,
            "username": username or "",
            "name": full_name or "",
        }
        save_user_data(data)
    else:
        changed = False
        if username and data[key].get("username") != username:
            data[key]["username"] = username
            changed = True
        if full_name and data[key].get("name") != full_name:
            data[key]["name"] = full_name
            changed = True
        if changed:
            save_user_data(data)
    return data[key]

def update_user(uid, userinfo):
    data = load_user_data()
    data[str(uid)] = userinfo
    save_user_data(data)

# ------------ MENUS ------------
def is_admin(user_id):
    return user_id in ADMINS

def main_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📞 Lookup", callback_data="osint"),
        InlineKeyboardButton("💰 Pricing", callback_data="pricing"),
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("🎁 Refer & Earn", callback_data="refer"),
    )
    markup.add(InlineKeyboardButton("👨‍💻 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}"))
    if is_admin(user_id):
        markup.add(InlineKeyboardButton("🛠 Admin", callback_data="admin_menu"))
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔍 Find User", callback_data="admin_find_user"),
        InlineKeyboardButton("➕ Add Credits", callback_data="admin_add_credits"),
        InlineKeyboardButton("➖ Remove Credits", callback_data="admin_remove_credits"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("⬅ Back", callback_data="back_to_main"),
    )
    return markup

# ------------ START COMMAND ------------
@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username, message.from_user.full_name)
    args = message.text.strip().split()

    if len(args) > 1 and args[1].startswith("_ref_"):
        ref_id = int(args[1].replace("_ref_", ""))
        if user["referral"] is None and ref_id != user_id:
            user["referral"] = ref_id
            user["credits"] += 3
            ref_user = get_user(ref_id)
            ref_user["credits"] += 3
            ref_user["ref_count"] += 1
            update_user(user_id, user)
            update_user(ref_id, ref_user)
            try:
                bot.send_message(ref_id, f"🎉 @{user['username']} joined with your referral! +3 credits.")
            except:
                pass

    bot.send_message(user_id, "Welcome to *HACKY-X-PRO*\nUse the menu below.", parse_mode="Markdown", reply_markup=main_menu(user_id))

# ------------ CALLBACK HANDLER ------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    user = get_user(user_id)

    if data == "osint":
        if user["credits"] < 1:
            bot.send_message(call.message.chat.id, "❌ You have 0 credits.")
        else:
            bot.send_message(call.message.chat.id, "📞 Send a mobile number:")

    elif data == "pricing":
        bot.send_message(call.message.chat.id, "*Credits:* 12=₹59 | 30=₹109 | 75=₹229\nContact admin to buy.", parse_mode="Markdown")

    elif data == "profile":
        msg = f"<b>Name:</b> {user['name']}\n<b>Username:</b> @{user['username']}\n<b>Credits:</b> {user['credits']}\n<b>Referrals:</b> {user['ref_count']}"
        bot.send_message(call.message.chat.id, msg, parse_mode="HTML")

    elif data == "refer":
        ref = f"https://t.me/{BOT_USERNAME}?start=_ref_{user_id}"
        bot.send_message(call.message.chat.id, f"<b>Refer link:</b> {ref}\nInvite & earn +3 credits!", parse_mode="HTML")

    elif data == "admin_menu" and is_admin(user_id):
        bot.edit_message_text("Admin Panel", call.message.chat.id, call.message.message_id, reply_markup=admin_menu())

    elif data == "back_to_main":
        bot.edit_message_text("Main Menu", call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))

    elif data == "admin_find_user":
        msg = bot.send_message(call.message.chat.id, "Send user ID or @username:")
        admin_states[user_id] = "find"
        bot.register_next_step_handler(msg, admin_find_user)

    elif data == "admin_add_credits":
        msg = bot.send_message(call.message.chat.id, "Send: user_id credits")
        admin_states[user_id] = "add"
        bot.register_next_step_handler(msg, admin_add_credits)

    elif data == "admin_remove_credits":
        msg = bot.send_message(call.message.chat.id, "Send: user_id credits")
        admin_states[user_id] = "remove"
        bot.register_next_step_handler(msg, admin_remove_credits)

    elif data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "Send broadcast message:")
        admin_states[user_id] = "broadcast"
        bot.register_next_step_handler(msg, admin_broadcast)

# ------------ ADMIN FUNCTIONS ------------
def admin_find_user(msg):
    key = msg.text.strip().lstrip("@")
    data = load_user_data()
    found = None
    if key.isdigit():
        found = data.get(key)
    else:
        for uid, u in data.items():
            if u.get("username", "") == key:
                key, found = uid, u
                break
    if found:
        bot.send_message(msg.chat.id, f"<b>User:</b> {key}\n<b>Credits:</b> {found['credits']}", parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "User not found.")
    admin_states.pop(msg.from_user.id, None)

def admin_add_credits(msg):
    try:
        uid, amt = msg.text.strip().split()
        data = load_user_data()
        data[uid]["credits"] += int(amt)
        save_user_data(data)
        bot.send_message(msg.chat.id, "✅ Added credits.")
    except:
        bot.send_message(msg.chat.id, "❌ Error.")
    admin_states.pop(msg.from_user.id, None)

def admin_remove_credits(msg):
    try:
        uid, amt = msg.text.strip().split()
        data = load_user_data()
        data[uid]["credits"] = max(0, data[uid]["credits"] - int(amt))
        save_user_data(data)
        bot.send_message(msg.chat.id, "✅ Removed credits.")
    except:
        bot.send_message(msg.chat.id, "❌ Error.")
    admin_states.pop(msg.from_user.id, None)

def admin_broadcast(msg):
    text = msg.text
    count = 0
    data = load_user_data()
    for uid in data:
        try:
            bot.send_message(int(uid), text)
            count += 1
        except:
            pass
    bot.send_message(msg.chat.id, f"✅ Broadcast sent to {count} users.")
    admin_states.pop(msg.from_user.id, None)

# ------------ HANDLE NUMBER INPUT ------------
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_number(message):
    user = get_user(message.from_user.id)
    if user["credits"] < 1:
        bot.send_message(message.chat.id, "❌ Not enough credits.")
        return
    try:
        r = requests.get(API_URL + message.text)
        result = r.text if r.status_code == 200 else "❌ API error."
    except Exception as e:
        result = f"⚠ Error: {e}"
    user["credits"] -= 1
    update_user(message.from_user.id, user)
    bot.send_message(message.chat.id, f"🔍 Info for {message.text}:\n\n{result}")

# ------------ RUN BOT SAFELY ------------
while True:
    try:
        logging.info("🤖 Bot running...")
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"❌ Crash: {e}")
