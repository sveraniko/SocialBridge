from wizard_bot.nav.routes import MAIN
from wizard_bot.nav.stack import reset_stack
from wizard_bot.ui.keyboards import main_menu_keyboard


async def show_main(panel, redis, chat_id: int) -> None:
    await reset_stack(redis, chat_id, MAIN)
    await panel.render(
        chat_id=chat_id,
        text="Campaign Wizard\n\nChoose an action:",
        keyboard=main_menu_keyboard(),
    )
