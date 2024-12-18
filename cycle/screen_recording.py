"""Record the screen."""

import logging
import time
from datetime import datetime
from multiprocessing import Process, Queue
from multiprocessing.synchronize import Event
from pathlib import Path

import cv2
import mss
import numpy as np

from cycle.utils.constants import FRAMES_PER_SECOND

log_ = logging.getLogger(__name__)


def capture_screen(
    queue: Queue,
    recording: Event,
    monitor_index: int,
) -> None:
    """Capture the screen and place frames in a queue.

    :param queue: Queue to store frames.
    :param recording: Event to control recording.
    :param monitor_index: Index of the monitor to capture.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        while recording.is_set():
            start_time = time.time()
            frame = np.array(sct.grab(monitor))
            queue.put(frame)
            elapsed_time = time.time() - start_time
            time.sleep(max(1 / FRAMES_PER_SECOND - elapsed_time, 0))


def encode_video(
    queue: Queue,
    output_directory: Path,
    recording: Event,
) -> None:
    """Write frames from the queue to the video file.

    :param queue: Queue to retrieve frames.
    :param output_directory: Directory to save the recording.
    :param recording: Event to control recording.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005
    output_filename = output_directory / f"screen_recording_{timestamp}.mp4"

    # Get the first frame to determine video dimensions.
    first_frame = queue.get()
    frame_height, frame_width = first_frame.shape[:2]

    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    out = cv2.VideoWriter(
        output_filename.as_posix(),
        fourcc,
        FRAMES_PER_SECOND,
        (frame_width, frame_height),
    )

    while recording.is_set():
        frame = queue.get()
        # Convert from BGRA to BGR (OpenCV uses BGR).
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        out.write(frame)

    out.release()


def record_screen(
    output_directory: Path,
    recording: Event,
    monitor_index: int,
) -> None:
    """Record the screen.

    :param output_directory: Directory to save the recording.
    :param recording: Event to control recording.
    :param monitor_index: Index of the monitor to record.
    """
    queue = Queue()

    capture_process = Process(
        target=capture_screen,
        args=(queue, recording, monitor_index),
    )
    encode_process = Process(
        target=encode_video,
        args=(queue, output_directory, recording),
    )

    capture_process.start()
    encode_process.start()

    capture_process.join()
    encode_process.join()
