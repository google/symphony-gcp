import sqlite3
from typing import Any, List, Optional, Union

from gce_provider.config import Config, get_config


class Statement:
    """Defines an SQL statement"""

    def __init__(
        self,
        query: str,
        params: Optional[Union[dict[str, Any], List[Any]]] = None,
    ):
        self.query = query
        self.params = params


class Transaction:
    """Automates the process of executing a database transaction"""

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            config = get_config()
        self.config = config
        self.logger = config.logger
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self):
        # set up a connection & a transaction
        self.connection = sqlite3.connect(self.config.db_path)
        self.cursor = self.connection.cursor()
        self.cursor.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # commit or rollback the transaction
        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()

    def execute(
        self,
        statements: List[Statement],
    ):
        """Transactionally execute a list of statements"""
        for statement in statements:
            self.logger.debug(f"execute query '{statement.query}' with params: {statement.params}")
            self.cursor.execute(statement.query, statement.params)

    def executemany(self, statements: List[Statement]):
        """Transactionally executemany a list of statements"""
        for statement in statements:
            self.logger.debug(
                f"executemany query '{statement.query}' with params: {statement.params}"
            )
            self.cursor.executemany(statement.query, statement.params)
