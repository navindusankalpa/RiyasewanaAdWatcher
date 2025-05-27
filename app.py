import json
import time
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import ad_watcher  # Assuming ad_watcher.py contains the logic to fetch and process car ads
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
ADS_CACHE = "ads_cache.json"
CONFIG_FILE = "telegram_config.json"
CAR_LINKS_FILE = "link_watcher.json"
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

class BotConfig:
    def __init__(self):
        self.config = self._load_config()
        # Ensure 'last_ads' exists in config
        if "last_ads" not in self.config:
            self.config["last_ads"] = {}
            self.save_config()
    
    def _load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"api_key": "", "users": {}, "last_ads": {}}
    
    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
    
    def add_user(self, user_id: int, user_data: dict):
        if str(user_id) not in self.config["users"]:
            self.config["users"][str(user_id)] = {
                "username": user_data.get("username"),
                "user_id": user_id,
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
                "language_code": user_data.get("language_code"),
                "is_bot": user_data.get("is_bot", False),
                "subscribed_models": []  # Track which car models user wants
            }
            self.save_config()
            return True
        return False
    
    def get_car_links(self):
        try:
            with open(CAR_LINKS_FILE) as f:
                return json.load(f).get("Cars", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    """Handle /config command to show bot configuration"""
    if str(user.id) == "1221095750":
        if os.path.exists(CONFIG_FILE):
            await update.message.reply_document(document=open(CONFIG_FILE, "rb"),
                                                filename=CONFIG_FILE,
                                                caption="Here is the current bot configuration.")
        else:
            await update.message.reply_text("Configuration file not found.")

async def adcache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    """Handle /config command to show bot configuration"""
    if str(user.id) == "1221095750":
        if os.path.exists(ADS_CACHE):
            await update.message.reply_document(document=open(ADS_CACHE, "rb"),
                                                filename=ADS_CACHE,
                                                caption="Here is the ad cache file.")
        else:
            await update.message.reply_text("Configuration file not found.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    bot_config = BotConfig()
    
    was_added = bot_config.add_user(user.id, {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "is_bot": user.is_bot
    })
    
    if was_added:
        await update.message.reply_text(
            f"🎉 Welcome {user.mention_markdown()}!\n"
            "You'll now receive notifications about new car ads.\n",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"👋 Welcome back {user.mention_markdown()}!\n"
            "You're already receiving updates.",
            parse_mode="Markdown"
        )

async def check_ads(context: ContextTypes.DEFAULT_TYPE):
    """Periodic ad checking job"""
    bot_config = BotConfig()
    car_links = bot_config.get_car_links()
    
    if not car_links:
        logging.warning("No car links found in configuration")
        return
    
    for model_name, url in car_links.items():
        try:
            new_ads = ad_watcher.watch_ads(url)
            if not new_ads:
                continue
                
            # Compare with last seen ads
            last_seen = bot_config.config["last_ads"].get(model_name, [])
            new_ads = [ad for ad in new_ads if ad["url"] not in last_seen]
            
            if new_ads:
                logging.info(f"Found {len(new_ads)} new {model_name} ads")
                bot_config.config["last_ads"][model_name] = [ad["url"] for ad in new_ads]
                bot_config.save_config()
                
                # Notify subscribed users
                for user_id, user_data in bot_config.config["users"].items():
                    if not user_data.get("subscribed_models") or model_name in user_data["subscribed_models"]:
                        for ad in new_ads:
                            print(ad)
                            try:
                                # await context.bot.send_message(
                                #     chat_id=user_id,
                                #     text=f"🚗 *New #{model_name} Available!*\n"
                                #          f"📌 {ad['title']}\n"
                                #          f"💰 *{ad['price']}*\n"
                                #          f"🛣️ {ad['mileage']}\n"
                                #          f"📍 {ad['location']}\n"
                                #          f"[🔗 View Ad]({ad['url']})",
                                #     parse_mode="Markdown"
                                # )
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=ad['image'],
                                    caption=f"🚗 *New #{model_name} Available!*\n\n"
                                         f"📌 {ad['title']}\n\n"
                                         f"💰 *{ad['price']}*\n"
                                         f"🛣️ {ad['mileage']}\n"
                                         f"📍 {ad['location']}\n"
                                         f"[🔗 View Ad]({ad['url']})\n\n"
                                         f"_Made by @NAVINDUNSK_",
                                    parse_mode="Markdown"
                                )
                            except Exception as e:
                                logging.error(f"Failed to notify {user_id}: {e}")
            
        except Exception as e:
            logging.error(f"Error checking {model_name} ads: {e}")

def main():
    bot_config = BotConfig()
    api_key = os.getenv('API_KEY')
    #api_key = bot_config.config["api_key"]
    print(api_key)
    
    if not api_key or api_key == "YOUR_TELEGRAM_BOT_TOKEN":
        raise ValueError("Please set your Telegram bot token in telegram_config.json")
    
    # Create and configure application
    application = Application.builder().token(api_key).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("config", config))
    application.add_handler(CommandHandler("adcache", adcache))
    
    # Set up periodic ad checking
    job_queue = application.job_queue
    job_queue.run_repeating(check_ads, interval=60.0, first=10.0)  # Check every 60 seconds
    
    # Start the bot
    logging.info("Starting bot with ad watcher...")
    application.run_polling()

if __name__ == "__main__":
    main()