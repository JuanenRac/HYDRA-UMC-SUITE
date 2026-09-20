# =============================================================================
# HYDRA-UMC-SUITE - Real per-part color override regression tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Covers the same real gap HYDRA-UMC-STUDIO's own hooks/usePartColors.ts
# closed: a part_colors.json saved by the separate HYDRA-UMC-EDITOR-STL
# tool used to have zero effect on SUITE's own live 3D viewport - these
# checks exercise part_colors.py's own loader plus its 3 real call sites
# (RobotGLRenderer._link_color, module_rig.rack_segments,
# module_rig.module_segments) without touching any real asset under
# assets/meshes/ (every fixture below lives in a real tmp directory).
# =============================================================================
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra_suite.render.part_colors import hex_to_rgb01, load_part_colors
from hydra_suite.render.viewport import RobotGLRenderer


def _noop() -> None:
    return None


def main() -> None:
    # --- load_part_colors: honest empty dict, never an error -----------
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        assert load_part_colors(tmp_path) == {}, "no sidecar file yet must be an honest {}"

        (tmp_path / "part_colors.json").write_text('{"link_1.STL": "#ff0000", "link_2.STL": "#00ff00"}', encoding="utf-8")
        assert load_part_colors(tmp_path) == {"link_1.STL": "#ff0000", "link_2.STL": "#00ff00"}

        (tmp_path / "part_colors.json").write_text("{not valid json", encoding="utf-8")
        assert load_part_colors(tmp_path) == {}, "a corrupt sidecar must fail closed to {}, never raise"

        (tmp_path / "part_colors.json").write_text('[1, 2, 3]', encoding="utf-8")
        assert load_part_colors(tmp_path) == {}, "a sidecar that isn't a JSON object must fail closed to {}"

        (tmp_path / "part_colors.json").write_text('{"link_1.STL": "#ff0000", "link_2.STL": 5}', encoding="utf-8")
        assert load_part_colors(tmp_path) == {"link_1.STL": "#ff0000"}, "a non-string value for one entry must be dropped, not crash the whole load"

    # --- hex_to_rgb01: real, exact conversion + honest None on garbage --
    assert hex_to_rgb01("#ff0000") == (1.0, 0.0, 0.0)
    assert hex_to_rgb01("#00ff00") == (0.0, 1.0, 0.0)
    assert hex_to_rgb01("#0000ff") == (0.0, 0.0, 1.0)
    r, g, b = hex_to_rgb01("#9fb4c9")
    assert abs(r - 0x9F / 255) < 1e-9 and abs(g - 0xB4 / 255) < 1e-9 and abs(b - 0xC9 / 255) < 1e-9
    for garbage in ("", "not-a-color", "#fff", "ff0000", None, 5, "#gggggg"):
        assert hex_to_rgb01(garbage) is None, f"expected None for garbage input {garbage!r}"

    # --- RobotGLRenderer._link_color: the real per-link lookup used by
    # paint_gl()/_draw_pnp() - constructed with no-op make_current/
    # done_current so this exercises the pure lookup with zero real GL
    # context (this method itself never touches the GPU). -----------------
    renderer = RobotGLRenderer(_noop, _noop)
    default = (0.72, 0.75, 0.80)
    assert renderer._link_color("robots-6-dof/ur5e", "base.stl", default) == default, "no colors loaded for this dir yet -> the caller's own default"

    renderer._part_colors_by_dir["robots-6-dof/ur5e"] = {"base.stl": "#123456"}
    got = renderer._link_color("robots-6-dof/ur5e", "base.stl", default)
    assert got == hex_to_rgb01("#123456"), "a real saved override must win over the default"
    assert renderer._link_color("robots-6-dof/ur5e", "shoulder.stl", default) == default, "an unlisted part in the same dir must still fall back to the default"

    renderer._part_colors_by_dir["robots-6-dof/ur5e"] = {"base.stl": "not-a-real-color"}
    assert renderer._link_color("robots-6-dof/ur5e", "base.stl", default) == default, "a corrupt saved override must fail closed to the default, never crash paint_gl"

    # --- module_rig.py: rack/heated-bed/vacuum-table segments honor a
    # real saved override, and never invent one when none is saved -------
    from hydra_suite.render import module_rig

    real_rack_dir = module_rig.RACK_DIR
    with tempfile.TemporaryDirectory() as tmp:
        fake_dir = Path(tmp)
        (fake_dir / "part_colors.json").write_text('{"base.stl": "#ff00ff"}', encoding="utf-8")
        module_rig.RACK_DIR = fake_dir
        try:
            rack = dict(type="Input", capacity=1, width=160, depth=160, color="#abcdef", usableSlots=[True])
            segs = module_rig.rack_segments(rack)
            base_seg = next(s for s in segs if s.model_id == "base")
            wall_seg = next(s for s in segs if s.model_id == "wall")
            assert base_seg.color == hex_to_rgb01("#ff00ff"), "the base part has a real saved override - it must be used"
            assert wall_seg.color == tuple(int("abcdef"[i:i+2], 16) / 255 for i in (0, 2, 4)), "the wall part has no saved override - it must keep the rack's own configured color"
        finally:
            module_rig.RACK_DIR = real_rack_dir

    print("VERIFY_PART_COLORS=PASS load=4 hex=8 link_color=4 rack_override=2")


if __name__ == "__main__":
    main()
