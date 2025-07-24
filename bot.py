import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime, time, timedelta
import pytz

# বিস্তারিত লগিং সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# নির্দিষ্ট টাইমজোন সেট করা হয়েছে
TARGET_TIMEZONE = pytz.timezone("Asia/Dhaka")

# আপনার বট টোকেন এবং চ্যানেল আইডি
BOT_TOKEN = "7989297833:AAFouPTFdw3j36zoBXe4EBML4UKtj4DhPAE"
CHANNEL_ID = "-1002752970291"


async def set_bot_commands(application: Application):
    """বট চালু হওয়ার সময় কমান্ড মেনু সেট করে।"""
    commands = [
        BotCommand("start", "বট চালু করুন এবং চ্যাট পরিষ্কার করুন"),
        BotCommand("newpost", "একটি নতুন পোস্ট শিডিউল করা শুরু করুন"),
        BotCommand("setphoto", "পোস্টের জন্য একটি ছবি সেট করুন"),
        BotCommand("setfile", "পোস্টের জন্য একটি ফাইল সেট করুন"),
        BotCommand("settime", "পোস্টের সময় নির্ধারণ করুন (HH:MM am/pm)"),
        BotCommand("status", "বর্তমান পোস্টের অবস্থা দেখুন"),
        BotCommand("schedule", "বর্তমান পোস্টটি শিডিউল করুন"),
        BotCommand("cancel", "বর্তমান পোস্ট বাতিল করুন"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("বটের কমান্ড মেনু সফলভাবে সেট করা হয়েছে।")


# *** আপডেট করা হয়েছে: এই ফাংশনটি এখন ব্যাকগ্রাউন্ডে চলবে ***
async def clear_chat_history(context: ContextTypes.DEFAULT_TYPE):
    """চ্যাটের সাম্প্রতিক মেসেজগুলো ব্যাকগ্রাউন্ডে ডিলিট করে।"""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    
    logger.info(f"চ্যাট {chat_id} এর ইতিহাস পরিষ্কার করা শুরু হচ্ছে...")
    try:
        # টেলিগ্রামের সীমাবদ্ধতার কারণে, বট শুধুমাত্র সাম্প্রতিক মেসেজগুলো ডিলিট করতে পারে।
        # আমরা এখানে সাম্প্রতিক ১০০টি মেসেজ ডিলিট করার চেষ্টা করছি।
        for i in range(message_id, 0, -1):
            if i < message_id - 100: break
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=i)
            except Exception:
                continue
        logger.info(f"চ্যাট {chat_id} এর ইতিহাস পরিষ্কার করা সম্পন্ন হয়েছে।")
    except Exception as e:
        logger.error(f"চ্যাট ইতিহাস পরিষ্কার করার সময় সমস্যা: {e}")


# *** আপডেট করা হয়েছে: এখন রিপ্লাই তাৎক্ষণিক এবং ডিলিট প্রক্রিয়া ব্যাকগ্রাউন্ডে চলবে ***
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start কমান্ড দিলে তাৎক্ষণিক স্বাগত বার্তা পাঠায় এবং চ্যাট পরিষ্কারের কাজ ব্যাকগ্রাউন্ডে পাঠায়।"""
    welcome_message = (
        "**স্বাগতম!** আমি আপনার পোস্ট শিডিউলার বট।\n\n"
        "আপনার চ্যাট ইতিহাস পরিষ্কার করা হচ্ছে... একটি নতুন পোস্ট তৈরি করতে, অনুগ্রহ করে /newpost কমান্ড দিন।\n\n"
        "আমার সমস্ত কমান্ড দেখতে চ্যাট বক্সের পাশের মেনু (`/`) বাটনে ক্লিক করুন।"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    # চ্যাট ডিলিট করার কাজটি ব্যাকগ্রাউন্ডে চালানোর জন্য Job Queue-তে পাঠানো হচ্ছে।
    context.job_queue.run_once(
        clear_chat_history,
        0, # 0 সেকেন্ড ডিলে মানে, যত দ্রুত সম্ভব কিন্তু বর্তমান প্রক্রিয়াকে ব্লক না করে
        data={'chat_id': update.effective_chat.id, 'message_id': update.message.message_id},
        name=f"clear_chat_{update.effective_chat.id}"
    )


async def new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """একটি নতুন পোস্ট তৈরির প্রক্রিয়া শুরু করে।"""
    context.user_data.clear()
    context.user_data['awaiting_photo'] = False
    context.user_data['awaiting_file'] = False
    await update.message.reply_text(
        "একটি নতুন পোস্ট প্রক্রিয়া শুরু হয়েছে।\n\n"
        "➡️ প্রথমে, /setphoto কমান্ড ব্যবহার করে ছবি সেট করুন।"
    )


async def set_photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্যবহারকারীকে ছবি পাঠানোর জন্য প্রস্তুত করে।"""
    context.user_data['awaiting_photo'] = True
    await update.message.reply_text("✅ এখন আপনার ছবিটি ক্যাপশনসহ পাঠান।")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """পাঠানো ছবিটি গ্রহণ করে।"""
    if context.user_data.get('awaiting_photo'):
        if update.message.photo and update.message.caption:
            context.user_data["photo_id"] = update.message.photo[-1].file_id
            context.user_data["caption"] = update.message.caption
            context.user_data['awaiting_photo'] = False
            await update.message.reply_text(
                "✅ ছবি সফলভাবে সেট হয়েছে।\n\n"
                "➡️ এবার, /setfile কমান্ড ব্যবহার করে ফাইল সেট করুন।"
            )
        else:
            await update.message.reply_text("❌ ভুল হয়েছে! অনুগ্রহ করে একটি ছবি ক্যাপশনসহ পাঠান।")
    else:
        await update.message.reply_text("ছবি পাঠানোর জন্য, অনুগ্রহ করে প্রথমে /setphoto কমান্ড দিন।")


async def set_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্যবহারকারীকে ফাইল পাঠানোর জন্য প্রস্তুত করে।"""
    context.user_data['awaiting_file'] = True
    await update.message.reply_text("✅ এখন আপনার ফাইলটি পাঠান।")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """পাঠানো ফাইলটি গ্রহণ করে।"""
    if context.user_data.get('awaiting_file'):
        if update.message.document:
            context.user_data["file_id"] = update.message.document.file_id
            context.user_data["file_name"] = update.message.document.file_name
            context.user_data['awaiting_file'] = False
            await update.message.reply_text(
                "✅ ফাইল সফলভাবে সেট হয়েছে।\n\n"
                "➡️ এবার, /settime কমান্ড দিয়ে সময় নির্ধারণ করুন (যেমন: /settime 10:30pm)।"
            )
        else:
            await update.message.reply_text("❌ ভুল হয়েছে! অনুগ্রহ করে একটি ফাইল (ডকুমেন্ট) পাঠান।")
    else:
        await update.message.reply_text("ফাইল পাঠানোর জন্য, অনুগ্রহ করে প্রথমে /setfile কমান্ড দিন।")


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """কমান্ড থেকে কাস্টম সময় নির্ধারণ করে।"""
    if not context.args:
        await update.message.reply_text(
            "❌ ভুল ফরম্যাট! অনুগ্রহ করে সময়ের সাথে কমান্ড দিন।\n"
            "উদাহরণ: `/settime 10:30pm` অথবা `/settime 22:30`"
        )
        return

    time_input = "".join(context.args).lower()
    parsed_time = None
    try:
        parsed_time = datetime.strptime(time_input, "%I:%M%p").time()
    except ValueError:
        try:
            parsed_time = datetime.strptime(time_input, "%H:%M").time()
        except ValueError:
            await update.message.reply_text(
                "❌ ভুল ফরম্যাট! অনুগ্রহ করে সঠিক ফরম্যাটে সময় দিন।\n"
                "উদাহরণ: `/settime 10:30pm` অথবা `/settime 22:30`"
            )
            return
    
    context.user_data['time'] = parsed_time.replace(tzinfo=TARGET_TIMEZONE)
    await update.message.reply_text(
        f"✅ সময় সফলভাবে {parsed_time.strftime('%I:%M %p')}-টায় সেট হয়েছে।\n\n"
        "➡️ সবকিছু ঠিক থাকলে, পোস্টটি চূড়ান্ত করতে /schedule কমান্ড দিন।"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বর্তমান পোস্টের অবস্থা দেখায়।"""
    if not context.user_data:
        await update.message.reply_text("বর্তমানে কোনো পোস্ট প্রক্রিয়া চলমান নেই। /newpost দিয়ে শুরু করুন।")
        return

    photo_set = "✅ সেট করা হয়েছে" if 'photo_id' in context.user_data else "❌ সেট করা হয়নি"
    file_set = "✅ সেট করা হয়েছে" if 'file_id' in context.user_data else "❌ সেট করা হয়নি"
    time_set = context.user_data['time'].strftime('%I:%M %p') if 'time' in context.user_data else "❌ সেট করা হয়নি"
    status_text = (
        "**বর্তমান পোস্টের অবস্থা:**\n\n"
        f"🖼️ ছবি: {photo_set}\n"
        f"📄 ফাইল: {file_set}\n"
        f"⏰ সময়: {time_set}\n\n"
        "সবকিছু ঠিক থাকলে /schedule কমান্ড দিন।"
    )
    await update.message.reply_text(status_text, parse_mode='Markdown')


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """চূড়ান্তভাবে পোস্টটি শিডিউল করে।"""
    if 'photo_id' not in context.user_data or 'file_id' not in context.user_data or 'time' not in context.user_data:
        await update.message.reply_text("❌ পোস্ট শিডিউল করা সম্ভব নয়। ছবি, ফাইল এবং সময়—সবকিছু সেট করা আবশ্যক। /status কমান্ড দিয়ে অবস্থা দেখুন।")
        return

    now = datetime.now(TARGET_TIMEZONE)
    run_time = context.user_data['time']
    run_date = now.replace(hour=run_time.hour, minute=run_time.minute, second=0, microsecond=0)

    if run_date < now:
        run_date += timedelta(days=1)

    job_data = context.user_data.copy()
    job_data['chat_id'] = update.effective_chat.id

    context.job_queue.run_once(
        post_to_channel,
        run_date,
        data=job_data,
        name=f"post_{update.effective_user.id}_{run_date.timestamp()}"
    )
    
    await update.message.reply_text(
        f"✅ **শিডিউল সফল!**\nআপনার পোস্টটি **{run_date.strftime('%d-%m-%Y, %I:%M %p')}**-টায় চ্যানেলে প্রকাশের জন্য নির্ধারিত হয়েছে।"
    )
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বর্তমান পোস্টের ডেটা মুছে দেয়।"""
    context.user_data.clear()
    await update.message.reply_text("বর্তমান পোস্টের প্রক্রিয়া বাতিল করা হয়েছে। নতুন করে শুরু করতে /newpost কমান্ড দিন।")


async def post_to_channel(context: ContextTypes.DEFAULT_TYPE):
    """নির্ধারিত সময়ে চ্যানেলে পোস্ট করে।"""
    data = context.job.data
    logger.info(f"চ্যানেল {CHANNEL_ID}-এ পোস্ট করার প্রক্রিয়া শুরু হচ্ছে।")
    try:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data["photo_id"], caption=data["caption"])
        await context.bot.send_document(chat_id=CHANNEL_ID, document=data["file_id"], filename=data["file_name"])
        logger.info(f"চ্যানেল {CHANNEL_ID}-এ সফলভাবে পোস্ট করা হয়েছে।")
    except Exception as e:
        logger.error(f"চ্যানেলে পোস্ট করার সময় মারাত্মক সমস্যা: {e}")
        await context.bot.send_message(chat_id=data["chat_id"], text=f"দুঃখিত, আপনার পোস্টটি চ্যানেলে প্রকাশ করা সম্ভব হয়নি। সমস্যা: {e}")


def main() -> None:
    """মূল ফাংশন, যা বটকে চালু করে এবং সমস্ত হ্যান্ডলার যোগ করে।"""
    application = Application.builder().token(BOT_TOKEN).post_init(set_bot_commands).build()

    # কমান্ড হ্যান্ডলার
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newpost", new_post))
    application.add_handler(CommandHandler("setphoto", set_photo_command))
    application.add_handler(CommandHandler("setfile", set_file_command))
    application.add_handler(CommandHandler("settime", set_time))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CommandHandler("cancel", cancel))

    # মিডিয়া হ্যান্ডলার
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_file))

    application.run_polling()


if __name__ == "__main__":
    main()
