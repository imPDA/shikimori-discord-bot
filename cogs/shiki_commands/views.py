from discord import Interaction, ui, TextStyle


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
    async def button_with_link(self, interaction: Interaction, button):
        modal = AuthCodeModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.auth_code = modal.code.value
        self.stop()

    # TODO abort button
