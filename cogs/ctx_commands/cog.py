from discord import Interaction, Member
from discord.ext.commands import Cog, Bot
from discord.app_commands import ContextMenu

from data.models import UserModel


class ContextMenuCog(Cog):
    # TODO description

    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    def cog_load(self) -> None:
        open_profile_ctx_command = ContextMenu(
            name="Профиль shikimori.me",
            callback=self.open_profile,
            guild_ids=[922919845450903573, 1115512510519443458],  # TODO discord.Object
        )
        open_profile_ctx_command.error(coro=self.open_profile_error)
        self.bot.tree.add_command(open_profile_ctx_command)

    async def open_profile(self, interaction: Interaction, member: Member):
        user_data: UserModel = await UserModel.get(discord_user_id=interaction.user.id)
        if not user_data.shikimori_user_id:
            return await interaction.response.send_message(
                f"{member.mention} не связал профиль Шикимори с дискордом",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"Ссылка на Шикимори профиль {member.mention}: https://shikimori.me/{user_data.shikimori_nickname}",
            suppress_embeds=True,
            ephemeral=True,
        )

    async def open_profile_error(self, interaction: Interaction, error):
        print(error)  # TODO logging
