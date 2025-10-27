from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура для админского подтверждения/отклонения задания
def admin_confirm_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Tasdiqlash ✅", 
                    callback_data=f"admin_accept_{submission_id}"
                ),
                InlineKeyboardButton(
                    text="Rad etish ❌", 
                    callback_data=f"admin_reject_{submission_id}"
                )
            ]
        ]
    )


# Клавиатура для кнопки "Tayyorman" / "Boshlash" для пользователя
def user_ready_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Tayyorman", callback_data="ready")]
        ]
    )

# Клавиатура для окончания дня / урока
def finish_day_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Darsni tugatdim", callback_data="finish_lesson")]
        ]
    )

# Клавиатура для начала выполнения задания
def task_submit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Topshiriqni bajarish", callback_data="do_task")]
        ]
    )
