# DStat GUI dev 2.0

Python 3 / Qt6 desktop edition of the DStat interface. It reuses the newer
serial protocol and experiment code while restoring the original window
organization: instrument settings and experiment controls at left, autosave
and data notebook at right, and serial connection controls along the bottom.

## Run from source

Requires Windows and Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m dstat_interface.main
```

## Build the Windows executable

From a Windows Command Prompt, run:

```bat
build_exe.bat
```

The script automatically prefers the workspace virtual environment at
`..\.venv\Scripts\python.exe`, then a local `.venv`, and finally `python` on
`PATH`. To select another interpreter, set `PYTHON_EXE` before running the
script, for example:

```bat
set PYTHON_EXE=C:\path\to\python.exe
build_exe.bat
```

The script installs the Python dependencies and PyInstaller, then creates an
onedir application at `dist\DStat-GUI-dev2\`. Run
`DStat-GUI-dev2.exe` from that folder; keep its `_internal` directory beside
the executable. The executable does not require Python to be installed on the
target computer.

Runtime logs and native crash traces are written to
`%LOCALAPPDATA%\DStat GUI 2.0\logs\` (`dstat-gui.log` and `crash.log`).

## Protocol terminal

The right-hand pane shows the serial conversation with the DStat while it
happens, which is useful for reviewing the command protocol:

| Colour | Symbol | Meaning |
| --- | --- | --- |
| blue | `→` | line sent by the GUI (`!n`, the command itself, parameters, `a` to stop) |
| green | `←` | line received from the DStat (`@ACK`, `@RCV`, `@DONE`, results) |
| grey | `·` | firmware comments (`#...` lines) and progress notes |
| amber | `!` | unexpected reply; the command was retried |
| red | `×` | command that could not be delivered |

Trailing spaces are rendered as `·` because the firmware counts them with
`strlen()` and they are part of the length prefix. Binary sample frames are
not logged (they would flood the pane); every 200 frames a summary note is
added instead. The pane can be hidden or restored with **View → Protocol
Terminal** (`Ctrl+P`), and its contents can be saved to a text file with
**Save…**.

## Using the instrument

Connect the DStat, click **Refresh**, select its COM port, and click
**Connect**. The port selection is shown in the full-width communication bar
at the bottom of the window. Confirm the detected firmware/board in the status
bar before running an experiment.

## Included techniques

The Python 3 engine currently provides cyclic voltammetry, linear sweep
voltammetry, square-wave voltammetry, differential pulse voltammetry,
chronoamperometry, and potentiometry. The original Python 2/GTK application
also listed AC voltammetry, photodiode, and offset calibration; those modes
are not implemented in the reused Python 3 engine and are not exposed here.

## Tests

```powershell
python -m unittest discover -s tests -v
```
