from discord.ext.commands import Bot
from discord import Guild


class ShikimoriBot(Bot):
    # TODO description

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (ID: {self.user.id})")   # TODO logging

    async def on_guild_join(self, guild: Guild):
        print(f"Joined {guild.name} (ID {guild.id})")  # TODO logging
