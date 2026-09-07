# =============================================================================
# HYDRA-UMC SUITE - ui/panels/laser_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The Laser module config panel - HYDRA-UMC-STUDIO's own Laser.tsx ported
# via module_config_panel.py's shared ModuleConfigPanel (see that file's
# own header for why the two source components are identical enough to
# share one implementation). "JuanenLaser" is the one real machine type
# STUDIO's own machineType selector currently offers.
# =============================================================================
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from hydra_suite.app import SuiteController
from hydra_suite.ui.panels.module_config_panel import ModuleConfigPanel


class LaserPanel(ModuleConfigPanel):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(controller, "juanenLaser", "HEADING_LASER", "JuanenLaser", parent)
