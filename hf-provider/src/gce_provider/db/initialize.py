import sqlite3
from typing import Optional

from common.utils.path_utils import ensure_path_exists
from gce_provider.config import Config, get_config

def alter_schema(conn: sqlite3.Connection, logger):
    """Safely alter the database schema without dropping data."""
    alter_query = "ALTER TABLE machines ADD COLUMN return_ttl TIMESTAMP"

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(machines)")
    columns = [col[1] for col in cursor.fetchall()]

    if "return_ttl" not in columns:
        conn.execute(alter_query)
        conn.commit()
        logger.info("Column 'return_ttl' added successfully.")
    else:
        logger.info("Column 'return_ttl' already exists, skipping alter.")

def main(config: Optional[Config] = None):
    if config is None:
        config = get_config()
    logger = config.logger

    # @formatter:off
    schema = """
    CREATE TABLE IF NOT EXISTS machines (
      machine_name VARCHAR(32) NOT NULL,
      request_id VARCHAR(32) NOT NULL,
      gcp_zone VARCHAR(32) NOT NULL,
      instance_group_manager VARCHAR(32) NOT NULL,
      machine_state INT DEFAULT 0,
      operation_id VARCHAR(32) NOT NULL,
      return_request_id VARCHAR(32),
      delete_operation_request_id VARCHAR(32),
      delete_operation_id VARCHAR(32),
      delete_grace_period INT,
      internal_ip VARCHAR(15),
      external_ip VARCHAR(15),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP);

      CREATE UNIQUE INDEX IF NOT EXISTS idx_machine_name ON machines(machine_name);
      CREATE UNIQUE INDEX IF NOT EXISTS
           idx_request_id_machine_name
        ON machines(request_id, machine_name);
      CREATE UNIQUE INDEX IF NOT EXISTS
           idx_insert_id_machine_name
        ON machines(operation_id, machine_name);

    CREATE TRIGGER IF NOT EXISTS set_updated_at
        AFTER UPDATE ON machines
        FOR EACH ROW
    BEGIN
        UPDATE machines SET updated_at = CURRENT_TIMESTAMP WHERE machine_name = OLD.machine_name;
    END;

    """

    logger.info(f"Initializing the database at {config.db_path}")
    ensure_path_exists(config.hf_db_dir)

    with sqlite3.connect(config.db_path) as conn:
        conn.executescript(schema)
        alter_schema(conn, logger)
    logger.info("Database initialization complete.")


if __name__ == "__main__":
    main()
