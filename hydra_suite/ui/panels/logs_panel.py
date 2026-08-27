# =============================================================================
# HYDRA-UMC SUITE - ui/panels/logs_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real-time log viewer with filters.
# Every record ever received is kept in `_all_entries` (unbounded within
# one session - this window doesn't run for weeks unattended the way
# HYDRA-UMC-SERVER does, so no rotation/cap is needed here); the level/
# text filters only control what's currently DISPLAYED, re-applied
# against that same full list rather than dropping anything - clearing a
# filter always brings back everything seen since the panel opened, not
# just what arrived after the filter changed.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hydra_suite import logging_handler
from hydra_suite.i18n import _

_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
_LEVEL_COLOR = {
    "DEBUG": "#888888",
    "INFO": "#d0d0d0",
    "WARNING": "#e0a030",
    "ERROR": "#e05050",
    "CRITICAL": "#ff3030",
}


@dataclass(frozen=True)
class _LogEntry:
    level: str
    logger_name: str
    message: str


class LogsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._all_entries: list[_LogEntry] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        heading = QLabel(_("HEADING_LOGS"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(_("LBL_LOG_LEVEL")))
        self._level_combo = QComboBox()
        self._level_combo.addItem(_("LOG_LEVEL_ALL"), None)
        for level in _LEVELS:
            self._level_combo.addItem(level, level)
        self._level_combo.currentIndexChanged.connect(self._refresh_display)
        filter_row.addWidget(self._level_combo)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(_("LOG_SEARCH_PLACEHOLDER"))
        self._search_box.textChanged.connect(self._refresh_display)
        filter_row.addWidget(self._search_box, stretch=1)

        clear_btn = QPushButton(_("BTN_CLEAR_LOGS"))
        clear_btn.clicked.connect(self._on_clear)
        filter_row.addWidget(clear_btn)
        layout.addLayout(filter_row)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._text.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(self._text, stretch=1)

        handler = logging_handler.install()
        handler.emitter.record_logged.connect(self._on_record)

    def _on_record(self, level: str, logger_name: str, message: str) -> None:
        self._all_entries.append(_LogEntry(level, logger_name, message))
        if self._entry_matches_filters(self._all_entries[-1]):
            self._append_line(self._all_entries[-1])

    def _entry_matches_filters(self, entry: _LogEntry) -> bool:
        wanted_level = self._level_combo.currentData()
        if wanted_level is not None and entry.level != wanted_level:
            return False
        needle = self._search_box.text().strip().lower()
        if needle and needle not in entry.message.lower() and needle not in entry.logger_name.lower():
            return False
        return True

    def _append_line(self, entry: _LogEntry) -> None:
        color = _LEVEL_COLOR.get(entry.level, "#d0d0d0")
        # Full replace-on-filter-change (_refresh_display) uses the same
        # per-line HTML this appends live, so a filtered view and a fresh
        # live view are never visually different formats.
        self._text.append(f'<span style="color:{color}">[{entry.level}] {entry.logger_name}: {entry.message}</span>')

    def _refresh_display(self) -> None:
        self._text.clear()
        for entry in self._all_entries:
            if self._entry_matches_filters(entry):
                self._append_line(entry)

    def _on_clear(self) -> None:
        self._all_entries.clear()
        self._text.clear()
