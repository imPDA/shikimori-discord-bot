# TODO get rid of globals

import os
from datetime import datetime

from aiohttp import ClientResponseError
from discord import Interaction, Embed, app_commands
from discord.app_commands import guilds, command, AppCommandError, describe
from discord.ext import commands

from dlr_light_api import Client as DLRClient
from dlr_light_api.datatypes import DiscordToken

from shikimori_extended_api import Client as ShikiClient
from shikimori_extended_api.datatypes import ShikiToken

from data.datatypes import ShikiMetadata
from data.models import DiscordTokenModel, ShikiTokenModel, UserModel

from .views import CheckAuthorizationView

ROOT_URL = 'https://shikimori.me'


# https://stackoverflow.com/questions/48255244/python-check-if-a-string-contains-cyrillic-characters
def contains_cyrillic(string: str) -> bool:
    return len(string.encode("ascii", "ignore")) < len(string)


def field_value(text: str) -> str:
    return text[:1024-3] + "..." if len(text) > 1024 else text


shiki_client = ShikiClient(
    application_name=os.environ['SHIKI_APPLICATION_NAME'],
    client_id=os.environ['SHIKI_CLIENT_ID'],
    client_secret=os.environ['SHIKI_CLIENT_SECRET'],
    redirect_uri='https://impda.duckdns.org:500/shikimori-oauth-callback'
)

dlr_client = DLRClient(
    client_id=os.environ['DLR_CLIENT_ID'],
    client_secret=os.environ['DLR_CLIENT_SECRET'],
    redirect_uri=os.environ['DLR_REDIRECT_URI'],
    discord_token=os.environ['BOT_TOKEN']
)


# TODO unify ShikiToken and DiscordToken
def shiki_token_from_model(token_model: ShikiTokenModel) -> ShikiToken:
    return ShikiToken(
        access_token=token_model.access_token,
        refresh_token=token_model.refresh_token,
        expires_in=token_model.expires_in,
        expires_at=token_model.expires_at
    )


def discord_token_from_model(token_model: DiscordTokenModel) -> DiscordToken:
    return DiscordToken(
        access_token=token_model.access_token,
        refresh_token=token_model.refresh_token,
        expires_in=token_model.expires_in,
        expires_at=token_model.expires_at
    )


@guilds(922919845450903573, 1115512510519443458)
class ShikiCog(commands.GroupCog, group_name='shikimori', group_description='...'):
    # TODO description

    # TODO move check authorization to token functionality
    async def check_shiki_authorization(self, shiki_token: ShikiTokenModel | ShikiToken) -> bool:
        if isinstance(shiki_token, ShikiTokenModel):
            shiki_token = shiki_token_from_model(shiki_token)

        try:
            user_info = await shiki_client.get_current_user_info(shiki_token)
        except ClientResponseError:
            user_info = None

        return True if user_info else False

    # TODO move check authorization to token functionality
    async def check_discord_authorization(self, discord_token: DiscordTokenModel) -> bool:
        if isinstance(discord_token, DiscordTokenModel):
            discord_token = discord_token_from_model(discord_token)

        metadata = await dlr_client.get_metadata(discord_token)

        return True if metadata else False

    def _made_message(self, shiki_auth: bool, discord_auth: bool) -> str:
        return f"{'✅' if shiki_auth else '❎'} Shikimori\n{'✅' if discord_auth else '❎'} Discord"

    @command(description="Проверить авторизацию")
    async def check_auth(self, interaction: Interaction):
        user = await UserModel.get_or_none(discord_user_id=interaction.user.id)  # TODO preload tokens?
        if not user:
            return await interaction.response.send_message(self._made_message(False, False), ephemeral=True)

        shiki_auth = (token := await user.shikimori_token) and await self.check_shiki_authorization(token)
        discord_auth = (token := await user.discord_token) and await self.check_discord_authorization(token)

        await interaction.response.send_message(self._made_message(shiki_auth, discord_auth), ephemeral=True)

    @command(name='authorize', description="Авторизоваться")
    async def authorize(self, interaction: Interaction):
        view = CheckAuthorizationView()
        await interaction.response.send_message(
            f"Нужно перейти по [ссылке](https://impda.duckdns.org:500/shikimori-auth?user_id={interaction.user.id}), войти под своим профилем и авторизовать бота\n",
            view=view,
            suppress_embeds=True,
            ephemeral=True,
        )

    @command(name='update', description="Обновить информацию")
    @describe(update_watch_time="Обновить время просмотра тоже (долго!)")
    async def update(self, interaction: Interaction, update_watch_time: bool = False):
        await interaction.response.defer(thinking=True, ephemeral=True)  # noqa
        user_data = await UserModel.get_or_none(discord_user_id=interaction.user.id)

        if not user_data:
            return await interaction.edit_original_response(content="Пользователь не найден")  # never authorized

        # TODO create function to check if shiki token is still good
        # so to check if user still granted access to shiki account
        # if not = do not update and delete from database

        updated_shiki_user_info = await shiki_client.go().users.id(user_data.shikimori_user_id).get()

        duration = await shiki_client.fetch_total_watch_time(updated_shiki_user_info['id']) if update_watch_time \
            else 0  # float, minutes

        # find out amount of anime completed
        anime_completed = 0
        rate_groups = updated_shiki_user_info['stats']['statuses']['anime']
        for rate_group in rate_groups:
            if rate_group['name'] == 'completed':
                anime_completed = rate_group['size']
                break

        # update data in database
        user_data = await user_data.update_from_dict({
            'shikimori_nickname': updated_shiki_user_info['nickname'],
            'anime_watched': anime_completed,
            'total_hours': duration,
        })

        discord_token_data = await DiscordTokenModel.get_or_none(user_id=interaction.user.id)
        if not discord_token_data:
            return interaction.edit_original_response(content="Нет привязки дискорда, обновление невозможно")

        # convert from database format to `DiscordToken`
        discord_token = discord_token_from_model(discord_token_data)
        if discord_token.is_expired:  # update token if expired and save new one in database
            discord_token = await dlr_client.refresh_token(discord_token)
            await discord_token_data.update_from_dict({
                'access_token': discord_token.access_token,
                'refresh_token': discord_token.refresh_token,
                'expires_in': int(discord_token.expires_in.total_seconds()),
                'expires_at': discord_token.expires_at,
            })

        # create metadata and push it to discord server
        metadata = ShikiMetadata(
            platform_username=user_data.shikimori_nickname,
            titles_watched=user_data.anime_watched,
            hours_watching=user_data.total_hours
        )
        await dlr_client.push_metadata(discord_token, metadata)

    @command(name='user', description="Показать информацию о пользователе")
    async def get_user_info(self, interaction: Interaction, name_or_id: str):
        """/api/users/:id/info or /api/users?search=:nickname"""
        await interaction.response.defer(thinking=True)

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
    async def name_or_id_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        global shiki_client

        if current.isdigit():
            user = await shiki_client.get_user_info(int(current))
            return [app_commands.Choice(name=user['nickname'], value=str(user['id'])), ]

        if len(current) < 3:
            return []

        users = await shiki_client.go().users(search=current.lower(), limit=20).get()  # real Discord limit is 25?
        return [app_commands.Choice(name=user['nickname'], value=str(user['id'])) for user in users]

    @command(name='anime', description="Показать информацию об аниме")
    async def get_anime_info(self, interaction: Interaction, name_or_id: str):
        """/api/animes/:id or /api/animes?search=:name"""
        await interaction.response.defer(thinking=True)

        anime_id = int(name_or_id)

        anime_info = await shiki_client.get_anime(anime_id)

        embed = Embed(
            title=f"{anime_info['russian']}\n{anime_info['japanese']}",
            url=f"{ROOT_URL}{anime_info['url']}",
            timestamp=datetime.now(),
        )
        embed.set_image(url=f"{ROOT_URL}{anime_info['image']['original']}")  # original / preview (?^?)

        if not (score := float(anime_info.get('score', 0))):
            scores = anime_info.get('rates_scores_stats', [{'name': 0, 'value': 1}])
            score = sum([int(r['name']) * int(r['value']) for r in scores]) / sum([int(r['value']) for r in scores])
        embed.add_field(name="Оценка", value=f"{score:.2f}")

        if anime_info.get('status', '') == 'released':
            episodes = f"{anime_info.get('episodes', '-')} (завершено)"
        else:
            episodes = f"{anime_info.get('episodes_aired', '-')} / {anime_info.get('episodes', '-')}"
        embed.add_field(name="Эпизоды", value=episodes)

        embed.add_field(name="Длительность", value=f"{anime_info.get('duration', '-')} мин")

        genres = ', '.join([g['russian'] for g in anime_info.get('genres', [])]) or "-"
        embed.add_field(name="Жанры", value=genres)

        rating = anime_info.get('rating').replace('_', '-').upper() or "-"
        embed.add_field(name="Рейтинг", value=rating)

        embed.add_field(name="Описание", value=field_value(anime_info.get('description', "-")), inline=False)

        embed.set_footer(text="shikimori.me", icon_url='https://shikimori.me/favicons/favicon-192x192.png')
        await interaction.edit_original_response(embed=embed)

    @get_anime_info.autocomplete('name_or_id')
    async def name_or_id_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        global shiki_client

        if current.isdigit():
            user = await shiki_client.get_anime(int(current))
            return [app_commands.Choice(name=user['russian'], value=str(user['id'])), ]

        if len(current) < 3:
            return []

        animes = await shiki_client.go().animes(search=current.lower(), limit=20).get()  # real Discord limit is 25?
        if contains_cyrillic(current):
            return [app_commands.Choice(name=anime['russian'], value=str(anime['id'])) for anime in animes]
        else:
            return [app_commands.Choice(name=anime['name'], value=str(anime['id'])) for anime in animes]

    @authorize.error
    async def authorize_error(self, interaction: Interaction, error: AppCommandError):
        print(error)

    @update.error
    async def update_error(self, interaction: Interaction, error: AppCommandError):
        print(error)

    @check_auth.error
    async def check_auth_error(self, interaction: Interaction, error: AppCommandError):
        print(error)  # TODO logging

    @get_user_info.error
    async def get_user_info_error(self, interaction: Interaction, error: AppCommandError):
        print(error)  # TODO logging

    @get_anime_info.error
    async def get_anime_info_error(self, interaction: Interaction, error: AppCommandError):
        print(error)  # TODO logging
