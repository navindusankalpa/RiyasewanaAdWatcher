import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

CONFIG_FILE = "telegram_config.json"

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default structure if file doesn't exist
        return {
            "api_key": None,
            "Users": None
        }

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def add_user(user_id, user_name, role="user"):
    """Add or update a user in the config"""
    config = load_config()
    user_key = f"user{len(config['Users']) + 1}"
    
    config['Users'][user_key] = {
        "id": user_id,
        "name": user_name,
        "role": role
    }
    
    save_config(config)
    return user_key

