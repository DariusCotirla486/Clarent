from __future__ import annotations

import queue
import time
import warnings
from typing import Any, Iterable

from meetingBot.stop_flag import StopFlag


def _suppress_soundcard_discontinuity_warnings() -> None:
    try:
        from soundcard.mediafoundation import SoundcardRuntimeWarning

        warnings.filterwarnings(
            "ignore",
            category=SoundcardRuntimeWarning,
            message="data discontinuity in recording",
        )
    except Exception:
        warnings.filterwarnings(
            "ignore",
            message="data discontinuity in recording",
        )


class SoundDeviceAudioSource:
    def __init__(
        self,
        sample_rate: int,
        chunk_seconds: float,
        channels: int,
        device: str | int | None,
        stop_flag: StopFlag,
        queue_size: int = 200,
    ) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise SystemExit(
                "Missing audio dependencies. Install them with "
                "`pip install sounddevice numpy`."
            ) from exc

        self.np = np
        self.sd = sd
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.channels = channels
        self.device = self._parse_device(device)
        self.stop_flag = stop_flag
        self.audio_queue: queue.Queue[Any] = queue.Queue(maxsize=queue_size)
        self.stream: Any = None

    @staticmethod
    def list_devices() -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise SystemExit(
                "Missing dependency: sounddevice. Install it with "
                "`pip install sounddevice`."
            ) from exc

        print(sd.query_devices())

    def __enter__(self) -> "SoundDeviceAudioSource":
        self.stream = self.sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=self._on_audio,
        )
        self.stream.start()
        print(
            "[audio] Listening on input device "
            f"{self.device if self.device is not None else '<default>'} "
            f"at {self.sample_rate} Hz."
        )
        return self

    def __exit__(self, *_: Any) -> None:
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def chunks(self) -> Iterable[Any]:
        frames_per_chunk = int(self.sample_rate * self.chunk_seconds)
        buffered: list[Any] = []
        buffered_frames = 0

        while not self.stop_flag.should_stop:
            try:
                audio_block = self.audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if audio_block.ndim > 1:
                audio_block = audio_block.mean(axis=1)

            buffered.append(audio_block.copy())
            buffered_frames += len(audio_block)

            while buffered_frames >= frames_per_chunk:
                merged = self.np.concatenate(buffered)
                chunk = merged[:frames_per_chunk].astype("float32")
                remainder = merged[frames_per_chunk:]

                buffered = [remainder] if len(remainder) else []
                buffered_frames = len(remainder)
                yield chunk

    def _on_audio(self, indata: Any, _frames: int, _time_info: Any, status: Any) -> None:
        if status:
            print(f"[audio] {status}")

        try:
            self.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(indata.copy())
            except queue.Empty:
                pass

    def _parse_device(self, device: str | int | None) -> str | int | None:
        if device is None:
            return None
        if isinstance(device, int):
            return device
        if device.isdigit():
            return int(device)
        return device


class LocalMicrophoneActivityMonitor:
    """Tracks whether the manager's local microphone is currently active."""

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        device: str | int | None,
        threshold: float,
        hangover_seconds: float,
        stop_flag: StopFlag,
        frame_seconds: float = 0.1,
    ) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise SystemExit(
                "Missing audio dependency for local mic ignore mode. Install it with "
                "`pip install sounddevice numpy`."
            ) from exc

        self.np = np
        self.sd = sd
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = self._parse_device(device)
        self.threshold = threshold
        self.hangover_seconds = hangover_seconds
        self.stop_flag = stop_flag
        self.frame_seconds = frame_seconds
        self.last_active_at = 0.0
        self.stream: Any = None

    def __enter__(self) -> "LocalMicrophoneActivityMonitor":
        self.stream = self.sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            blocksize=max(1, int(self.sample_rate * self.frame_seconds)),
            callback=self._on_audio,
        )
        self.stream.start()
        print(
            "[audio] Manager microphone ignore gate enabled on "
            f"{self.device if self.device is not None else '<default input>'} "
            f"(threshold={self.threshold:.4f})."
        )
        return self

    def __exit__(self, *_: Any) -> None:
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def is_active(self) -> bool:
        return time.monotonic() - self.last_active_at <= self.hangover_seconds

    def _on_audio(self, indata: Any, _frames: int, _time_info: Any, status: Any) -> None:
        if self.stop_flag.should_stop:
            return
        if status:
            print(f"[audio] manager mic gate: {status}")

        audio_block = indata
        if audio_block.ndim > 1:
            audio_block = audio_block.mean(axis=1)
        if rms(self.np.asarray(audio_block, dtype="float32")) >= self.threshold:
            self.last_active_at = time.monotonic()

    def _parse_device(self, device: str | int | None) -> str | int | None:
        if device is None:
            return None
        if isinstance(device, int):
            return device
        if device.isdigit():
            return int(device)
        return device


class SoundCardLoopbackAudioSource:
    """Record audio playing through a selected output device."""

    def __init__(
        self,
        sample_rate: int,
        chunk_seconds: float,
        channels: int,
        device: str | int | None,
        stop_flag: StopFlag,
    ) -> None:
        _suppress_soundcard_discontinuity_warnings()
        try:
            import numpy as np
            import soundcard as sc
        except ImportError as exc:
            raise SystemExit(
                "Missing loopback audio dependencies. Install them with "
                "`pip install soundcard numpy`."
            ) from exc

        self.np = np
        self.sc = sc
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.channels = channels
        self.device = str(device) if device is not None else None
        self.stop_flag = stop_flag
        self.loopback_microphone: Any = None
        self.recorder: Any = None
        self.recorder_context: Any = None

    @staticmethod
    def list_devices() -> None:
        try:
            import soundcard as sc
        except ImportError as exc:
            raise SystemExit(
                "Missing dependency: soundcard. Install it with `pip install soundcard`."
            ) from exc

        print("Speakers/output devices that can usually be loopback-recorded:")
        for index, speaker in enumerate(sc.all_speakers()):
            print(f"  [{index}] {speaker.name} ({speaker.id})")

        print("\nLoopback microphones exposed by soundcard:")
        for index, microphone in enumerate(sc.all_microphones(include_loopback=True)):
            print(f"  [{index}] {microphone.name} ({microphone.id})")

    def __enter__(self) -> "SoundCardLoopbackAudioSource":
        self.loopback_microphone = self._select_loopback_microphone()
        self.recorder_context = self.loopback_microphone.recorder(
            samplerate=self.sample_rate,
            channels=self.channels,
        )
        self.recorder = self.recorder_context.__enter__()
        print(
            "[audio] Listening to speaker loopback "
            f"'{self.loopback_microphone.name}' at {self.sample_rate} Hz."
        )
        return self

    def __exit__(self, *_: Any) -> None:
        if self.recorder_context:
            self.recorder_context.__exit__(None, None, None)

    def chunks(self) -> Iterable[Any]:
        frames_per_chunk = int(self.sample_rate * self.chunk_seconds)
        while not self.stop_flag.should_stop:
            audio = self.recorder.record(numframes=frames_per_chunk)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            yield self.np.asarray(audio, dtype="float32")

    def _select_loopback_microphone(self) -> Any:
        if not self.device:
            speaker = self.sc.default_speaker()
            return self.sc.get_microphone(id=speaker.name, include_loopback=True)

        device = self.device.lower()
        speakers = self.sc.all_speakers()

        if self.device.isdigit():
            index = int(self.device)
            if 0 <= index < len(speakers):
                speaker = speakers[index]
                return self.sc.get_microphone(id=speaker.name, include_loopback=True)

        for speaker in speakers:
            if device in speaker.name.lower() or device in str(speaker.id).lower():
                return self.sc.get_microphone(id=speaker.name, include_loopback=True)

        microphones = self.sc.all_microphones(include_loopback=True)
        for microphone in microphones:
            if device in microphone.name.lower() or device in str(microphone.id).lower():
                return microphone

        available = ", ".join(speaker.name for speaker in speakers)
        raise SystemExit(
            f"Could not find output/loopback device matching '{self.device}'. "
            f"Available speakers: {available}"
        )


def create_audio_source(args: Any, stop_flag: StopFlag) -> Any:
    chunk_seconds = (
        args.vad_frame_seconds
        if getattr(args, "dynamic_chunks", False)
        else args.chunk_seconds
    )

    if args.audio_backend == "soundcard-loopback":
        return SoundCardLoopbackAudioSource(
            sample_rate=args.sample_rate,
            chunk_seconds=chunk_seconds,
            channels=args.channels,
            device=args.audio_device,
            stop_flag=stop_flag,
        )

    return SoundDeviceAudioSource(
        sample_rate=args.sample_rate,
        chunk_seconds=chunk_seconds,
        channels=args.channels,
        device=args.audio_device,
        stop_flag=stop_flag,
    )


def list_audio_devices(audio_backend: str) -> None:
    if audio_backend == "soundcard-loopback":
        SoundCardLoopbackAudioSource.list_devices()
        print("\nInput devices usable for --manager-mic-device:")
        SoundDeviceAudioSource.list_devices()
    else:
        SoundDeviceAudioSource.list_devices()


def rms(audio: Any) -> float:
    import numpy as np

    return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
