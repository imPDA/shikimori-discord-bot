from discord import Interaction, ui, TextStyle
from discord.ui import Item
from shikimori_extended_api.datatypes import ShikiToken

from data.models import UserModel, ShikiTokenModel


class CheckAuthorizationView(ui.View):
    @ui.button(label="Проверить авторизацию")
    async def check_button(self, interaction: Interaction, button) -> None:
        # check if there is a fresh token in DB. If so: authorized
        user: UserModel = await UserModel.get_or_none(discord_user_id=interaction.user.id)  # noqa
        # shiki_id = shiki_users_vault.get(interaction.user.id).shiki_id
        token_data: ShikiTokenModel = await user.shikimori_token
        token = ShikiToken(
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            expires_in=token_data.expires_in,
            expires_at=token_data.expires_at
        )
        if token and not token.is_expired:
            await interaction.response.send_message("Авторизован!", ephemeral=True)
        else:
            await interaction.response.send_message("Не авторизован!", ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item[any], /) -> None:
        print(error)  # TODO logging


class AuthCodeModal(ui.Modal, title="Код авторизации"):
    code = ui.TextInput(label="Код", style=TextStyle.short, placeholder="Код из 43 символов")

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        self.stop()


class AuthorizeView(ui.View):
    def __init__(self):
        super().__init__()
        self.auth_code = None

    @ui.button(label='Ввести код')
    async def button_with_link(self, interaction: Interaction, button):  # why it is the `button with link` ?
        modal = AuthCodeModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.auth_code = modal.code.value
        self.stop()

    # TODO abort button
