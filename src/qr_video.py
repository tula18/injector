import base64
import glob
import os
import shutil
import subprocess
import tempfile
import zipfile

import cv2
import numpy as np
import qrcode
from colorama import Fore, Style

from src.payload import build_encrypted_payload, recover_file_from_payload

# Frame line format: MAGIC|index|total|base64_chunk
MAGIC = "QRVID1"

_EC_LEVELS = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


class QRVideoEncoder:
    """Encode a file into QR codes, stored either as an MP4 slideshow or a ZIP of PNGs.

    Reuses the encryption + metadata pipeline (via build_encrypted_payload); the resulting
    encrypted blob is base64-encoded, split into chunks, and each chunk becomes one QR frame.
    """

    def __init__(self, input_file, output_video, password, security_levels, logger,
                 chunk_size=2000, fps=5, frames_per_qr=1, canvas=720, error_correction="M",
                 output_format="mp4"):
        self.input_file = input_file
        self.output_video = output_video
        self.password = password
        self.security_levels = security_levels
        self.logger = logger
        self.chunk_size = chunk_size
        self.fps = fps
        self.frames_per_qr = frames_per_qr
        self.canvas = canvas
        self.error_correction = _EC_LEVELS.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_M)
        self.output_format = output_format.lower()

        self.logger.info(
            f"{Fore.CYAN}Starting QR encoding ({self.output_format}) with security level "
            f"{self.security_levels}{Style.RESET_ALL}")

    def _render_qr(self, text):
        """Render one QR code as a fixed-size (canvas x canvas) BGR uint8 frame.

        The QR is drawn at an integer box size so every module is exactly the same
        number of pixels wide (no distortion), then padded with a white margin to the
        fixed canvas size. Uniform, undistorted modules are what makes detection reliable.
        """
        qr = qrcode.QRCode(error_correction=self.error_correction, box_size=1, border=4)
        qr.add_data(text)
        qr.make(fit=True)

        modules = len(qr.get_matrix())  # side length in modules, including the border
        box = max(1, self.canvas // modules)
        qr.box_size = box
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")

        qr_arr = np.array(qr_img)
        side = qr_arr.shape[0]
        if side > self.canvas:
            # Extremely dense QR (should not happen with the default chunk size): scale down.
            qr_arr = cv2.resize(qr_arr, (self.canvas, self.canvas), interpolation=cv2.INTER_NEAREST)
            side = self.canvas

        canvas = np.full((self.canvas, self.canvas), 255, dtype=np.uint8)
        offset = (self.canvas - side) // 2
        canvas[offset:offset + side, offset:offset + side] = qr_arr
        return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

    def build(self):
        """Encode the input file into QR codes stored as an MP4 or a ZIP of PNGs."""
        encrypted_metadata = build_encrypted_payload(
            self.input_file, self.password, self.security_levels, self.logger)

        b64 = base64.b64encode(encrypted_metadata).decode("ascii")
        chunks = [b64[i:i + self.chunk_size] for i in range(0, len(b64), self.chunk_size)]
        total = len(chunks)
        self.logger.info(f"Payload split into {total} QR code(s).")

        if self.output_format == "zip":
            self._write_zip(chunks, total)
        # H.264 (ffmpeg) compresses sharp QR frames roughly 10x smaller than OpenCV's mp4v,
        # so use it when ffmpeg is available and fall back to the in-process writer otherwise.
        elif shutil.which("ffmpeg"):
            self._write_with_ffmpeg(chunks, total)
        else:
            self.logger.info("ffmpeg not found; falling back to OpenCV VideoWriter.")
            self._write_with_opencv(chunks, total)

        self.logger.info(
            f"QR encoding complete. {total} QR code(s) written to {self.output_video}.")
        return self.output_video

    # Backwards-compatible alias for the original method name.
    def build_video(self):
        return self.build()

    def _write_zip(self, chunks, total):
        """Render each QR to a PNG and store them all in a ZIP archive.

        PNG is already compressed, so ZIP_STORED avoids pointless double-compression.
        """
        with zipfile.ZipFile(self.output_video, "w", zipfile.ZIP_STORED) as zf:
            for index, chunk in enumerate(chunks):
                frame = self._render_qr(f"{MAGIC}|{index}|{total}|{chunk}")
                ok, buf = cv2.imencode(".png", frame)
                if not ok:
                    raise RuntimeError(f"Failed to PNG-encode QR frame {index}")
                zf.writestr(f"qr_{index:06d}.png", buf.tobytes())
                self.logger.debug(f"Added QR PNG {index + 1}/{total} to archive.")

    def _write_with_ffmpeg(self, chunks, total):
        """Render each QR to a PNG then let ffmpeg encode a compact H.264 MP4."""
        frame_dir = tempfile.mkdtemp(prefix="qrvid_")
        try:
            for index, chunk in enumerate(chunks):
                frame = self._render_qr(f"{MAGIC}|{index}|{total}|{chunk}")
                cv2.imwrite(os.path.join(frame_dir, f"f{index:06d}.png"), frame)
                self.logger.debug(f"Rendered QR frame {index + 1}/{total}.")

            # Effective frame rate accounts for holding each QR for frames_per_qr frames.
            effective_fps = max(1, self.fps // max(1, self.frames_per_qr))
            cmd = [
                "ffmpeg", "-y", "-framerate", str(effective_fps),
                "-i", os.path.join(frame_dir, "f%06d.png"),
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                self.output_video,
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0 or not os.path.exists(self.output_video):
                self.logger.error(
                    f"ffmpeg failed (rc={result.returncode}); falling back to OpenCV. "
                    f"{result.stderr.decode(errors='ignore')[-300:]}")
                self._write_with_opencv(chunks, total)
        finally:
            shutil.rmtree(frame_dir, ignore_errors=True)

    def _write_with_opencv(self, chunks, total):
        """In-process fallback: try H.264 (avc1), then mp4v."""
        writer = None
        for codec in ("avc1", "mp4v"):
            fourcc = cv2.VideoWriter_fourcc(*codec)
            candidate = cv2.VideoWriter(self.output_video, fourcc, self.fps,
                                        (self.canvas, self.canvas))
            if candidate.isOpened():
                writer = candidate
                self.logger.debug(f"Using OpenCV VideoWriter codec '{codec}'.")
                break
            candidate.release()
        if writer is None:
            raise RuntimeError(f"Could not open a VideoWriter for {self.output_video}")

        try:
            for index, chunk in enumerate(chunks):
                frame = self._render_qr(f"{MAGIC}|{index}|{total}|{chunk}")
                for _ in range(self.frames_per_qr):
                    writer.write(frame)
                self.logger.debug(f"Wrote QR frame {index + 1}/{total}.")
        finally:
            writer.release()


class QRVideoDecoder:
    """Read QR codes back into the original file, from an MP4 or a folder of PNG images."""

    def __init__(self, video_file, password, security_levels, logger, out_dir="."):
        self.video_file = video_file
        self.password = password
        self.security_levels = security_levels
        self.logger = logger
        self.out_dir = out_dir

    @staticmethod
    def _make_detector():
        """Prefer the Aruco-based QR detector: it is dramatically more reliable at
        locating QR codes than the classic detector. Fall back to the classic one on
        older OpenCV builds that lack it."""
        if hasattr(cv2, "QRCodeDetectorAruco"):
            return cv2.QRCodeDetectorAruco()
        return cv2.QRCodeDetector()

    def _decode_frame(self, detector, frame):
        """Return the list of decoded QR strings found in a frame (usually one)."""
        try:
            ok, decoded, _points, _straight = detector.detectAndDecodeMulti(frame)
            if ok and decoded:
                return [d for d in decoded if d]
        except cv2.error:
            pass
        # Single-QR fallback for detectors/frames where the multi variant returns nothing.
        data, _points, _straight = detector.detectAndDecode(frame)
        return [data] if data else []

    def _collect(self, chunks, total, data):
        """Parse one decoded QR string and record its chunk. Returns the updated total."""
        parts = data.split("|", 3)
        if len(parts) != 4 or parts[0] != MAGIC:
            return total
        index = int(parts[1])
        total = int(parts[2])
        if index not in chunks:
            chunks[index] = parts[3]
            self.logger.debug(f"Captured QR chunk {index} ({len(chunks)}/{total}).")
        return total

    @staticmethod
    def _validate(chunks, total, source):
        if total is None:
            raise ValueError(f"No QR codes found in the {source}.")
        missing = [i for i in range(total) if i not in chunks]
        if missing:
            raise ValueError(f"Incomplete QR {source}: missing chunk(s) {missing} of {total}.")

    def _read_chunks(self):
        """Scan every video frame, decode QR codes, and collect {index: chunk}. Repeated
        frames (each QR is held for several frames) are naturally de-duplicated."""
        cap = cv2.VideoCapture(self.video_file)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video {self.video_file}")

        detector = self._make_detector()
        chunks = {}
        total = None
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                for data in self._decode_frame(detector, frame):
                    total = self._collect(chunks, total, data)
                if total is not None and len(chunks) == total:
                    break
        finally:
            cap.release()

        self._validate(chunks, total, "video")
        return chunks, total

    def _read_chunks_from_images(self):
        """Read every PNG in the folder, decode its QR code, and collect {index: chunk}.
        Filenames/order do not matter — each QR carries its own index/total."""
        pngs = sorted(
            p for p in glob.glob(os.path.join(self.video_file, "*"))
            if p.lower().endswith(".png")
        )
        if not pngs:
            raise ValueError(f"No PNG images found in folder {self.video_file}.")

        detector = self._make_detector()
        chunks = {}
        total = None
        for path in pngs:
            frame = cv2.imread(path)
            if frame is None:
                self.logger.debug(f"Skipping unreadable image {path}.")
                continue
            for data in self._decode_frame(detector, frame):
                total = self._collect(chunks, total, data)

        self._validate(chunks, total, "image set")
        return chunks, total

    def extract_and_decrypt(self):
        self.logger.info(
            f"{Fore.CYAN}Starting QR decoding with security level "
            f"{self.security_levels}{Style.RESET_ALL}")

        if os.path.isdir(self.video_file):
            chunks, total = self._read_chunks_from_images()
        else:
            chunks, total = self._read_chunks()
        b64 = "".join(chunks[i] for i in range(total))
        encrypted_metadata = base64.b64decode(b64)

        info, data = recover_file_from_payload(
            encrypted_metadata, self.password, self.security_levels, self.logger, self.out_dir)
        self.logger.info(
            f"QR decoding complete. Recovered {info.get('original_filename')}.")
        return info, data
