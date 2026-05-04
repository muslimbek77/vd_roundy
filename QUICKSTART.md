# 🚀 Bot Ishga Tushirish Yo'riqnomasi

## ⚡ Tezkor Boshlanish (5 daqiqa)

### 1️⃣ Virtual Environment Yaratish
```bash
cd /home/rasulbek/another-project/korrupsiya-bot/Simple-Aiogram-Template

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 2️⃣ Paketlarni O'rnatish
```bash
pip install -r requirements.txt
```

### 3️⃣ .env Faylini Yaratish
```bash
# Mazmun:
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMINS=123456789,987654321
```

### 4️⃣ Botni Ishga Tushirish
```bash
python bot.py
```

✅ **Tugadi!** Bot Telegram chati orqali komandalarni qabul qila boshladi.

---

## 📂 Fayl Tuzilmasi

```
Simple-Aiogram-Template/
├── bot.py                    # 🎯 Asosiy bot fayli
├── loader.py                 # 🔌 Bot va Database initsializatsiya
├── README.md                 # 📖 Asl README
├── OPTIMIZATIONS.md          # 📋 Optimizatsiyalar
├── SUMMARY.md                # 📊 Xulosa
├── CHECKLIST.md              # ✅ Tekshiruv
├── requirements.txt          # 📦 Paketlar
│
├── data/
│   └── config.py             # ⚙️ Konfiguratsiya (env)
│
├── baza/
│   └── sqlite.py             # 🗄️ Database qatlami
│
├── handlers/
│   ├── __init__.py           # Import qo'llanish
│   ├── users/
│   │   ├── start.py          # /start komandasi
│   │   ├── help.py           # /help komandasi
│   │   ├── about.py          # /about komandasi
│   │   └── admin.py          # 🔐 Admin paneli
│   ├── errors/
│   │   └── error_handler.py  # 🛡️ Global error handler
│   ├── channels/
│   └── groups/
│
├── middlewares/
│   ├── throttling.py         # ⏱️ Rate limiting
│   └── checksub.py           # 📋 Obuna tekshiruvi
│
├── keyboard_buttons/
│   ├── admin_keyboard.py     # 🎮 Admin tugmalari
│   └── subscription.py       # 📦 Obuna tugmalari
│
├── filters/
│   └── admin.py              # 🔐 Admin filter
│
├── states/
│   └── reklama.py            # 📢 FSM holatlari
│
├── utils/
│   └── misc/
│       └── subscription.py   # ✅ Obuna tekshiruvi
│
└── menucommands/
    └── set_bot_commands.py   # 📋 Bot komandalarini o'rnatish
```

---

## 🎮 Asosiy Komandalar

| Komanda | Tafsir | Uchun |
|---------|--------|-------|
| `/start` | Botni boshlash | Barchasi |
| `/help` | Yordam olish | Barchasi |
| `/about` | Bot haqida | Barchasi |
| `/admin` | Admin paneli | Faqat Admin |

---

## 🔐 Admin Paneli

### Tugmalar:
1. **👥 Foydalanuvchilar soni** - Jami foydalanuvchi sonini ko'rish
2. **📢 Reklama yuborish** - Barcha foydalanuvchilarga xabar yuborish
3. **⛓️ Kanallar ro'yxati** - Obuna kanallarini ko'rish
4. **➕ Kanal qo'shish** - Yangi obuna kanali qo'shish
5. **➖ Kanal o'chirish** - Obuna kanalini olib tashlash

### Admin ID'larini O'rnatish

`.env` faylida:
```
ADMINS=123456789,987654321,555555555
```

Raqamlarni vergul bilan ajrating. ID'larni Telegram deb olish uchun:
1. Bot uyida `/start` bosing
2. Bot ID'ni logga qarang

---

## 🐛 Debugging

### Logging Qayta Ishlash
```bash
# INFO level (default - tavsiya etiladi)
python bot.py

# DEBUG level uchun (development uchun)
# loader.py dagi debug=False ni debug=True o'zgartiring
```

### Log Misollar
```
2026-05-04 10:30:45 - bot - INFO - Configuring middleware...
2026-05-04 10:30:45 - bot - INFO - Starting bot polling...
2026-05-04 10:30:46 - loader - INFO - Bot initialized successfully
```

### Database Debug

```python
# loader.py
db = Database(path_to_db="main.db", debug=True)
```

Bu barcha SQL so'rovlarini konsolga chop etadi.

---

## 🔧 Muammolarni Hal Qilish

### ❌ Error: "ModuleNotFoundError: No module named 'aiogram'"
```bash
pip install -r requirements.txt
```

### ❌ Error: "BOT_TOKEN environment variable is not set"
```bash
# .env faylini tekshiring va BOT_TOKEN qo'shing
cat .env
```

### ❌ Bot ishga tushgani lekin komanda ishlama
```bash
# admin.py logging'ni tekshiring
# logger.error yoki logger.warning qidiring
```

### ❌ "Permission denied" kanalni qo'shganda
```
Bot kanalga admin sifatida qo'shilishi kerak!
Qadam:
1. Bot username'ini oling (BotFather-dan)
2. Kanalga admin qo'shing
3. Admin huquqlarini bering
4. Qaytadan urinib ko'ring
```

---

## 📊 Database Operatsiyalari

### Database Fayli
```
main.db - SQLite database
```

### Jadvallar
- **Users** - Foydalanuvchilar
- **Channels** - Obuna kanalları

### Backup Qilish
```bash
cp main.db main.db.backup
```

---

## 🌐 Bot Settings

### Bot Xususiyatlari

| Xususiyat | Qiymat | Maqsad |
|-----------|--------|--------|
| Parse Mode | HTML | Matn formatlash |
| Rate Limit | 0.5 sec | Spam oldi olish |
| Advert Delay | 0.01 sec | Telegram API cheklovi |
| Debug Mode | False | Production uchun |

### O'zgartirilgan Settings

`bot.py` dagi middleware:
```python
dp.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))
```

---

## 📈 Performance Tips

1. **Reklama yuborish** - Foydalanuvchi soniga qarab 1-2 daqiqa vaqt oladi
2. **Database** - Automatic indexing o'rnatilgan (tezroq)
3. **Logging** - INFO level (DEBUG emas production-da)
4. **Admin Lookup** - Set() foydalanish (tez)

---

## 🎯 Yangi Featurni Qo'shish

### 1. Yangi Komanda Qo'shish

Fayl: `handlers/users/mycommand.py`
```python
import logging
from aiogram.types import Message
from aiogram.filters import Command
from loader import dp

logger = logging.getLogger(__name__)

@dp.message(Command("mycommand"))
async def my_handler(message: Message) -> None:
    """Mening komandasi"""
    try:
        await message.answer("Assalom!")
        logger.info(f"Command executed by {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("Xato yuz berdi")
```

### 2. Database Method Qo'shish

Fayl: `baza/sqlite.py`
```python
def my_query(self, some_param: str) -> Optional[Tuple]:
    """Mening so'rovim"""
    sql = "SELECT * FROM Users WHERE full_name = ?"
    try:
        return self.execute(sql, parameters=(some_param,), fetchone=True)
    except Exception as e:
        logger.error(f"Failed: {e}")
        return None
```

### 3. Middleware Qo'shish

Fayl: `middlewares/mylogic.py`
```python
import logging
from aiogram import BaseMiddleware

logger = logging.getLogger(__name__)

class MyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logger.info(f"Event: {event}")
        return await handler(event, data)
```

---

## 📞 Savollar va Javoblar

**Q: Bot RAM tamashaini iste'mol qiladi?**
A: O'rtacha 50-100 MB. Katta ro'yxat uchun optimize qiling.

**Q: Database qayta boshlaysiz?**
A: `main.db` o'chirib qaytadan ishga tushiring.

**Q: Admin ID'ni qanday topaman?**
A: Botga /start bosing, logga qarang (user_id).

**Q: Reklama yuborish vaqtini kıskartsa bo'ladimi?**
A: Yo'q, Telegram API cheklovi. 0.01 sec qo'lin.

**Q: Yangi handler'ni qanday yuklayman?**
A: `handlers/__init__.py` ga `from . import mycommand` qo'shing.

---

## ✅ Production Checklist

```
[ ] .env fayli o'rnatilgan
[ ] BOT_TOKEN to'g'ri
[ ] ADMINS ID'lar to'g'ri  
[ ] main.db fayli o'chirilgan
[ ] logging level INFO
[ ] debug mode False
[ ] /start komandasi ishlaydi
[ ] Admin paneli ishlaydi
[ ] Reklama yuborish ishlaydi
[ ] Logs tekshirildi (xatolar yo'q)
```

---

## 🚀 Deploy Qilish

### Vercel (Freemium)
```bash
# requirements.txt bilan deploy
```

### Heroku (Legacy - To'lovli)
```bash
git push heroku main
```

### Local VPS / Server
```bash
# SSH orqali
ssh user@server.com
python bot.py &  # background da ishga tushirish
```

---

## 📚 Ko'shimcha Resurlar

- **Aiogram Docs:** https://docs.aiogram.dev/
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Python Docs:** https://docs.python.org/

---

## 🎓 Yangi Bo'lsangiz

1. Python basic'larni o'rganing
2. Async/await tushuntiring
3. Telegram Bot API tanishing
4. Aiogram dokumentatsiyani o'qing
5. Oddiy bot yarating
6. Bosqichma-bosqich murakkab qiling

---

**✅ Tayyor!** Siz hozir asosiy fayllarni o'zgartirishga tayyor.

**Oxirgi yangilash:** 2026-05-04  
**Versiya:** 1.0.0
