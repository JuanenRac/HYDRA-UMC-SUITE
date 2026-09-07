# =============================================================================
# HYDRA-UMC SUITE - render/viewport.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real-time 3D robot viewport - a core-profile GLSL shader (not legacy
# immediate-mode glBegin/glEnd, since Qt's own default-created context on
# most drivers is a core-profile one that doesn't support the legacy path
# at all). Renders the real STL meshes (render/mesh.py) for all 24 real
# robot models plus a primitive-built "Generic" fallback
# (render/generic_rig.py), posed every frame from the real forward
# kinematics (render/kinematics.py) driven by live joint angles from a
# connected HydraConnection's own RobotView - not a stylized placeholder,
# the same "real geometry, real chain" standard HYDRA-UMC-STUDIO's own
# *Arm.tsx components already hold themselves to.
#
# Y-up world (matches Three.js/HYDRA-UMC-STUDIO, see kinematics.py's own
# header) - the camera's own up vector and pan axes below are Y-up too.
#
# RobotGLRenderer below owns every real GL call and every piece of pose/
# camera state - genuinely context-agnostic (it never touches
# QOpenGLWidget itself), driven entirely through the `make_current`/
# `done_current` callables its own constructor takes. RobotViewport (the
# classic QOpenGLWidget the whole QDockWidget app already uses in 13
# places) is now a thin wrapper delegating initializeGL/resizeGL/paintGL/
# every public setter to one RobotGLRenderer instance, with IDENTICAL
# real behavior to the pre-refactor version (including the "skip a
# repaint when the pose didn't actually change" optimization - see
# set_joints_deg's own comment). OffscreenRobotRenderer (bottom of this
# file) is the SAME split's other real owner - the Qt Quick shell's own
# 3D Viewport panel (qt_suite.py) renders through it instead of a widget's
# own compositor, reusing this exact rendering code rather than a second,
# drifting copy - see that class's own header for why it's a genuinely
# separate QOpenGLContext/QOffscreenSurface/FBO rather than Qt Quick's own
# QQuickFramebufferObject (which would force the whole app off Windows'
# real default Direct3D11 Quick backend onto OpenGL just for one panel).
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
from OpenGL import GL as gl
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QMouseEvent, QOffscreenSurface, QOpenGLContext, QSurfaceFormat, QWheelEvent
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from hydra_suite.render.generic_rig import SEGMENTS, generic_frame_transforms, segment_world_transform
from hydra_suite.render.kinematics import ROBOT_REGISTRY, quat_family_mesh_world_transforms, ur_mesh_world_transforms
from hydra_suite.render.mesh import Mesh, load_link_set, make_box_mesh, make_cylinder_mesh
from hydra_suite.render.module_rig import module_segments
from hydra_suite.render.module_rig import segment_world_transform as module_segment_world_transform
from hydra_suite.render.pnp_rig import PNP_LINK_NAMES, PNP_MESH_DIR, PNP_MESH_FILES, pnp_world_link_transforms

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "meshes"

DEFAULT_MODEL = "UR5e (6-DOF)"

# LumenPnP/JuanenPnP link colors - hex values copied verbatim from
# LumenPnPRig.tsx's own frameMat/carriageMat/nozzleMat (Opulo's own real
# brand yellow on the moving nozzle carriages, neutral aluminum-extrusion
# gray for the fixed frame and the Y/X carriages).
_PNP_COLOR_FRAME = (0x9A / 255, 0xA1 / 255, 0xAB / 255)
_PNP_COLOR_CARRIAGE = (0xC7 / 255, 0xCD / 255, 0xD6 / 255)
_PNP_COLOR_NOZZLE = (0xEA / 255, 0xB3 / 255, 0x08 / 255)
_PNP_LINK_COLORS: dict[str, tuple[float, float, float]] = {
    "base": _PNP_COLOR_FRAME,
    "y_carriage": _PNP_COLOR_CARRIAGE,
    "x_carriage": _PNP_COLOR_CARRIAGE,
    "z_carriage_n1": _PNP_COLOR_NOZZLE,
    "z_carriage_n2": _PNP_COLOR_NOZZLE,
}

VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat3 uNormalMatrix;

out vec3 vNormalWorld;
out vec3 vPositionWorld;

void main() {
    vec4 worldPos = uModel * vec4(inPosition, 1.0);
    vPositionWorld = worldPos.xyz;
    vNormalWorld = normalize(uNormalMatrix * inNormal);
    gl_Position = uProjection * uView * worldPos;
}
"""

FRAGMENT_SHADER = """
#version 330 core
in vec3 vNormalWorld;
in vec3 vPositionWorld;

uniform vec3 uBaseColor;
uniform vec3 uCameraPos;

out vec4 fragColor;

void main() {
    vec3 lightDir1 = normalize(vec3(0.5, 0.8, 0.6));
    vec3 lightDir2 = normalize(vec3(-0.4, 0.3, -0.5));
    vec3 n = normalize(vNormalWorld);

    float diffuse1 = max(dot(n, lightDir1), 0.0);
    float diffuse2 = max(dot(n, lightDir2), 0.0) * 0.35;
    float ambient = 0.28;

    vec3 viewDir = normalize(uCameraPos - vPositionWorld);
    vec3 halfVec = normalize(lightDir1 + viewDir);
    float spec = pow(max(dot(n, halfVec), 0.0), 32.0) * 0.4;

    // Faint cyan rim light - the "futuristic industrial" accent this
    // whole app's own QSS theme uses elsewhere, not just a plain gray
    // robot floating in a plain void.
    float rim = pow(1.0 - max(dot(n, viewDir), 0.0), 3.0) * 0.5;
    vec3 rimColor = vec3(0.13, 0.83, 0.93);

    vec3 color = uBaseColor * (ambient + diffuse1 + diffuse2) + vec3(spec) + rimColor * rim;
    fragColor = vec4(color, 1.0);
}
"""


def perspective(fovy_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / np.tan(np.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, 0:3] = s
    m[1, 0:3] = u
    m[2, 0:3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


class GLMeshBuffer:
    """One VBO holding a single link's interleaved position+normal data."""

    def __init__(self, mesh: Mesh):
        interleaved = np.hstack([mesh.vertices, mesh.normals]).astype(np.float32)
        self.vertex_count = len(mesh.vertices)
        self.vao = gl.glGenVertexArrays(1)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, interleaved.nbytes, interleaved, gl.GL_STATIC_DRAW)
        stride = 6 * 4  # 6 floats/vertex, 4 bytes/float
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(3 * 4))
        gl.glEnableVertexAttribArray(1)
        gl.glBindVertexArray(0)

    def draw(self) -> None:
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.vertex_count)
        gl.glBindVertexArray(0)


class RobotGLRenderer:
    """Every real GL call and every piece of pose/camera state for the 3D
    viewport - genuinely context-agnostic. `make_current`/`done_current`
    are real callables the OWNER (a QOpenGLWidget, or an offscreen FBO
    wrapper) provides so mesh uploads that happen outside
    initialize_gl()/paint_gl() (a runtime model switch, an attached-module
    change) bind the right context regardless of which real owner this
    renderer belongs to - see RobotViewport/qt_suite.py's own
    OffscreenRobotRenderer for the two real owners."""

    def __init__(self, make_current: Callable[[], None], done_current: Callable[[], None]):
        self._make_current = make_current
        self._done_current = done_current

        self._program: int | None = None
        self._gl_ready = False
        # Uniform locations resolved once, right after linking (see
        # initialize_gl) - a name->location lookup never changes for the
        # lifetime of a linked program, so paint_gl/_draw_model/_draw_generic
        # below look one up from this dict instead of re-querying it from
        # the driver by string on every single draw call, every frame.
        self._uniforms: dict[str, int] = {}

        # Real-mesh robots: one GLMeshBuffer set per mesh_dir, loaded lazily
        # and cached (a server might have several robots of the same
        # model - no point re-uploading identical geometry to the GPU for
        # each one) rather than eagerly loading all 9 robots' meshes at
        # startup, most of which may never be viewed in a given session.
        self._mesh_buffers_by_dir: dict[str, dict[str, GLMeshBuffer]] = {}
        # Generic rig: one buffer per SEGMENTS index, built once (fixed
        # geometry - only the pose changes frame to frame).
        self._generic_buffers: list[GLMeshBuffer] = []

        self._model_name = DEFAULT_MODEL
        entry = ROBOT_REGISTRY[DEFAULT_MODEL]
        self._joints_deg: dict[str, float] = dict(entry.home_pose_deg)

        # Module-only mode (render/module_rig.py) - a SEPARATE renderer
        # embedded in ModuleConfigPanel switches into this via
        # set_attached_module() instead of ever calling set_robot_model();
        # no robot is drawn while a module is set. None = normal
        # robot-viewport mode (the shared 3D Viewport dock and every
        # *ArmDetail screen use this that way).
        self._attached_module_type: str | None = None
        self._module_buffers: list[GLMeshBuffer] = []
        self._module_segments_cache: list = []
        self._pending_module_rebuild = False

        # PnP module-only mode (render/pnp_rig.py) - a separate real-mesh
        # sibling of the module-only mode above, used by
        # ui/panels/pick_and_place_panel.py's own embedded viewport
        # instead of set_attached_module(): juanenPnP/lumenPnP have a real
        # STL rig (assets/meshes/lumenpnp/), not primitive box/cylinder
        # geometry, and a real 2-axis-plus-2-nozzle pose rather than a
        # static width/length. Mutually exclusive with
        # _attached_module_type in practice (each embedding panel only
        # ever calls one of the two setters on a given instance) but kept
        # as an independent flag rather than folded into it, since the
        # mesh-loading/draw path genuinely differs (real STL set vs.
        # primitives built from Segment).
        self._pnp_machine_type: str | None = None
        self._pnp_pose: tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)
        self._pending_pnp_mesh_load = False

        self._yaw = -35.0
        self._pitch = 20.0
        self._distance = 2.2
        self._target = np.array([0.0, 0.4, 0.0], dtype=np.float32)

        self._width = 320
        self._height = 240

    # --- public setters (owner decides whether/how to schedule a repaint
    # after calling one of these - see set_joints_deg's own real return
    # value for why that decision needs real information, not just
    # "always repaint") -----------------------------------------------

    def set_joints_deg(self, joints: dict[str, float]) -> bool:
        # Callers may invoke this on EVERY active_state_changed tick, which
        # fires for ANY change anywhere in the swarm's settings tree (any
        # robot, any controller, a metrics-unrelated config field) - not
        # just a change to the one robot this viewport is currently
        # showing. Against a real multi-robot swarm streaming live
        # telemetry, every one of those pushes would otherwise schedule a
        # full GL repaint here regardless of whether the robot on screen
        # actually moved - the busier the rest of the swarm, the more this
        # one viewport would repaint for motion that has nothing to do
        # with what it's displaying. Comparing against the pose already on
        # screen and reporting "nothing changed" back to the caller fixes
        # that at the source (the actual cost - GL draw calls - never
        # happens) instead of throttling/debouncing calls that would still
        # eventually fire.
        if joints == self._joints_deg:
            return False
        self._joints_deg = dict(joints)
        return True

    def set_robot_model(self, model_name: str) -> bool:
        """Switches which robot is rendered - loads that model's own STL
        set on first use (a no-op for models already cached, and for
        "Generic", which has no STL to load at all)."""
        if model_name not in ROBOT_REGISTRY:
            return False
        self._model_name = model_name
        entry = ROBOT_REGISTRY[model_name]
        self._joints_deg = dict(entry.home_pose_deg)
        if self._gl_ready and entry.family in ("ur", "quat") and entry.mesh_dir not in self._mesh_buffers_by_dir:
            self._load_mesh_set(entry.mesh_dir, entry.link_names, entry.mesh_files)
        return True

    def set_attached_module(self, module_type: str | None, width_mm: float = 500.0, length_mm: float = 500.0) -> None:
        """Switches this renderer into module-only mode (render/module_rig.py)
        - a real live 3D preview of a tool-attachment module's own real
        geometry, matching HYDRA-UMC-STUDIO's own SharedModule3DView.tsx.
        `module_type=None` returns to normal robot-viewport mode."""
        self._attached_module_type = module_type
        segs = module_segments(module_type, width_mm, length_mm) if module_type else []
        if self._gl_ready:
            self._make_current()
            try:
                self._module_buffers = [
                    GLMeshBuffer(make_cylinder_mesh(*seg.size) if seg.kind == "cylinder" else make_box_mesh(*seg.size))
                    for seg in segs
                ]
            finally:
                self._done_current()
            self._module_segments_cache = segs
        else:
            # GL context not ready yet (constructed but not shown/rendered)
            # - initialize_gl()'s own real-world caller order means this
            # can happen for a freshly-created module-only renderer; stash
            # the real segments so the buffers can be built once
            # initialize_gl() does run, instead of silently losing this call.
            self._module_segments_cache = segs
            self._pending_module_rebuild = True

    def set_attached_pnp(
        self,
        machine_type: str | None,
        axis_x_mm: float = 0.0,
        axis_y_mm: float = 0.0,
        axis_z_mm: float = 0.0,
        nozzle1_deg: float = 0.0,
        nozzle2_deg: float = 0.0,
    ) -> None:
        """Switches this renderer into PnP module-only mode
        (render/pnp_rig.py) - a real live 3D preview of the LumenPnP/
        JuanenPnP gantry, matching HYDRA-UMC-STUDIO's own real-mesh
        LumenPnPRig.tsx. `machine_type` is `"juanenPnP"`/`"lumenPnP"` (both
        share the exact same real mesh set and rig - see
        assets/meshes/lumenpnp/ATTRIBUTION.txt) or `None` to leave PnP
        mode. The mesh set loads once, lazily, on first real use (same
        caching as every robot's own mesh set in _mesh_buffers_by_dir) -
        not at construction time, since a renderer that's never shown a
        PnP preview shouldn't pay for it."""
        self._pnp_machine_type = machine_type
        self._pnp_pose = (axis_x_mm, axis_y_mm, axis_z_mm, nozzle1_deg, nozzle2_deg)
        if machine_type is not None and PNP_MESH_DIR not in self._mesh_buffers_by_dir:
            if self._gl_ready:
                self._load_mesh_set(PNP_MESH_DIR, PNP_LINK_NAMES, PNP_MESH_FILES)
            else:
                # Same real-world timing gap set_attached_module() already
                # guards against: a freshly-constructed, not-yet-rendered
                # renderer has no GL context yet for _load_mesh_set()'s own
                # make_current() to bind - stash the request so
                # initialize_gl() can load it once a context actually
                # exists, instead of silently losing this call.
                self._pending_pnp_mesh_load = True

    def orbit(self, dx: float, dy: float) -> None:
        self._yaw -= dx * 0.4
        self._pitch = float(np.clip(self._pitch + dy * 0.4, -85.0, 85.0))

    def pan(self, dx: float, dy: float) -> None:
        yaw = np.radians(self._yaw)
        right = np.array([-np.sin(yaw), 0.0, np.cos(yaw)], dtype=np.float32)
        up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        pan_scale = self._distance * 0.0015
        self._target -= right * dx * pan_scale
        self._target += up * dy * pan_scale

    def zoom(self, factor: float) -> None:
        self._distance = float(np.clip(self._distance * factor, 0.3, 15.0))

    def _load_mesh_set(self, mesh_dir: str, link_names: tuple[str, ...], mesh_files: dict[str, str]) -> None:
        meshes = load_link_set(ASSETS_DIR / mesh_dir, mesh_files)
        # set_robot_model() (this method's only non-initialize_gl caller)
        # runs from a plain Qt slot - Qt only guarantees the OWNER's own
        # GL context is current inside initializeGL/paintGL/resizeGL (or,
        # for the offscreen owner, inside its own explicit render call),
        # not here, so glGenVertexArrays/glGenBuffers below could otherwise
        # execute against whatever context happened to be bound at that
        # moment (or none) - looked fine with only 3 models (one preloaded
        # in initialize_gl, the rest never switched-to fast enough to
        # expose it) but broke with real GLError(1282) on
        # glBindVertexArray once more on-demand loads made the timing-
        # dependent luck run out. make_current()/done_current() make this
        # correct regardless of call timing or which real owner this is.
        self._make_current()
        try:
            self._mesh_buffers_by_dir[mesh_dir] = {name: GLMeshBuffer(meshes[name]) for name in link_names}
        finally:
            self._done_current()

    # --- GL lifecycle (called by the owner's own initializeGL/resizeGL/
    # paintGL, or by the offscreen owner's own equivalent explicit calls -
    # a real GL context is already current by the time any of these run,
    # guaranteed by the owner) -------------------------------------------

    def initialize_gl(self) -> None:
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)  # white 3D viewport background, per explicit request

        self._program = self._compile_program(VERTEX_SHADER, FRAGMENT_SHADER)
        self._uniforms = {
            name: gl.glGetUniformLocation(self._program, name)
            for name in ("uModel", "uView", "uProjection", "uNormalMatrix", "uBaseColor", "uCameraPos")
        }

        self._generic_buffers = [
            GLMeshBuffer(make_cylinder_mesh(*seg.size) if seg.kind == "cylinder" else make_box_mesh(*seg.size))
            for seg in SEGMENTS
        ]

        self._gl_ready = True
        if self._pending_module_rebuild:
            self._module_buffers = [
                GLMeshBuffer(make_cylinder_mesh(*seg.size) if seg.kind == "cylinder" else make_box_mesh(*seg.size))
                for seg in self._module_segments_cache
            ]
            self._pending_module_rebuild = False
        if self._pending_pnp_mesh_load:
            self._load_mesh_set(PNP_MESH_DIR, PNP_LINK_NAMES, PNP_MESH_FILES)
            self._pending_pnp_mesh_load = False
        entry = ROBOT_REGISTRY[self._model_name]
        if entry.family in ("ur", "quat"):
            self._load_mesh_set(entry.mesh_dir, entry.link_names, entry.mesh_files)

    def resize_gl(self, w: int, h: int) -> None:
        self._width, self._height = max(1, w), max(1, h)
        gl.glViewport(0, 0, self._width, self._height)

    def paint_gl(self) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self._program is None:
            return

        gl.glUseProgram(self._program)

        eye = self._camera_eye()
        view = look_at(eye, self._target, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        aspect = max(self._width, 1) / max(self._height, 1)
        proj = perspective(45.0, aspect, 0.01, 50.0)

        gl.glUniformMatrix4fv(self._uniforms["uView"], 1, gl.GL_TRUE, view)
        gl.glUniformMatrix4fv(self._uniforms["uProjection"], 1, gl.GL_TRUE, proj)
        gl.glUniform3f(self._uniforms["uCameraPos"], *eye)

        if self._pnp_machine_type is not None:
            self._draw_pnp()
            return

        if self._attached_module_type is not None:
            self._draw_module_preview()
            return

        entry = ROBOT_REGISTRY.get(self._model_name)
        if entry is None:
            return

        if entry.family == "generic":
            self._draw_generic()
            return

        buffers = self._mesh_buffers_by_dir.get(entry.mesh_dir)
        if not buffers:
            return  # not loaded yet (only happens for a brand-new model right at startup, before initialize_gl's own preload runs)

        gl.glUniform3f(self._uniforms["uBaseColor"], 0.72, 0.75, 0.80)

        if entry.family == "ur":
            transforms = ur_mesh_world_transforms(entry.chain, entry.mesh_offsets, self._joints_deg)
        else:  # "quat"
            cfg = entry.quat_config
            transforms = quat_family_mesh_world_transforms(cfg.chain, cfg.mesh_offsets, cfg.root_axis_target, cfg.base_offset, self._joints_deg)

        for name, model in zip(entry.link_names, transforms):
            self._draw_model(model, buffers[name])

    def _draw_module_preview(self) -> None:
        for seg, buf in zip(self._module_segments_cache, self._module_buffers):
            model = module_segment_world_transform(seg)
            gl.glUniform3f(self._uniforms["uBaseColor"], *seg.color)
            self._draw_model(model, buf)

    def _draw_pnp(self) -> None:
        buffers = self._mesh_buffers_by_dir.get(PNP_MESH_DIR)
        if not buffers:
            return  # not loaded yet - only happens for a fraction of a frame right after set_attached_pnp()'s own initial call
        transforms = pnp_world_link_transforms(*self._pnp_pose)
        for name in PNP_LINK_NAMES:
            gl.glUniform3f(self._uniforms["uBaseColor"], *_PNP_LINK_COLORS[name])
            self._draw_model(transforms[name], buffers[name])

    def _draw_generic(self) -> None:
        frames = generic_frame_transforms(self._joints_deg)
        for seg, buf in zip(SEGMENTS, self._generic_buffers):
            model = segment_world_transform(frames, seg)
            gl.glUniform3f(self._uniforms["uBaseColor"], *seg.color)
            self._draw_model(model, buf)

    def _draw_model(self, model: np.ndarray, buf: GLMeshBuffer) -> None:
        model32 = model.astype(np.float32)
        normal_matrix = np.linalg.inv(model32[:3, :3]).T.astype(np.float32)
        gl.glUniformMatrix4fv(self._uniforms["uModel"], 1, gl.GL_TRUE, model32)
        gl.glUniformMatrix3fv(self._uniforms["uNormalMatrix"], 1, gl.GL_TRUE, normal_matrix)
        buf.draw()

    # --- camera ---------------------------------------------------------------

    def _camera_eye(self) -> np.ndarray:
        yaw = np.radians(self._yaw)
        pitch = np.radians(self._pitch)
        x = self._distance * np.cos(pitch) * np.cos(yaw)
        z = self._distance * np.cos(pitch) * np.sin(yaw)
        y = self._distance * np.sin(pitch)
        return self._target + np.array([x, y, z], dtype=np.float32)

    # --- shader compilation -----------------------------------------------

    @staticmethod
    def _compile_shader(source: str, shader_type: int) -> int:
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
            log = gl.glGetShaderInfoLog(shader).decode()
            raise RuntimeError(f"Shader compile error:\n{log}")
        return shader

    @classmethod
    def _compile_program(cls, vertex_src: str, fragment_src: str) -> int:
        vs = cls._compile_shader(vertex_src, gl.GL_VERTEX_SHADER)
        fs = cls._compile_shader(fragment_src, gl.GL_FRAGMENT_SHADER)
        program = gl.glCreateProgram()
        gl.glAttachShader(program, vs)
        gl.glAttachShader(program, fs)
        gl.glLinkProgram(program)
        if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
            log = gl.glGetProgramInfoLog(program).decode()
            raise RuntimeError(f"Shader link error:\n{log}")
        gl.glDeleteShader(vs)
        gl.glDeleteShader(fs)
        return program


class RobotViewport(QOpenGLWidget):
    """Orbit camera (left-drag rotate, wheel zoom, right/middle-drag pan)
    over a live-posed robot - any of the 24 real STL-backed models
    (ROBOT_REGISTRY in kinematics.py) plus a primitive-built "Generic"
    fallback (generic_rig.py), switched at runtime via set_robot_model().
    A thin QOpenGLWidget wrapper around one real RobotGLRenderer - see
    this module's own header for why the GL logic itself lives there now,
    not here."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._renderer = RobotGLRenderer(self.makeCurrent, self.doneCurrent)
        self._last_mouse_pos: QPointF | None = None
        self._drag_button: Qt.MouseButton | None = None

    def set_joints_deg(self, joints: dict[str, float]) -> None:
        if self._renderer.set_joints_deg(joints):
            self.update()

    def set_robot_model(self, model_name: str) -> None:
        if self._renderer.set_robot_model(model_name):
            self.update()

    def set_attached_module(self, module_type: str | None, width_mm: float = 500.0, length_mm: float = 500.0) -> None:
        self._renderer.set_attached_module(module_type, width_mm, length_mm)
        self.update()

    def set_attached_pnp(
        self,
        machine_type: str | None,
        axis_x_mm: float = 0.0,
        axis_y_mm: float = 0.0,
        axis_z_mm: float = 0.0,
        nozzle1_deg: float = 0.0,
        nozzle2_deg: float = 0.0,
    ) -> None:
        self._renderer.set_attached_pnp(machine_type, axis_x_mm, axis_y_mm, axis_z_mm, nozzle1_deg, nozzle2_deg)
        self.update()

    # --- Qt/OpenGL lifecycle -------------------------------------------------

    def initializeGL(self) -> None:
        self._renderer.initialize_gl()

    def resizeGL(self, w: int, h: int) -> None:
        self._renderer.resize_gl(w, h)

    def paintGL(self) -> None:
        self._renderer.paint_gl()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = event.position()
        self._drag_button = event.button()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = None
        self._drag_button = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_mouse_pos is None:
            return
        delta = event.position() - self._last_mouse_pos
        self._last_mouse_pos = event.position()
        if self._drag_button == Qt.MouseButton.LeftButton:
            self._renderer.orbit(delta.x(), delta.y())
            self.update()
        elif self._drag_button in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._renderer.pan(delta.x(), delta.y())
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 0.9 if event.angleDelta().y() > 0 else 1.1
        self._renderer.zoom(factor)
        self.update()


class OffscreenRobotRenderer:
    """The Qt Quick shell's own real render path for the 3D Viewport
    panel - a genuinely separate QOpenGLContext/QOffscreenSurface/
    QOpenGLFramebufferObject, entirely independent of Qt Quick's own
    scenegraph (which defaults to Direct3D11 on Windows, not OpenGL).
    Reuses RobotGLRenderer's exact real rendering code rather than a
    second, drifting copy - see this module's own header. Deliberately
    NOT Qt Quick's own QQuickFramebufferObject: that API requires the
    whole app's Quick backend forced onto OpenGL (QQuickWindow's own
    graphics API is a real, global, one-shot choice made before any
    window exists) just to support this one panel, and needs real
    same-API GPU resource sharing with Quick's own render thread. This
    class trades a same-thread glReadPixels() round trip (real, but
    cheap for a robot preview - not a 60fps game) for zero backend/
    threading risk to the rest of this app: every render() call happens
    synchronously on the calling (GUI/asyncio) thread, right after a
    real state mutation, with no window ever created for this context -
    the result is a plain QImage the caller hands to QML through the
    same real QQuickImageProvider pattern CameraFrameProvider already
    uses for live camera frames."""

    def __init__(self) -> None:
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)

        self._surface = QOffscreenSurface()
        self._surface.setFormat(fmt)
        self._surface.create()
        if not self._surface.isValid():
            raise RuntimeError("Failed to create an offscreen surface for the 3D Viewport panel")

        self._context = QOpenGLContext()
        self._context.setFormat(fmt)
        if not self._context.create():
            raise RuntimeError("Failed to create an offscreen OpenGL context for the 3D Viewport panel")

        self._fbo: QOpenGLFramebufferObject | None = None
        self._width = 640
        self._height = 480
        # Real, reproducible bug found here (not a theory): initialize_gl()
        # for the real default model (UR5e, "ur" family) triggers its own
        # nested make_current()/done_current() cycle via _load_mesh_set()
        # (RobotGLRenderer's real, pre-existing lazy-mesh-load path, also
        # used correctly by the QOpenGLWidget side). Against THIS class's
        # own standalone QOpenGLContext/QOffscreenSurface pair specifically
        # (not the widget's own Qt-managed context), letting that inner
        # doneCurrent() actually run and then re-running makeCurrent() a
        # moment later left the context in a state where the very next
        # QOpenGLFramebufferObject construction segfaults - confirmed by
        # bisecting a real, minimal repro script line by line, not a
        # guess. A simple reentrancy counter - only the OUTERMOST
        # make_current()/done_current() pair here ever touches the real
        # context - fixes it for real.
        self._current_depth = 0

        self._renderer = RobotGLRenderer(self._make_current, self._done_current)
        self._make_current()
        try:
            self._renderer.initialize_gl()
            self._ensure_fbo()
        finally:
            self._done_current()

    def _make_current(self) -> None:
        if self._current_depth == 0:
            self._context.makeCurrent(self._surface)
        self._current_depth += 1

    def _done_current(self) -> None:
        self._current_depth -= 1
        if self._current_depth == 0:
            self._context.doneCurrent()

    def _ensure_fbo(self) -> None:
        if self._fbo is not None and self._fbo.size().width() == self._width and self._fbo.size().height() == self._height:
            return
        fbo_format = QOpenGLFramebufferObjectFormat()
        fbo_format.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        self._fbo = QOpenGLFramebufferObject(self._width, self._height, fbo_format)
        self._renderer.resize_gl(self._width, self._height)

    def resize(self, width: int, height: int) -> None:
        width, height = max(1, int(width)), max(1, int(height))
        if width == self._width and height == self._height:
            return
        self._width, self._height = width, height
        self._make_current()
        try:
            self._ensure_fbo()
        finally:
            self._done_current()

    def render(self) -> QImage:
        """Real, synchronous render - bind the FBO, run the exact same
        paint_gl() the widget path uses, read the real pixels back."""
        self._make_current()
        try:
            self._ensure_fbo()
            self._fbo.bind()
            self._renderer.paint_gl()
            self._fbo.release()
            return self._fbo.toImage()
        finally:
            self._done_current()

    # -- forwarded setters (mirrors RobotViewport's own real public API -
    # the caller (qt_suite.py's own bridge) always calls render() again
    # right after one of these, so there's no "did this actually change"
    # decision to make here the way the widget path's own update()
    # scheduling needs) -----------------------------------------------

    def set_joints_deg(self, joints: dict[str, float]) -> None:
        self._renderer.set_joints_deg(joints)

    def set_robot_model(self, model_name: str) -> None:
        self._renderer.set_robot_model(model_name)

    def orbit(self, dx: float, dy: float) -> None:
        self._renderer.orbit(dx, dy)

    def pan(self, dx: float, dy: float) -> None:
        self._renderer.pan(dx, dy)

    def zoom(self, factor: float) -> None:
        self._renderer.zoom(factor)
