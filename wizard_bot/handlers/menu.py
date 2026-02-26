from wizard_bot.handlers.campaigns import render_campaigns
from wizard_bot.handlers.start import show_main
from wizard_bot.nav import routes
from wizard_bot.nav.stack import pop_route, push_route


async def handle_callback(data: str, chat_id: int, panel, redis, sb_client, settings) -> None:
    if data == f"nav:{routes.CAMPAIGNS_LIST}":
        await push_route(redis, chat_id, routes.CAMPAIGNS_LIST, routes.MAIN)
        await render_campaigns(panel, sb_client, chat_id, settings.WIZARD_CAMPAIGNS_PAGE_LIMIT)
        return

    if data == "act:refresh_campaigns":
        await render_campaigns(panel, sb_client, chat_id, settings.WIZARD_CAMPAIGNS_PAGE_LIMIT)
        return

    if data == "act:back":
        route = await pop_route(redis, chat_id, routes.MAIN)
        if route == routes.MAIN:
            await show_main(panel, redis, chat_id)
            return
        if route == routes.CAMPAIGNS_LIST:
            await render_campaigns(panel, sb_client, chat_id, settings.WIZARD_CAMPAIGNS_PAGE_LIMIT)
            return

    if data == f"nav:{routes.MAIN}":
        await show_main(panel, redis, chat_id)
