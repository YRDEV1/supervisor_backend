from uvicorn import run
from app.src.core.config import HOST, PORT

if __name__ == "__main__":
    run(app="app.src.main:app", host=HOST, port=PORT)