from dlr_light_api.datatypes import MetadataField, MetadataType, Metadata
from pydantic import BaseModel


class ShikiUser(BaseModel):
    shiki_id: int = 0
    shiki_nickname: str = ''
    anime_watched: int = 0
    total_hours: int = 0


class ShikiMetadata(Metadata):
    platform_name: str = 'shikimori.me'
    titles_watched = MetadataField(MetadataType.INT_GTE, 'аниме просмотрено', 'или больше тайтлов')
    hours_watching = MetadataField(MetadataType.INT_GTE, 'часов за проcмотром', 'часов или больше')
