import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "gpt-5.6-luna"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./bank_support.db"
)