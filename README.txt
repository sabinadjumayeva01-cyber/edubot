Training Bot (Telegram) - README
--------------------------------
Tuzuvchi: ChatGPT (auto-generated)
Ishga tushirish:
  1) Python 3.11 tavsiya etiladi.
  2) Virtual muhit yarating va faollashtiring.
  3) pip install -r requirements.txt
  4) ENV (Koyeb) yoki localda config.py ichiga BOT_TOKEN va ADMIN_ID tekshiring.
  5) python main.py

Koyeb uchun:
  - Koyeb-da repo yaratib zip ichidagi fayllarni yuklang yoki GitHubdan deploy qiling.
  - Procfile worker: python main.py

Muhim:
  - Ushbu loyiha aiogram kutubxonasiga tayanadi.
  - Token va admin id loyihaga joylangan (siz bergan).
  - Agar tokenni .env yoki Koyeb env vars orqali saqlashni istasangiz,
    config.py ichidagi BOT_TOKEN o'rniga os.environ.get('BOT_TOKEN') ishlatishingiz mumkin.

Fayl tuzilmasi:
  main.py - botni ishga tushiruvchi
  config.py - token va admin id
  database.py - SQLite bog'lanish va helper funktsiyalar
  handlers/ - foydalanuvchi va admin handlerlar
  utils/ - yordamchi fayllar (keyboards, states)
  data/lessons - yuklangan lesson fayllari
  bot.db - bo'sh yoki boshlang'ich bazasi
  requirements.txt - bog'liqliklar
  Procfile, runtime.txt
