import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, MEDIA_DIR
import database
from handlers.admin import admin_router
from handlers.user import user_router


# === Создание dispatcher и bot ===
dp = Dispatcher()
dp.include_router(admin_router)
dp.include_router(user_router)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

# === Webhook config ===
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://YOUR-KOYEB-APP.koyeb.app")  # ⚠️ замени после деплоя
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"


# === Startup / Shutdown ===
async def on_startup(app: web.Application):
    os.makedirs(MEDIA_DIR, exist_ok=True)
    await database.init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook установлен:", WEBHOOK_URL)


async def on_shutdown(app: web.Application):
    await bot.session.close()
    print("🛑 Bot остановлен")


# === Основная функция ===
def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
