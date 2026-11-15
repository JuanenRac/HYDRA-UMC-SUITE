# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ros2_security.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The requirement of ROS 2 security (SROS2) of the ROS 2 bridge. The bridge keeps it in its own configuration file (security.require_sros2, OFF
# by default, so a machine without a keystore keeps starting) and does not report it to the server, so this app can neither read nor change it:
# this module only prepares the lines to add to that file and the environment the bridge then checks at start. Nothing is sent anywhere, and
# nothing here ever says that the bridge is secured. Read without any window toolkit.
# =============================================================================
from __future__ import annotations

import json

from hydra_suite.i18n import _

# What the bridge checks in its environment when the requirement is on (ROS 2 itself reads these variables).
ENVIRONMENT = (
    "ROS_SECURITY_ENABLE=true",
    "ROS_SECURITY_STRATEGY=Enforce",
    'ROS_SECURITY_KEYSTORE=<directory that holds "enclaves">',
)


def preparation(required: bool) -> dict | None:
    """The lines to add for the wanted value; None for the default (off), where there is nothing to add."""
    if not required:
        return None
    return {"config": json.dumps({"security": {"require_sros2": True}}, indent=2), "environment": list(ENVIRONMENT)}


def view(required: bool) -> dict:
    """What the section shows: the plain statement, the state sentence and, only when switched on, the lines to add."""
    prepared = preparation(required)
    return {
        "notReported": _("ROS2SEC_NOT_REPORTED"),
        "state": _("ROS2SEC_STATE_ON") if prepared else _("ROS2SEC_STATE_OFF"),
        "prepared": prepared is not None,
        "config": prepared["config"] if prepared else "",
        "environment": "\n".join(prepared["environment"]) if prepared else "",
    }
