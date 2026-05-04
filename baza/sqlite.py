import sqlite3
import logging
from typing import Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path_to_db: str = "main.db", debug: bool = False):
        self.path_to_db = path_to_db
        self.debug = debug
        self._init_db()

    def _init_db(self) -> None:
        """Initsizatsiya qilish va jadvallarni yaratish"""
        try:
            connection = sqlite3.connect(self.path_to_db)
            connection.execute("PRAGMA foreign_keys = ON")
            connection.close()
            logger.info(f"Database {self.path_to_db} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @property
    def connection(self) -> sqlite3.Connection:
        """Bazaga ulanish yaratish"""
        conn = sqlite3.connect(self.path_to_db)
        conn.execute("PRAGMA foreign_keys = ON")
        if self.debug:
            conn.set_trace_callback(self._log_sql)
        return conn

    @staticmethod
    def _log_sql(statement: str) -> None:
        """SQL so'rovlarini logga yozish"""
        logger.debug(f"SQL: {statement}")

    def execute(
        self, 
        sql: str, 
        parameters: Tuple = None, 
        fetchone: bool = False, 
        fetchall: bool = False, 
        commit: bool = False
    ) -> Optional[Any]:
        """SQL so'rovni bajaritsh"""
        if parameters is None:
            parameters = ()
        
        connection = self.connection
        cursor = connection.cursor()
        data = None
        
        try:
            cursor.execute(sql, parameters)
            
            if commit:
                connection.commit()
                logger.debug(f"Query committed: {sql}")
            
            if fetchall:
                data = cursor.fetchall()
            elif fetchone:
                data = cursor.fetchone()
                
            return data
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}\nSQL: {sql}\nParams: {parameters}")
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_table_users(self) -> None:
        """Foydalanuvchilar jadvalini yaratish"""
        sql = """
        CREATE TABLE IF NOT EXISTS Users (
            full_name TEXT,
            telegram_id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_telegram_id ON Users(telegram_id);
        """
        try:
            self.execute(sql, commit=True)
            logger.info("Users table created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create users table: {e}")
    
    def create_table_channels(self) -> None:
        """Kanallar jadvalini yaratish"""
        sql = """
        CREATE TABLE IF NOT EXISTS Channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_link TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_channel_id ON Channels(channel_id);
        """
        try:
            self.execute(sql, commit=True)
            logger.info("Channels table created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create channels table: {e}")

    @staticmethod
    def format_args(sql: str, parameters: dict) -> Tuple[str, Tuple]:
        """SQL so'rovni parametrlarni sozlashtirish"""
        sql += " AND ".join([f"{item} = ?" for item in parameters])
        return sql, tuple(parameters.values())

    def add_user(self, telegram_id: int, full_name: str) -> None:
        """Yangi foydalanuvchini qo'shish"""
        sql = """
        INSERT INTO Users (telegram_id, full_name) VALUES(?, ?);
        """
        try:
            self.execute(sql, parameters=(telegram_id, full_name), commit=True)
            logger.info(f"User added: {telegram_id}")
        except sqlite3.IntegrityError:
            logger.warning(f"User {telegram_id} already exists")
        except sqlite3.Error as e:
            logger.error(f"Failed to add user: {e}")
            raise

    def add_channel(self, channel_id: int, channel_name: str, channel_link: str) -> None:
        """Yangi kanalni qo'shish"""
        sql = "INSERT INTO Channels (channel_id, channel_name, channel_link) VALUES(?, ?, ?);"
        try:
            self.execute(sql, parameters=(channel_id, channel_name, channel_link), commit=True)
            logger.info(f"Channel added: {channel_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to add channel: {e}")
            raise
    
    def select_all_channels(self) -> List[Tuple]:
        """Barcha kanallarni olib olish"""
        sql = "SELECT * FROM Channels ORDER BY created_at DESC"
        try:
            result = self.execute(sql, fetchall=True)
            return result or []
        except sqlite3.Error as e:
            logger.error(f"Failed to select channels: {e}")
            return []

    def delete_channel(self, channel_id: int) -> None:
        """Kanalni o'chirish"""
        try:
            self.execute(
                "DELETE FROM Channels WHERE channel_id = ?", 
                parameters=(channel_id,), 
                commit=True
            )
            logger.info(f"Channel deleted: {channel_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete channel: {e}")
            raise

    def select_all_users(self) -> List[Tuple]:
        """Barcha foydalanuvchilarni olib olish"""
        sql = "SELECT * FROM Users ORDER BY created_at DESC"
        try:
            result = self.execute(sql, fetchall=True)
            return result or []
        except sqlite3.Error as e:
            logger.error(f"Failed to select users: {e}")
            return []

    def select_user(self, **kwargs) -> Optional[Tuple]:
        """Foydalanuvchini qidirish"""
        base_sql = "SELECT * FROM Users WHERE "
        sql, parameters = self.format_args(base_sql, kwargs)
        try:
            return self.execute(sql, parameters=parameters, fetchone=True)
        except sqlite3.Error as e:
            logger.error(f"Failed to select user: {e}")
            return None

    def count_users(self) -> int:
        """Foydalanuvchilar sonini hisoblash"""
        try:
            result = self.execute("SELECT COUNT(*) FROM Users;", fetchone=True)
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count users: {e}")
            return 0

    def delete_users(self) -> None:
        """Barcha foydalanuvchilarni o'chirish"""
        try:
            self.execute("DELETE FROM Users;", commit=True)
            logger.warning("All users deleted from database")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete users: {e}")
            raise
    
    def all_users_id(self) -> List[Tuple]:
        """Barcha foydalanuvchilarning ID larini olib olish"""
        try:
            result = self.execute("SELECT telegram_id FROM Users;", fetchall=True)
            return result or []
        except sqlite3.Error as e:
            logger.error(f"Failed to get user IDs: {e}")
            return []