import asyncio
import os

import discord

from tortoise import connections, Tortoise

from clients.bot import ShikimoriBot

from dotenv import load_dotenv
load_dotenv()

from cogs.shiki_commands.cog import ShikiCog
from cogs.ctx_commands.cog import ContextMenuCog
from cogs.manage_commangs.sync import SyncCog
from cogs.manage_commangs.cog import ManageCog


async def main():
    HOST = os.environ['DB_HOST']
    PORT = os.environ['DB_PORT']
    USER = os.environ['DB_USER']
    PASS = os.environ['DB_PASS']
    NAME = os.environ['DB_NAME']

    await Tortoise.init(
        db_url=f'mysql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}',
        modules={"models": ["data.models"]},
    )

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    my_bot = ShikimoriBot(
        command_prefix="!",
        intents=intents,
        status=discord.Status.idle,
        activity=discord.Game(name='/shikimori')
    )

    await my_bot.add_cog(ShikiCog())

    await my_bot.add_cog(ContextMenuCog(bot=my_bot))

    await my_bot.add_cog(ManageCog())

    await my_bot.add_cog(SyncCog())

    try:
        await my_bot.start(os.environ['BOT_TOKEN'])
    except KeyboardInterrupt:
        await my_bot.close()
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(main())
