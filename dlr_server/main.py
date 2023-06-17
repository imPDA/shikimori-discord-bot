import asyncio
import os

from quart import Quart, redirect, request, Response, make_response
from quart.sessions import SecureCookieSessionInterface

from hypercorn import Config
from hypercorn.asyncio import serve

import tortoise.contrib.quart

from data.models import DiscordTokenModel, ShikiTokenModel, UserModel
from data.datatypes import ShikiMetadata

from shikimori_extended_api import Client as ShikiClient
from dlr_light_api.datatypes import DiscordToken
from dlr_light_api import Client

import dotenv
dotenv.load_dotenv()

app = Quart(__name__)
app.secret_key = os.environ.get('COOKIE_SECRET')
session_serializer = SecureCookieSessionInterface().get_signing_serializer(app)

REDIRECT_URL = 'https://discord.com/app'


linked_role_client = Client(
    client_id=os.environ['DLR_CLIENT_ID'],
    client_secret=os.environ['DLR_CLIENT_SECRET'],
    redirect_uri=os.environ['DLR_REDIRECT_URI'],
    discord_token=os.environ['BOT_TOKEN']
)

shiki_client = ShikiClient(
    application_name=os.environ['SHIKI_APPLICATION_NAME'],
    client_id=os.environ['SHIKI_CLIENT_ID'],
    client_secret=os.environ['SHIKI_CLIENT_SECRET'],
    redirect_uri='https://impda.duckdns.org:500/shikimori-oauth-callback'
)


@app.route('/linked-role')
async def linked_role():
    global linked_role_client

    url, state = linked_role_client.oauth_url

    response = await make_response(redirect(url))
    response.set_cookie(key='clientState', value=state, max_age=60 * 5)

    return response


@app.route('/discord-oauth-callback')
async def discord_oauth_callback():
    global linked_role_client

    discord_state = request.args.get('state')
    client_state = request.cookies.get('clientState')
    if client_state != discord_state:
        return Response("State verification failed.", status=403)

    try:
        code = request.args['code']
        token = await linked_role_client.get_oauth_token(code)
        user_data = await linked_role_client.get_user_data(token)
        user_id = int(user_data['user']['id'])

        token_data, _ = await DiscordTokenModel.update_or_create(
            user_id=user_id,
            defaults={
                'access_token': token.access_token,
                'refresh_token': token.refresh_token,
                'expires_in': int(token.expires_in.total_seconds()),
                'expires_at': token.expires_at,
            }
        )
        await UserModel.update_or_create(
            discord_user_id=user_id,
            defaults={'discord_token_id': token_data.pk}
        )

        try:
            await _update_metadata(user_id)  # must provide metadata to Discord!  # TODO flask.g
        except Exception as e:
            # if metadata not updated properly - just log it  # TODO logging
            print('Error updating metadata after discord oauth callback:', e)

        return redirect(REDIRECT_URL)
    except Exception as e:
        return Response(str(e), status=500)


# @app.route('/update-metadata', methods=['POST'])
# async def update_metadata():
#     try:
#         user_id = int(request.form['userId'])
#         await _update_metadata(user_id)
#
#         return Response(status=204)
#     except Exception as e:
#         return Response(str(e), status=500)


async def _update_metadata(discord_user_id: int):
    global linked_role_client

    user_data = await UserModel.get_or_none(discord_user_id=discord_user_id)
    if not user_data:
        raise KeyError(f"Error updating the user: no user with id {discord_user_id} found.")

    token_data = await user_data.discord_token
    if not token_data:
        raise KeyError(f"Error updating the user: user {discord_user_id} doesnt have Discord token.")

    token = DiscordToken(  # TODO replace by function
        user_id=token_data.user_id,
        access_token=token_data.access_token,
        refresh_token=token_data.refresh_token,
        expires_in=token_data.expires_in,
        expires_at=token_data.expires_at.replace(tzinfo=None)
    )

    if token.is_expired:
        token = await linked_role_client.refresh_token(token)
        await token_data.update_from_dict({
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'expires_in': int(token.expires_in.total_seconds()),
            'expires_at': token.expires_at,
        })

    metadata = ShikiMetadata(
        platform_username=user_data.shikimori_nickname,
        titles_watched=user_data.anime_watched,
        hours_watching=user_data.total_hours
    )

    await linked_role_client.push_metadata(token, metadata)


@app.route('/shikimori-auth')
async def shikimori_auth():
    # this path is redirecting to shiki auth page
    discord_user_id = request.args.get('user_id')  # TODO: change to userId
    response = redirect(shiki_client.auth_url)
    response.set_cookie('user_id', discord_user_id, max_age=5 * 60)  # TODO: change to userId

    return response


@app.route('/shikimori-oauth-callback')
async def shikimori_oauth_callback():
    global shiki_client

    code = request.args.get('code')
    try:
        token = await shiki_client.get_access_token(code)
        user_info = await shiki_client.get_current_user_info(token)
    except Exception as e:
        return Response(str(e), status=500)
    else:
        shiki_token_data, _ = await ShikiTokenModel.update_or_create(
            user_id=user_info['id'],
            defaults={
                'access_token': token.access_token,
                'refresh_token': token.refresh_token,
                'expires_in': token.expires_in.total_seconds(),
                'expires_at': token.expires_at
            }
        )

        additional_data = await shiki_client.go().users.id(272747).get()

        # find out amount of anime completed
        anime_completed = 0
        rate_groups = additional_data['stats']['statuses']['anime']
        for rate_group in rate_groups:
            if rate_group['name'] == 'completed':
                anime_completed = rate_group['size']
                break

        discord_user_id = int(request.cookies.get('user_id'))  # TODO: change to userId
        await UserModel.update_or_create(
            discord_user_id=discord_user_id,
            defaults={
                'shikimori_user_id': user_info['id'],
                'shikimori_nickname': user_info['nickname'],
                'shikimori_token_id': shiki_token_data.pk,
                'anime_watched': anime_completed
            }
        )

        # TODO try to fix ugly code (2x try-except blocks)
        try:
            await _update_metadata(discord_user_id)  # must provide metadata to Discord!
        except Exception as e:
            # if metadata not updated properly - just log it  # TODO logging
            print('Error updating metadata after shikimori oauth callback:', e)

    return redirect("https://shikimori.me/")  # TODO get rid of hardcode


HOST = os.environ['DB_HOST']
PORT = os.environ['DB_PORT']
USER = os.environ['DB_USER']
PASS = os.environ['DB_PASS']
NAME = os.environ['DB_NAME']

tortoise.contrib.quart.register_tortoise(
    app,
    db_url=f'mysql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}',
    modules={"models": ["data.models"]},
)


# to silence SSL errors
def _exception_handler(loop, context):
    exception = context.get("exception")
    import ssl
    if isinstance(exception, ssl.SSLError):
        pass
    else:
        loop.default_exception_handler(context)


shutdown_event = asyncio.Event()


def _signal_handler(*_: any) -> None:
    shutdown_event.set()


if __name__ == '__main__':
    config = Config()
    config.bind = ['0.0.0.0:5000']
    config.keyfile = os.environ['CERT_KEY']
    config.certfile = os.environ['CERT_FILE']

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_exception_handler)
    # loop.add_signal_handler(signal.SIGTERM, _signal_handler)

    loop.run_until_complete(serve(app, config, shutdown_trigger=lambda: asyncio.Future()))

    # app.run(host='0.0.0.0', port=5000, debug=True)
