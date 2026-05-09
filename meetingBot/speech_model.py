from __future__ import annotations

from typing import Any


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_size: str,
        device: str,
        compute_type: str,
        language: str | None,
        task: str,
    ) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SystemExit(
                "Missing dependency: faster-whisper. Install it with "
                "`pip install faster-whisper`."
            ) from exc

        normalized_model = model_size.lower()
        if task == "translate" and "turbo" in normalized_model:
            print(
                "[asr] Warning: Whisper turbo is optimized for transcription, "
                "not translation. Use large-v3 for non-English speech translation."
            )
        if task == "translate" and normalized_model.startswith("distil"):
            print(
                "[asr] Warning: distil-large-v3 is best treated as an English "
                "transcription model. Use large-v3 for multilingual translation."
            )

        print(
            f"[asr] Loading faster-whisper model '{model_size}' "
            f"on {device} ({compute_type})..."
        )
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language
        self.task = task

    def transcribe(self, audio: Any) -> tuple[str, str | None]:
        try:
            segments, info = self.model.transcribe(
                audio,
                language=self.language,
                task=self.task,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
        except RuntimeError as exc:
            message = str(exc)
            if "cublas64_12.dll" in message or "cudnn" in message.lower():
                raise SystemExit(
                    "CUDA runtime libraries required by faster-whisper are missing. "
                    "Install cuBLAS for CUDA 12 and cuDNN 9, or run with "
                    "`--asr-device cpu --compute-type int8`, or use a CTranslate2 "
                    "version matching your installed CUDA/cuDNN runtime."
                ) from exc
            raise

        text_parts = [segment.text.strip() for segment in segments if segment.text]
        return " ".join(text_parts).strip(), getattr(info, "language", None)
