# =============================================================================
# HYDRA-UMC-SUITE - language file parity verifier
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Every language/*.lng carries exactly the keys english.lng has, with the same
# {placeholders} and the same number of literal \n line breaks, and every
# language the window offers (i18n.AVAILABLE_LANGUAGES) has its file. A missing
# key silently shows the English text (or the bare key) in the window, and a
# renamed placeholder breaks the message at run time. No Qt is needed.
# =============================================================================
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hydra_suite.i18n import AVAILABLE_LANGUAGES, LANGUAGE_FOLDER

PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def load(name: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (LANGUAGE_FOLDER / f"{name}.lng").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            assert key not in values, f"{name}.lng: key {key} appears twice (the later one silently wins)"
            values[key] = value
    return values


# The words every app of the ecosystem shows the same way live in contracts/i18n/common.json of HYDRA-UMC-SDK; the language files carry them as COMMON_<ID>.
# The 56 words are in the eight files, none empty, and (when a checkout of the SDK is at hand: HYDRA_UMC_SDK_DIR or the sibling folder) exactly as the contract writes them.
# The keys that said the same thing in the same words were removed and the screens ask for the common one: they must not come back.
COMMON_IDS = 56
REMOVED_AS_DUPLICATES = ["ACCESS_DISABLE", "ACCESS_ENABLE", "AUDIT_COL_ACCOUNT", "AUDIT_COL_ROBOT", "AUDIT_COL_TIME", "AUDIT_COL_TYPE", "BTN_CLEAR", "BTN_CLEAR_LOGS", "BTN_CLOSE", "BTN_PAUSE", "BTN_PLAYBACK_PAUSE", "BTN_SAVE", "CAMERA_MEDIA_DELETE", "CAMERA_MEDIA_PAUSE", "COL_ROBOT", "COL_ROBOTS", "COL_ROLE", "DOCK_USERS", "HUBGATE_SAVED", "LBL_ADMIN_SERVER_STAT_CONTROLLERS", "LBL_ADMIN_SERVER_STAT_ROBOTS", "LBL_COL_TIME", "LBL_IP_PASSWORD", "LBL_MEMORY", "LBL_NAME", "LBL_PASSWORD", "LBL_ROBOTS", "LBL_SPEED", "LBL_SUPERVISOR_MEMORY", "LBL_SUPERVISOR_TEMP_TREND", "LBL_TEMP", "MODELS_COL_NAME", "OPSPROP_APPROVE", "PLANNERID_SAVED", "SECURITY_SAVED", "SETUP_HISTORY_COL_ACCOUNT", "SETUP_HISTORY_COL_ROBOT", "SETUP_HISTORY_COL_TIME", "SETUP_HISTORY_COL_TYPE", "SETUP_HISTORY_COL_WHO", "SETUP_SECURITY_COL_KEY", "SWARM_COL_ROBOT", "TOTP_CANCEL", "TOTP_KEY", "TRJ_CANCEL", "USERS_DELETE", "USERS_NEW_PASSWORD", "USERS_ROLE_ADMIN", "USERS_ROLE_OPERATOR"]


def check_common_texts(codes: list[str]) -> None:
    import os

    english = load("english")
    ids = sorted(key for key in english if key.startswith("COMMON_"))
    assert len(ids) == COMMON_IDS, f"expected {COMMON_IDS} common texts, found {len(ids)}"
    for code in codes:
        table = load(code)
        assert all(table.get(key, "").strip() for key in ids), f"{code}: a common text is missing or empty"
        back = [key for key in REMOVED_AS_DUPLICATES if key in table]
        assert not back, f"{code}: {back[:3]} came back; the screens use the common text"
    roots = [os.environ.get("HYDRA_UMC_SDK_DIR"), str(ROOT.parent / "HYDRA-UMC-SDK")]
    contract = next((Path(r) / "contracts" / "i18n" / "common.json" for r in roots if r and (Path(r) / "contracts" / "i18n" / "common.json").is_file()), None)
    if contract is None:
        return
    data = json.loads(contract.read_text(encoding="utf-8"))
    names = {"en": "english", "es": "spanish", "de": "german", "fr": "french", "it": "italian", "ja": "japanese", "zh": "chinese", "pt": "portuguese"}
    for entry in data["strings"]:
        for lang, text in entry["text"].items():
            key = "COMMON_" + entry["id"].upper()
            assert load(names[lang]).get(key) == text, f"{names[lang]}: {key} is not the text of the contract"


def main() -> None:
    english = load("english")
    assert len(english) > 400, f"english.lng looks truncated: {len(english)} keys"
    codes = [code for code, _label in AVAILABLE_LANGUAGES]
    assert "portuguese" in codes, "the language menu does not offer Portuguese"
    on_disk = sorted(p.stem for p in LANGUAGE_FOLDER.glob("*.lng"))
    assert sorted(codes) == on_disk, f"menu {sorted(codes)} != files on disk {on_disk}"
    for code in codes:
        if code == "english":
            continue
        table = load(code)
        missing = sorted(set(english) - set(table))
        extra = sorted(set(table) - set(english))
        assert not missing and not extra, f"{code}: missing {missing[:5]}, extra {extra[:5]}"
        for key, value in english.items():
            assert sorted(PLACEHOLDER.findall(table[key])) == sorted(PLACEHOLDER.findall(value)), f"{code}: {key} changed its placeholders"
            assert table[key].count("\\n") == value.count("\\n"), f"{code}: {key} changed its line breaks"
            assert table[key].strip(), f"{code}: {key} is empty"
    check_common_texts(codes)
    print(f"verify_language_files: OK ({len(codes)} languages x {len(english)} keys)")


if __name__ == "__main__":
    main()
