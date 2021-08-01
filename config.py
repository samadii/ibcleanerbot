import os
    
class Config:
    bot_api = os.environ.get("BOT_TOKEN")
    DEFAULT_VOTE_COUNT = int(os.environ.get("DEFAULT_VOTE_COUNT", 10))
    DEFAULT_DELETE_TIMEOUT = int(os.environ.get("DEFAULT_DELETE_TIMEOUT", 60))
    DB_URI = os.environ.get("DB_URI", 'sqlite:///db.db')
