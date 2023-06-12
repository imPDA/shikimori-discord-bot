from discord import Interaction, Member
from discord.ext.commands import Cog, Bot
from discord.app_commands import ContextMenu

from data import Vault


class ContextMenuCog(Cog):
    # TODO description

    def __init__(self, bot: Bot, shiki_users_vault: Vault):
        super().__init__()

        self.shiki_users = shiki_users_vault
        self.bot = bot

    def cog_load(self) -> None:
        open_profile_ctx_command = ContextMenu(
            name='Профиль shikimori.me',
            callback=self.open_profile,
            guild_ids=[922919845450903573, 1115512510519443458],  # TODO discord.Object
        )
        open_profile_ctx_command.error(coro=self.open_profile_error)
        self.bot.tree.add_command(open_profile_ctx_command)

    async def open_profile(self, interaction: Interaction, member: Member):
        shiki_user = self.shiki_users.get(member.id)
        if not shiki_user:
            return await interaction.response.send_message(
                f"{member.mention} не связал профиль Шикимори с дискордом",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"Ссылка на Шикимори профиль {member.mention}: https://shikimori.me/{shiki_user.shiki_nickname}",
            suppress_embeds=True,
            ephemeral=True,
        )

    async def open_profile_error(self, interaction, error):
        print(error)  # TODO logging

# TODO оформление
