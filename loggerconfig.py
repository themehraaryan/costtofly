#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — Session-based rotating file logger (safe-ish single-process).
- Produces one session file per process run: <basename>_<YYYY-MM-DD_HH-MM-SS>.ext
- When a session file exceeds maxBytes it is renamed with incremental suffixes:
    <basename>_<ts>-1.ext, <basename>_<ts>-2.ext, ...
- Keeps up to backupCount older session files (excluding the currently active file).
- Uses atomic replace when available; logs non-fatal errors instead of raising.
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class SessionBasedRotatingFileHandler(RotatingFileHandler):
    """
    Rotating file handler that generates per-session log files.

    Behavior summary:
    - At instantiation a session timestamp is appended to base filename.
    - When rollover triggers, the current active file is moved to an incremental
      session snapshot file (atomic if possible).
    - _cleanup_old_files keeps at most `backupCount` session snapshot files
      (does not delete the active file).
    """

    def __init__(
        self,
        base_filename: str,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = None,
        delay: bool = False,
    ):
        # session timestamp created once for the process/run
        self.session_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # store base path (without session suffix) for pattern matching
        self.base_name = base_filename
        filename = self._get_session_filename()
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)

    def _get_session_filename(self, counter: Optional[int] = None) -> str:
        """
        Produce the session filename.
        If counter is provided, returns a rotated snapshot name:
            <name>_<session_timestamp>-<counter><ext>
        Otherwise returns the active session filename:
            <name>_<session_timestamp><ext>
        """
        name, ext = os.path.splitext(self.base_name)
        if counter is None:
            return f"{name}_{self.session_timestamp}{ext}"
        return f"{name}_{self.session_timestamp}-{counter}{ext}"

    def doRollover(self) -> None:
        """
        Perform a size-based rollover:
        - Close stream
        - Find next available counter (1,2,3...)
        - Move/replace current baseFilename -> session_filename(counter)
        - Run cleanup to prune old session snapshot files (not the active one)
        - Reopen stream if not delayed
        """
        if self.stream:
            try:
                self.stream.close()
            except Exception:
                # best-effort close; do not raise from logging
                logging.getLogger(__name__).exception("Failed to close stream during rollover.")
            self.stream = None

        # pick the next unused counter for this session
        counter = 1
        while os.path.exists(self._get_session_filename(counter)):
            counter += 1

        try:
            if os.path.exists(self.baseFilename):
                # Prefer atomic replace; fallback to rename or copy/remove.
                try:
                    os.replace(self.baseFilename, self._get_session_filename(counter))
                except AttributeError:
                    # os.replace always exists in modern Python; fallback for very old versions
                    os.rename(self.baseFilename, self._get_session_filename(counter))
                except OSError:
                    # As a last resort try copy2 + remove
                    try:
                        shutil.copy2(self.baseFilename, self._get_session_filename(counter))
                        os.remove(self.baseFilename)
                    except Exception:
                        logging.getLogger(__name__).exception(
                            "Failed to rotate log file via copy/remove."
                        )
        except Exception:
            logging.getLogger(__name__).exception("Unexpected error during rollover.")

        # prune old session files (keeps newest `backupCount` snapshots; active file not counted)
        if self.backupCount > 0:
            self._cleanup_old_files()

        # reopen the stream if required
        if not self.delay:
            self.stream = self._open()

    def _cleanup_old_files(self) -> None:
        """
        Remove the oldest session snapshot files for this base filename when the
        number of snapshots exceeds backupCount. Excludes the currently active file.
        Logs any deletion errors.
        """
        try:
            dir_name = os.path.dirname(self.base_name) or "."
            base_name = os.path.basename(self.base_name)
            name, ext = os.path.splitext(base_name)

            # collect candidate snapshot files that match the pattern "<name>_*.ext"
            candidates = []
            for fname in os.listdir(dir_name):
                if not fname.startswith(f"{name}_") or not fname.endswith(ext):
                    continue
                full = os.path.join(dir_name, fname)
                if not os.path.isfile(full):
                    continue
                # exclude the active file (current baseFilename)
                try:
                    if os.path.abspath(full) == os.path.abspath(self.baseFilename):
                        continue
                except Exception:
                    # if we can't compare for some reason, keep the file conservative
                    continue
                candidates.append((os.path.getmtime(full), full))

            # oldest first
            candidates.sort()

            # prune until we have at most backupCount snapshots left
            while len(candidates) > self.backupCount:
                _, oldest = candidates.pop(0)
                try:
                    os.remove(oldest)
                except OSError:
                    logging.getLogger(__name__).exception("Failed to remove old log file: %s", oldest)

        except Exception:
            logging.getLogger(__name__).exception("Unexpected error during log cleanup.")


def setup_logger(
    name: str = "rank_tracker",
    log_level: int = logging.INFO,
    logs_dir: str = "Logs",
    base_filename: str = "rank_tracker.log",
    max_bytes: int = 50 * 1024 * 1024,
    backup_count: int = 10,
    encoding: Optional[str] = "utf-8",
) -> logging.Logger:
    """
    Configure and return a session-based logger.

    Parameters:
    - name: logger name (use module name typically)
    - log_level: base log level
    - logs_dir: directory to store logs
    - base_filename: base log filename (without session suffix)
    - max_bytes: rollover threshold in bytes (0 disables size-based rollover)
    - backup_count: how many session snapshot files to keep (does NOT count active file)
    - encoding: file encoding

    Returns:
    - Configured logger instance (propagation disabled)
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # clear existing handlers to avoid double outputs when reloading modules
    logger.handlers.clear()

    # ensure log directory exists (race-tolerant)
    os.makedirs(logs_dir, exist_ok=True)

    log_file_path = os.path.join(logs_dir, base_filename)

    # create the session-based rotating handler
    file_handler = SessionBasedRotatingFileHandler(
        log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding
    )

    # console handler
    console_handler = logging.StreamHandler()

    # formatter used for both handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # prevent messages from being propagated to the root logger (avoid duplicates)
    logger.propagate = False

    return logger


# small demo when run directly (useful for quick manual tests)
if __name__ == "__main__":
    test_logger = setup_logger(log_level=logging.DEBUG, max_bytes=1024, backup_count=3)
    test_logger.info("Logger demo start")
    for i in range(500):
        test_logger.debug("line %d: %s", i, "x" * 100)
    test_logger.info("Logger demo end")
