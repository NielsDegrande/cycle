"""Cycle Application."""

import asyncio
import multiprocessing
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Self

import mss
from box import Box

from cycle.recording_transcription import transcribe_recording
from cycle.screen_recording import record_screen
from cycle.utils.strings import change_video_to_text_extension, split_on_separator
from cycle.workflow_automation import automate_workflow


class CycleApp:
    """Cycle Application."""

    def __init__(self: Self, config: Box) -> None:
        """Initialize the CycleApp class."""
        self.config = config
        self.root = tk.Tk()
        self.recording = False
        self.recording_event = multiprocessing.Event()
        self.recordings_directory = Path(self.config.directories.recordings)
        self.recordings_directory.mkdir(exist_ok=True)
        self.transcripts_directory = Path(self.config.directories.transcripts)
        self.transcripts_directory.mkdir(exist_ok=True)

        self._create_gui()
        self._run()

    def _create_gui(self: Self) -> None:
        """Create the GUI."""
        self.root.title("Cycle")
        self.root.geometry("1000x500")

        # Center the window on the screen.
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.style = ttk.Style()
        self.style.configure("Record.TButton", foreground="red")

        # Create a frame to hold the recording controls.
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=20)

        self.record_button = ttk.Button(
            controls_frame,
            text="Start Recording",
            command=self._toggle_recording,
            style="Record.TButton",
        )
        self.record_button.pack(side=tk.LEFT, padx=10)

        # Create a dropdown for monitor selection.
        self.monitor_var = tk.StringVar()
        self.monitor_dropdown = ttk.Combobox(
            controls_frame,
            textvariable=self.monitor_var,
            state="readonly",
        )
        self._populate_monitor_dropdown()
        self.monitor_dropdown.pack(side=tk.LEFT, padx=10)

        self.status_label = ttk.Label(controls_frame, text="Status: Ready")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.time_label = ttk.Label(controls_frame, text="Duration: 00:00")
        self.time_label.pack(side=tk.LEFT, padx=10)

        # Create a frame to hold the listbox and buttons.
        frame = tk.Frame(self.root)
        frame.pack(pady=10, fill=tk.BOTH, expand=True)

        # Add padding to the left of the recording list.
        listbox_frame = tk.Frame(frame)
        listbox_frame.pack(side=tk.LEFT, padx=20, fill=tk.BOTH, expand=True)

        self.recordings_listbox = tk.Listbox(master=listbox_frame, width=50)
        self.recordings_listbox.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        self._update_recordings_list()

        # Create a frame for the buttons.
        button_frame = tk.Frame(frame)
        button_frame.pack(side=tk.LEFT, padx=10)
        button_width = 20

        self.rename_button = ttk.Button(
            button_frame,
            text="Rename Selected",
            command=self._rename_selected,
            width=button_width,
        )
        self.rename_button.pack(pady=5, padx=(0, 20), anchor="w")

        self.delete_button = ttk.Button(
            button_frame,
            text="Delete Selected",
            command=self._delete_selected,
            width=button_width,
        )
        self.delete_button.pack(pady=5, padx=(0, 20), anchor="w")

        self.watch_button = ttk.Button(
            button_frame,
            text="Watch Selected",
            command=self._watch_selected,
            width=button_width,
        )
        self.watch_button.pack(pady=5, padx=(0, 20), anchor="w")

        self.display_transcript_button = ttk.Button(
            button_frame,
            text="Display Transcript",
            command=self._display_selected_transcript,
            width=button_width,
        )
        self.display_transcript_button.pack(pady=5, padx=(0, 20), anchor="w")

        self.transcribe_button = ttk.Button(
            button_frame,
            text="Transcribe Selected",
            command=self._transcribe_selected,
            width=button_width,
        )
        self.transcribe_button.pack(pady=5, padx=(0, 20), anchor="w")

        self.playback_button = ttk.Button(
            button_frame,
            text="Playback Workflow",
            command=self._playback_workflow,
            width=button_width,
        )
        self.playback_button.pack(pady=5, padx=(0, 20), anchor="w")

    def _populate_monitor_dropdown(self: Self) -> None:
        """Populate the monitor dropdown with available monitors."""
        monitors = mss.mss().monitors
        monitor_names = [
            f"Monitor {i}: {monitor['width']}x{monitor['height']}"
            for i, monitor in enumerate(monitors[1:], start=1)
        ]
        self.monitor_dropdown["values"] = monitor_names
        if monitor_names:
            self.monitor_var.set(monitor_names[0])

    def _run(self: Self) -> None:
        """Run the application."""
        self.root.mainloop()

    def _toggle_recording(self: Self) -> None:
        """Start or stop recording."""
        if not self.recording_event.is_set():
            self.start_time = time.time()
            self._start_recording()
            self._update_timer()
        else:
            self._stop_recording()

    def _start_recording(self: Self) -> None:
        """Start recording the screen."""
        self.recording_event.set()
        self.record_button.configure(text="Stop Recording")
        self.status_label.configure(text="Status: Recording...")

        # Get the selected monitor index from the dropdown.
        selected_monitor = self.monitor_var.get()
        # Monitor index is 1-indexed. 1 is the primary monitor.
        monitor_index = self.monitor_dropdown["values"].index(selected_monitor) + 1

        # Start recording in a separate thread.
        record_thread = threading.Thread(
            target=record_screen,
            args=(
                Path(self.config.directories.recordings),
                self.recording_event,
                monitor_index,
            ),
        )
        record_thread.start()

    def _stop_recording(self: Self) -> None:
        """Stop recording the screen."""
        self.recording_event.clear()
        self.record_button.configure(text="Start Recording")
        self.status_label.configure(text="Status: Ready")
        self.time_label.configure(text="Duration: 00:00")
        self._update_recordings_list()

    def _update_timer(self: Self) -> None:
        """Update the timer label."""
        if self.recording_event.is_set():
            elapsed_time = int(time.time() - self.start_time)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            self.time_label.configure(text=f"Duration: {minutes:02d}:{seconds:02d}")
            self.root.after(1000, self._update_timer)

    def _update_recordings_list(self: Self) -> None:
        """Update the listbox with the recordings."""
        self.recordings_listbox.delete(0, tk.END)
        for recording in sorted(self.recordings_directory.glob("*.mp4")):
            self.recordings_listbox.insert(tk.END, recording.name)

    def _transcribe_selected(self: Self) -> None:
        """Transcribe the selected recording."""
        selected_index = self.recordings_listbox.curselection()
        if not selected_index:
            return

        selected_recording = self.recordings_listbox.get(selected_index)
        recording_path = self.recordings_directory / selected_recording

        transcript = transcribe_recording(self.config, recording_path)
        self._save_transcript(transcript, recording_name=selected_recording)
        self._display_selected_transcript()

    def _save_transcript(self: Self, transcript: str, recording_name: str) -> None:
        """Save the transcript to a file.

        :param transcript: The transcript to save.
        :param recording_name: The name of the recording.
        """
        save_path = self.transcripts_directory / change_video_to_text_extension(
            recording_name,
        )
        with Path.open(save_path, "w") as file:
            file.write(transcript)

    def _display_selected_transcript(self: Self) -> None:
        """Display the selected transcript."""
        selected_index = self.recordings_listbox.curselection()
        if not selected_index:
            return

        selected_recording = self.recordings_listbox.get(first=selected_index)
        transcript_path = self.transcripts_directory / change_video_to_text_extension(
            selected_recording,
        )
        if not transcript_path.exists():
            messagebox.showerror(
                "Transcript Not Found",
                f"Transcript for {selected_recording} not found. "
                "Transcribe the recording first.",
            )
            return

        with Path.open(transcript_path, "r") as file:
            transcript = file.read()

        cleaned_transcript = "".join(
            split_on_separator(
                transcript,
                self.config.separator,
            ),
        )
        transcript_window = tk.Toplevel(master=self.root)
        transcript_window.title("Transcript")
        transcript_text = tk.Text(transcript_window, wrap=tk.WORD)
        transcript_text.insert(tk.END, cleaned_transcript)
        transcript_text.pack(expand=True, fill=tk.BOTH)

    def _rename_selected(self: Self) -> None:
        """Rename the selected recording."""
        selected_index = self.recordings_listbox.curselection()
        if not selected_index:
            return

        selected_recording = self.recordings_listbox.get(selected_index)
        recording_path = self.recordings_directory / selected_recording

        new_name = simpledialog.askstring("Rename Recording", "Enter new name:")
        if new_name:
            new_path = recording_path.with_name(new_name + recording_path.suffix)
            recording_path.rename(new_path)
            self._update_recordings_list()

    def _delete_selected(self: Self) -> None:
        """Delete the selected recording."""
        selected_index = self.recordings_listbox.curselection()
        if not selected_index:
            return

        selected_recording = self.recordings_listbox.get(selected_index)
        recording_path = self.recordings_directory / selected_recording

        if messagebox.askyesno(
            "Delete Recording",
            f"Are you sure you want to delete {selected_recording}?",
        ):
            recording_path.unlink()
            self._update_recordings_list()

    def _watch_selected(self: Self) -> None:
        """Watch the selected recording."""
        selected_index = self.recordings_listbox.curselection()
        if not selected_index:
            return

        selected_recording = self.recordings_listbox.get(selected_index)
        recording_path = self.recordings_directory / selected_recording

        webbrowser.open(recording_path.absolute().as_uri())

    def _spawn_workflow_thread(self: Self, transcript: str, instruction: str) -> None:
        """Run the automate workflow in a separate thread.

        :param transcript: The workflow transcript.
        :param instruction: The user-provided instruction.
        """
        asyncio.run(
            automate_workflow(
                config=self.config,
                transcript=transcript,
                instruction=instruction,
            ),
        )

    def _playback_workflow(self: Self) -> None:
        """Playback the workflow."""
        selected_index = self.recordings_listbox.curselection()
        if not selected_index:
            return

        selected_recording = self.recordings_listbox.get(first=selected_index)
        transcript_path = self.transcripts_directory / change_video_to_text_extension(
            selected_recording,
        )
        if not transcript_path.exists():
            messagebox.showerror(
                "Transcript Not Found",
                f"Transcript for {selected_recording} not found. "
                "Transcribe the recording first.",
            )
            return

        with Path.open(transcript_path, "r") as file:
            transcript = file.read()

        instruction = simpledialog.askstring("Instruction", "Enter the instruction:")
        if instruction:
            proceed = messagebox.askokcancel(
                "Start Workflow",
                f"Click OK to start the workflow with instruction '{instruction}'.",
            )
            if proceed:
                threading.Thread(
                    target=self._spawn_workflow_thread,
                    args=(transcript, instruction),
                ).start()
