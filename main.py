import random
import sqlite3
import requests
from bs4 import BeautifulSoup
from telegram.request import HTTPXRequest
from telegram import WebAppInfo
from flask import Flask, request, jsonify
from flask_cors import CORS 
from threading import Thread

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
ADMIN_ID = 8212671849
TOKEN = "8576361861:AAHZcQ9-t38FExyq7trPDDPUwIBjYp7MGR4"

WAITING_FOR_PHONE = 0
WAITING_FOR_TX_ID = 1

MIN_AMOUNT = 20
MAX_AMOUNT = 1000

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("ludex.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    phone TEXT,
    balance INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    tx_id TEXT UNIQUE,
    amount INTEGER,
    type TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pending_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    tx_id TEXT,
    amount INTEGER
)
""")

conn.commit()

# =========================
# TELEBIRR VERIFY
# =========================

def verify_telebirr(tx_id):
    url = f"https://transactioninfo.ethiotelecom.et/receipt/{tx_id}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return tx_id in soup.get_text()

        return False

    except:
        return False

# =========================
# DATABASE HELPERS
# =========================

def user_exists(user_id):
    cursor.execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (user_id,)
    )
    return cursor.fetchone()

def create_user(user_id, phone):
    cursor.execute(
        "INSERT INTO users (telegram_id, phone, balance) VALUES (?, ?, ?)",
        (user_id, phone, 0)
    )
    conn.commit()

def get_phone(user_id):

    cursor.execute(
        "SELECT phone FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return "Unknown"    

def get_balance(user_id):
    cursor.execute(
        "SELECT balance FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return "Unknown"

def update_balance(user_id, amount):
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE telegram_id=?",
        (amount, user_id)
    )

    conn.commit()

def tx_exists(tx_id):
    cursor.execute(
        "SELECT * FROM transactions WHERE tx_id=?",
        (tx_id,)
    )

    return cursor.fetchone()

def save_transaction(user_id, tx_id, amount, tx_type, status):
    cursor.execute("""
    INSERT INTO transactions
    (telegram_id, tx_id, amount, type, status)
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        tx_id,
        amount,
        tx_type,
        status
    ))

    conn.commit()

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_exists(user_id):

        await show_main_menu(update)

        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to Ludex Games 🎮\n\n"
        "Please enter your phone number:"
    )

    return WAITING_FOR_PHONE

# =========================
# REGISTER
# =========================

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):

    phone = update.message.text.strip()
    user_id = update.effective_user.id

    if not phone.startswith("09") or len(phone) != 10:
        await update.message.reply_text(
            "❌ Invalid phone number."
        )

        return WAITING_FOR_PHONE

    create_user(user_id, phone)

    await update.message.reply_text(
        "✅ Registration successful!"
    )

    await show_main_menu(update)

    return ConversationHandler.END

# =========================
# MAIN MENU
# =========================

async def show_main_menu(update):
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", web_app=WebAppInfo(url="https://ludexwebapp1.vercel.app/"))],
        [
            InlineKeyboardButton("💰 Deposit", callback_data='deposit'),
            InlineKeyboardButton("🏧 Withdraw", callback_data='withdraw')
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data='profile'),
            InlineKeyboardButton("📜 Transactions", callback_data='history')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    target = update.message if update.message else update.callback_query.message
    
    await target.reply_photo(
        photo=open('photo_2026-05-13_16-33-49.jpg', 'rb'),
        caption="<b>Ludex Games</b>\nChoose an option:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# =========================
# PROFILE
# =========================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance = get_balance(user_id)

    await query.message.reply_text(
        f"👤 Your Profile\n\n"
        f"💰 Balance: {balance} Birr"
    )

# =========================
# DEPOSIT MENU
# =========================

async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("20", callback_data='dep_20'),
            InlineKeyboardButton("50", callback_data='dep_50'),
            InlineKeyboardButton("100", callback_data='dep_100')
        ],
        [
            InlineKeyboardButton("200", callback_data='dep_200'),
            InlineKeyboardButton("500", callback_data='dep_500')
        ],
        [
            InlineKeyboardButton("800", callback_data='dep_800'),
            InlineKeyboardButton("1000", callback_data='dep_1000')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_photo(
        photo=open("C:\\Users\\Bamlak\\telegram_game_bot\\photo_2026-05-13_16-33-49.jpg", "rb"),
        caption=(
            "💰 Deposit Menu\n\n"
            "Choose deposit amount.\n"
            "Minimum: 20 Birr\n"
            "Maximum: 1000 Birr"
        ),
        reply_markup=reply_markup,
        read_timeout=60,
        write_timeout=60
    )

# =========================
# DEPOSIT SELECT
# =========================

async def deposit_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    amount = int(query.data.split("_")[1])

    context.user_data["deposit_amount"] = amount
    context.user_data["waiting_tx"] = True

    phone=get_phone(query.from_user.id)

    await query.message.reply_text(
        f"💰 Deposit Request\n\n"
        f"⚠️ IMPORTANT:\n"
        f"You MUST deposit using your registered number:\n"
        f"{phone}\n\n"
        f"Send {amount} Birr to:\n"
        f"0914859991\n\n"
        f"Then send your Transaction ID."
    )

# =========================
# TX VERIFY
# =========================

async def verify_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context .user_data.get ( "waiting_tx" ):
        return

    tx_id = update.message.text.strip()

    user_id = update.effective_user.id

    amount = context.user_data.get("deposit_amount")

    if len(tx_id) < 6:

      await update.message.reply_text(
        "❌ Invalid Transaction ID."

    ) 
      return

    if not amount:
        await update.message.reply_text(
            "❌ Deposit session expired."
        )
        return ConversationHandler.END

    if tx_exists(tx_id):
        await update.message.reply_text(
            "❌ Transaction already used."
        )
        return ConversationHandler.END

    cursor.execute("""
    INSERT INTO pending_deposits
    (telegram_id, tx_id, amount)
    VALUES (?, ?, ?)
    """, (
        user_id,
        tx_id,
        amount
    ))

    conn.commit()

    keyboard = [[
        InlineKeyboardButton(
            "✅ Approve",
            callback_data=f"approve_{user_id}_{amount}_{tx_id}"
        ),

        InlineKeyboardButton(
            "❌ Reject",
            callback_data=f"reject_{tx_id}"
        )
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    phone = get_phone(user_id)

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"💰 New Deposit Request\n\n"
            f"Phone: {phone}\n"
            f"Amount: {amount} Birr\n"
            f"TX ID: {tx_id}"
        ),
        reply_markup=reply_markup
    )

    await update.message.reply_text(
        "✅ Deposit request submitted.\n"
        "Waiting for admin approval."
    )
    context.user_data["waiting_tx"] = False

    return ConversationHandler.END

async def approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data.split("_")

    action = data[0]
    user_id = int(data[1])
    amount = int(data[2])
    tx_id = data[3]

    if action == "approve":

        update_balance(user_id, amount)

        save_transaction(
            user_id,
            tx_id,
            amount,
            "deposit",
            "success"
        )

        cursor.execute(
            "DELETE FROM pending_deposits WHERE tx_id=?",
            (tx_id,)
        )

        conn.commit()

        balance = get_balance(user_id)

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Deposit Approved\n\n"
                f"💰 Amount: {amount} Birr\n"
                f"🏦 Balance: {balance} Birr"
            )   
        )

        context.user_data["waiting_tx"] = False

        await query.edit_message_text(
            f"✅ Approved {amount} Birr"
        )

    elif action == "reject":

       cursor.execute(
            "DELETE FROM pending_deposits WHERE tx_id=?",
            (tx_id,)
        )

    conn.commit()

    await context.bot.send_message(
            chat_id=user_id,
            text="❌ Deposit rejected."
        )

    await query.edit_message_text(
            "❌ Deposit rejected."
        )

# =========================
# WITHDRAW MENU
# =========================

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("50", callback_data='with_50'), InlineKeyboardButton("100", callback_data='with_100')],
        [InlineKeyboardButton("200", callback_data='with_200'), InlineKeyboardButton("500", callback_data='with_500')],
        [InlineKeyboardButton("800", callback_data='with_800'), InlineKeyboardButton("1000", callback_data='with_1000')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_photo(
        photo=open("C:\\Users\\Bamlak\\telegram_game_bot\\photo_2026-05-13_16-33-49.jpg", "rb"),
        caption="🏧 Withdraw Menu",
        reply_markup=reply_markup,
        read_timeout=60,
        write_timeout=60
    )

# =========================
# WITHDRAW SELECT
# =========================

async def withdraw_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    amount = int(query.data.split("_")[1])
    user_id = query.from_user.id
    balance = get_balance(user_id)

    if balance < amount:
        await query.message.reply_text("❌ Insufficient balance.")
        return

    update_balance(user_id, -amount)
    save_transaction(user_id, f"withdraw_{user_id}_{amount}", amount, "withdraw", "pending")
    new_balance = get_balance(user_id)

    await query.message.reply_text(
        f"✅ Withdrawal Request Submitted\n\n"
        f"💸 Amount: {amount} Birr\n"
        f"💰 New Balance: {new_balance} Birr\n\n"
        f"Admin will process shortly."
    )

# =========================
# TRANSACTION HISTORY
# =========================

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    cursor.execute("SELECT amount, type, status FROM transactions WHERE telegram_id=? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()

    if not rows:
        await query.message.reply_text("No transactions found.")
        return

    text = "📜 Last Transactions\n\n"
    for row in rows:
        text += f"{row[1]} | {row[0]} Birr | {row[2]}\n"
    await query.message.reply_text(text)

# =========================
# DICE GAME
# =========================

async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)

    text = (
        f"🎲 You rolled: {user_roll}\n"
        f"🤖 Bot rolled: {bot_roll}\n\n"
    )

    if user_roll > bot_roll:

        text += "✅ You won!"

    elif user_roll < bot_roll:

        text += "❌ You lost."

    else:

        text += "🤝 Draw."

    await query.message.reply_text(text)

# =========================
# HANDLERS & APP LAUNCH
# =========================

# 1. Setup Timeout Configuration
request_config = HTTPXRequest(connect_timeout=60, read_timeout=60)

# 2. Build Application with Token and Request Config
app = ApplicationBuilder().token(TOKEN).request(request_config).build()

# 3. Setup Conversation Handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)]
    },
    fallbacks=[CommandHandler("start", start)]
)

# 4. Add all handlers to app
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(profile, pattern='^profile$'))
app.add_handler(CallbackQueryHandler(deposit_menu, pattern='^deposit$'))
app.add_handler(CallbackQueryHandler(deposit_selected, pattern='^dep_'))
app.add_handler(CallbackQueryHandler(withdraw_menu, pattern='^withdraw$'))
app.add_handler(CallbackQueryHandler(withdraw_selected, pattern='^with_'))
app.add_handler(CallbackQueryHandler(history, pattern='^history$'))
app.add_handler(
    CallbackQueryHandler(
        approve_deposit,
        pattern='^(approve|reject)_'
    )
)
app.add_handler(
    CallbackQueryHandler(
        dice_game,
        pattern='^dice$'
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        verify_tx
    )
)

async def error_handler(update, context):

    print(f"ERROR: {context.error}")

    try:
        if update and update.effective_message:

            await update.effective_message.reply_text(
                "❌ Something went wrong.\n"
                "Please try again."
            )

    except:
        pass

    app.add_error_handler(error_handler)

# Create Flask app
flask_app = Flask(__name__)
CORS(flask_app)  # Enable CORS for all routes

@flask_app.route('/api/balance', methods=['GET'])
def api_get_balance():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'No user_id'}), 400
    bal = get_balance(user_id)   # your existing function
    return jsonify({'balance': bal})

@flask_app.route('/api/game/result', methods=['POST'])
def api_game_result():
    data = request.get_json()
    user_id = data.get('user_id')
    bet = data.get('bet', 0)
    won = data.get('won', False)
    if not user_id:
        return jsonify({'error': 'No user_id'}), 400
    if won:
        win_amount = int(bet * 0.9)   # 10% fee
        update_balance(user_id, win_amount)
        new_balance = get_balance(user_id)
        return jsonify({'success': True, 'new_balance': new_balance, 'won': win_amount})
    else:
        update_balance(user_id, -bet)
        new_balance = get_balance(user_id)
        return jsonify({'success': True, 'new_balance': new_balance, 'lost': bet})

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False)

# Start Flask in background thread
Thread(target=run_flask, daemon=True).start()

print("🔥 Ludex Games Bot Running...")
app.run_polling()