from __future__ import annotations

import datetime as dt
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from meetingBot.audio_devices import rms


@dataclass
class DynamicSpeechSegment:
    audio: Any
    started_at: dt.datetime
    ended_at: dt.datetime
    duration_seconds: float
    speaker: str | None = None


class SimpleSpeakerDiarizer:
    """Tiny online turn labeler.

    This is not full diarization. It only assigns stable-ish speaker labels to
    whole speech turns from coarse audio features, which is useful enough for a
    first UI signal and cheap enough to run locally without another model.
    """

    def __init__(self, sample_rate: int, threshold: float = 0.55, max_speakers: int = 4) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.max_speakers = max_speakers
        self.centroids: list[np.ndarray] = []
        self.counts: list[int] = []

    def label(self, audio: Any) -> str:
        features = self._features(audio)
        if not self.centroids:
            self.centroids.append(features)
            self.counts.append(1)
            return "Speaker 1"

        distances = [float(np.linalg.norm(features - centroid)) for centroid in self.centroids]
        best_index = int(np.argmin(distances))
        if distances[best_index] > self.threshold and len(self.centroids) < self.max_speakers:
            self.centroids.append(features)
            self.counts.append(1)
            return f"Speaker {len(self.centroids)}"

        self.counts[best_index] += 1
        learning_rate = min(0.35, 1.0 / self.counts[best_index])
        self.centroids[best_index] = (
            (1.0 - learning_rate) * self.centroids[best_index]
            + learning_rate * features
        )
        return f"Speaker {best_index + 1}"

    def _features(self, audio: Any) -> np.ndarray:
        samples = np.asarray(audio, dtype=np.float32)
        if len(samples) < 4:
            return np.zeros(3, dtype=np.float32)

        energy = np.log10(rms(samples) + 1e-6)
        signs = samples >= 0
        zero_crossing_rate = float(np.mean(signs[1:] != signs[:-1]))
        spectrum = np.abs(np.fft.rfft(samples))
        if float(np.sum(spectrum)) <= 1e-8:
            spectral_centroid = 0.0
        else:
            frequencies = np.fft.rfftfreq(len(samples), d=1.0 / self.sample_rate)
            spectral_centroid = float(np.sum(frequencies * spectrum) / np.sum(spectrum))
            spectral_centroid = spectral_centroid / (self.sample_rate / 2.0)

        return np.asarray(
            [
                energy * 0.45,
                zero_crossing_rate * 3.0,
                spectral_centroid * 1.4,
            ],
            dtype=np.float32,
        )


class RmsVoiceDetector:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.name = "rms"

    def is_speech(self, audio: Any) -> bool:
        return rms(audio) >= self.threshold


class SileroVoiceDetector:
    def __init__(
        self,
        sample_rate: int,
        threshold: float,
        rms_fallback_threshold: float,
        required: bool = False,
    ) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.rms_fallback = RmsVoiceDetector(rms_fallback_threshold)
        self.name = "silero"
        self.window_size = 512 if sample_rate == 16_000 else 256
        try:
            import torch
            from silero_vad import load_silero_vad

            self.torch = torch
            self.model = load_silero_vad()
            if hasattr(self.model, "reset_states"):
                self.model.reset_states()
            print(f"[vad] Silero VAD enabled (threshold={self.threshold:.2f}).")
        except Exception as exc:
            if required:
                raise SystemExit(
                    "Silero VAD requires PyTorch. Install it in the same Python "
                    "environment as the bot with `py -m pip install torch silero-vad`, "
                    "or use `--vad-mode auto`/`--vad-mode rms`."
                ) from exc
            self.torch = None
            self.model = None
            self.name = "rms"
            print(f"[vad] Silero VAD unavailable ({exc}). Falling back to RMS VAD.")

    def is_speech(self, audio: Any) -> bool:
        if self.model is None or self.torch is None:
            return self.rms_fallback.is_speech(audio)

        samples = np.asarray(audio, dtype=np.float32)
        if len(samples) == 0:
            return False

        probabilities: list[float] = []
        with self.torch.no_grad():
            for start in range(0, len(samples), self.window_size):
                window = samples[start:start + self.window_size]
                if len(window) < self.window_size:
                    window = np.pad(window, (0, self.window_size - len(window)))
                tensor = self.torch.from_numpy(window)
                probability = float(self.model(tensor, self.sample_rate).item())
                probabilities.append(probability)

        if not probabilities:
            return False
        return max(probabilities) >= self.threshold


class DynamicSpeechSegmenter:
    def __init__(
        self,
        sample_rate: int,
        silence_threshold: float,
        vad_mode: str,
        silero_threshold: float,
        pre_buffer_seconds: float,
        speech_start_seconds: float,
        speech_end_silence_seconds: float,
        min_segment_seconds: float,
        max_segment_seconds: float,
        end_padding_seconds: float = 0.3,
        diarization: str = "simple",
    ) -> None:
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.voice_detector = self._create_voice_detector(vad_mode, silero_threshold)
        self.pre_buffer_seconds = pre_buffer_seconds
        self.speech_start_seconds = speech_start_seconds
        self.speech_end_silence_seconds = speech_end_silence_seconds
        self.min_segment_seconds = min_segment_seconds
        self.max_segment_seconds = max_segment_seconds
        self.end_padding_seconds = end_padding_seconds
        self.diarizer = SimpleSpeakerDiarizer(sample_rate) if diarization == "simple" else None

        self.pre_buffer: deque[Any] = deque()
        self.pre_buffer_duration = 0.0
        self.pending_speech: list[Any] = []
        self.pending_speech_duration = 0.0
        self.recording = False
        self.segment_frames: list[Any] = []
        self.segment_duration = 0.0
        self.silence_duration = 0.0

    def process_frame(
        self,
        frame: Any,
        frame_ended_at: dt.datetime,
        force_silence: bool = False,
    ) -> DynamicSpeechSegment | None:
        audio_frame = np.asarray(frame, dtype=np.float32)
        frame_duration = len(audio_frame) / self.sample_rate if len(audio_frame) else 0.0
        if frame_duration <= 0:
            return None

        if force_silence:
            audio_frame = np.zeros_like(audio_frame)
            voiced = False
        else:
            voiced = self.voice_detector.is_speech(audio_frame)

        if not self.recording:
            if voiced:
                self.pending_speech.append(audio_frame)
                self.pending_speech_duration += frame_duration
                if self.pending_speech_duration >= self.speech_start_seconds:
                    self.recording = True
                    self.segment_frames = list(self.pre_buffer) + self.pending_speech
                    self.segment_duration = self.pre_buffer_duration + self.pending_speech_duration
                    self.silence_duration = 0.0
                    self.pre_buffer.clear()
                    self.pre_buffer_duration = 0.0
                    self.pending_speech = []
                    self.pending_speech_duration = 0.0
                return None

            self._return_pending_to_pre_buffer()
            self._append_pre_buffer(audio_frame, frame_duration)
            return None

        self.segment_frames.append(audio_frame)
        self.segment_duration += frame_duration
        if voiced:
            self.silence_duration = 0.0
        else:
            self.silence_duration += frame_duration

        if self.segment_duration >= self.max_segment_seconds:
            return self._finish_segment(frame_ended_at, trim_trailing_silence=False)

        if (
            self.silence_duration >= self.speech_end_silence_seconds
            and self.segment_duration >= self.min_segment_seconds
        ):
            return self._finish_segment(frame_ended_at, trim_trailing_silence=True)

        return None

    def flush(self, ended_at: dt.datetime) -> DynamicSpeechSegment | None:
        if not self.recording or self.segment_duration < self.min_segment_seconds:
            self._reset_segment()
            return None
        return self._finish_segment(ended_at, trim_trailing_silence=True)

    def _finish_segment(
        self,
        frame_ended_at: dt.datetime,
        trim_trailing_silence: bool,
    ) -> DynamicSpeechSegment | None:
        frames = self.segment_frames
        silence_to_trim = 0.0
        if trim_trailing_silence and self.silence_duration > self.end_padding_seconds:
            silence_to_trim = self.silence_duration - self.end_padding_seconds
            frames_to_trim = int(silence_to_trim / (len(frames[-1]) / self.sample_rate))
            if frames_to_trim > 0 and frames_to_trim < len(frames):
                frames = frames[:-frames_to_trim]

        if not frames:
            self._reset_segment()
            return None

        audio = np.concatenate(frames).astype(np.float32)
        duration_seconds = len(audio) / self.sample_rate
        ended_at = frame_ended_at - dt.timedelta(seconds=silence_to_trim)
        started_at = ended_at - dt.timedelta(seconds=duration_seconds)
        speaker = self.diarizer.label(audio) if self.diarizer else None
        self._reset_segment()
        return DynamicSpeechSegment(
            audio=audio,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            speaker=speaker,
        )

    def _append_pre_buffer(self, frame: Any, frame_duration: float) -> None:
        self.pre_buffer.append(frame)
        self.pre_buffer_duration += frame_duration
        while self.pre_buffer_duration > self.pre_buffer_seconds and self.pre_buffer:
            removed = self.pre_buffer.popleft()
            self.pre_buffer_duration -= len(removed) / self.sample_rate

    def _return_pending_to_pre_buffer(self) -> None:
        for frame in self.pending_speech:
            self._append_pre_buffer(frame, len(frame) / self.sample_rate)
        self.pending_speech = []
        self.pending_speech_duration = 0.0

    def _reset_segment(self) -> None:
        self.recording = False
        self.segment_frames = []
        self.segment_duration = 0.0
        self.silence_duration = 0.0

    def _create_voice_detector(self, vad_mode: str, silero_threshold: float) -> Any:
        if vad_mode == "rms":
            print(f"[vad] RMS VAD enabled (threshold={self.silence_threshold:.4f}).")
            return RmsVoiceDetector(self.silence_threshold)

        if vad_mode == "silero":
            return SileroVoiceDetector(
                sample_rate=self.sample_rate,
                threshold=silero_threshold,
                rms_fallback_threshold=self.silence_threshold,
                required=True,
            )

        detector = SileroVoiceDetector(
            sample_rate=self.sample_rate,
            threshold=silero_threshold,
            rms_fallback_threshold=self.silence_threshold,
        )
        return detector
