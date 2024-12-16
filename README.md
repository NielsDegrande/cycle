# Cycle

Recycle your workflows.

![cycle logo](assets/cycle-logo.png)

<!-- TODO: Add badges. -->

## How

Improve RPA with a GenAI touch:

1. Record a workflow with macOS Screen Recording.
1. Process the video to generate instructions.
1. Use computer use to playback the recording,
   combined with a custom instruction.

## Getting Started

Set up the right Python version with Tkinter:

```shell
brew install python-tk
export PATH="$PATH:/usr/local/opt/tcl-tk/bin"
export LDFLAGS="-L/usr/local/opt/tcl-tk/lib"
export CPPFLAGS="-I/usr/local/opt/tcl-tk/include"
export PKG_CONFIG_PATH="/usr/local/opt/tcl-tk/lib/pkgconfig"
export TCLTK_LIBS="-L/opt/homebrew/opt/tcl-tk/lib -ltcl9.0.0_1 -ltk9.0.0_1"
export TCLTK_CFLAGS="-I/opt/homebrew/opt/tcl-tk/include"
pyenv install 3.12
```

Set up a virtual environment:

```shell
python3 -m venv venv
source venv/bin/activate
make install_dev
```

## Roadmap

- [ ] Integrate with MCP and Agent Protocols.
- [ ] Make foundation model independent.
