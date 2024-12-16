"""Package entry point."""

import logging
import tkinter as tk

from dotenv import load_dotenv

from cycle.screen_recorder import ScreenRecorder


def main() -> None:
    """Run a pipeline."""
    log_ = logging.getLogger(__name__)

    log_.info("Load configuration.")
    load_dotenv()

    root = tk.Tk()
    ScreenRecorder(root)
    root.mainloop()


if __name__ == "__main__":
    main()
