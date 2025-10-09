from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class TickerHistory(Base):
  __tablename__ = "ticker_history"

  id = Column(Integer, primary_key=True)
  ticker = Column(String, unique=True, nullable=False)

engine = create_engine("sqlite:///history.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
  Base.metadata.create_all(engine)
