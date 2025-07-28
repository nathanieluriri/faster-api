import os
from dotenv import load_dotenv

load_dotenv()

# Choose between 'sqlite' or 'mongodb'
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

if DB_TYPE == "sqlite":
    # SQLite setup
    import sqlite3

    database_name = "db.db"

    class DBFunctions:
        def __init__(self, table_name):
            self.table_name = table_name

        @staticmethod
        def __insert(table_name: str, data: dict):
            if not table_name.isidentifier():
                raise ValueError("Invalid table name")

            keys = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            values = tuple(data.values())

            if table_name == "password_reset_token":
                query = f"INSERT OR REPLACE INTO {table_name} ({keys}) VALUES ({placeholders})"
            else:
                query = f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})"

            with sqlite3.connect(database_name) as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                return cursor.lastrowid

        @staticmethod
        def __update(table_name: str, data: dict, filter_dict: dict):
            if not table_name.isidentifier():
                raise ValueError("Invalid table name")

            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            where_clause = " AND ".join([f"{k} = ?" for k in filter_dict.keys()])
            values = list(data.values()) + list(filter_dict.values())

            query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

            with sqlite3.connect(database_name) as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount

        @staticmethod
        def __delete(table_name: str, filter_dict: dict, limit: int = None):
            if not table_name.isidentifier():
                raise ValueError("Invalid table name")

            where_clause = " AND ".join([f"{k} = ?" for k in filter_dict])
            values = list(filter_dict.values())

            if limit is not None:
                query = f"""
                    DELETE FROM {table_name}
                    WHERE rowid IN (
                        SELECT rowid FROM {table_name}
                        WHERE {where_clause}
                        LIMIT ?
                    )
                """
                values.append(limit)
            else:
                query = f"DELETE FROM {table_name} WHERE {where_clause}"

            with sqlite3.connect(database_name) as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount

        def insert_one(self, data: dict) -> str:
            return self.__insert(table_name=self.table_name, data=data)

        def update_one(self, filter_dict: dict, data: dict) -> int:
            return self.__update(filter_dict=filter_dict, table_name=self.table_name, data=data)

        def delete_one(self, filter_dict: dict) -> int:
            return self.__delete(table_name=self.table_name, filter_dict=filter_dict, limit=1)

        def delete_many(self, filter_dict: dict, limit: int = None) -> int:
            return self.__delete(table_name=self.table_name, filter_dict=filter_dict, limit=limit)

        def find_one(self, filter_dict: dict) -> dict:
            if not filter_dict:
                raise ValueError("Filter dictionary cannot be empty.")

            with sqlite3.connect(database_name) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                where_clause = " AND ".join(f"{key} = ?" for key in filter_dict)
                values = tuple(filter_dict.values())
                query = f"SELECT * FROM {self.table_name} WHERE {where_clause} LIMIT 1"
                cursor.execute(query, values)
                row = cursor.fetchone()
                return dict(row) if row else None

        def find(self, filter_dict: dict = None, limit: int = None, skip: int = None) -> list:
            with sqlite3.connect(database_name) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                where_clause = ""
                values = []

                if filter_dict:
                    where_clause = "WHERE " + " AND ".join(f"{k} = ?" for k in filter_dict)
                    values.extend(filter_dict.values())

                limit_clause = f"LIMIT {limit}" if limit is not None else ""
                offset_clause = f"OFFSET {skip}" if skip is not None else ""

                query = f"SELECT * FROM {self.table_name} {where_clause} {limit_clause} {offset_clause}".strip()
                cursor.execute(query, tuple(values))
                results = cursor.fetchall()
                return [dict(row) for row in results]

        def update_all_rows(self, key: str, value):
            with sqlite3.connect(database_name) as conn:
                cursor = conn.cursor()
                query = f"UPDATE {self.table_name} SET {key} = ?"
                cursor.execute(query, (value,))
                conn.commit()

    class DBWrapper:
        def __getattr__(self, table_name):
            return DBFunctions(table_name)

    db = DBWrapper()

elif DB_TYPE == "mongodb":
    from motor.motor_asyncio import AsyncIOMotorClient

    DB = os.getenv("DB_NAME")
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB]

else:
    raise ValueError("Unsupported DB_TYPE. Must be either 'sqlite' or 'mongodb'.")
