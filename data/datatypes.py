from pydantic import BaseModel
from datetime import datetime


class DiscordToken(BaseModel):
    type: str
    access_token: str
    refresh_token: str
    expires_at: datetime = None

    @property
    def is_fresh(self):
        return datetime.now() < self.expires_at


class ShikiToken(BaseModel):
    type: str = 'Bearer'
    access_token: str
    refresh_token: str
    expires_at: datetime = None

    @property
    def is_fresh(self):
        return datetime.now() < self.expires_at


class ShikiUser(BaseModel):
    shiki_id: int = 0
    shiki_nickname: str = ''
    anime_watched: int = 0
    total_hours: int = 0
