import os

from mysql import connector

from shikimori_extended_api.datatypes import ShikiToken
from dlr_light_api.datatypes import DiscordToken
from data.datatypes import ShikiUser

from .vault import MySQLVault

mydb = connector.connect(
    host=os.environ['DB_HOST'],
    port=os.environ['DB_PORT'],
    user=os.environ['DB_USER'],
    password=os.environ['DB_PASS'],
    database=os.environ['DB_NAME'],
)

discord_tokens_vault = MySQLVault(
    sql_db=mydb,
    prototype=DiscordToken,
    table_name='discord_tokens',
    pk_name='user_id',
    create=True
)

shiki_tokens_vault = MySQLVault(
    sql_db=mydb,
    prototype=ShikiToken,
    table_name='shikimori_tokens',
    pk_name='user_id',
    create=True
)

shiki_users_vault = MySQLVault(
    sql_db=mydb,
    prototype=ShikiUser,
    table_name='shikimori_users',
    pk_name='user_id',
    create=True
)
