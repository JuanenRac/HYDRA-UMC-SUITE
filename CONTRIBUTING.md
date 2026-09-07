# Contributing to HYDRA-UMC-SUITE 🧰

## Technology Stack
- **Language**: Python 3.12+.
- **Framework**: PySide6 (Qt6).
- **3D**: PyOpenGL.

## Guidelines
1. **Qt Threading**: Never perform network I/O on the main GUI thread. Use `qasync` or `QThread`.
2. **Styling**: Use the provided `industrial_dark.qss` for new widgets.
3. **Kinematics**: New robot models must be verified against the STUDIO implementation.
