import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "kyron_scheduling.db"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SECRET_KEY = os.environ.get("SECRET_KEY", "kyron-dev-secret-2026")
    JSON_SORT_KEYS = False
