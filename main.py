import asyncio
import os

import discord

from discord import Intents
from tortoise import Tortoise

from clients.bot import ShikimoriBot

from dotenv import load_dotenv
load_dotenv()

HOST = os.environ['DB_HOST']
PORT = os.environ['DB_PORT']
USER = os.environ['DB_USER']
PASS = os.environ['DB_PASS']
NAME = os.environ['DB_NAME']

from cogs.shiki_commands.cog import ShikiCog
from cogs.ctx_commands.cog import ContextMenuCog
from cogs.manage_commangs.sync import SyncCog
from cogs.manage_commangs.cog import ManageCog

from data import discord_tokens_vault, shiki_tokens_vault, shiki_users_vault


async def main():
    intents = Intents.default()
    intents.message_content = True
    intents.members = True

    my_bot = ShikimoriBot(
        command_prefix="!",
        intents=intents,
        status=discord.Status.idle,
        activity=discord.Game(name='/shikimori')
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

    await my_bot.add_cog(ManageCog())

    await my_bot.add_cog(SyncCog())

    await Tortoise.init(
        db_url=f'mysql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}',
        modules={"models": ["data.models"]}
    )

    try:
        await my_bot.start(os.environ['BOT_TOKEN'])
    except KeyboardInterrupt:
        await my_bot.close()
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(main())
