from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost/chat_db"
)

engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
