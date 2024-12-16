"""Record the screen."""

import threading
import time
import tkinter as tk
from datetime import UTC, datetime
from tkinter import ttk
from typing import Self

import cv2
import numpy as np
from PIL import ImageGrab


class ScreenRecorder:
    """Screen Recorder."""

    def __init__(self: Self, root: tk.Tk) -> None:
        """Initialize the ScreenRecorder class."""
        self.root = root
        self.root.title("Screen Recorder")
        self.root.geometry("300x150")

        self.recording = False
        self.output_filename: str

        # Create GUI elements.
        self.style = ttk.Style()
        self.style.configure("Record.TButton", foreground="red")

        self.record_button = ttk.Button(
            root,
            text="Start Recording",
            command=self._toggle_recording,
            style="Record.TButton",
        )
        self.record_button.pack(pady=20)

        self.status_label = ttk.Label(root, text="Status: Ready")
        self.status_label.pack(pady=10)

        self.time_label = ttk.Label(root, text="Duration: 00:00")
        self.time_label.pack(pady=10)

    def _toggle_recording(self: Self) -> None:
        """Start or stop recording."""
        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self: Self) -> None:
        """Start recording the screen."""
        self.recording = True
        self.record_button.configure(text="Stop Recording")
        self.status_label.configure(text="Status: Recording...")

        # Generate output filename with timestamp.
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        self.output_filename = f"screen_recording_{timestamp}.avi"

        # Start recording in a separate thread.
        self.record_thread = threading.Thread(target=self._record_screen)
        self.record_thread.start()

        # Start timer update
        self.start_time = time.time()
        self._update_timer()

    def _stop_recording(self: Self) -> None:
        """Stop recording the screen."""
        self.recording = False
        self.record_button.configure(text="Start Recording")
        self.status_label.configure(text="Status: Ready")
        self.time_label.configure(text="Duration: 00:00")

    def _update_timer(self: Self) -> None:
        """Update the timer label."""
        if self.recording:
            elapsed_time = int(time.time() - self.start_time)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            self.time_label.configure(text=f"Duration: {minutes:02d}:{seconds:02d}")
            self.root.after(1000, self._update_timer)

    def _record_screen(self: Self) -> None:
        """Record the screen."""
        screen_size = ImageGrab.grab().size
        fourcc = cv2.VideoWriter.fourcc(*"MJPG")
        out = cv2.VideoWriter(self.output_filename, fourcc, 20.0, screen_size)

        while self.recording:
            # Capture the screen.
            screen = np.array(ImageGrab.grab())
            # Convert from RGB to BGR (OpenCV uses BGR).
            frame = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
            # Write frame.
            out.write(frame)

        out.release()
