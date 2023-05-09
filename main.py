import asyncio
import os

import discord

from discord import Intents

from clients.bot import ShikimoriBot

from cogs.shiki_commands.cog import ShikiCog
from cogs.ctx_commands.cog import ContextMenuCog


from data import discord_tokens_vault, shiki_tokens_vault, shiki_users_vault


async def main():
    DISCORD_TOKEN = os.environ['BOT_TOKEN']

    intents = Intents.default()
    intents.message_content = True
    intents.members = True

    my_bot = ShikimoriBot(
        command_prefix="!",
        intents=intents,
        status=discord.Status.idle,
        activity=discord.Game(name='/shikimori'),

    )

    await my_bot.add_cog(ShikiCog(
        discord_tokens_vault=discord_tokens_vault,
        shiki_tokens_vault=shiki_tokens_vault,
        shiki_users_vault=shiki_users_vault
    ))

    await my_bot.add_cog(ContextMenuCog(
        bot=my_bot,
        shiki_users_vault=shiki_users_vault
    ))

    try:
        await my_bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await my_bot.close()


if __name__ == '__main__':
    asyncio.run(main())

# TODO help command
