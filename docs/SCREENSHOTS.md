# Renewing the screenshots of the README

The pictures of the README (`images/screenshots/`, listed in `docs/screenshots.json`) can be taken again on a GitHub runner, so a new version does not need a run on your own computer.

1. Start the workflow **Screenshots (manual)** from the Actions tab, or from a terminal: `gh workflow run screenshots.yml --ref main` (any branch works: `--ref <branch>`). It only starts by hand; it never runs on a push or on a pull request, it has no secrets and the token is read-only.
2. It installs the dependencies and runs `tools/capture_screenshots.py`: the real Qt Quick interface on the offscreen Qt platform with the software renderer, against a made-up server connection with made-up robots. The screens that are only a 3D view are not in the set (the offscreen platform has no OpenGL).
3. When it ends, download the artifact **screenshots** (kept for 14 days): `gh run download <run id> --name screenshots`. The job summary lists every file and its size.
4. Look at the pictures and copy the ones you want into `images/screenshots/`. The workflow never changes the repository.

The runner draws with the fonts of Linux, so letter shapes can differ a little from the pictures taken on Windows with `python tools/capture_screenshots.py`.
