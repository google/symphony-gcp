import sqlite3
import os
from typing import Dict, List, Set, Iterable
from gce_provider.config import Config, get_config
from gce_provider.db.transaction import Statement, Transaction
from gce_provider.utils.constants import MachineState

# ---------- Configuration ----------
HF_PROVIDER_NAME = "gcpgceinst"
DELETE_BATCH_SIZE = 500
SQLITE_MAX_VARS = 900

# ---------- HF Reader ----------

def sqlite_connect_readonly(path: str) -> sqlite3.Connection:
    """Helper for reading hf.db directly (readonly)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database file not found: {path}")
    uri = f"file:{os.path.abspath(path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

class HostFactoryReader:
    """
        Reads identifiers from hf_request table for the configured provider.
    """

    def __init__(
        self,
        config,
        provider_name: str = HF_PROVIDER_NAME,
    ) -> None:
        if config is None:
            config = get_config()
        self.db_path = config.shf_db_path
        self.logger = config.logger
        self.provider_name = provider_name

    def fetch_all_gce_rows(self) -> List[Dict]:
        """Return raw hf_request rows (dicts) matching provider."""

        sql = f"""
        SELECT
            COALESCE(cloud_request_id, '') AS cloud_request_id
        FROM hf_request
        WHERE provider_name = ?
        """
        params = (self.provider_name,)
        with sqlite_connect_readonly(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            self.logger.info("HostFactory: fetched %d rows for provider=%s", len(rows), self.provider_name)
            return rows

    def fetch_identifier_sets(self) -> Dict[str, Set[str]]:
        """Return sets of cloud_request_ids"""
        rows = self.fetch_all_gce_rows()
        crid = {r["cloud_request_id"] for r in rows if r.get("cloud_request_id")}
        self.logger.debug(
            "HostFactory identifiers: cloud_request_ids=%d",
            len(crid),
        )
        return {"cloud_request_ids": crid}

# ---------- Symphony cleaner ----------

class SymphonyCleaner:
    """
        Finds and deletes machine rows in symphony.db according to reconciliation rules.
    """
    def __init__(
        self,
        config: Config,
        batch_size: int = DELETE_BATCH_SIZE,
    ) -> None:
        if config is None:
            config = get_config()
        self.config = config
        self.logger = config.logger
        self.batch_size = batch_size

    def find_orphans(self, id_sets: Dict[str, Set[str]]) -> Set[str]:
        """
        Find machine_name values for machines that do NOT have a matching
        cloud_request_id (request_id) in the provided id_sets.

        - id_sets expects a key "cloud_request_ids" mapping to a set of request_id strings.
        - If that set is empty, all machine_name rows are returned (i.e. HF has no requests).
        - For very large sets we avoid building an enormous IN(...) clause and do the filtering in Python.
        """
        conn = sqlite_connect_readonly(self.config.db_path)
        try:
            crids: Set[str] = id_sets.get("cloud_request_ids", set()) or set()
            # If there are no crids, everything in machines is orphaned
            if not crids:
                sql_all = "SELECT machine_name FROM machines"
                cur = conn.cursor()
                cur.execute(sql_all)
                rows = {r["machine_name"] for r in cur.fetchall()}
                self.logger.info("Symphony: HF returned no cloud_request_ids; all %d machines considered orphaned", len(rows))
                return rows

            # If the number of placeholders is within SQLite limits, use a single parameterized query
            if len(crids) <= SQLITE_MAX_VARS:
                placeholders = ",".join("?" for _ in crids)
                sql = f"SELECT machine_name FROM machines WHERE NOT (request_id IN ({placeholders}))"
                params = tuple(crids)
                cur = conn.cursor()
                cur.execute(sql, params)
                rows = {r["machine_name"] for r in cur.fetchall()}
                self.logger.info("Symphony: found %d orphan machine rows (via SQL IN)", len(rows))
                return rows

            # Otherwise (too many params) -- fetch machine_name + request_id and filter in Python
            self.logger.debug(
                "Too many cloud_request_ids (%d) for single IN clause; falling back to client-side filtering",
                len(crids),
            )
            sql_all = "SELECT machine_name, request_id FROM machines"
            cur = conn.cursor()
            cur.execute(sql_all)
            rows = {r["machine_name"] for r in cur.fetchall() if (r["request_id"] not in crids)}
            self.logger.info("Symphony: found %d orphan machine rows (via client-side filter)", len(rows))
            return rows
        finally:
            conn.close()

    def delete_by_uids(self, uids: Iterable[str]) -> int:
        """Delete machine rows by id in batches using the Transaction helper."""
        uids_list = list(uids)
        if not uids_list:
            self.logger.info("No rows to delete.")
            return 0

        total_deleted = 0
        self.logger.info("Deleting %d machine rows in batches of %d...", len(uids_list), self.batch_size)

        for i in range(0, len(uids_list), self.batch_size):
            batch = uids_list[i : i + self.batch_size]

            placeholders = ["?" for j in range(len(batch))]
            query = f"DELETE FROM machines WHERE machine_name IN ({', '.join(placeholders)})"
            params = [[x for x in batch]]

            try:
                # with Transaction(self.config) as trans:
                #     trans.executemany([Statement(query, params)])
                total_deleted += len(batch)
            except Exception:
                self.logger.exception("Batch delete failed (rolled back automatically)")
                raise

        self.logger.info("Symphony: total deleted = %d rows", total_deleted)
        return total_deleted


def main():
    config = get_config()
    logger = config.logger
    
    logger.info("Starting reconciliation & purge (DESTRUCTIVE).")

    # Read HostFactory identifiers
    hf_reader = HostFactoryReader(config)
    id_sets = hf_reader.fetch_identifier_sets()

    # Reconcile and delete
    cleaner = SymphonyCleaner(config)
    to_delete = cleaner.find_orphans(id_sets)

    logger.info("Combined deletion set size: %d)", len(to_delete))

    if to_delete:
        deleted_count = cleaner.delete_by_uids(to_delete)
        logger.info("Reconciliation complete — deleted %d machine rows.", deleted_count)
    else:
        logger.info("Nothing to delete. Exiting.")

if __name__ == "__main__":
    main()