from __future__ import annotations

import os

from datetime import datetime, timezone

from tortoise.models import Model
from tortoise import fields, Tortoise, run_async


class TokenModel(Model):
    user_id = fields.BigIntField()
    access_token = fields.CharField(max_length=60)
    refresh_token = fields.CharField(max_length=60)
    expires_in = fields.IntField()
    expires_at = fields.data.DatetimeField()

    def __str__(self):
        return f"{self.__name__}<{self.user_id}>"

    @property
    def is_expired(self):
        return datetime.now() > self.expires_at


class DiscordTokenModel(TokenModel):
    class Meta:
        table = 'discordtokens'


class ShikiTokenModel(TokenModel):
    class Meta:
        table = 'shikimoritokens'


class UserModel(Model):
    discord_user_id = fields.BigIntField()
    shikimori_user_id = fields.IntField(null=True)

    shikimori_nickname = fields.CharField(max_length=255, null=True)  # TODO find out max length
    anime_watched = fields.IntField(null=True)
    total_hours = fields.IntField(null=True)

    discord_token = fields.ForeignKeyField('models.DiscordTokenModel', null=True)
    shikimori_token = fields.ForeignKeyField('models.ShikiTokenModel', null=True)

    def __str__(self):
        return f"User<{self.shikimori_nickname}>"

    class Meta:
        table = 'users'


# import dotenv
# dotenv.load_dotenv('../.env')
#
# HOST = os.environ['DB_HOST']
# PORT = os.environ['DB_PORT']
# USER = os.environ['DB_USER']
# PASS = os.environ['DB_PASS']
# NAME = os.environ['DB_NAME']
#
# run_async(
#     Tortoise.init(
#         db_url=f'mysql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}',
#         modules={"models": ["__main__"]}
#     )
# )


if __name__ == '__main__':
    import os
    import dotenv
    from tortoise import Tortoise, run_async

    dotenv.load_dotenv('../.env')

    HOST = os.environ['DB_HOST']
    PORT = os.environ['DB_PORT']
    USER = os.environ['DB_USER']
    PASS = os.environ['DB_PASS']
    NAME = os.environ['DB_NAME']


    async def init():
        await Tortoise.init(
            db_url=f'mysql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}',
            modules={'models': ["__main__"]}
        )

        await Tortoise.generate_schemas()

    run_async(init())
