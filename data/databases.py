import os

from mysql import connector
from .vault import MySQLVault
from .datatypes import DiscordToken, ShikiToken, ShikiUser

mydb = connector.connect(
    host=os.environ.get('DB_HOST'),
    port=os.environ.get('DB_PORT'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASS'),
    database=os.environ.get('DB_NAME'),
)

discord_tokens_vault = MySQLVault(
    sql_db=mydb,
    prototype=DiscordToken,
    table_name='shikimori_tokens',
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
