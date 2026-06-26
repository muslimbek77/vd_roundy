from aiogram.fsm.state import State, StatesGroup


class Adverts(StatesGroup):
    """Reklama yuborish holatlari"""
    adverts = State()


class ChannelState(StatesGroup):
    """Kanal qo'shish holatlari"""
    kanal_qoshish = State()
    private_link = State()
    target_count = State()


class DelChannelState(StatesGroup):
    """Kanal o'chirish holatlari"""
    delete_channel = State()


class SupportState(StatesGroup):
    """Admin foydalanuvchiga yozish holatlari"""
    notify_message = State()
    ask_message = State()


class AdminState(StatesGroup):
    """Admin boshqaruvi holatlari"""
    add_admin = State()
