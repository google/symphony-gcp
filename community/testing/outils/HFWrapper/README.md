# HostFactory Python Wrapper

This is (as of now) a simple python wrapper for the HostFactory API of IBM's Spectrum Symphony.

See the notebook `play.ipynb` for a simple example.

## Installation

Requires UV and the project python version installed.

- Create a venv with `uv venv`
- Activate the venv with `source .venv/bin/activate`
- Install the project with `uv sync --all-groups`


### Configure VSCode

If you want to use the VSCode notebook for development.

- Get the environment executable path by running `command -v python`. 
- Press `Ctrl+Shift+P` on VSCode and type `Python: Select Enterpreter`.
- Press enter and select `Enter interpreter path...`
- Paste the environment executable path and press enter.
- Go to the notebook, press select kernel and select the current selected environment jupyter kernel.
