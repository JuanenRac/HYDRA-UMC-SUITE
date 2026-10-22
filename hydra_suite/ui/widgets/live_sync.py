# =============================================================================
# HYDRA-UMC SUITE - ui/widgets/live_sync.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Small helpers that keep a panel calm while the server pushes live changes:
#   - sync_combo(): a combo box is rebuilt only when its list really changed,
#     so an open drop-down is not closed and the scroll position is kept
#   - set_text_unless_editing(): a field the operator is typing in is not
#     overwritten by a state that arrives in the meantime
#   - run_timers_while_visible(): a poller runs only while its panel is on screen
#   - Trailing: runs a call once, after a pause (debounce) or at most once per
#     interval (coalesce), with the arguments of the latest request - for
#     sliders and spin boxes that would otherwise send the whole settings
#     tree on every step, and for refreshes triggered by bursts of deltas
# =============================================================================
from __future__ import annotations

from typing import Any, Callable, Sequence

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget


def sync_combo(combo: QComboBox, entries: Sequence[tuple[str, Any]], keep_data: Any = None) -> int:
    """Makes `combo` list `entries` ((text, data) pairs). The widget is only
    touched when the list differs from what it already shows. The entry whose
    data equals `keep_data` stays (or becomes) the current one, else the
    first. Returns the index now current (0 for an empty list). Call it with
    the combo's signals blocked, like the code it replaces."""
    shown = [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
    wanted = [(text, data) for text, data in entries]
    if shown != wanted:
        combo.clear()
        for text, data in wanted:
            combo.addItem(text, data)
    index = 0
    if keep_data is not None:
        for i, (_text, data) in enumerate(wanted):
            if data == keep_data:
                index = i
                break
    if wanted and combo.currentIndex() != index:
        combo.setCurrentIndex(index)
    return index


def set_text_unless_editing(edit: QLineEdit, text: str) -> bool:
    """Writes `text` into `edit` when it differs and the operator is not
    typing in it. Returns True when the text was written."""
    if edit.text() == text or edit.hasFocus():
        return False
    edit.setText(text)
    return True


class Trailing(QObject):
    """Runs `callback(*args)` once, with the latest arguments.

    restart=True is a debounce: every request postpones the call, so it runs
    after `interval_ms` without a new request. restart=False is a coalescer:
    the first request starts the clock and the later ones only replace the
    arguments, so the call runs at most once per interval. `flush()` runs a
    pending call at once (before closing, say) and `cancel()` drops it."""

    def __init__(self, callback: Callable[..., None], interval_ms: int = 150, restart: bool = True, parent: QObject | None = None):
        super().__init__(parent)
        self._callback = callback
        self._restart = restart
        self._args: tuple = ()
        self._pending = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._fire)

    @property
    def pending(self) -> bool:
        return self._pending

    def request(self, *args: Any) -> None:
        self._args = args
        self._pending = True
        if self._restart or not self._timer.isActive():
            self._timer.start()

    def flush(self) -> None:
        if self._pending:
            self._timer.stop()
            self._fire()

    def cancel(self) -> None:
        self._timer.stop()
        self._pending = False

    def _fire(self) -> None:
        if not self._pending:
            return
        self._pending = False
        self._callback(*self._args)


class _VisibilityGate(QObject):
    def __init__(self, widget: QWidget, timers: Sequence[QTimer], on_show: Callable[[], None] | None):
        super().__init__(widget)
        self._widget = widget
        self._timers = list(timers)
        self._on_show = on_show
        widget.installEventFilter(self)
        if widget.isVisible():
            self._start()

    def _start(self) -> None:
        for timer in self._timers:
            timer.start()
        if self._on_show is not None:
            self._on_show()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._widget:
            if event.type() == QEvent.Type.Show:
                self._start()
            elif event.type() == QEvent.Type.Hide:
                for timer in self._timers:
                    timer.stop()
        return False


def run_timers_while_visible(widget: QWidget, timers: Sequence[QTimer], on_show: Callable[[], None] | None = None) -> QObject:
    """Starts `timers` when `widget` is shown (calling `on_show` once, to catch
    up at once) and stops them when it is hidden - a panel in a hidden dock or
    another tab no longer polls the server. The timers must not be started by
    the caller. Keep the returned object only if you need it; it lives as long
    as the widget."""
    return _VisibilityGate(widget, timers, on_show)
