import os
import uuid
from urllib.parse import urlencode

from dlr_light_api import Client
from shikimori_extended_api import Client as ShikiClient
from dlr_light_api.datatypes import DiscordToken
from flask import Flask, redirect, request, Response, make_response
from flask.sessions import SecureCookieSessionInterface


import dotenv
dotenv.load_dotenv('../.env')
print(os.environ.get('CLIENT_ID'))


from data.datatypes import ShikiMetadata
from data.databases import discord_tokens_vault
from data.databases import shiki_users_vault
from data.databases import shiki_tokens_vault

app = Flask(__name__)
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
def linked_role():
    url, state = linked_role_client.oauth_url

    response = make_response(redirect(url))
    response.set_cookie(key='clientState', value=state, max_age=60 * 5)

    return response


@app.route('/discord-oauth-callback')
async def discord_oauth_callback():
    discord_state = request.args.get('state')
    client_state = request.cookies.get('clientState')
    if client_state != discord_state:
        return Response("State verification failed.", status=403)

    try:
        code = request.args['code']
        token = await linked_role_client.get_oauth_token(code)

        print("Authorised, token acquired!")

        user_data = await linked_role_client.get_user_data(token)
        user_id = int(user_data['user']['id'])
        discord_tokens_vault.save(user_id, token)

        await _update_metadata(user_id)

        return redirect(REDIRECT_URL)
    except Exception as e:
        return Response(str(e), status=500)


@app.route('/update-metadata', methods=['POST'])
async def update_metadata():
    try:
        user_id = int(request.form['userId'])
        await _update_metadata(user_id)

        return Response(status=204)
    except Exception as e:
        return Response(str(e), status=500)


async def _update_metadata(user_id: int):
    token: DiscordToken = discord_tokens_vault.get(user_id)

    if token.is_expired:
        token = await linked_role_client.refresh_token(token)
        discord_tokens_vault.save(user_id, token)

    shiki_user = shiki_users_vault.get(user_id)
    metadata = ShikiMetadata(
        platform_username=shiki_user.shiki_nickname,
        titles_watched=shiki_user.anime_watched,
        hours_watching=shiki_user.total_hours
    )

    print('a:', metadata.to_dict())

    await linked_role_client.push_metadata(token, metadata)
    print(await linked_role_client.get_metadata(token))


@app.route('/shikimori-auth')
def shikimori_auth():
    response = make_response(redirect(shiki_client.auth_url))
    return response


@app.route('/shikimori-oauth-callback')
async def shikimori_oauth_callback():
    code = request.args.get("code")
    print(code)
    token = await shiki_client.get_access_token(code)
    user = await shiki_client.get_current_user_info(token)
    print(user)
    print(user['id'])
    print(token)
    shiki_tokens_vault.save(user['id'], token)

    return redirect("https://shikimori.me/")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')

    # Now if you run this code and navigate to https://yourwebsite/linked-role you will be redirected to Discord
    # authorization page. After confirmation, you will receive token and then redirected to `REDIRECT_URL`.
