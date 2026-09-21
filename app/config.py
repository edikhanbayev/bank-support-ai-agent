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

CHECKPOINT_DB_URI = os.getenv(
    "CHECKPOINT_DB_URI"
)

JWT_SECRET = os.getenv(
    "JWT_SECRET"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)