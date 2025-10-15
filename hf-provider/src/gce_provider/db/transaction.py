import sqlite3
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
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

    def __init__(self, config: Optional[Config] = None, timeout: float = 30.0):
        if config is None:
            config = get_config()
        self.config = config
        self.timeout = timeout

        self.logger = config.logger
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self):
        # set up a connection & a transaction
        self.connection = sqlite3.connect(
            self.config.db_path, timeout=self.timeout, check_same_thread=False
        )

        self.connection.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)};")

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

    def _retryable(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                self.logger.warning(f"Database locked, retrying: {e}")
                raise
            self.logger.error(f"SQLite error: {e}")
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(sqlite3.OperationalError),
        reraise=True,
    )
    def _execute_with_retry(self, query: str, params: list[tuple]):
        return self._retryable(self.cursor.execute, query, params)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(sqlite3.OperationalError),
        reraise=True,
    )
    def _executemany_with_retry(self, query: str, params: list[tuple]):
        return self._retryable(self.cursor.executemany, query, params)

    def execute(
        self,
        statements: List[Statement],
    ):
        """Transactionally execute a list of statements"""
        for statement in statements:
            self.logger.debug(
                f"execute query '{statement.query}' with params: {statement.params}"
            )
            self._execute_with_retry(statement.query, statement.params)

    def executemany(self, statements: List[Statement]):
        """Transactionally executemany a list of statements"""
        for statement in statements:
            self.logger.debug(
                f"executemany query '{statement.query}' with params: {statement.params}"
            )
            self._executemany_with_retry(statement.query, statement.params)
