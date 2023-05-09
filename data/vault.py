import inspect
from datetime import datetime
from typing import Protocol, TypeVar, Type

from mysql import connector
from mysql.connector import MySQLConnection, errorcode

from pydantic import BaseModel


_T = TypeVar('_T', bound=BaseModel)


class Vault(Protocol):
    def get(self, pk: int) -> _T:
        raise NotImplementedError

    def save(self, pk: int, data: _T) -> _T:
        raise NotImplementedError

    def update(self, pk: int, data: _T) -> None:
        raise NotImplementedError

    def delete(self, pk: int) -> None:
        raise NotImplementedError

    def erase(self) -> None:
        raise NotImplementedError


class MySQLVault(Vault):
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)

        db = kwargs.get('sql_db')
        prototype = kwargs.get('prototype')
        table_name = kwargs.get('table_name')

        if not cls.__is_table_exists(db, table_name):  # check if table exists
            if kwargs.pop('create', False):  # create table if `create` kwarg is `True`
                print(f"Creating '{table_name}' table")  # TODO logging
                cls.__create_table(db, table_name, prototype)
            else:
                raise Exception(f"Table '{table_name}' is not found!")  # or raise an exception

        return instance

    @classmethod
    def __create_table(cls, db: MySQLConnection, table_name: str, prototype: _T):
        DATATYPES = {  # TODO
            datetime: 'DATETIME',
            int: 'INT',
            str: 'VARCHAR(45)',
            float: 'FLOAT'
        }

        SQL = inspect.cleandoc(f"""
            CREATE TABLE {table_name} (
                `idtokens` INT UNSIGNED NOT NULL AUTO_INCREMENT,
                `user_id` BIGINT UNSIGNED NOT NULL, 
                {", ".join([f"`{k}` {DATATYPES[v.type_]} NOT NULL" for k, v in prototype.__fields__.items()])},
                PRIMARY KEY (`idtokens`)
            );
        """)
        cursor = db.cursor()
        cursor.execute(SQL)
        cursor.close()

    @classmethod
    def __is_table_exists(cls, db: MySQLConnection, table_name: str):
        SQL = f"SELECT 1 FROM {table_name} LIMIT 1;"

        cursor = db.cursor()

        try:
            cursor.execute(SQL)
        except connector.ProgrammingError as err:
            if err.errno == errorcode.ER_NO_SUCH_TABLE:
                return False
            raise
        finally:
            cursor.close()

        return True

    def __init__(
            self,
            *,
            sql_db: MySQLConnection,
            prototype: Type[_T],
            table_name: str,
            pk_name: str,
            **kwargs
    ):
        self.db = sql_db
        self.prototype = prototype
        self.table_name = table_name
        self.pk_name = pk_name

    def __clean_data(self, data: _T | dict) -> _T | None:
        if self.prototype.__name__ != data.__repr_name__():
            try:
                return data.parse_obj(data)
            except Exception as e:
                print(e)
                raise TypeError("Wrong type!")
        else:
            return data  # TODO add validation check ?

    def get(self, pk: int) -> BaseModel:
        fields = self.prototype.__fields__.keys()

        SQL = inspect.cleandoc(f"""
            SELECT {', '.join(fields)} 
            FROM {self.table_name} 
            WHERE {self.pk_name}='{pk}'
        """)

        cursor = self.db.cursor()
        cursor.execute(SQL)
        result = cursor.fetchone()
        cursor.close()

        return result and self.prototype.parse_obj(zip(fields, result))

    def save(self, pk: int, data: _T | dict) -> None:
        data = self.__clean_data(data)

        if self.get(pk):
            return self.update(pk, data)

        data = data.dict()

        SQL = inspect.cleandoc(f"""
            INSERT INTO {self.table_name} ({self.pk_name}, {', '.join(data.keys())}) 
            VALUES ('{pk}', '{"', '".join([str(v) for v in data.values()])}')
        """)

        cursor = self.db.cursor()
        cursor.execute(SQL)
        self.db.commit()
        cursor.close()

    def update(self, pk: int, data: _T) -> None:
        data = self.__clean_data(data)

        SQL = inspect.cleandoc(f"""
            UPDATE {self.table_name}
            SET {', '.join([f"{k} = '{v}'" for k, v in data.dict().items()])}
            WHERE {self.pk_name} = '{pk}';
        """)

        cursor = self.db.cursor()
        cursor.execute(SQL)
        self.db.commit()
        cursor.close()

    def delete(self, pk: int) -> None:
        SQL = inspect.cleandoc(f"""
            DELETE FROM {self.table_name} 
            WHERE {self.pk_name} = '{pk}';
        """)

        cursor = self.db.cursor()
        cursor.execute(SQL)
        self.db.commit()
        cursor.close()

    def erase(self):
        SQL = inspect.cleandoc(f"""
            DROP TABLE {self.table_name}
        """)

        cursor = self.db.cursor()
        cursor.execute(SQL)
        cursor.close()

# TODO logging
