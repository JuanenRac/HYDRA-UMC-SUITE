# =============================================================================
# HYDRA-UMC SUITE - extras_bridge.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The part of the interface that looks at the whole swarm and at the path of a trajectory, kept apart from the big bridge:
#
#   swarm view      every robot of every server in one table, with the global STOP and a STOP per server;
#   combined mode   choose the robots that move together with the selected one (`combinedWith`, the `combine` command);
#   path viewer     the path of the trajectory from above, from the side and from the front, with what is wrong with it;
#   preview         Play and Send show that path and those problems first and ask;
#   updates         the versions of this program and of the servers against the published ones.
#
# The logic is in hydra_suite/swarm.py, trajectory_view.py and update_check.py (no Qt); this file only joins it to the
# connections and to QML as `suiteBackend.extras`. Three switches (swarm view, preview before Play, check of versions)
# and the combined mode are the operator's, kept in the configuration file, and all of them are off until switched on.
# =============================================================================
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from hydra_suite import __version__, reach, swarm, trajectory_view, update_check
from hydra_suite.app import StopAllSummary, describe_stop_all
from hydra_suite.i18n import _, load_config, save_config

if TYPE_CHECKING:  # pragma: no cover
    from qt_suite import SuiteQtBridge

logger = logging.getLogger(__name__)

SWARM_KEY = "swarm_view"
COMBINED_KEY = "combined_mode"
PREVIEW_KEY = "trajectory_preview"
UPDATES_KEY = "update_check"
REFRESH_MS = 2000


def _flag(config: dict, key: str, default: bool) -> bool:
    value = config.get(key)
    return value if isinstance(value, bool) else default


class SuiteExtras(QObject):
    changed = Signal()
    # The text of the dialog that asks before Play or Send: title, lines, kind ("play" or "send"), whether it is clean.
    previewRequested = Signal()

    def __init__(self, bridge: "SuiteQtBridge", parent: QObject | None = None):
        super().__init__(parent or bridge)
        self._bridge = bridge
        self._controller = bridge._controller
        config = load_config()
        self._swarm_on = _flag(config, SWARM_KEY, swarm.SETTINGS["enabledByDefault"])
        self._combined_on = _flag(config, COMBINED_KEY, swarm.SETTINGS["combinedModeByDefault"])
        self._preview_on = _flag(config, PREVIEW_KEY, trajectory_view.SETTINGS["previewBeforePlayByDefault"])
        self._updates_on = _flag(config, UPDATES_KEY, update_check.SETTINGS["enabledByDefault"])
        self._swarm_filter = "all"
        self._swarm_text = ""
        self._swarm_rows_cache: list[dict[str, Any]] = []
        self._update_result: dict[str, Any] | None = None
        self._update_busy = False
        self._pending_kind = ""
        self._pending_report: dict[str, Any] | None = None
        self._orbit_yaw = trajectory_view.ORBIT_SETTINGS["yawDeg"]
        self._orbit_pitch = trajectory_view.ORBIT_SETTINGS["pitchDeg"]
        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._tick)
        if self._swarm_on:
            self._timer.start()
        bridge._trajectoryChanged.connect(self.changed.emit)
        self._controller.connection_claims_changed.connect(lambda _cid: self.changed.emit())
        self._controller.connection_status_changed.connect(lambda _cid, _status: self.changed.emit())

    # -- switches -----------------------------------------------------------------------------------------------

    def _store(self, key: str, value: bool) -> None:
        if not save_config({key: value}):
            self._bridge._set_notice(_("MSG_EXTRAS_NOT_SAVED"), "warn")

    @Property(bool, notify=changed)
    def swarmEnabled(self) -> bool:
        return self._swarm_on

    @Slot(bool)
    def setSwarmEnabled(self, on: bool) -> None:
        self._swarm_on = bool(on)
        self._store(SWARM_KEY, self._swarm_on)
        if self._swarm_on:
            self._timer.start()
        else:
            self._timer.stop()
        self.changed.emit()

    @Property(bool, notify=changed)
    def combinedModeEnabled(self) -> bool:
        return self._combined_on

    @Slot(bool)
    def setCombinedModeEnabled(self, on: bool) -> None:
        self._combined_on = bool(on)
        self._store(COMBINED_KEY, self._combined_on)
        self.changed.emit()

    @Property(bool, notify=changed)
    def previewEnabled(self) -> bool:
        return self._preview_on

    @Slot(bool)
    def setPreviewEnabled(self, on: bool) -> None:
        self._preview_on = bool(on)
        self._store(PREVIEW_KEY, self._preview_on)
        self.changed.emit()

    @Property(bool, notify=changed)
    def updatesEnabled(self) -> bool:
        return self._updates_on

    @Slot(bool)
    def setUpdatesEnabled(self, on: bool) -> None:
        self._updates_on = bool(on)
        self._store(UPDATES_KEY, self._updates_on)
        self.changed.emit()

    def _tick(self) -> None:
        if self._swarm_on and self._bridge._active_key == "swarm":
            self.changed.emit()

    # -- swarm view ---------------------------------------------------------------------------------------------

    def _servers(self) -> list[swarm.SwarmServer]:
        active = self._controller._active_id
        servers: list[swarm.SwarmServer] = []
        for conn_id, conn in self._controller.connections.items():
            status = self._bridge._server_statuses.get(conn_id, "connecting")
            login = self._bridge._server_login.get(conn_id)
            if login is not None and not login[0]:
                status = "login_failed"
            raws = [robot.raw for controller in conn.state.controllers for robot in controller.robots]
            claims = {}
            for claim in conn.claims:
                claims[int(claim.robot_id)] = claim.owner_username
            servers.append(swarm.SwarmServer(conn_id, conn.info.display_name, status, raws, claims, conn_id == active))
        return servers

    def _my_account(self) -> str | None:
        conn = self._controller.active_connection
        return (conn.info.username or None) if conn is not None else None

    @Property("QVariantList", constant=True)
    def swarmFilters(self) -> list[dict[str, str]]:
        return [{"value": f, "label": _(f"SWARM_FILTER_{f.upper()}")} for f in swarm.FILTERS]

    @Property(str, notify=changed)
    def swarmFilter(self) -> str:
        return self._swarm_filter

    @Slot(str)
    def setSwarmFilter(self, mode: str) -> None:
        if mode in swarm.FILTERS and mode != self._swarm_filter:
            self._swarm_filter = mode
            self.changed.emit()

    @Property(str, notify=changed)
    def swarmText(self) -> str:
        return self._swarm_text

    @Slot(str)
    def setSwarmText(self, text: str) -> None:
        if text != self._swarm_text:
            self._swarm_text = text
            self.changed.emit()

    def swarm_rows_raw(self) -> list[dict[str, Any]]:
        return swarm.build_rows(self._servers())

    @Property("QVariantList", notify=changed)
    def swarmRows(self) -> list[dict[str, Any]]:
        if not self._swarm_on:
            return []
        me = self._my_account()
        rows = swarm.filter_rows(self.swarm_rows_raw(), self._swarm_filter, self._swarm_text, me)
        shown: list[dict[str, Any]] = []
        for row in rows:
            down = row["source"] == "none"
            shown.append({
                **row,
                "sourceText": _("SWARM_SERVER_DOWN", status=row["status"]) if down else _(f"SWARM_SOURCE_{row['source'].upper()}"),
                "playbackText": "" if down else _(f"SWARM_PLAY_{row['playback'].upper()}"),
                "combinedText": self._combined_text(row),
                "attention": swarm.needs_attention(row, me),
                "down": down,
            })
        return shown

    @staticmethod
    def _combined_text(row: dict[str, Any]) -> str:
        parts = []
        if row["combinedWith"]:
            parts.append(_("SWARM_COMBINED_WITH", ids=", ".join(f"#{i}" for i in row["combinedWith"])))
        if row["ledBy"]:
            parts.append(_("SWARM_LED_BY", ids=", ".join(f"#{i}" for i in row["ledBy"])))
        return "; ".join(parts)

    @Property(str, notify=changed)
    def swarmSummary(self) -> str:
        if not self._swarm_on:
            return ""
        s = swarm.summarize(self.swarm_rows_raw())
        return _("SWARM_SUMMARY", servers=s["servers"], reachable=s["serversReachable"], robots=s["robots"], online=s["online"],
                 playing=s["playing"], held=s["held"], combined=s["combined"])

    @Slot()
    def swarmStopAll(self) -> None:
        self._controller.stop_all()

    @Slot(str)
    def swarmStopServer(self, conn_id: str) -> None:
        conn = self._controller.connections.get(conn_id)
        if conn is not None:
            asyncio.ensure_future(self._stop_server(conn_id, conn))

    async def _stop_server(self, conn_id: str, conn: Any) -> None:
        try:
            result = await conn.stop_all()
            summary = StopAllSummary("done" if result.confirmed else "not_confirmed", {conn.info.display_name: result})
        except Exception as error:  # the stop is never silent: a failure is shown
            logger.warning("stop of %s failed: %s", conn_id, error)
            summary = StopAllSummary("not_confirmed", reason=str(error) or error.__class__.__name__)
        headline, details, severity = describe_stop_all(summary)
        self._bridge._set_notice(" ".join([headline, *details]), "info" if severity == "ok" else "warn")

    @Slot(str, int)
    def swarmOpen(self, conn_id: str, robot_id: int) -> None:
        """Makes a server active and selects one of its robots (the rest of the program then shows it)."""
        if conn_id not in self._controller.connections:
            return
        self._controller.set_active(conn_id)
        if robot_id >= 0:
            self._bridge._select_robot(str(robot_id))
        self._bridge.changed.emit()
        self.changed.emit()

    # -- combined mode ------------------------------------------------------------------------------------------

    def _selected_raw(self) -> dict[str, Any] | None:
        robot = self._bridge._selected_robot()
        return robot.raw if robot is not None else None

    def _selected_id(self) -> int | None:
        raw = self._selected_raw()
        return swarm._int_id(raw.get("id")) if raw is not None else None

    def _robots_by_id(self) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        for robot in self._bridge._active_robots():
            number = swarm._int_id(robot.raw.get("id"))
            if number is not None:
                result[number] = robot.raw
        return result

    @Property(str, notify=changed)
    def combinedStatus(self) -> str:
        """What the selected robot is combined with (shown whether or not the mode is on)."""
        raw = self._selected_raw()
        own = self._selected_id()
        if raw is None or own is None:
            return ""
        names = self._robots_by_id()

        def label(number: int) -> str:
            other = names.get(number)
            return str(other.get("name") or f"#{number}") if other is not None else f"#{number}"

        parts = []
        with_ids = swarm.combined_ids(raw)
        if with_ids:
            parts.append(_("COMBINE_ACTIVE", robots=", ".join(label(n) for n in with_ids)))
        led = [n for n, other in names.items() if own in swarm.combined_ids(other)]
        if led:
            parts.append(_("COMBINE_LEADS", robots=", ".join(label(n) for n in led)))
        return " ".join(parts) if parts else _("COMBINE_NONE")

    @Property("QVariantList", notify=changed)
    def combineOptions(self) -> list[dict[str, Any]]:
        raw = self._selected_raw()
        own = self._selected_id()
        if raw is None or own is None:
            return []
        chosen = swarm.combined_ids(raw)
        return [{**option, "checked": option["id"] in chosen} for option in swarm.combine_candidates(self._robots_by_id().values(), own)]

    @Property(int, constant=True)
    def combineLimit(self) -> int:
        return swarm.MAX_COMBINED

    @Slot(int, bool)
    def toggleCombine(self, robot_id: int, on: bool) -> None:
        robot = self._bridge._selected_robot()
        own = self._selected_id()
        if not self._combined_on or robot is None or own is None:
            return
        current = swarm.combined_ids(robot.raw)
        new = swarm.toggle_combined(current, robot_id, on, own)
        if on and new == current and robot_id not in current:
            self._bridge._set_notice(_("COMBINE_LIMIT", max=swarm.MAX_COMBINED), "warn")
            self.changed.emit()
            return
        if new == current:
            return

        def mutate(r: Any, value=new) -> None:
            r.raw["combinedWith"] = list(value)

        self._bridge._edit_robot(robot, {"combinedWith": new}, mutate)
        self.changed.emit()

    # -- path viewer and preview --------------------------------------------------------------------------------

    def _local_points(self) -> list[dict[str, Any]]:
        return [dict(p) for p in self._bridge._trajectory_points]

    def _report_for(self, points: list[dict[str, Any]], model: str | None) -> dict[str, Any]:
        return trajectory_view.analyze(points, model)

    def _issue_text(self, issue: dict[str, Any]) -> str:
        if issue["kind"] == "limit":
            return _("TRJ_ISSUE_LIMIT", point=issue["point"] + 1, joint=issue["joint"].upper(), value=f"{issue['value']:.0f}", min=f"{issue['min']:g}", max=f"{issue['max']:g}")
        return _("TRJ_ISSUE_STEP", point=issue["point"] + 1, joint=issue["joint"].upper(), delta=f"{issue['delta']:.0f}")

    def _describe(self, report: dict[str, Any]) -> dict[str, Any]:
        listed = trajectory_view.LISTED_ISSUES
        lines = [self._issue_text(i) for i in report["issues"][:listed]]
        if len(report["issues"]) > listed:
            lines.append(_("TRJ_MORE", count=len(report["issues"]) - listed))
        paths = [
            {"plane": plane, "label": _(f"TRJ_VIEW_{plane.upper()}"), "points": [{"x": x, "y": y} for x, y in trajectory_view.project(report["path"], plane)]}
            for plane in trajectory_view.PLANES
        ]
        paths.append({
            "plane": trajectory_view.ORBIT,
            "label": _("TRJ_VIEW_ORBIT", yaw=f"{self._orbit_yaw:.0f}", pitch=f"{self._orbit_pitch:.0f}"),
            "points": [{"x": x, "y": y} for x, y in trajectory_view.project_orbit(report["path"], self._orbit_yaw, self._orbit_pitch)],
        })
        summary = _("TRJ_SUMMARY", count=report["points"], length=f"{report['lengthMm']:.0f}", step=f"{report['maxStepDeg']:.0f}")
        return {"summary": summary, "clean": report["clean"], "issues": lines, "paths": paths, "points": report["points"], "count": len(report["issues"])}

    @Property("QVariantMap", notify=changed)
    def trajectoryView(self) -> dict[str, Any]:
        """The path of the points being edited, drawn on three planes, with its summary and issues."""
        robot = self._bridge._selected_robot()
        report = self._report_for(self._local_points(), robot.model if robot is not None else None)
        return self._describe(report)

    @Property(int, constant=True)
    def trajectoryViewWidth(self) -> int:
        return int(trajectory_view.VIEW["width"])

    @Property(int, constant=True)
    def trajectoryViewHeight(self) -> int:
        return int(trajectory_view.VIEW["height"])

    @Slot(int, int)
    def rotateTrajectoryOrbit(self, d_yaw: int, d_pitch: int) -> None:
        """One step of the turn of the fourth view (left/right, up/down); the step is `orbit.stepDeg` of assets/trajectory_view.json."""
        self._orbit_yaw, self._orbit_pitch = trajectory_view.turn_orbit(self._orbit_yaw, self._orbit_pitch, int(d_yaw), int(d_pitch))
        self.changed.emit()

    @Slot(int, result="QVariantMap")
    def trajectoryPointPosition(self, index: int) -> dict[str, Any]:
        """x, y, z (millimetres, as text for the fields) of a point of the list being edited; empty when it has none."""
        points = self._bridge._trajectory_points
        robot = self._bridge._selected_robot()
        if not 0 <= index < len(points):
            return {}
        position = trajectory_view.position_of(robot.model if robot is not None else None, points[index])
        return {} if position is None else {"x": f"{position[0]:.1f}", "y": f"{position[1]:.1f}", "z": f"{position[2]:.1f}"}

    @Slot(int, str, str, str)
    def setTrajectoryPointPosition(self, index: int, x: str, y: str, z: str) -> None:
        """Move a point to a typed position: the joints that come closest are found with the inverse kinematics, and a position the
        model cannot reach (farther than the tolerance of the Work import) leaves the point as it was."""
        points = self._bridge._trajectory_points
        robot = self._bridge._selected_robot()
        if not 0 <= index < len(points):
            return
        values = [trajectory_view.parse_millimetres(v) for v in (x, y, z)]
        if any(v is None for v in values):
            self._bridge._set_notice(_("TRJ_EDIT_INVALID"), "warn")
            return
        tolerance = reach.tolerance_from_config(load_config())
        moved, code, miss = trajectory_view.move_point(robot.model if robot is not None else None, points[index], (values[0], values[1], values[2]), tolerance)  # type: ignore[arg-type]
        if moved is None:
            key = {"no_kinematics": "TRJ_EDIT_NO_MODEL", "unreachable": "TRJ_EDIT_UNREACHABLE"}.get(code, "TRJ_EDIT_INVALID")
            self._bridge._set_notice(_(key, miss=f"{miss:.1f}", tolerance=f"{tolerance:g}"), "warn")
            return
        points[index] = moved
        self._bridge._set_notice(_("TRJ_EDIT_DONE", point=index + 1, x=f"{moved['x']:.1f}", y=f"{moved['y']:.1f}", z=f"{moved['z']:.1f}", miss=f"{miss:.1f}"), "info")
        self._bridge._trajectoryChanged.emit()

    @Slot(int, int)
    def moveTrajectoryPoint(self, index: int, offset: int) -> None:
        points = self._bridge._trajectory_points
        target = index + offset
        if 0 <= index < len(points) and 0 <= target < len(points) and offset != 0:
            points[index], points[target] = points[target], points[index]
            self._bridge._trajectoryChanged.emit()

    @Slot(int)
    def duplicateTrajectoryPoint(self, index: int) -> None:
        points = self._bridge._trajectory_points
        if 0 <= index < len(points):
            points.insert(index + 1, dict(points[index]))
            self._bridge._trajectoryChanged.emit()

    def _recorded_points(self) -> list[dict[str, Any]]:
        robot = self._bridge._selected_robot()
        raw = robot.raw.get("recordedPoints") if robot is not None else None
        return [dict(p) for p in raw if isinstance(p, dict)] if isinstance(raw, list) else []

    @Property("QVariantMap", notify=changed)
    def pendingPreview(self) -> dict[str, Any]:
        return self._pending_report or {}

    @Property(str, notify=changed)
    def pendingKind(self) -> str:
        return self._pending_kind

    @Slot()
    def requestPlay(self) -> None:
        """Play: with the check switched on, shows the path and the problems of the recorded points first and asks."""
        robot = self._bridge._selected_robot()
        if robot is None:
            return
        if not self._preview_on:
            self._bridge.playSelectedRobot()
            return
        self._ask("play", self._report_for(self._recorded_points(), robot.model))

    @Slot()
    def requestSend(self) -> None:
        """Send the edited points to the robot as its trajectory (with the check first when it is switched on)."""
        robot = self._bridge._selected_robot()
        if robot is None or not self._bridge._trajectory_points:
            return
        if not self._preview_on:
            self._send_points()
            return
        self._ask("send", self._report_for(self._local_points(), robot.model))

    def _ask(self, kind: str, report: dict[str, Any]) -> None:
        self._pending_kind = kind
        self._pending_report = self._describe(report)
        self.changed.emit()
        self.previewRequested.emit()

    @Slot()
    def confirmPreview(self) -> None:
        kind, self._pending_kind, self._pending_report = self._pending_kind, "", None
        if kind == "play":
            self._bridge.playSelectedRobot()
        elif kind == "send":
            self._send_points()
        self.changed.emit()

    @Slot()
    def cancelPreview(self) -> None:
        self._pending_kind, self._pending_report = "", None
        self.changed.emit()

    def _send_points(self) -> None:
        robot = self._bridge._selected_robot()
        if robot is None or not self._bridge._trajectory_points:
            return
        model = robot.model
        points: list[dict[str, Any]] = []
        for local in self._bridge._trajectory_points:
            point: dict[str, Any] = {"motionType": "model-joints", **{name: float(local[name]) for name in trajectory_view.JOINTS}}
            position = trajectory_view.position_of(model, point)
            if position is not None:
                point["x"], point["y"], point["z"] = position
            points.append(point)

        def mutate(r: Any, value=points) -> None:
            r.raw["recordedPoints"] = [dict(p) for p in value]

        self._bridge._edit_robot(robot, {"recordedPoints": points}, mutate)
        self._bridge._set_notice(_("TRJ_SENT", count=len(points)), "info")
        self.changed.emit()

    # -- check of versions --------------------------------------------------------------------------------------

    @Property(bool, notify=changed)
    def updateBusy(self) -> bool:
        return self._update_busy

    @Property("QVariantMap", notify=changed)
    def updateResult(self) -> dict[str, Any]:
        result = self._update_result
        if result is None:
            return {}
        suite = result["suite"]
        rows = [{
            "title": _("UPD_THIS_PROGRAM"),
            "installed": suite["installed"] or "-",
            "latest": suite["latest"] or "-",
            "state": _(f"UPD_STATE_{suite['state'].upper()}"),
            "api": "",
            "bad": suite["state"] == "outdated",
        }]
        for server in result["servers"]:
            api = "" if server["api"] == "unknown" else _(f"UPD_API_{server['api'].upper()}", version=server["apiVersion"], minimum=update_check.SETTINGS["minRemoteApiVersion"])
            rows.append({
                "title": _("UPD_SERVER", name=server["name"]),
                "installed": server["installed"] or "-",
                "latest": server["latest"] or "-",
                "state": _(f"UPD_STATE_{server['state'].upper()}"),
                "api": api,
                "bad": server["state"] == "outdated" or server["api"] == "too_old",
            })
        return {"rows": rows, "errors": [_("UPD_ERROR_LINE", detail=e) for e in result["errors"]]}

    @Slot()
    def checkUpdates(self) -> None:
        if not self._updates_on or self._update_busy:
            return
        self._update_busy = True
        self.changed.emit()
        asyncio.ensure_future(self._check_updates())

    async def _check_updates(self) -> None:
        servers = [
            {"name": conn.info.display_name, "appVersion": conn.info.app_version, "remoteApiVersion": conn.info.remote_api_version}
            for conn in self._controller.connections.values()
        ]
        try:
            self._update_result = await asyncio.get_running_loop().run_in_executor(None, update_check.run_check, __version__, servers)
        except Exception as error:  # run_check does not raise; this is only the last guard
            self._update_result = {"suite": {"installed": __version__, "latest": None, "state": "unknown"}, "servers": [], "errors": [str(error)]}
        finally:
            self._update_busy = False
            self.changed.emit()
