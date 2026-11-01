# =============================================================================
# HYDRA-UMC SUITE - robot_edits.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The edits of one robot as commands. The recorded points, the repeat flag, the model, the role, the robots it is
# combined with, the joint values of the sliders and the layout of the XY table used to travel only inside the
# whole settings tree, which the server takes from an administrator alone and where the last writer wins. The server
# has a command for each of them (points, loop, model, role, combine, joints, xyTableConfig), carried out under the
# reservation, If-Match and arming rules of every other command. This file decides, from what a panel changed,
# which commands say the same thing: the same plan HYDRA-UMC-STUDIO makes (src/lib/robotEdits.ts). Nothing here
# talks to the network.
# =============================================================================
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

EDIT_COMMANDS: frozenset[str] = frozenset({"points", "loop", "model", "role", "combine", "joints", "xyTableConfig"})

#: The fields of the layout of the XY table that travel with the xyTableConfig command.
TABLE_LAYOUT_FIELDS: tuple[str, ...] = ("tableSize", "worldPos", "worldRot", "renderScale")


@dataclass
class RobotEditPlan:
    #: (command, params) in the order they go out.
    commands: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    #: The changed fields no command covers (they still travel in the settings tree, for an account that may save it).
    rest: list[str] = field(default_factory=list)


def _same(a: Any, b: Any) -> bool:
    return a == b or json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def plan_robot_edits(current: dict[str, Any] | None, updates: dict[str, Any], *, joints: bool = False) -> RobotEditPlan:
    """The commands that say what `updates` changes on `current` (the raw dict of the robot).

    Joints are only planned when asked for: the pose worked out from a jog travels with the jog itself, and only the
    sliders send the joints.
    """
    current = current or {}
    plan = RobotEditPlan()
    table: dict[str, Any] | None = None
    for key, value in updates.items():
        if key == "recordedPoints":
            if isinstance(value, list):
                plan.commands.append(("points", {"points": value}))
            else:
                plan.rest.append(key)
        elif key == "model":
            if isinstance(value, str) and value.strip():
                plan.commands.append(("model", {"model": value}))
            else:
                plan.rest.append(key)
        elif key == "role":
            if isinstance(value, str):
                plan.commands.append(("role", {"role": value}))
            else:
                plan.rest.append(key)
        elif key == "combinedWith":
            if isinstance(value, list) and all(isinstance(i, int) and not isinstance(i, bool) for i in value):
                plan.commands.append(("combine", {"with": value}))
            else:
                plan.rest.append(key)
        elif key == "joints":
            if joints and isinstance(value, dict):
                plan.commands.append(("joints", {"joints": value}))
            else:
                plan.rest.append(key)
        elif key == "playbackState":
            nxt = value if isinstance(value, dict) else {}
            before = current.get("playbackState") if isinstance(current.get("playbackState"), dict) else {}
            changed = [f for f in {**before, **nxt} if not _same(before.get(f), nxt.get(f))]
            if not changed:
                continue
            if changed == ["isLooping"] and isinstance(nxt.get("isLooping"), bool):
                plan.commands.append(("loop", {"value": nxt["isLooping"]}))
            else:
                plan.rest.append(key)
        elif key == "hasXYTable":
            if isinstance(value, bool):
                table = table if table is not None else {}
                table["enabled"] = value
            else:
                plan.rest.append(key)
        elif key == "xyTable":
            nxt = value if isinstance(value, dict) else {}
            before = current.get("xyTable") if isinstance(current.get("xyTable"), dict) else {}
            covered = True
            for f in {**before, **nxt}:
                if _same(before.get(f), nxt.get(f)):
                    continue
                if f in TABLE_LAYOUT_FIELDS and nxt.get(f) is not None:
                    table = table if table is not None else {}
                    table[f] = nxt[f]
                else:
                    covered = False  # the position of the table travels with the table command, not with its layout
            if not covered:
                plan.rest.append(key)
        else:
            plan.rest.append(key)
    if table:
        plan.commands.append(("xyTableConfig", table))
    return plan
