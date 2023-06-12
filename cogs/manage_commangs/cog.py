import os

from discord import Interaction

from discord.ext import commands

from discord.app_commands import guilds, command, AppCommandError
from discord.app_commands.checks import has_permissions

from dlr_light_api import Client as DLRClient

from data.datatypes import ShikiMetadata


@guilds(922919845450903573, 1115512510519443458)
@has_permissions(administrator=True)
class ManageCog(commands.GroupCog, group_name='shikimori_manage', group_description='...'):

    @command(name='register_dlr_schema', description="Обновить DLR схему")
    async def register_dlr_schema(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)  # noqa

        dlr_client = DLRClient(
            client_id=os.environ['DLR_CLIENT_ID'],
            client_secret=os.environ['DLR_CLIENT_SECRET'],
            redirect_uri=os.environ['DLR_REDIRECT_URI'],
            discord_token=os.environ['BOT_TOKEN']
        )

        response = await dlr_client.register_metadata_schema(ShikiMetadata)  # noqa
        if response == ShikiMetadata.to_schema():
            await interaction.edit_original_response(content="Успешно обновлено!")
        else:
            await interaction.edit_original_response(content=f"**Ошибка**\n\n*{response}*")

    @register_dlr_schema.error
    async def register_dlr_schema_error(self, interaction: Interaction, error: AppCommandError):
        print(error)  # TODO logging
