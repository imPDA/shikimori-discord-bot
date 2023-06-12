from __future__ import annotations

from datetime import datetime, timezone

from tortoise.models import Model
from tortoise import fields


class Token(Model):
    user_id = fields.BigIntField()
    access_token = fields.CharField(max_length=60)
    refresh_token = fields.CharField(max_length=60)
    expires_in = fields.IntField()
    expires_at = fields.data.DatetimeField()

    def __str__(self):
        return f"{self.__name__}<{self.user_id}>"

    @property
    def is_expired(self):
        return datetime.now(tz=timezone.utc) > self.expires_at


class DiscordToken(Token):
    pass


class ShikiToken(Token):
    pass


class User(Model):
    discord_user_id = fields.BigIntField()
    shiki_user_id = fields.IntField()

    shiki_nickname = fields.CharField(max_length=255)
    anime_watched = fields.IntField()
    total_hours = fields.IntField()

    discord_token = fields.ForeignKeyField('models.DiscordToken', null=True)
    shiki_token = fields.ForeignKeyField('models.ShikiToken', null=True)

    def __str__(self):
        return f"User<{self.shiki_nickname}>"


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
