import telebot
from telebot import types
from datetime import datetime, timedelta

API_TOKEN = '****' # токен тг
bot = telebot.TeleBot(API_TOKEN)
ADMIN_IDS = [123456789]  # список админов(примеры id)


active_conversations = {}  
message_pairs = {} 

def log(action, details):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {action}: {details}")

def create_reply_keyboard(conversation_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_{conversation_id}"))
    return markup

@bot.message_handler(commands=['start'])
def start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    log("START", f"User {user_id} (@{message.from_user.username})")

    if len(args) > 1 and args[1].isdigit():
        partner_id = int(args[1])
        active_conversations[user_id] = {
            "partner_id": partner_id,
            "expires": datetime.now() + timedelta(hours=24)
        }
        active_conversations[partner_id] = {
            "partner_id": user_id,
            "expires": datetime.now() + timedelta(hours=24)
        }
        
        log("CONVERSATION_STARTED", f"Between {user_id} and {partner_id}")
        bot.send_message(user_id, "✍️ Напишите сообщение:", parse_mode="Markdown")
    else:
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        log("LINK_GENERATED", f"For {user_id}: {link}")
        bot.send_message(
            user_id,
            f"🔗 Ваша ссылка для анонимных сообщений:\n\n"
            f"[Нажмите здесь]({link}) или отправьте друзьям:\n"
            f"`{link}`",
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda message: True)
def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in active_conversations:
        partner_id = active_conversations[user_id]["partner_id"]
        
        sent_msg = bot.send_message(
            partner_id,
            f"📨 Анонимное сообщение:\n\n{message.text}",
            parse_mode="Markdown",
            reply_markup=create_reply_keyboard(user_id)
        )
        
        message_pairs[sent_msg.message_id] = {
            "original_sender": user_id,
            "original_receiver": partner_id
        }
        
        log("MESSAGE_SENT", 
            f"From {user_id} to {partner_id} | "
            f"MsgID: {sent_msg.message_id}")
        
        # Для админов
        if partner_id in ADMIN_IDS:
            bot.send_message(
                partner_id,
                f"👁️ Админ: сообщение от @{message.from_user.username}:\n{message.text}",
                parse_mode="Markdown"
            )
        
        bot.send_message(user_id, "✅ Сообщение отправлено!", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def handle_reply(call: types.CallbackQuery):
    try:
        original_sender_id = int(call.data.split('_')[1])
        current_user_id = call.from_user.id
        
        if original_sender_id in active_conversations:
            active_conversations[current_user_id] = {
                "partner_id": original_sender_id,
                "expires": datetime.now() + timedelta(hours=24)
            }
            
            log("REPLY_INITIATED", 
                f"User {current_user_id} replying to {original_sender_id}")
            
            bot.send_message(
                current_user_id,
                "✍️ Напишите ответ:",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Готово к ответу")
        else:
            log("REPLY_FAILED", "Conversation expired")
            bot.answer_callback_query(call.id, "❌ Диалог завершен")
    except Exception as e:
        log("CALLBACK_ERROR", f"Error: {str(e)}")
        bot.answer_callback_query(call.id, "❌ Ошибка")
2
def cleanup_expired():
    now = datetime.now()
    expired = [uid for uid, conv in active_conversations.items() if conv["expires"] < now]
    for uid in expired:
        del active_conversations[uid]
    if expired:
        log("CLEANUP", f"Removed {len(expired)} expired conversations")

if __name__ == "__main__":
    print("=== Бот запущен ===")
    print(f"Админы: {ADMIN_IDS}")
    print("=== Логи ===")
    
    import threading
    def schedule_cleanup():
        while True:
            cleanup_expired()
            threading.Event().wait(3600) 
    
    cleanup_thread = threading.Thread(target=schedule_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    bot.polling()
