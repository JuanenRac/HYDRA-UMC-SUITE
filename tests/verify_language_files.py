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
            values[key] = value
    return values


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
            assert table[key].count("\n") == value.count("\n"), f"{code}: {key} changed its line breaks"
            assert table[key].strip(), f"{code}: {key} is empty"
    print(f"verify_language_files: OK ({len(codes)} languages x {len(english)} keys)")


if __name__ == "__main__":
    main()
