import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
DATABASE_URL = os.getenv("DATABASE_URL")
DOCS_URL = os.getenv("DOCS_URL")
OPENAPI_URL = os.getenv("OPENAPI_URL")
REDOC_URL = os.getenv("REDOC_URL")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be set in the environment")