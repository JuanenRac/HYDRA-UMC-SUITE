# =============================================================================
# HYDRA-UMC SUITE - render/viewport.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real-time 3D robot viewport - QOpenGLWidget + a small GLSL shader
# (core profile, not legacy immediate-mode glBegin/glEnd, since Qt's own
# default-created context on most drivers is a core-profile one that
# doesn't support the legacy path at all). Renders the real STL meshes
# (render/mesh.py) for all 9 real robot models plus a primitive-built
# "Generic" fallback (render/generic_rig.py), posed every frame from the
# real forward kinematics (render/kinematics.py) driven by live joint
# angles from a connected HydraConnection's own RobotView - not a
# stylized placeholder, the same "real geometry, real chain" standard
# HYDRA-UMC-STUDIO's own *Arm.tsx components already hold themselves to.
#
# Y-up world (matches Three.js/HYDRA-UMC-STUDIO, see kinematics.py's own
# header) - the camera's own up vector and pan axes below are Y-up too.
# =============================================================================
from __future__ import annotations

from pathlib import Path

import numpy as np
from OpenGL import GL as gl
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from hydra_suite.render.generic_rig import SEGMENTS, generic_frame_transforms, segment_world_transform
from hydra_suite.render.kinematics import ROBOT_REGISTRY, quat_family_link_transforms, ur_mesh_world_transforms
from hydra_suite.render.mesh import Mesh, load_link_set, make_box_mesh, make_cylinder_mesh

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "meshes"

DEFAULT_MODEL = "UR5e (6-DOF)"

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


class RobotViewport(QOpenGLWidget):
    """Orbit camera (left-drag rotate, wheel zoom, right/middle-drag pan)
    over a live-posed robot - any of the 9 real STL-backed models
    (ROBOT_REGISTRY in kinematics.py) plus a primitive-built "Generic"
    fallback (generic_rig.py), switched at runtime via set_robot_model()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._program: int | None = None
        self._gl_ready = False

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

        self._yaw = -35.0
        self._pitch = 20.0
        self._distance = 2.2
        self._target = np.array([0.0, 0.4, 0.0], dtype=np.float32)
        self._last_mouse_pos: QPointF | None = None
        self._drag_button: Qt.MouseButton | None = None

    def set_joints_deg(self, joints: dict[str, float]) -> None:
        self._joints_deg = dict(joints)
        self.update()

    def set_robot_model(self, model_name: str) -> None:
        """Switches which robot is rendered - loads that model's own STL
        set on first use (a no-op for models already cached, and for
        "Generic", which has no STL to load at all)."""
        if model_name not in ROBOT_REGISTRY:
            return
        self._model_name = model_name
        entry = ROBOT_REGISTRY[model_name]
        self._joints_deg = dict(entry.home_pose_deg)
        if self._gl_ready and entry.family in ("ur", "quat") and entry.mesh_dir not in self._mesh_buffers_by_dir:
            self._load_mesh_set(entry.mesh_dir, entry.link_names, entry.mesh_files)
        self.update()

    def _load_mesh_set(self, mesh_dir: str, link_names: tuple[str, ...], mesh_files: dict[str, str]) -> None:
        meshes = load_link_set(ASSETS_DIR / mesh_dir, mesh_files)
        # set_robot_model() (this method's only non-initializeGL caller)
        # runs from a plain Qt slot - Qt only guarantees THIS widget's own
        # GL context is current inside initializeGL/paintGL/resizeGL, not
        # here, so glGenVertexArrays/glGenBuffers below could otherwise
        # execute against whatever context happened to be bound at that
        # moment (or none) - looked fine with only 3 models (one preloaded
        # in initializeGL, the rest never switched-to fast enough to
        # expose it) but broke with real GLError(1282) on
        # glBindVertexArray once more on-demand loads made the timing-
        # dependent luck run out. makeCurrent()/doneCurrent() make this
        # correct regardless of call timing.
        self.makeCurrent()
        try:
            self._mesh_buffers_by_dir[mesh_dir] = {name: GLMeshBuffer(meshes[name]) for name in link_names}
        finally:
            self.doneCurrent()

    # --- Qt/OpenGL lifecycle -------------------------------------------------

    def initializeGL(self) -> None:
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)  # white 3D viewport background, per explicit request

        self._program = self._compile_program(VERTEX_SHADER, FRAGMENT_SHADER)

        self._generic_buffers = [
            GLMeshBuffer(make_cylinder_mesh(*seg.size) if seg.kind == "cylinder" else make_box_mesh(*seg.size))
            for seg in SEGMENTS
        ]

        self._gl_ready = True
        entry = ROBOT_REGISTRY[self._model_name]
        if entry.family in ("ur", "quat"):
            self._load_mesh_set(entry.mesh_dir, entry.link_names, entry.mesh_files)

    def resizeGL(self, w: int, h: int) -> None:
        gl.glViewport(0, 0, max(1, w), max(1, h))

    def paintGL(self) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self._program is None:
            return

        gl.glUseProgram(self._program)

        eye = self._camera_eye()
        view = look_at(eye, self._target, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        aspect = max(self.width(), 1) / max(self.height(), 1)
        proj = perspective(45.0, aspect, 0.01, 50.0)

        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self._program, "uView"), 1, gl.GL_TRUE, view)
        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self._program, "uProjection"), 1, gl.GL_TRUE, proj)
        gl.glUniform3f(gl.glGetUniformLocation(self._program, "uCameraPos"), *eye)

        entry = ROBOT_REGISTRY.get(self._model_name)
        if entry is None:
            return

        if entry.family == "generic":
            self._draw_generic()
            return

        buffers = self._mesh_buffers_by_dir.get(entry.mesh_dir)
        if not buffers:
            return  # not loaded yet (only happens for a brand-new model right at startup, before initializeGL's own preload runs)

        gl.glUniform3f(gl.glGetUniformLocation(self._program, "uBaseColor"), 0.72, 0.75, 0.80)

        if entry.family == "ur":
            transforms = ur_mesh_world_transforms(entry.chain, entry.mesh_offsets, self._joints_deg)
        else:  # "quat"
            cfg = entry.quat_config
            transforms = quat_family_link_transforms(cfg.chain, cfg.root_axis_target, cfg.base_offset, self._joints_deg)

        for name, model in zip(entry.link_names, transforms):
            self._draw_model(model, buffers[name])

    def _draw_generic(self) -> None:
        frames = generic_frame_transforms(self._joints_deg)
        for seg, buf in zip(SEGMENTS, self._generic_buffers):
            model = segment_world_transform(frames, seg)
            gl.glUniform3f(gl.glGetUniformLocation(self._program, "uBaseColor"), *seg.color)
            self._draw_model(model, buf)

    def _draw_model(self, model: np.ndarray, buf: GLMeshBuffer) -> None:
        model32 = model.astype(np.float32)
        normal_matrix = np.linalg.inv(model32[:3, :3]).T.astype(np.float32)
        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self._program, "uModel"), 1, gl.GL_TRUE, model32)
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self._program, "uNormalMatrix"), 1, gl.GL_TRUE, normal_matrix)
        buf.draw()

    # --- camera ---------------------------------------------------------------

    def _camera_eye(self) -> np.ndarray:
        yaw = np.radians(self._yaw)
        pitch = np.radians(self._pitch)
        x = self._distance * np.cos(pitch) * np.cos(yaw)
        z = self._distance * np.cos(pitch) * np.sin(yaw)
        y = self._distance * np.sin(pitch)
        return self._target + np.array([x, y, z], dtype=np.float32)

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
            self._yaw -= delta.x() * 0.4
            self._pitch = float(np.clip(self._pitch + delta.y() * 0.4, -85.0, 85.0))
            self.update()
        elif self._drag_button in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            yaw = np.radians(self._yaw)
            right = np.array([-np.sin(yaw), 0.0, np.cos(yaw)], dtype=np.float32)
            up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
            pan_scale = self._distance * 0.0015
            self._target -= right * delta.x() * pan_scale
            self._target += up * delta.y() * pan_scale
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 0.9 if event.angleDelta().y() > 0 else 1.1
        self._distance = float(np.clip(self._distance * factor, 0.3, 15.0))
        self.update()

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
