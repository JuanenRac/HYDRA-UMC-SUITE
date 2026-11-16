# =============================================================================
# HYDRA-UMC SUITE - tests/verify_qml_plaintext.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The texts that come from the server or from other clients (the administration log, the audit record, the names of
# accounts and robots) must be drawn as plain text, never as styled text: every Text element bound to those values has
# to say so. Static check of assets/qml/Main.qml, no Qt needed.
# =============================================================================
import re
import sys
from pathlib import Path

SOURCE = Path("assets/qml/Main.qml").read_text(encoding="utf-8").replace("\r\n", "\n")
BOUND = re.compile(r"Text \{ text: modelData\.(?:seq|time|type|outcome|account|controller|address|robot|detail);[^\n]*")
failures = []
for line_number, line in enumerate(SOURCE.splitlines(), 1):
    for match in BOUND.finditer(line):
        if "textFormat:" not in match.group(0):
            failures.append(line_number)
LOG_DELEGATE = "delegate: Text {\n                    required property string modelData\n                    width: ListView.view.width\n                    textFormat: Text.PlainText"
if LOG_DELEGATE not in SOURCE:
    failures.append(0)
if failures:
    print("FAIL: Text elements bound to server data without textFormat at lines", failures)
    sys.exit(1)
print("PASS: texts bound to server data are drawn as plain text")
