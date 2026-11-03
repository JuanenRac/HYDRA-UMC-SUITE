# Bench tests

Every test below is **not executed**. The windows, the build scripts and the tester are covered by tests that read the files or use a fake transport; the packaged program has not been built and run, and no test has talked to a real board or a game controller. Write a result only after a person ran the step.

## What the software already covers (no hardware needed)

- `tests/verify_build_scripts.py` reads the packaging scripts (it does not run them) and checks that the images folder and the icon are included.
- The unit tests cover the tester with a fake transport.

## Setup

- A Windows PC with the build tools, a Robot Controller or URTC head board on a CAN adapter on a bench supply with its actuators disconnected, and a USB game controller.

## Steps

| # | Step | Expected result | Result |
|---|------|-----------------|--------|
| 1 | Build the program with the packaging script and start it from an empty folder. | It starts, shows its images and the icon in the title bar and the task bar, and every QML plugin loads. Record any missing plugin. | not executed |
| 2 | Run the tester's self-test against the real board. | Every line of the self-test passes or names the line that failed. | not executed |
| 3 | Run the F-RAM erase of the tester. | The memory reads back cleared; with the board off, the tool reports no transport instead of success. | not executed |
| 4 | Plug the game controller, assign the axes and jog a simulated robot, then a real one at the lowest speed. | The axes follow the stick, a released stick stops the motion and unplugging stops it as well. | not executed |
| 5 | Unplug the adapter during each of the steps above. | The tool reports the loss and does not leave a command pending. | not executed |

## What this bench cannot show

Different controllers (dead zones, button layouts) and different Windows versions; list the ones used with every result.
