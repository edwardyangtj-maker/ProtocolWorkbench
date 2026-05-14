from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from protocol_workbench.core.models import LogRecord


class LoggerService(QObject):
    log_signal = Signal(str, str)
    packet_signal = Signal(dict)

    LEVEL_DEBUG = "DEBUG"
    LEVEL_INFO = "INFO"
    LEVEL_WARN = "WARN"
    LEVEL_ERROR = "ERROR"
    LEVEL_TX = "TX"
    LEVEL_RX = "RX"

    def __init__(self, log_dir: Path | None = None, parent=None):
        super().__init__(parent)
        self.log_dir = log_dir
        self._runtime_log = None
        self._tx_log = None
        self._rx_log = None
        self._error_log = None
        self._packets_file = None
        self._python_logger = logging.getLogger("protocol_workbench")
        if not self._python_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self._python_logger.addHandler(handler)
            self._python_logger.setLevel(logging.DEBUG)

        if self.log_dir is None:
            default_dir = Path.home() / ".protocol_workbench" / "logs"
            self.set_log_dir(default_dir)

    def set_log_dir(self, log_dir: Path):
        self.log_dir = log_dir
        self._close_files()
        self._open_files()

    def _open_files(self):
        if self.log_dir is None:
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._runtime_log = open(self.log_dir / "runtime.log", "a", encoding="utf-8")
            self._tx_log = open(self.log_dir / "tx.log", "a", encoding="utf-8")
            self._rx_log = open(self.log_dir / "rx.log", "a", encoding="utf-8")
            self._error_log = open(self.log_dir / "error.log", "a", encoding="utf-8")
            self._packets_file = open(self.log_dir / "packets.jsonl", "a", encoding="utf-8")
        except Exception as e:
            self._python_logger.error(f"Failed to open log files: {e}")

    def _close_files(self):
        for f in [self._runtime_log, self._tx_log, self._rx_log, self._error_log, self._packets_file]:
            if f and not f.closed:
                try:
                    f.close()
                except Exception:
                    pass
        self._runtime_log = None
        self._tx_log = None
        self._rx_log = None
        self._error_log = None
        self._packets_file = None

    def _write_to_file(self, file, message: str):
        if file and not file.closed:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                file.write(f"[{timestamp}] {message}\n")
                file.flush()
            except Exception:
                pass

    def debug(self, message: str):
        self._log(self.LEVEL_DEBUG, message)

    def info(self, message: str):
        self._log(self.LEVEL_INFO, message)

    def warn(self, message: str):
        self._log(self.LEVEL_WARN, message)

    def error(self, message: str):
        self._log(self.LEVEL_ERROR, message)

    def tx(self, message: str, record: LogRecord | None = None):
        self._log(self.LEVEL_TX, message)
        self._write_to_file(self._tx_log, message)
        if record:
            self._write_packet(record)

    def rx(self, message: str, record: LogRecord | None = None):
        self._log(self.LEVEL_RX, message)
        self._write_to_file(self._rx_log, message)
        if record:
            self._write_packet(record)

    def _log(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level}] {message}"
        self.log_signal.emit(level, formatted)
        self._write_to_file(self._runtime_log, f"[{level}] {message}")
        if level == self.LEVEL_ERROR:
            self._write_to_file(self._error_log, message)
        if level == self.LEVEL_DEBUG:
            self._python_logger.debug(message)
        elif level == self.LEVEL_INFO:
            self._python_logger.info(message)
        elif level == self.LEVEL_WARN:
            self._python_logger.warning(message)
        elif level == self.LEVEL_ERROR:
            self._python_logger.error(message)

    def _write_packet(self, record: LogRecord):
        if self._packets_file and not self._packets_file.closed:
            try:
                self._packets_file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                self._packets_file.flush()
            except Exception:
                pass
        self.packet_signal.emit(record.to_dict())

    def close(self):
        self._close_files()
