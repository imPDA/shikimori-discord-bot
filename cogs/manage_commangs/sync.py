from discord.ext.commands import command, Context, Cog
from discord.app_commands.checks import has_permissions


class SyncCog(Cog):
    # TODO description

    @command()
    @has_permissions(administrator=True)
    async def sync(self, ctx: Context) -> None:
        fmt = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(fmt)} commands globally"
        )

    @command(name='synchere')
    @has_permissions(administrator=True)
    async def sync_here(self, ctx: Context) -> None:
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)

        await ctx.send(
            f"Synced {len(fmt)} commands in {ctx.guild}"
        )

    @sync.error
    async def sync_error(self, ctx: Context, error):
        print(error)  # TODO logging

    @sync_here.error
    async def sync_here_error(self, ctx: Context, error):
        print(error)  # TODO logging
