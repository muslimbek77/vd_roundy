from aiogram.fsm.state import State, StatesGroup


class Adverts(StatesGroup):
    """Reklama yuborish holatlari"""
    adverts = State()


class ChannelState(StatesGroup):
    """Kanal qo'shish holatlari"""
    kanal_qoshish = State()


class DelChannelState(StatesGroup):
    """Kanal o'chirish holatlari"""
    delete_channel = State()