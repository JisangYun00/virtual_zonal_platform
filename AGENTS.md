# Working on this project

- Read README.md for the current contract, CONTRIBUTING.md for the team rules, docs/design.md for decided vs open items, docs/measurements.md for measured facts, and docs/progress.md for done and next work. Planned modules are not implemented features.
- Python 3.8 (the Jetson runs 3.8.10), standard library only except camera files. Run from this directory; no installation.
- State changes only through `core/state.py`. Messages are built and parsed only in `core/protocol.py`. `core/` does no I/O (pass time in as an argument). Device I/O goes in `zone_controller/` (Jetson) or `central/` (laptop), which never import each other.
- Commands set a target state (`SET_SIGNAL`, `SET_BRAKE`); only button handling may toggle.
- Each device starts with one command in `bringup/`. New processes or setup steps for a device go in its bringup script.
- Run `python3 -m unittest discover -s tests -v` before and after changes. It checks import boundaries and runs scenarios A-D through both bringup scripts with `--local` on 127.0.0.x.
- When a contract changes, update code, tests, README, and docs together. Do not edit an expected value just to silence a failure. Record measurements with their date and method in docs/measurements.md; label estimates.
- Code and comments in English; README and docs in Korean.
- Report the checks you actually ran. Passing tests do not authorize commits or pushes.
