import os

from shikimori_extended_api import Client


class BotShikiClient(Client):
    def __init__(
            self,
            **kwargs,
    ):
        super().__init__(
            application_name=os.environ.get('SHIKI_APPLICATION_NAME'),
            client_id=os.environ.get('SHIKI_CLIENT_ID'),
            client_secret=os.environ.get('SHIKI_CLIENT_SECRET'),
            **kwargs
        )
