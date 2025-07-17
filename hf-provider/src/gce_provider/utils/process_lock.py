import os


class LockManagerError(RuntimeError):
    pass


class LockManager:
    def __init__(self, lockfile_path: str = None):
        self.lockfile_path = lockfile_path

    def __enter__(self):
        # Check if lock file exists
        lockfile = self.lockfile_path
        if os.path.exists(lockfile):
            message = f"Process is already running, see {lockfile}."
            raise LockManagerError(message)

        # Create lock file
        try:
            with open(lockfile, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            raise LockManagerError() from e

    def __exit__(self, exc_type, exc_value, traceback):
        lockfile = self.lockfile_path
        if os.path.exists(lockfile):
            os.remove(lockfile)
