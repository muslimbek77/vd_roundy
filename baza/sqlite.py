import logging
import json
import sqlite3
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2 import Error as PostgresError
except ImportError:  # pragma: no cover - installed in prod/venv
    psycopg2 = None
    PostgresError = Exception

logger = logging.getLogger(__name__)

BACKUP_TABLES = (
    "Users",
    "Channels",
    "ChannelJoins",
    "Meta",
    "Admins",
    "BannedUsers",
    "SupportThreads",
)


class Database:
    def __init__(
        self,
        path_to_db: str = "main.db",
        debug: bool = False,
        database_url: Optional[str] = None,
    ):
        self.path_to_db = path_to_db
        self.debug = debug
        self.database_url = database_url
        self.db_type = "postgres" if database_url and database_url.startswith("postgres") else "sqlite"
        self._init_db()

    def _init_db(self) -> None:
        """Bazaga ulanishni tekshirish"""
        connection = None
        try:
            connection = self.connection
            if self.db_type == "sqlite":
                connection.execute("PRAGMA foreign_keys = ON")
            logger.info("Database initialized successfully using %s", self.db_type)
        except Exception as error:
            logger.error("Failed to initialize database: %s", error)
            raise
        finally:
            if connection is not None:
                connection.close()

    @property
    def connection(self):
        """Bazaga ulanish yaratish"""
        if self.db_type == "postgres":
            if psycopg2 is None:
                raise RuntimeError("psycopg2 is not installed")

            parsed = urlparse(self.database_url)
            connection = psycopg2.connect(
                dbname=parsed.path.lstrip("/"),
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
            )
            connection.autocommit = False
            return connection

        conn = sqlite3.connect(self.path_to_db)
        conn.execute("PRAGMA foreign_keys = ON")
        if self.debug:
            conn.set_trace_callback(self._log_sql)
        return conn

    @staticmethod
    def _log_sql(statement: str) -> None:
        logger.debug("SQL: %s", statement)

    def _rewrite_sql(self, sql: str) -> str:
        if self.db_type != "postgres":
            return sql

        return (
            sql.replace("?", "%s")
            .replace("INTEGER PRIMARY KEY", "BIGINT PRIMARY KEY")
            .replace("INSERT OR REPLACE INTO", "INSERT INTO")
        )

    def execute(
        self,
        sql: str,
        parameters: Tuple = None,
        fetchone: bool = False,
        fetchall: bool = False,
        commit: bool = False,
    ) -> Optional[Any]:
        """SQL so'rovni bajarish"""
        if parameters is None:
            parameters = ()

        connection = self.connection
        cursor = connection.cursor()
        data = None
        query = self._rewrite_sql(sql)

        try:
            cursor.execute(query, parameters)

            if commit:
                connection.commit()

            if fetchall:
                data = cursor.fetchall()
            elif fetchone:
                data = cursor.fetchone()

            return data
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Database error: %s\nSQL: %s\nParams: %s", error, query, parameters)
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def execute_script(self, sql: str) -> None:
        """Bir nechta SQL statementlarni ketma-ket bajarish"""
        statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
        connection = self.connection
        cursor = connection.cursor()
        try:
            for statement in statements:
                cursor.execute(self._rewrite_sql(statement))
            connection.commit()
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Database script error: %s\nSQL: %s", error, sql)
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def create_table_users(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS Users (
            full_name TEXT,
            telegram_id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_telegram_id ON Users(telegram_id);
        """
        try:
            self.execute_script(sql)
            self._ensure_column("Users", "created_at", "TIMESTAMP")
            self._ensure_column("Users", "last_seen_at", "TIMESTAMP")
            self._ensure_column("Users", "is_active", "INTEGER DEFAULT 1")
            self.execute(
                "UPDATE Users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;",
                commit=True,
            )
            self.execute(
                "UPDATE Users SET last_seen_at = CURRENT_TIMESTAMP WHERE last_seen_at IS NULL;",
                commit=True,
            )
            self.execute(
                "UPDATE Users SET is_active = 1 WHERE is_active IS NULL;",
                commit=True,
            )
            logger.info("Users table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create users table: %s", error)

    def create_table_channels(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS Channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_link TEXT NOT NULL,
            channel_mode TEXT DEFAULT 'regular',
            target_count INTEGER DEFAULT 0,
            joined_count INTEGER DEFAULT 0,
            is_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_channel_id ON Channels(channel_id);
        """
        try:
            self.execute_script(sql)
            self._ensure_column("Channels", "created_at", "TIMESTAMP")
            self._ensure_column("Channels", "channel_mode", "TEXT DEFAULT 'regular'")
            self._ensure_column("Channels", "target_count", "INTEGER DEFAULT 0")
            self._ensure_column("Channels", "joined_count", "INTEGER DEFAULT 0")
            self._ensure_column("Channels", "is_enabled", "INTEGER DEFAULT 1")
            self.execute(
                "UPDATE Channels SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;",
                commit=True,
            )
            self.execute(
                "UPDATE Channels SET channel_mode = 'regular' WHERE channel_mode IS NULL OR channel_mode = '';",
                commit=True,
            )
            self.execute(
                "UPDATE Channels SET target_count = 0 WHERE target_count IS NULL;",
                commit=True,
            )
            self.execute(
                "UPDATE Channels SET joined_count = 0 WHERE joined_count IS NULL;",
                commit=True,
            )
            self.execute(
                "UPDATE Channels SET is_enabled = 1 WHERE is_enabled IS NULL;",
                commit=True,
            )
            logger.info("Channels table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create channels table: %s", error)

    def create_table_channel_joins(self) -> None:
        if self.db_type == "postgres":
            sql = """
            CREATE TABLE IF NOT EXISTS ChannelJoins (
                channel_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_channel_joins_user ON ChannelJoins(user_id);
            """
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS ChannelJoins (
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_channel_joins_user ON ChannelJoins(user_id);
            """
        try:
            self.execute_script(sql)
            self._ensure_channel_joins_bigint()
            logger.info("ChannelJoins table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create channel joins table: %s", error)

    def _ensure_channel_joins_bigint(self) -> None:
        if self.db_type != "postgres":
            return

        connection = self.connection
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'channeljoins' AND column_name = 'channel_id';
                """
            )
            channel_id_type = cursor.fetchone()
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'channeljoins' AND column_name = 'user_id';
                """
            )
            user_id_type = cursor.fetchone()

            if channel_id_type and channel_id_type[0] != "bigint":
                cursor.execute("ALTER TABLE ChannelJoins ALTER COLUMN channel_id TYPE BIGINT;")
            if user_id_type and user_id_type[0] != "bigint":
                cursor.execute("ALTER TABLE ChannelJoins ALTER COLUMN user_id TYPE BIGINT;")
            connection.commit()
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to ensure bigint columns for ChannelJoins: %s", error)
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def create_table_meta(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS Meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
        try:
            self.execute_script(sql)
            logger.info("Meta table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create meta table: %s", error)

    def create_table_admins(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS Admins (
            admin_id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.execute_script(sql)
            logger.info("Admins table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create admins table: %s", error)

    def create_table_bans(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS BannedUsers (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            banned_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.execute_script(sql)
            logger.info("BannedUsers table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create banned users table: %s", error)

    def create_table_support_threads(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS SupportThreads (
            user_id INTEGER PRIMARY KEY,
            admin_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            is_open INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.execute_script(sql)
            logger.info("SupportThreads table created successfully")
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to create support threads table: %s", error)

    def _ensure_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        if self.has_column(table_name, column_name):
            return

        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        self.execute(alter_sql, commit=True)
        logger.info("Column %s added to %s", column_name, table_name)

    def has_column(self, table_name: str, column_name: str) -> bool:
        if self.db_type == "postgres":
            sql = """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            LIMIT 1;
            """
            return bool(self.execute(sql, parameters=(table_name.lower(), column_name), fetchone=True))

        sql = f"PRAGMA table_info({table_name})"
        columns = self.execute(sql, fetchall=True) or []
        return any(column[1] == column_name for column in columns)

    def has_table(self, table_name: str) -> bool:
        if self.db_type == "postgres":
            sql = """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            LIMIT 1;
            """
            return bool(self.execute(sql, parameters=(table_name.lower(),), fetchone=True))

        sql = """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1;
        """
        return bool(self.execute(sql, parameters=(table_name,), fetchone=True))

    def export_backup(self, file_path: str) -> str:
        connection = self.connection
        cursor = connection.cursor()
        payload: dict[str, Any] = {
            "db_type": self.db_type,
            "tables": {},
        }

        try:
            for table_name in BACKUP_TABLES:
                if not self.has_table(table_name):
                    continue

                cursor.execute(self._rewrite_sql(f"SELECT * FROM {table_name};"))
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description or []]
                payload["tables"][table_name] = {
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows],
                }

            with open(file_path, "w", encoding="utf-8") as backup_file:
                json.dump(payload, backup_file, ensure_ascii=False, indent=2, default=str)

            return file_path
        finally:
            cursor.close()
            connection.close()

    def add_user(self, telegram_id: int, full_name: str) -> bool:
        if self.select_user(telegram_id=telegram_id):
            logger.warning("User %s already exists", telegram_id)
            return False

        if self.db_type == "postgres":
            sql = """
            INSERT INTO Users (telegram_id, full_name)
            VALUES(%s, %s)
            ON CONFLICT (telegram_id) DO NOTHING;
            """
        else:
            sql = """
            INSERT INTO Users (telegram_id, full_name) VALUES(?, ?);
            """

        try:
            self.execute(sql, parameters=(telegram_id, full_name), commit=True)
            logger.info("User added: %s", telegram_id)
            return True
        except (sqlite3.IntegrityError, PostgresError):
            logger.warning("User %s already exists", telegram_id)
            return False

    def ensure_admins(self, admin_ids: List[int]) -> None:
        for admin_id in admin_ids:
            self.add_admin(admin_id)

    def add_admin(self, admin_id: int) -> None:
        if self.db_type == "postgres":
            sql = """
            INSERT INTO Admins (admin_id)
            VALUES(%s)
            ON CONFLICT (admin_id) DO NOTHING;
            """
        else:
            sql = """
            INSERT OR IGNORE INTO Admins (admin_id)
            VALUES(?);
            """
        self.execute(sql, parameters=(admin_id,), commit=True)

    def remove_admin(self, admin_id: int) -> None:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        self.execute(
            f"DELETE FROM Admins WHERE admin_id = {placeholder};",
            parameters=(admin_id,),
            commit=True,
        )

    def is_admin(self, admin_id: int) -> bool:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        result = self.execute(
            f"SELECT 1 FROM Admins WHERE admin_id = {placeholder} LIMIT 1;",
            parameters=(admin_id,),
            fetchone=True,
        )
        return bool(result)

    def count_admins(self) -> int:
        try:
            result = self.execute("SELECT COUNT(*) FROM Admins;", fetchone=True)
            return result[0] if result else 0
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to count admins: %s", error)
            return 0

    def list_admin_ids(self) -> List[int]:
        try:
            rows = self.execute("SELECT admin_id FROM Admins ORDER BY admin_id;", fetchall=True) or []
            return [row[0] for row in rows]
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to list admins: %s", error)
            return []

    def list_admins_with_names(self) -> List[Tuple[int, Optional[str]]]:
        try:
            rows = self.execute(
                """
                SELECT a.admin_id, u.full_name
                FROM Admins a
                LEFT JOIN Users u ON u.telegram_id = a.admin_id
                ORDER BY a.admin_id;
                """,
                fetchall=True,
            ) or []
            return [(row[0], row[1]) for row in rows]
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to list admins with names: %s", error)
            return []

    def list_removable_admins_with_names(self, protected_admin_ids: List[int]) -> List[Tuple[int, Optional[str]]]:
        admins = self.list_admins_with_names()
        protected = set(protected_admin_ids)
        return [admin for admin in admins if admin[0] not in protected]

    def ban_user(self, user_id: int, banned_by: int, reason: str = "Admin tomonidan bloklandi") -> None:
        if self.db_type == "postgres":
            sql = """
            INSERT INTO BannedUsers (user_id, reason, banned_by)
            VALUES(%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET reason = EXCLUDED.reason,
                banned_by = EXCLUDED.banned_by;
            """
        else:
            sql = """
            INSERT OR REPLACE INTO BannedUsers (user_id, reason, banned_by)
            VALUES(?, ?, ?);
            """
        self.execute(sql, parameters=(user_id, reason, banned_by), commit=True)
        self.set_user_active(user_id, False)

    def is_banned(self, user_id: int) -> bool:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        result = self.execute(
            f"SELECT 1 FROM BannedUsers WHERE user_id = {placeholder} LIMIT 1;",
            parameters=(user_id,),
            fetchone=True,
        )
        return bool(result)

    def open_support_thread(self, user_id: int, admin_id: int, mode: str) -> None:
        if self.db_type == "postgres":
            sql = """
            INSERT INTO SupportThreads (user_id, admin_id, mode, is_open)
            VALUES(%s, %s, %s, 1)
            ON CONFLICT (user_id) DO UPDATE
            SET admin_id = EXCLUDED.admin_id,
                mode = EXCLUDED.mode,
                is_open = 1;
            """
        else:
            sql = """
            INSERT OR REPLACE INTO SupportThreads (user_id, admin_id, mode, is_open)
            VALUES(?, ?, ?, 1);
            """
        self.execute(sql, parameters=(user_id, admin_id, mode), commit=True)

    def get_open_support_thread(self, user_id: int) -> Optional[Tuple]:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        return self.execute(
            f"""
            SELECT user_id, admin_id, mode
            FROM SupportThreads
            WHERE user_id = {placeholder} AND is_open = 1
            LIMIT 1;
            """,
            parameters=(user_id,),
            fetchone=True,
        )

    def close_support_thread(self, user_id: int) -> None:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        self.execute(
            f"UPDATE SupportThreads SET is_open = 0 WHERE user_id = {placeholder};",
            parameters=(user_id,),
            commit=True,
        )

    def update_user_profile(self, telegram_id: int, full_name: str) -> None:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        sql = f"""
        UPDATE Users
        SET full_name = {placeholder}
        WHERE telegram_id = {placeholder};
        """
        self.execute(sql, parameters=(full_name, telegram_id), commit=True)

    def touch_user(self, telegram_id: int, full_name: Optional[str] = None) -> None:
        if self.select_user(telegram_id=telegram_id) is None:
            if full_name is None:
                full_name = "Unknown"
            self.add_user(telegram_id=telegram_id, full_name=full_name)
            return

        if self.db_type == "postgres":
            params: Tuple[Any, ...] = (telegram_id,)
            assignments = ["last_seen_at = CURRENT_TIMESTAMP", "is_active = 1"]
            if full_name is not None:
                assignments.insert(0, "full_name = %s")
                params = (full_name, telegram_id)
            sql = f"""
            UPDATE Users
            SET {", ".join(assignments)}
            WHERE telegram_id = %s;
            """
        else:
            params = (telegram_id,)
            assignments = ["last_seen_at = CURRENT_TIMESTAMP", "is_active = 1"]
            if full_name is not None:
                assignments.insert(0, "full_name = ?")
                params = (full_name, telegram_id)
            sql = f"""
            UPDATE Users
            SET {", ".join(assignments)}
            WHERE telegram_id = ?;
            """

        self.execute(sql, parameters=params, commit=True)

    def set_user_active(self, telegram_id: int, is_active: bool) -> None:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        sql = f"""
        UPDATE Users
        SET is_active = {placeholder}
        WHERE telegram_id = {placeholder};
        """
        self.execute(sql, parameters=(1 if is_active else 0, telegram_id), commit=True)

    def add_channel(
        self,
        channel_id: int,
        channel_name: str,
        channel_link: str,
        channel_mode: str = "regular",
        target_count: int = 0,
        joined_count: int = 0,
        is_enabled: bool = True,
    ) -> None:
        if self.db_type == "postgres":
            sql = """
            INSERT INTO Channels (
                channel_id,
                channel_name,
                channel_link,
                channel_mode,
                target_count,
                joined_count,
                is_enabled
            )
            VALUES(%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (channel_id) DO UPDATE
            SET channel_name = EXCLUDED.channel_name,
                channel_link = EXCLUDED.channel_link,
                channel_mode = EXCLUDED.channel_mode,
                target_count = EXCLUDED.target_count,
                joined_count = EXCLUDED.joined_count,
                is_enabled = EXCLUDED.is_enabled;
            """
        else:
            sql = """
            INSERT OR REPLACE INTO Channels (
                channel_id,
                channel_name,
                channel_link,
                channel_mode,
                target_count,
                joined_count,
                is_enabled
            )
            VALUES(?, ?, ?, ?, ?, ?, ?);
            """

        self.execute(
            sql,
            parameters=(
                channel_id,
                channel_name,
                channel_link,
                channel_mode,
                target_count,
                joined_count,
                1 if is_enabled else 0,
            ),
            commit=True,
        )
        logger.info("Channel added: %s", channel_id)

    def select_all_channels(self, detailed: bool = False, active_only: bool = False) -> List[Tuple]:
        order_clause = " ORDER BY created_at DESC" if self.has_column("Channels", "created_at") else ""
        where_clause = " WHERE is_enabled = 1" if active_only and self.has_column("Channels", "is_enabled") else ""
        if detailed:
            sql = (
                "SELECT channel_id, channel_name, channel_link, channel_mode, target_count, joined_count, is_enabled "
                f"FROM Channels{where_clause}{order_clause}"
            )
        else:
            sql = f"SELECT channel_id, channel_name, channel_link FROM Channels{where_clause}{order_clause}"
        try:
            return self.execute(sql, fetchall=True) or []
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to select channels: %s", error)
            return []

    def get_channel(self, channel_id: int) -> Optional[Tuple]:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        try:
            return self.execute(
                f"""
                SELECT channel_id, channel_name, channel_link, channel_mode, target_count, joined_count, is_enabled
                FROM Channels
                WHERE channel_id = {placeholder}
                LIMIT 1;
                """,
                parameters=(channel_id,),
                fetchone=True,
            )
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to get channel: %s", error)
            return None

    def has_channel_join(self, channel_id: int, user_id: int) -> bool:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        try:
            result = self.execute(
                f"""
                SELECT 1
                FROM ChannelJoins
                WHERE channel_id = {placeholder} AND user_id = {placeholder}
                LIMIT 1;
                """,
                parameters=(channel_id, user_id),
                fetchone=True,
            )
            return bool(result)
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to check channel join: %s", error)
            return False

    def disable_channel(self, channel_id: int) -> None:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        self.execute(
            f"UPDATE Channels SET is_enabled = 0 WHERE channel_id = {placeholder};",
            parameters=(channel_id,),
            commit=True,
        )

    def record_channel_join(self, channel_id: int, user_id: int) -> bool:
        connection = self.connection
        cursor = connection.cursor()
        try:
            if self.db_type == "postgres":
                cursor.execute(
                    """
                    INSERT INTO ChannelJoins (channel_id, user_id)
                    VALUES(%s, %s)
                    ON CONFLICT (channel_id, user_id) DO NOTHING;
                    """,
                    (channel_id, user_id),
                )
                inserted = cursor.rowcount > 0
                if inserted:
                    cursor.execute(
                        """
                        UPDATE Channels
                        SET joined_count = joined_count + 1
                        WHERE channel_id = %s;
                        """,
                        (channel_id,),
                    )
            else:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO ChannelJoins (channel_id, user_id)
                    VALUES(?, ?);
                    """,
                    (channel_id, user_id),
                )
                inserted = cursor.rowcount > 0
                if inserted:
                    cursor.execute(
                        """
                        UPDATE Channels
                        SET joined_count = joined_count + 1
                        WHERE channel_id = ?;
                        """,
                        (channel_id,),
                    )

            connection.commit()
            return inserted
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to record channel join: %s", error)
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def delete_channel(self, channel_id: int) -> None:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        self.execute(
            f"DELETE FROM Channels WHERE channel_id = {placeholder}",
            parameters=(channel_id,),
            commit=True,
        )
        logger.info("Channel deleted: %s", channel_id)

    def select_all_users(self) -> List[Tuple]:
        order_clause = " ORDER BY created_at DESC" if self.has_column("Users", "created_at") else ""
        sql = f"SELECT full_name, telegram_id FROM Users{order_clause}"
        try:
            return self.execute(sql, fetchall=True) or []
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to select users: %s", error)
            return []

    def select_user(self, **kwargs) -> Optional[Tuple]:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        conditions = " AND ".join([f"{item} = {placeholder}" for item in kwargs])
        sql = f"SELECT full_name, telegram_id FROM Users WHERE {conditions}"
        try:
            return self.execute(sql, parameters=tuple(kwargs.values()), fetchone=True)
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to select user: %s", error)
            return None

    def count_users(self) -> int:
        try:
            result = self.execute("SELECT COUNT(*) FROM Users;", fetchone=True)
            return result[0] if result else 0
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to count users: %s", error)
            return 0

    def count_active_users(self) -> int:
        try:
            result = self.execute("SELECT COUNT(*) FROM Users WHERE is_active = 1;", fetchone=True)
            return result[0] if result else 0
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to count active users: %s", error)
            return 0

    def count_inactive_users(self) -> int:
        try:
            result = self.execute("SELECT COUNT(*) FROM Users WHERE is_active = 0;", fetchone=True)
            return result[0] if result else 0
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to count inactive users: %s", error)
            return 0

    def delete_users(self) -> None:
        self.execute("DELETE FROM Users;", commit=True)
        logger.warning("All users deleted from database")

    def all_users_id(self) -> List[Tuple]:
        try:
            return self.execute("SELECT telegram_id FROM Users;", fetchall=True) or []
        except (sqlite3.Error, PostgresError) as error:
            logger.error("Failed to get user IDs: %s", error)
            return []

    def set_meta(self, key: str, value: str) -> None:
        if self.db_type == "postgres":
            sql = """
            INSERT INTO Meta (key, value)
            VALUES(%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """
        else:
            sql = """
            INSERT OR REPLACE INTO Meta (key, value)
            VALUES(?, ?);
            """

        self.execute(sql, parameters=(key, value), commit=True)

    def get_meta(self, key: str) -> Optional[str]:
        placeholder = "%s" if self.db_type == "postgres" else "?"
        result = self.execute(
            f"SELECT value FROM Meta WHERE key = {placeholder};",
            parameters=(key,),
            fetchone=True,
        )
        return result[0] if result else None

    def ensure_meta(self, key: str, value: str) -> str:
        current_value = self.get_meta(key)
        if current_value is not None:
            return current_value

        self.set_meta(key, value)
        return value
