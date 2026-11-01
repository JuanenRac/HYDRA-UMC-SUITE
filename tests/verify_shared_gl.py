# =============================================================================
# HYDRA-UMC SUITE - tests/verify_shared_gl.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The 3D views share one GL context (render/viewport.py): the renderers that draw in the same context share the
# program and the buffers of every mesh set instead of loading their own copy, and the context is created once. The
# checks do not need a graphics card: no GL call is made (the context is a stand-in, the renderers are only built).
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.render.viewport import GLResources, RobotGLRenderer, SharedGLContext

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class FakeContext(SharedGLContext):
    """A context that touches no graphics API: it only counts the pairs of make_current / done_current that reach it."""

    created = 0

    def __init__(self) -> None:
        FakeContext.created += 1
        self.resources = GLResources()
        self._current_depth = 0
        self.real_makes = 0
        self.real_dones = 0

    def make_current(self) -> None:
        if self._current_depth == 0:
            self.real_makes += 1
        self._current_depth += 1

    def done_current(self) -> None:
        self._current_depth -= 1
        if self._current_depth == 0:
            self.real_dones += 1


def main() -> int:
    SharedGLContext.reset()
    SharedGLContext._instance = None
    first = FakeContext.get()
    second = FakeContext.get()
    check("context: one for everybody, created once", (first is second, FakeContext.created), (True, 1))
    SharedGLContext.reset()
    third = FakeContext.get()
    check("context: a reset makes the next view create a new one", (third is first, FakeContext.created), (False, 2))

    third.make_current()
    third.make_current()
    third.done_current()
    check("context: nested pairs touch the real context only once", (third.real_makes, third.real_dones), (1, 0))
    third.done_current()
    check("context: and release it with the outermost pair", (third.real_makes, third.real_dones), (1, 1))

    shared = third.resources
    a = RobotGLRenderer(third.make_current, third.done_current, shared)
    b = RobotGLRenderer(third.make_current, third.done_current, shared)
    check("renderers of one context share the mesh buffers, the colors of the parts and the frames", (a._mesh_buffers_by_dir is b._mesh_buffers_by_dir is shared.mesh_buffers_by_dir, a._part_colors_by_dir is b._part_colors_by_dir, a._machine_frames is b._machine_frames), (True, True, True))
    a._mesh_buffers_by_dir["robots-6-dof/ur5e"] = {"base": object()}
    check("a mesh set one of them loaded is there for the other", "robots-6-dof/ur5e" in b._mesh_buffers_by_dir, True)

    alone = RobotGLRenderer(lambda: None, lambda: None)
    check("a renderer built without a context of its own to share keeps private resources", (alone._mesh_buffers_by_dir is shared.mesh_buffers_by_dir, alone._resources is not shared), (False, True))

    check("the program is built once per context: none until the first view starts", (shared.program, shared.uniforms, shared.generic_buffers), (None, {}, []))
    SharedGLContext.reset()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
