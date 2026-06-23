from models import SessionLocal, User, Order, Subscription, Favorite
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- CRUD для пользователей ---
def get_user(db: Session, tg_id: int):
    return db.query(User).filter(User.tg_id == tg_id).first()

def create_user(db: Session, tg_id: int, name: str = None, phone: str = None):
    user = User(tg_id=tg_id, name=name, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, tg_id: int, **kwargs):
    user = get_user(db, tg_id)
    if user:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user

# --- CRUD для заказов ---
def create_order(db: Session, user_id: int, data: dict):
    order = Order(user_id=user_id, **data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def get_active_orders(db: Session, region: str, limit: int = 10):
    return db.query(Order).filter(
        Order.region == region,
        Order.status == "active"
    ).order_by(Order.created_at.desc()).limit(limit).all()

def get_order(db: Session, order_id: int):
    return db.query(Order).filter(Order.id == order_id).first()

# --- CRUD для избранного ---
def add_favorite(db: Session, user_id: int, order_id: int):
    fav = Favorite(user_id=user_id, order_id=order_id)
    db.add(fav)
    db.commit()
    return fav

def remove_favorite(db: Session, user_id: int, order_id: int):
    fav = db.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.order_id == order_id
    ).first()
    if fav:
        db.delete(fav)
        db.commit()
        return True
    return False

def get_favorites(db: Session, user_id: int):
    return db.query(Favorite).filter(Favorite.user_id == user_id).all()

# --- CRUD для просмотров контактов ---
def use_free_view(db: Session, user_id: int):
    user = get_user(db, user_id)
    if user and user.free_views > 0:
        user.free_views -= 1
        db.commit()
        return True
    return False

def check_can_view_contact(db: Session, user_id: int):
    user = get_user(db, user_id)
    if not user:
        return False
    if user.has_subscription and user.subscription_end and user.subscription_end > datetime.utcnow():
        return True
    if user.free_views > 0:
        return True
    return False
