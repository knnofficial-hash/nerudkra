from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import re

from config import BOT_TOKEN
from database import get_db, get_user, create_user, update_user, create_order, get_active_orders, get_order, add_favorite, remove_favorite, get_favorites, use_free_view, check_can_view_contact
from keyboards import main_menu, order_buttons, region_buttons, subscription_button

router = Router()

# --- FSM для создания заказа (12 шагов) ---
class OrderForm(StatesGroup):
    type_choice = State()
    category_choice = State()
    address = State()
    latitude = State()  # если геолокация
    date = State()
    time = State()
    phone = State()
    name = State()
    comment = State()

# --- /start ---
@router.message(Command("start"))
async def start_command(message: types.Message):
    tg_id = message.from_user.id
    
    with get_db() as db:
        user = get_user(db, tg_id)
        if not user:
            create_user(db, tg_id, name=message.from_user.full_name)
            await message.answer(
                "👋 Добро пожаловать!\n\n"
                "Выберите ваш регион, чтобы получать заказы:",
                reply_markup=region_buttons
            )
        else:
            await message.answer(
                "👋 Добро пожаловать в бот-агрегатор заказов!\n\n"
                "Используйте меню для навигации:",
                reply_markup=main_menu
            )

# --- Обработка выбора региона ---
@router.callback_query(F.data.startswith("region_"))
async def set_region(callback: types.CallbackQuery):
    region = callback.data.split("_")[1]  # msk или spb
    tg_id = callback.from_user.id
    
    with get_db() as db:
        update_user(db, tg_id, region=region)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Регион установлен: {'Москва и МО' if region == 'msk' else 'Санкт-Петербург и ЛО'}\n\n"
        "Теперь выберите категорию и пользуйтесь ботом!",
        reply_markup=main_menu
    )
    await callback.answer()

# --- Выбор спецтехники ---
@router.message(F.text == "🚛 Выбрать спецтехнику")
async def choose_equipment(message: types.Message):
    equipment_list = [
        "Экскаватор", "Погрузчик", "Бульдозер", "Самосвал",
        "Кран", "Автовышка", "Ямобур", "Фреза", "Каток",
        "Асфальтоукладчик", "Автогрейдер", "Скрепер", "Трактор",
        "Экскаватор-погрузчик", "Мини-экскаватор", "Фронтальный погрузчик",
        "Телескопический погрузчик", "Автобетоносмеситель", "Бетоновоз",
        "Бортовой автомобиль", "Тягач", "Трал"
    ]
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=eq, callback_data=f"equip_{eq}")]
            for eq in equipment_list
        ]
    )
    await message.answer("Выберите спецтехнику:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("equip_"))
async def save_equipment(callback: types.CallbackQuery):
    equipment = callback.data.split("_", 1)[1]
    tg_id = callback.from_user.id
    
    with get_db() as db:
        update_user(db, tg_id, category="tech", equipment=equipment)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Выбрана техника: {equipment}\n"
        "Теперь вы будете получать заказы на эту категорию!",
        reply_markup=main_menu
    )
    await callback.answer()

# --- Выбор нерудки ---
@router.message(F.text == "🪨 Выбрать нерудку")
async def choose_nerud(message: types.Message):
    nerud_list = ["Песок", "Щебень", "Гравий", "Отсев", "ПГС"]
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=mat, callback_data=f"nerud_{mat}")]
            for mat in nerud_list
        ]
    )
    await message.answer("Выберите нерудный материал:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("nerud_"))
async def save_nerud(callback: types.CallbackQuery):
    material = callback.data.split("_", 1)[1]
    tg_id = callback.from_user.id
    
    with get_db() as db:
        update_user(db, tg_id, category="nerud", equipment=material)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Выбран материал: {material}\n"
        "Теперь вы будете получать заказы на эту категорию!",
        reply_markup=main_menu
    )
    await callback.answer()

# --- Выбор отвала ---
@router.message(F.text == "🗑 Выбрать отвал")
async def choose_otval(message: types.Message):
    tg_id = message.from_user.id
    
    with get_db() as db:
        update_user(db, tg_id, category="otval", equipment="Отвал")
    
    await message.answer(
        "✅ Выбрана категория: Отвал\n"
        "Теперь вы будете получать заказы на эту категорию!",
        reply_markup=main_menu
    )

# --- СОЗДАНИЕ ЗАКАЗА (12 шагов) ---
@router.message(F.text == "📦 Выставить заказ")
async def start_order(message: types.Message, state: FSMContext):
    # Проверяем, что пользователь выбрал регион
    with get_db() as db:
        user = get_user(db, message.from_user.id)
        if not user or not user.region:
            await message.answer(
                "⚠️ Сначала выберите регион через кнопку '📍 Выбрать регион'"
            )
            return
    
    # Шаг 1: Выбор типа техники
    equipment_list = [
        "Экскаватор", "Погрузчик", "Бульдозер", "Самосвал",
        "Кран", "Автовышка", "Ямобур", "Фреза", "Каток",
        "Асфальтоукладчик", "Автогрейдер", "Скрепер", "Трактор",
        "Экскаватор-погрузчик", "Мини-экскаватор", "Фронтальный погрузчик",
        "Телескопический погрузчик", "Автобетоносмеситель", "Бетоновоз",
        "Бортовой автомобиль", "Тягач", "Трал"
    ]
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=eq, callback_data=f"order_type_{eq}")]
            for eq in equipment_list
        ]
    )
    
    await state.set_state(OrderForm.type_choice)
    await message.answer(
        "📋 Шаг 1/12: Выберите тип техники:",
        reply_markup=keyboard
    )

@router.callback_query(StateFilter(OrderForm.type_choice), F.data.startswith("order_type_"))
async def order_type(callback: types.CallbackQuery, state: FSMContext):
    equipment = callback.data.split("_", 2)[2]
    await state.update_data(type=equipment)
    
    await state.set_state(OrderForm.address)
    await callback.message.delete()
    await callback.message.answer(
        "📍 Шаг 2/12: Отправьте геолокацию или введите адрес вручную:\n\n"
        "Для отправки геолокации нажмите 📎 → 📍 Геолокация\n"
        "Или просто напишите адрес текстом"
    )
    await callback.answer()

# Шаг 2: Адрес (текст или геолокация)
@router.message(StateFilter(OrderForm.address), F.location)
async def order_address_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    await state.update_data(latitude=str(lat), longitude=str(lon))
    # Здесь нужно определить регион по координатам
    # Пока упрощённо - определяем по IP или оставляем пользователю
    await state.set_state(OrderForm.date)
    await message.answer(
        "📅 Шаг 3/12: Введите дату (в формате ДД.ММ.ГГГГ):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@router.message(StateFilter(OrderForm.address), F.text)
async def order_address_text(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.date)
    await message.answer(
        "📅 Шаг 3/12: Введите дату (в формате ДД.ММ.ГГГГ):"
    )

# Шаг 3: Дата
@router.message(StateFilter(OrderForm.date))
async def order_date(message: types.Message, state: FSMContext):
    date_pattern = r"\d{2}\.\d{2}\.\d{4}"
    if not re.match(date_pattern, message.text):
        await message.answer("❌ Неверный формат. Используйте ДД.ММ.ГГГГ")
        return
    
    await state.update_data(date=message.text)
    await state.set_state(OrderForm.time)
    await message.answer(
        "🕐 Шаг 4/12: Введите время (в формате ЧЧ:ММ) или пропустите, отправив '-'"
    )

# Шаг 4: Время
@router.message(StateFilter(OrderForm.time))
async def order_time(message: types.Message, state: FSMContext):
    time = message.text
    if time != "-":
        time_pattern = r"\d{2}:\d{2}"
        if not re.match(time_pattern, time):
            await message.answer("❌ Неверный формат. Используйте ЧЧ:ММ или '-' для пропуска")
            return
    
    await state.update_data(time=time if time != "-" else None)
    await state.set_state(OrderForm.phone)
    await message.answer(
        "📞 Шаг 5/12: Введите ваш номер телефона для связи:"
    )

# Шаг 5: Телефон
@router.message(StateFilter(OrderForm.phone))
async def order_phone(message: types.Message, state: FSMContext):
    phone = re.sub(r"\D", "", message.text)
    if len(phone) < 10:
        await message.answer("❌ Введите корректный номер телефона")
        return
    
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.name)
    await message.answer(
        "👤 Шаг 6/12: Введите ваше имя:"
    )

# Шаг 6: Имя
@router.message(StateFilter(OrderForm.name))
async def order_name(message: types.Message, state: FSMContext):
    await state.update_data(contact_name=message.text)
    await state.set_state(OrderForm.comment)
    await message.answer(
        "💬 Шаг 7/12: Введите комментарий (или '-' для пропуска):"
    )

# Шаг 7: Комментарий
@router.message(StateFilter(OrderForm.comment))
async def order_comment(message: types.Message, state: FSMContext):
    comment = message.text
    if comment == "-":
        comment = None
    
    await state.update_data(comment=comment)
    
    # Собираем все данные
    data = await state.get_data()
    
    # Шаг 8: Сохраняем заказ
    tg_id = message.from_user.id
    with get_db() as db:
        user = get_user(db, tg_id)
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            await state.clear()
            return
        
        # Определяем регион (пока берем из профиля)
        region = user.region
        
        order_data = {
            "type": "tech",  # упрощённо
            "category": data.get("type"),
            "address": data.get("address", "Не указан"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "date": data.get("date"),
            "time": data.get("time"),
            "phone": data.get("phone"),
            "contact_name": data.get("contact_name"),
            "comment": data.get("comment"),
            "region": region,
            "status": "active"
        }
        
        order = create_order(db, user.id, order_data)
    
    await state.clear()
    await message.answer(
        "✅ Заказ успешно опубликован!\n\n"
        f"📋 Категория: {data.get('type')}\n"
        f"📍 Адрес: {data.get('address', 'Не указан')}\n"
        f"📅 Дата: {data.get('date')}\n"
        f"👤 Имя: {data.get('contact_name')}\n\n"
        "Заказ будет виден в ленте заказов.",
        reply_markup=main_menu
    )

# --- ЛЕНТА ЗАКАЗОВ ---
@router.message(F.text == "📋 Лента заказов")
async def show_feed(message: types.Message):
    tg_id = message.from_user.id
    
    with get_db() as db:
        user = get_user(db, tg_id)
        if not user or not user.region:
            await message.answer("⚠️ Сначала выберите регион")
            return
        
        orders = get_active_orders(db, user.region, limit=10)
        
        if not orders:
            await message.answer("📭 В вашем регионе пока нет активных заказов")
            return
        
        for order in orders:
            text = (
                f"📦 Заказ #{order.id}\n"
                f"🏗 {order.category}\n"
                f"📍 {order.address}\n"
                f"📅 {order.date}"
            )
            if order.time:
                text += f" 🕐 {order.time}"
            if order.comment:
                text += f"\n💬 {order.comment}"
            
            # Проверяем, в избранном ли
            is_fav = db.query(Favorite).filter(
                Favorite.user_id == user.id,
                Favorite.order_id == order.id
            ).first() is not None
            
            await message.answer(
                text,
                reply_markup=order_buttons(order.id, is_fav)
            )

# --- ИЗБРАННОЕ ---
@router.message(F.text == "⭐ Избранное")
async def show_favorites(message: types.Message):
    tg_id = message.from_user.id
    
    with get_db() as db:
        user = get_user(db, tg_id)
        if not user:
            await message.answer("❌ Ошибка")
            return
        
        favorites = get_favorites(db, user.id)
        
        if not favorites:
            await message.answer("⭐ У вас пока нет избранных заказов")
            return
        
        for fav in favorites:
            order = fav.order
            text = (
                f"📦 Заказ #{order.id}\n"
                f"🏗 {order.category}\n"
                f"📍 {order.address}\n"
                f"📅 {order.date}"
            )
            if order.time:
                text += f" 🕐 {order.time}"
            
            await message.answer(
                text,
                reply_markup=order_buttons(order.id, True)
            )

# --- ДОБАВЛЕНИЕ В ИЗБРАННОЕ ---
@router.callback_query(F.data.startswith("fav_"))
async def add_favorite_callback(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    tg_id = callback.from_user.id
    
    with get_db() as db:
        user = get_user(db, tg_id)
        if user:
            add_favorite(db, user.id, order_id)
            await callback.answer("⭐ Добавлено в избранное!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка", show_alert=True)

# --- УБРАТЬ ИЗ ИЗБРАННОГО ---
@router.callback_query(F.data.startswith("unfav_"))
async def remove_favorite_callback(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    tg_id = callback.from_user.id
    
    with get_db() as db:
        user = get_user(db, tg_id)
        if user:
            remove_favorite(db, user.id, order_id)
            await callback.answer("❌ Убрано из избранного", show_alert=True)
        else:
            await callback.answer("❌ Ошибка", show_alert=True)

# --- ПОКАЗ КОНТАКТОВ ---
@router.callback_query(F.data.startswith("contact_"))
async def show_contact(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    tg_id = callback.from_user.id
    
    with get_db() as db:
        user = get_user(db, tg_id)
        if not user:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        # Проверяем, можно ли показать контакты
        can_view = check_can_view_contact(db, tg_id)
        
        if not can_view:
            await callback.message.answer(
                "⚠️ У вас закончились бесплатные просмотры.\n"
                "Оформите подписку для безлимитного доступа:",
                reply_markup=subscription_button
            )
            await callback.answer()
            return
        
        order = get_order(db, order_id)
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Используем один бесплатный просмотр
        use_free_view(db, tg_id)
        
        text = (
            f"📞 Контакты по заказу #{order.id}:\n\n"
            f"👤 Имя: {order.contact_name}\n"
            f"📱 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
        )
        
        # Показываем сколько осталось просмотров
        user = get_user(db, tg_id)  # обновляем данные
        remaining = user.free_views if not user.has_subscription else "♾️"
        text += f"\n📊 Осталось просмотров: {remaining}"
        
        await callback.message.answer(text)
        await callback.answer()
