import os
from datetime import datetime

from aiohttp import ClientResponseError
from discord import Interaction, Message, Embed, app_commands
from discord.app_commands import guilds, command, AppCommandError
from discord.ext import commands
from dlr_light_api import Client as DLRClient
from dlr_light_api.datatypes import DiscordToken

from shikimori_extended_api import Client as ShikiClient

from data import Vault
from data.datatypes import ShikiMetadata, ShikiUser

from .views import AuthorizeView


@guilds(922919845450903573, )
class ShikiCog(commands.GroupCog, group_name='shikimori', group_description='...'):
    # TODO description

    def __init__(self, discord_tokens_vault: Vault, shiki_tokens_vault: Vault, shiki_users_vault: Vault):
        super().__init__()

        self.discord_tokens = discord_tokens_vault
        self.shiki_tokens = shiki_tokens_vault
        self.shiki_users = shiki_users_vault

    @command(name='authorize', description="Авторизоваться")
    async def authorize(self, interaction: Interaction):
        view = AuthorizeView()

        shiki_client = ShikiClient(
            application_name=os.environ['SHIKI_APPLICATION_NAME'],
            client_id=os.environ['SHIKI_CLIENT_ID'],
            client_secret=os.environ['SHIKI_CLIENT_SECRET']
        )

        await interaction.response.send_message(  # noqa
            f"1) Перейди по [ссылке]({shiki_client.auth_url}) и авторизуйся на Шикимори\n"
            f"2) Нажми на кнопку и введи полученный код авторизации",
            view=view,
            suppress_embeds=True,
            ephemeral=True,
        )
        await view.wait()

        msg: Message = await interaction.followup.send("Проверяю код...", ephemeral=True)
        try:
            print(view.auth_code)
            token = await shiki_client.get_access_token(view.auth_code)
        except ClientResponseError as e:
            print(e)  # TODO logging
            return await msg.edit(content="❎ Код неверный!")

        if token:
            await msg.edit(content="✅ Код верный!")
            self.shiki_tokens.save(interaction.user.id, token)
            await self._update_info(interaction.user.id)
        else:
            await msg.edit(content="❎ Код неверный!")

    @command(name='update', description="Обновить информацию")
    async def update(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)  # noqa
        await self._update_info(interaction.user.id)
        await interaction.edit_original_response(content="Данные обновлены!")

    async def _update_info(self, user_id: int) -> bool:
        discord_token: DiscordToken = self.discord_tokens.get(user_id)
        if not discord_token:
            return False

        shiki_user = await self._get_shiki_user(user_id)
        print('Sh1ki user:', shiki_user)
        self.shiki_users.save(user_id, shiki_user)

        metadata = ShikiMetadata(
            platform_username=shiki_user.shiki_nickname,
            titles_watched=shiki_user.anime_watched,
            hours_watching=shiki_user.total_hours
        )

        dlr_client = DLRClient(
            client_id=os.environ['DLR_CLIENT_ID'],
            client_secret=os.environ['DLR_CLIENT_SECRET'],
            redirect_uri=os.environ['DLR_REDIRECT_URI'],
            discord_token=os.environ['BOT_TOKEN']
        )

        if discord_token.is_expired:
            discord_token = await dlr_client.refresh_token(discord_token)
            self.discord_tokens.update(user_id, discord_token)

        await dlr_client.push_metadata(discord_token, metadata)

    async def _get_shiki_user(self, user_id: int, count_watchtime: bool = False) -> ShikiUser:
        shiki_token = self.shiki_tokens.get(user_id)
        shiki_client = ShikiClient(
            application_name=os.environ['SHIKI_APPLICATION_NAME'],
            client_id=os.environ['SHIKI_CLIENT_ID'],
            client_secret=os.environ['SHIKI_CLIENT_SECRET']
        )

        shiki_info = await shiki_client.get_current_user_info(shiki_token)
        shiki_id = shiki_info['id']
        rates = await shiki_client.get_all_user_anime_rates(shiki_id, status='completed')
        duration = await shiki_client.get_watch_time(shiki_id) if count_watchtime else 0  # float, in minutes

        return ShikiUser(
            shiki_id=shiki_id,
            shiki_nickname=shiki_info.get('nickname'),
            anime_watched=len(rates),
            total_hours=int(duration / 60)
        )

    @authorize.error
    async def authorize_error(self, interaction: Interaction, error: AppCommandError):
        print(error)

    @update.error
    async def update_error(self, interaction: Interaction, error: AppCommandError):
        print(error)

    @command(name='user', description="Показать информацию о пользователе")
    async def get_user_info(self, interaction: Interaction, name_or_id: str):
        """/api/users/:id/info"""
        await interaction.response.defer(thinking=True)

        shiki_client = ShikiClient(
            application_name=os.environ['SHIKI_APPLICATION_NAME'],
            client_id=os.environ['SHIKI_CLIENT_ID'],
            client_secret=os.environ['SHIKI_CLIENT_SECRET']
        )

        shiki_id = int(name_or_id)
        user_info = await shiki_client.get_user_info(shiki_id)

        embed = Embed(
            title=f"{user_info['nickname']} /{user_info['id']}/",
            url=user_info['url'],
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=user_info['image']['x160'])

        sex = {'male': 'Мужской', 'female': 'Женский'}
        embed.add_field(name="Пол", value=sex.get(user_info['sex'], "Неизвестно"))
        embed.add_field(name="День рождения", value=user_info.get('birth_on', "Неизвестно"))
        embed.add_field(name="Полных лет", value=user_info.get('full_years', "Неизвестно"))
        embed.add_field(
            name="Последний раз онлайн",
            value=user_info.get('last_online_at') and datetime.fromisoformat(user_info.get('last_online_at'))
            .strftime('%d.%m.%Y %H:%M')
        )

        embed.set_footer(text="shikimori.me", icon_url='https://shikimori.me/favicons/favicon-192x192.png')
        await interaction.edit_original_response(embed=embed)

    @get_user_info.autocomplete('name_or_id')
    async def user_key_autocomplete(
            self,
            interaction: Interaction,
            current: str
    ) -> list[app_commands.Choice[str]]:
        if current.isdigit():
            shiki_client = ShikiClient(
                application_name=os.environ['SHIKI_APPLICATION_NAME'],
                client_id=os.environ['SHIKI_CLIENT_ID'],
                client_secret=os.environ['SHIKI_CLIENT_SECRET']
            )
            user = await shiki_client.get_user_info(int(current))
            return [app_commands.Choice(name=user['nickname'], value=str(user['id'])), ]

        if len(current) < 3:
            return []

        shiki_client = ShikiClient(
            application_name=os.environ['SHIKI_APPLICATION_NAME'],
            client_id=os.environ['SHIKI_CLIENT_ID'],
            client_secret=os.environ['SHIKI_CLIENT_SECRET']
        )
        users = await shiki_client.go().users(search=current.lower(), limit=20).get()  # real Discord limit is 25?
        return [app_commands.Choice(name=user['nickname'], value=str(user['id'])) for user in users]

    @get_user_info.error
    async def get_user_info_error(self, interaction: Interaction, error: AppCommandError):
        print(error)  # TODO logging
