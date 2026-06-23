from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- Главное меню ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚛 Выбрать спецтехнику")],
        [KeyboardButton(text="🪨 Выбрать нерудку")],
        [KeyboardButton(text="🗑 Выбрать отвал")],
        [KeyboardButton(text="📦 Выставить заказ")],
        [KeyboardButton(text="📋 Лента заказов")],
        [KeyboardButton(text="⭐ Избранное")],
        [KeyboardButton(text="💎 Подписка навсегда")],
        [KeyboardButton(text="⚙️ Управление подписками")],
        [KeyboardButton(text="📍 Выбрать регион")],
        [KeyboardButton(text="📡 Радиус получения")],
        [KeyboardButton(text="💳 Выбрать тип оплаты")],
        [KeyboardButton(text="📞 Показать телефон")],
        [KeyboardButton(text="✉️ Написать нам")],
        [KeyboardButton(text="❓ Как оплатить?")],
        [KeyboardButton(text="🆘 Помощь")],
    ],
    resize_keyboard=True
)

# --- Инлайн кнопки для карточки заказа ---
def order_buttons(order_id: int, is_favorite: bool = False):
    buttons = [
        [InlineKeyboardButton(text="⭐ Добавить в избранное", callback_data=f"fav_{order_id}")],
        [InlineKeyboardButton(text="📞 Показать контакты", callback_data=f"contact_{order_id}")]
    ]
    if is_favorite:
        buttons.append([InlineKeyboardButton(text="❌ Убрать из избранного", callback_data=f"unfav_{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Кнопка для подписки ---
subscription_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💎 Оформить подписку", callback_data="subscribe")]
    ]
)

# --- Кнопки регионов ---
region_buttons = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📍 Москва и МО", callback_data="region_msk")],
        [InlineKeyboardButton(text="📍 Санкт-Петербург и ЛО", callback_data="region_spb")]
    ]
)
