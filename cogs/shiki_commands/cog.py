from aiohttp import ClientResponseError
from discord import Interaction, Message
from discord.app_commands import guilds, command, AppCommandError
from discord.ext import commands

from clients.shikimori_client import BotShikiClient
from data import Vault

from .views import AuthorizeView
from clients import linked_role_client


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

        shiki_client = BotShikiClient()

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
            tokens = await shiki_client.get_access_token(view.auth_code)
        except ClientResponseError as e:
            print(e)  # TODO logging
            return await msg.edit(content="❎ Код неверный!")

        if tokens:
            await msg.edit(content="✅ Код верный!")
            self.shiki_tokens.save(interaction.user.id, tokens)
            await self.__update_info(client=shiki_client)
        else:
            await msg.edit(content="❎ Код неверный!")

    @command(name='update', description="Обновить информацию")
    async def update(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)  # noqa
        await self.__update_info(interaction.user.id)
        await interaction.response.send_message('Данные обновлены!')  # noqa

    async def __update_info(self, user_id: int = None, *, client: BotShikiClient = None):
        if not any([user_id, client]):
            raise ValueError('Must provide at list one argument')

        if not client:
            shiki_token = self.shiki_tokens.get(user_id)
            client = BotShikiClient(
                access_token=shiki_token.access_token,
                refresh_token=shiki_token.refresh_token,
                expires_at=shiki_token.expires_at,
            )

        shiki_info = await client.get_current_user_info()
        shiki_id = shiki_info['id']
        rates = await client.get_all_user_anime_rates(shiki_id, status='completed')
        # duration = await shiki_client.get_watch_time(shiki_id)  # float, in minutes

        data = {
            'shiki_id': shiki_id,
            'shiki_nickname': shiki_info.get('nickname'),
            'anime_watched': len(rates),
            # 'total_hours': int(duration / 60),
        }
        data = self.shiki_users.save(user_id, data)

        discord_token = self.discord_tokens.get(user_id)

        metadata = data.dict(exclude={'shiki_id', 'shiki_nickname'})
        try:
            await linked_role_client.push_metadata(
                user_id,
                discord_token.access_token,
                'Shikimori.me',  # TODO name as constant `Shikimori.me`
                metadata,
                platform_username=f"{data.shiki_nickname}",
            )
        except Exception as e:  # unauthorized ?
            linked_role_client.refresh_tokens(discord_token)
            await linked_role_client.push_metadata(
                user_id,
                discord_token.access_token,
                'Shikimori.me',  # TODO name as constant `Shikimori.me`
                metadata,
                platform_username=f"{data.shiki_nickname}",
            )

    @authorize.error
    async def authorize_error(self, interaction: Interaction, error: AppCommandError):
        print(error)

    @update.error
    async def update_error(self, interaction: Interaction, error: AppCommandError):
        print(error)

    @command(name='user', description="Показать информацию о пользователе с определённым ID")
    async def get_user_info(self, interaction: Interaction, shiki_id: int = 272747):
        """/api/users/:id/info"""
        await interaction.response.defer(thinking=True)
        user_info = await self.shiki_users.get_user_info(shiki_id)
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

    @get_user_info.error
    async def get_user_info_error(self, interaction: Interaction, error: AppCommandError):
        print(error)  # TODO logging
