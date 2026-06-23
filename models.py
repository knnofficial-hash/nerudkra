from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String(100))
    phone = Column(String(20))
    region = Column(String(50))  # "msk" или "spb"
    category = Column(String(50))  # "tech", "nerud", "otval"
    equipment = Column(String(100))  # конкретная техника/материал
    free_views = Column(Integer, default=10)
    has_subscription = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="author")
    favorites = relationship("Favorite", back_populates="user")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String(50))  # "tech", "nerud", "otval"
    category = Column(String(100))  # конкретная техника/материал
    address = Column(String(500))
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    date = Column(String(20))
    time = Column(String(20), nullable=True)
    phone = Column(String(20))
    contact_name = Column(String(100))
    comment = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, completed, deleted
    source = Column(String(20), default="user")  # user, parsed
    region = Column(String(50))  # msk, spb
    created_at = Column(DateTime, default=datetime.utcnow)
    
    author = relationship("User", back_populates="orders")
    favorites = relationship("Favorite", back_populates="order")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(String(50))  # "forever", "monthly"
    category = Column(String(100))  # какая техника/материал
    price = Column(Integer)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="favorites")
    order = relationship("Order", back_populates="favorites")

# Создаём таблицы
Base.metadata.create_all(engine)
