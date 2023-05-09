import os
import uuid
from datetime import datetime, timedelta

import aiohttp

from data import DiscordToken


class Error401(Exception):
    ...


class LinkedRoleAPI:
    def __init__(self, client_id: int, redirect_uri: str, client_secret: str):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret

    @property
    def oauth_url(self) -> (str, str):
        state = str(uuid.uuid4())
        ROOT = 'https://discord.com/api/oauth2/authorize'
        query = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': state,
            'scope': 'role_connections.write identify',
            'prompt': 'consent',
        }
        url = ROOT + '?' + '&'.join([f'{k}={v}' for k, v in query.items()])

        return url, state

    async def get_oauth_token(self, code: str) -> DiscordToken:
        URL = 'https://discord.com/api/v10/oauth2/token'

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(URL, data=data) as response:
                if response.status == 200:
                    data = await response.json()
                    return DiscordToken(
                        type=data['token_type'],
                        access_token=data['access_token'],
                        refresh_token=data['refresh_token'],
                        expires_at=datetime.now() + timedelta(seconds=data['expires_in']),
                    )
                else:
                    raise Exception(f"Error fetching OAuth tokens: {response.status}, {await response.text()}")

    async def get_refresh_tokens(self, token: DiscordToken) -> DiscordToken:
        URL = 'https://discord.com/api/v10/oauth2/token'

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': token.refresh_token,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(URL, data=data) as response:
                if response.status == 200:
                    data = await response.json()
                    return DiscordToken(
                        type=data['token_type'],
                        access_token=data['access_token'],
                        refresh_token=data['refresh_token'],
                        expires_at=datetime.now() + timedelta(seconds=data['expires_in']),
                    )
                else:
                    raise Exception(f"Error refreshing access token: {response.status}, {await response.text()}")

    @staticmethod
    async def get_user_data(token: DiscordToken) -> dict:
        URL = 'https://discord.com/api/v10/oauth2/@me'
        headers = {
            'Authorization': f'Bearer {token.access_token}',
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(URL) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Error fetching user data: {response.status}, {await response.text()}")

    async def push_metadata(
            self,
            user_id: int,
            access_token: str,
            platform_name: str,
            metadata: dict,
            platform_username: str = None
    ) -> None:
        # GET/PUT /users/@me/applications/:id/role-connection
        URL = f'https://discord.com/api/v10/users/@me/applications/{self.client_id}/role-connection'

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        data = {
            'platform_name': platform_name,
            'metadata': metadata,
        }
        if platform_username:
            data.update({'platform_username': platform_username})

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.put(URL, data=json.dumps(data)) as response:
                if response.status == 401:
                    raise Error401(f"Error pushing discord metadata: {response.status}, {await response.text()}, {headers}")

                if response.status != 200:
                    raise Exception(f"Error pushing discord metadata: {response.status}, {await response.text()}")

    async def get_metadata(self, user_id: int, access_token: str) -> dict:
        # GET/PUT /users/@me/applications/:id/role-connection
        URL = f'https://discord.com/api/v10/users/@me/applications/{self.client_id}/role-connection'

        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(URL) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Error getting discord metadata: {response.status}, {await response.text()}")


linked_role_client = LinkedRoleAPI(
    client_id=int(os.environ.get('LR_CLIENT_ID')),
    client_secret=os.environ.get('LR_CLIENT_SECRET'),
    redirect_uri=os.environ.get('LR_REDIRECT_URI')
)
