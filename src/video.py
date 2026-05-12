import os
import subprocess
import tempfile
from stegano import lsb


def _run_ffmpeg(args, error_msg):
    """Run an ffmpeg command, raising RuntimeError on failure."""
    result = subprocess.run(
        ['ffmpeg'] + args,
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"{error_msg}: {result.stderr.decode(errors='replace')}")


def _get_video_fps(video_path):
    """Return the frame-rate of the video as a string (e.g. '30000/1001')."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=r_frame_rate',
         '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
        capture_output=True, text=True
    )
    fps = result.stdout.strip()
    return fps if fps else '30'


def hide_in_video(video_path, message, output_path):
    """
    Hide *message* in the first frame of *video_path* and write the
    result to *output_path*.

    All frames are extracted as lossless PNGs, LSB steganography is
    applied to the first frame, then the video is reconstructed using
    lossless H.264 RGB (libx264rgb, CRF 0).  Because libx264rgb stores
    data in native RGB without a YUV conversion, the pixel values – and
    therefore the hidden LSB data – are preserved exactly.
    """
    fps = _get_video_fps(video_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        frames_dir = os.path.join(tmpdir, 'frames')
        os.makedirs(frames_dir)
        frame_pattern = os.path.join(frames_dir, 'frame_%05d.png')

        # 1. Extract all frames as lossless PNGs
        _run_ffmpeg(
            ['-i', video_path, '-vsync', '0', frame_pattern, '-y'],
            'Failed to extract video frames'
        )

        # 2. Apply LSB steganography to the first frame in-place
        frames = sorted(os.listdir(frames_dir))
        if not frames:
            raise RuntimeError('No frames could be extracted from the video')
        first_frame_path = os.path.join(frames_dir, frames[0])
        encoded_image = lsb.hide(first_frame_path, message)
        encoded_image.save(first_frame_path)

        # 3. Reconstruct the video from the modified frame sequence.
        #    libx264rgb with CRF 0 gives truly lossless H.264 in RGB,
        #    so every pixel survives the round-trip unchanged.
        #    The audio stream (if any) is copied without re-encoding.
        _run_ffmpeg(
            ['-framerate', fps,
             '-i', frame_pattern,
             '-i', video_path,
             '-map', '0:v', '-map', '1:a?',
             '-c:v', 'libx264rgb', '-crf', '0', '-preset', 'ultrafast',
             '-c:a', 'copy', '-y', output_path],
            'Failed to reconstruct video'
        )


def reveal_from_video(video_path):
    """
    Extract the hidden message from the first frame of *video_path*.

    Returns the hidden string, or *None* if nothing was found.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        frame_path = os.path.join(tmpdir, 'frame0.png')

        _run_ffmpeg(
            ['-i', video_path,
             '-vf', 'select=eq(n\\,0)', '-vframes', '1',
             '-y', frame_path],
            'Failed to extract first frame'
        )

        return lsb.reveal(frame_path)
