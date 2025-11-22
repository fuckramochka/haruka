import os

class Config:
    # === HARDCODED CORE ===
    API_ID = 25916528
    API_HASH = "7ecf8cdbf096d1068531fc612fd0fb33"
    SESSION_NAME = "HARUKA"
    
    # === DEFAULTS ===
    PREFIX = "."
    COMMAND_TIMEOUT = 240  # Seconds for execution
    DB_FILE = "haruka_data.db"
    
    # === PATHS ===
    BASE_DIR = os.getcwd() # User's working directory
    SYSTEM_DIR = os.path.dirname(os.path.abspath(__file__))
    PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")