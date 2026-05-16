from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import signal
import time
from pathlib import Path
from typing import Any

from meetingBot.audio_devices import (
    LocalMicrophoneActivityMonitor,
    create_audio_source,
    list_audio_devices,
    rms,
)
from meetingBot.meeting_browser import MeetingBrowser, meeting_browser_has_ended
from meetingBot.segments import TranscriptSegment
from meetingBot.speech_segments import DynamicSpeechSegment, DynamicSpeechSegmenter
from meetingBot.speech_model import FasterWhisperTranscriber
from meetingBot.stop_flag import StopFlag
from meetingBot.transcript_sink import TranscriptSink


UTC = dt.timezone.utc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Join a meeting and create a local faster-whisper live transcript.",
    )
    parser.add_argument("--meeting-url", help="Meeting URL to open with Playwright.")
    parser.add_argument(
        "--platform",
        choices=["generic", "google-meet", "teams", "zoom", "jitsi"],
        default="generic",
        help="Meeting platform. This only affects the join-button heuristics.",
    )
    parser.add_argument("--display-name", default="Clarent Bot")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headlessly. Some meeting audio may not reach speaker loopback in headless mode.",
    )
    parser.add_argument(
        "--start-minimized",
        action="store_true",
        help="Start headed Chromium minimized. This keeps audio playback more reliable than headless mode.",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Keep Chromium visible for platforms that are minimized by default.",
    )
    parser.set_defaults(
        grant_media_permissions=False,
        deny_media_permission_prompts=True,
        block_native_app_prompts=True,
        prefer_zoom_web_client_url=True,
    )
    parser.add_argument(
        "--grant-media-permissions",
        dest="grant_media_permissions",
        action="store_true",
        help="Auto-grant fake browser mic/camera permissions. Use only if deny mode fails.",
    )
    parser.add_argument(
        "--no-grant-media-permissions",
        dest="grant_media_permissions",
        action="store_false",
        help="Do not auto-grant browser media permissions. This is the default.",
    )
    parser.add_argument(
        "--deny-media-permission-prompts",
        dest="deny_media_permission_prompts",
        action="store_true",
        help="Silently deny browser mic/camera prompts. Enabled by default.",
    )
    parser.add_argument(
        "--no-deny-media-permission-prompts",
        dest="deny_media_permission_prompts",
        action="store_false",
        help="Allow browser mic/camera prompts to appear.",
    )
    parser.add_argument(
        "--block-native-app-prompts",
        dest="block_native_app_prompts",
        action="store_true",
        help="Try to block Zoom/Teams native-app launch prompts. Enabled by default.",
    )
    parser.add_argument(
        "--no-block-native-app-prompts",
        dest="block_native_app_prompts",
        action="store_false",
        help="Allow Zoom/Teams native-app launch prompts.",
    )
    parser.add_argument(
        "--prefer-zoom-web-client-url",
        dest="prefer_zoom_web_client_url",
        action="store_true",
        help="Rewrite Zoom /j/ links to the web client and prefill the bot name. Enabled by default.",
    )
    parser.add_argument(
        "--no-prefer-zoom-web-client-url",
        dest="prefer_zoom_web_client_url",
        action="store_false",
        help="Open the original Zoom link instead of rewriting to the web client.",
    )
    parser.add_argument(
        "--browser-profile",
        help="Optional Chromium profile directory for already-signed-in accounts.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Only transcribe local audio. Useful for testing the STT pipeline.",
    )
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit.")
    parser.add_argument(
        "--audio-backend",
        choices=["sounddevice", "soundcard-loopback"],
        default="sounddevice",
        help="Use sounddevice for input devices or soundcard-loopback for speaker/output capture.",
    )
    parser.add_argument(
        "--audio-device",
        help="Device index/name. For soundcard-loopback, pass the speaker/output device.",
    )
    parser.add_argument("--sample-rate", type=int, default=16_000)
    parser.add_argument("--channels", type=int, default=1)
    parser.set_defaults(dynamic_chunks=True)
    parser.add_argument(
        "--dynamic-chunks",
        dest="dynamic_chunks",
        action="store_true",
        help="Create transcript segments from speech start/end detection. Enabled by default.",
    )
    parser.add_argument(
        "--fixed-chunks",
        dest="dynamic_chunks",
        action="store_false",
        help="Use fixed --chunk-seconds transcript chunks instead of speech activity detection.",
    )
    parser.add_argument("--chunk-seconds", type=float, default=6.0, help="Fixed chunk length used with --fixed-chunks.")
    parser.add_argument(
        "--vad-frame-seconds",
        type=float,
        default=0.2,
        help="Small audio frame size used by dynamic speech detection.",
    )
    parser.add_argument(
        "--pre-buffer-seconds",
        type=float,
        default=0.3,
        help="Audio kept before speech starts so the first word is not cut.",
    )
    parser.add_argument(
        "--speech-start-seconds",
        type=float,
        default=0.3,
        help="Speech must be present this long before a dynamic segment starts.",
    )
    parser.add_argument(
        "--speech-end-silence-seconds",
        type=float,
        default=4.0,
        help="Dynamic segment ends after this much silence.",
    )
    parser.add_argument(
        "--min-segment-seconds",
        type=float,
        default=0.8,
        help="Ignore very short dynamic speech segments.",
    )
    parser.add_argument(
        "--max-segment-seconds",
        type=float,
        default=30.0,
        help="Force-close a dynamic segment after this duration.",
    )
    parser.add_argument(
        "--diarization",
        choices=["off", "simple"],
        default="off",
        help="Experimental whole-turn speaker labels. This is not full diarization.",
    )
    parser.set_defaults(ignore_local_mic=True)
    parser.add_argument(
        "--ignore-local-mic",
        dest="ignore_local_mic",
        action="store_true",
        help="Treat meeting audio as silence while the manager's local microphone is active. Enabled by default.",
    )
    parser.add_argument(
        "--no-ignore-local-mic",
        dest="ignore_local_mic",
        action="store_false",
        help="Do not use the manager microphone gate.",
    )
    parser.add_argument(
        "--manager-mic-device",
        help="Input device index/name for the manager microphone gate. Defaults to the system default input.",
    )
    parser.add_argument(
        "--manager-mic-threshold",
        type=float,
        default=0.01,
        help="RMS threshold that marks the manager microphone as active.",
    )
    parser.add_argument(
        "--manager-mic-hangover-seconds",
        type=float,
        default=0.8,
        help="Keep ignoring meeting audio this long after manager mic activity.",
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=0.003,
        help="RMS threshold used to decide whether a frame contains speech.",
    )
    parser.add_argument(
        "--stop-after-silence-seconds",
        type=float,
        default=0.0,
        help="Optional fallback: stop after this many seconds of low-volume chunks. 0 disables it.",
    )
    parser.add_argument("--model-size", default="small", help="faster-whisper model name/size.")
    parser.add_argument(
        "--asr-device",
        choices=["cpu", "cuda", "auto"],
        default="cpu",
        help="Where faster-whisper should run.",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="Examples: int8, int8_float16, float16, float32.",
    )
    parser.add_argument(
        "--language",
        help="Optional spoken language code, for example en or ro. Auto-detect when omitted.",
    )
    parser.add_argument(
        "--task",
        choices=["transcribe", "translate"],
        default="transcribe",
        help="Use translate to produce English text from non-English speech.",
    )
    parser.add_argument(
        "--meeting-id",
        help="Optional Clarent/Spring meeting id included in transcript payloads.",
    )
    parser.add_argument(
        "--transcript-out",
        default=f"transcripts/meeting-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl",
        help="JSONL transcript output path.",
    )
    parser.add_argument(
        "--api-url",
        help="Optional Spring Boot endpoint for transcript chunks, e.g. http://localhost:8080/api/meetings/1/transcript",
    )
    parser.add_argument("--api-token", help="Optional bearer token for --api-url.")
    return parser


def iso_from_datetime(value: dt.datetime) -> str:
    return value.astimezone(UTC).isoformat()


def create_browser_context(args: argparse.Namespace) -> Any:
    if args.no_browser:
        return contextlib.nullcontext()

    start_minimized = args.start_minimized
    if args.platform in {"google-meet", "teams"} and not args.headless and not args.show_browser:
        start_minimized = True

    return MeetingBrowser(
        meeting_url=args.meeting_url,
        platform=args.platform,
        display_name=args.display_name,
        headless=args.headless,
        browser_profile=args.browser_profile,
        start_minimized=start_minimized,
        grant_media_permissions=args.grant_media_permissions,
        deny_media_permission_prompts=args.deny_media_permission_prompts,
        block_native_app_prompts=args.block_native_app_prompts,
        prefer_zoom_web_client_url=args.prefer_zoom_web_client_url,
    )


def create_local_mic_gate(args: argparse.Namespace, stop_flag: StopFlag) -> Any:
    if not args.ignore_local_mic:
        return contextlib.nullcontext(None)

    return LocalMicrophoneActivityMonitor(
        sample_rate=args.sample_rate,
        channels=1,
        device=args.manager_mic_device,
        threshold=args.manager_mic_threshold,
        hangover_seconds=args.manager_mic_hangover_seconds,
        stop_flag=stop_flag,
    )


def write_transcript_segment(
    *,
    args: argparse.Namespace,
    transcriber: FasterWhisperTranscriber,
    sink: TranscriptSink,
    audio_chunk: Any,
    started_at: dt.datetime,
    ended_at: dt.datetime,
    duration_seconds: float,
    speaker: str | None = None,
) -> bool:
    text, detected_language = transcriber.transcribe(audio_chunk)
    if not text:
        print("[asr] no speech detected")
        return False

    segment = TranscriptSegment(
        started_at=iso_from_datetime(started_at),
        ended_at=iso_from_datetime(ended_at),
        duration_seconds=duration_seconds,
        text=text,
        language=detected_language,
        speaker=speaker,
        meeting_id=args.meeting_id,
        task=args.task,
    )
    sink.write(segment)
    timestamp = dt.datetime.now().strftime("%H:%M:%S")
    speaker_prefix = f"{speaker}: " if speaker else ""
    print(f"[{timestamp}] {speaker_prefix}{text}")
    return True


def write_dynamic_segment(
    *,
    args: argparse.Namespace,
    transcriber: FasterWhisperTranscriber,
    sink: TranscriptSink,
    segment: DynamicSpeechSegment | None,
) -> bool:
    if segment is None:
        return False

    return write_transcript_segment(
        args=args,
        transcriber=transcriber,
        sink=sink,
        audio_chunk=segment.audio,
        started_at=segment.started_at,
        ended_at=segment.ended_at,
        duration_seconds=segment.duration_seconds,
        speaker=segment.speaker,
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices(args.audio_backend)
        return 0

    if not args.no_browser and not args.meeting_url:
        parser.error("--meeting-url is required unless --no-browser is used.")

    stop_flag = StopFlag()
    signal.signal(signal.SIGINT, stop_flag.request_stop)
    signal.signal(signal.SIGTERM, stop_flag.request_stop)

    transcriber = FasterWhisperTranscriber(
        model_size=args.model_size,
        device=args.asr_device,
        compute_type=args.compute_type,
        language=args.language,
        task=args.task,
    )
    sink = TranscriptSink(
        output_path=Path(args.transcript_out),
        api_url=args.api_url,
        api_token=args.api_token,
    )

    print("[bot] Press Ctrl+C to stop listening.")
    with create_browser_context(args) as meeting_browser:
        with create_local_mic_gate(args, stop_flag) as local_mic_gate:
            with create_audio_source(args, stop_flag) as audio_source:
                last_audible_at = time.monotonic()
                if args.dynamic_chunks:
                    print(
                        "[audio] Dynamic speech chunks enabled "
                        f"(pre-buffer={args.pre_buffer_seconds:.1f}s, "
                        f"end-silence={args.speech_end_silence_seconds:.1f}s, "
                        f"diarization={args.diarization}, "
                        f"ignore-local-mic={args.ignore_local_mic})."
                    )
                    segmenter = DynamicSpeechSegmenter(
                        sample_rate=args.sample_rate,
                        silence_threshold=args.silence_threshold,
                        pre_buffer_seconds=args.pre_buffer_seconds,
                        speech_start_seconds=args.speech_start_seconds,
                        speech_end_silence_seconds=args.speech_end_silence_seconds,
                        min_segment_seconds=args.min_segment_seconds,
                        max_segment_seconds=args.max_segment_seconds,
                        diarization=args.diarization,
                    )
                    last_frame_ended_at = dt.datetime.now(tz=UTC)

                    for audio_frame in audio_source.chunks():
                        if stop_flag.should_stop:
                            break

                        frame_ended_at = dt.datetime.now(tz=UTC)
                        last_frame_ended_at = frame_ended_at

                        if meeting_browser_has_ended(meeting_browser):
                            print("[browser] Meeting appears to have ended. Closing listener.")
                            write_dynamic_segment(
                                args=args,
                                transcriber=transcriber,
                                sink=sink,
                                segment=segmenter.flush(frame_ended_at),
                            )
                            stop_flag.request_stop()
                            break

                        manager_speaking = bool(local_mic_gate and local_mic_gate.is_active())
                        if not manager_speaking and rms(audio_frame) >= args.silence_threshold:
                            last_audible_at = time.monotonic()

                        write_dynamic_segment(
                            args=args,
                            transcriber=transcriber,
                            sink=sink,
                            segment=segmenter.process_frame(
                                audio_frame,
                                frame_ended_at,
                                force_silence=manager_speaking,
                            ),
                        )

                        if (
                            args.stop_after_silence_seconds > 0
                            and time.monotonic() - last_audible_at >= args.stop_after_silence_seconds
                        ):
                            print("[audio] Silence timeout reached. Closing listener.")
                            write_dynamic_segment(
                                args=args,
                                transcriber=transcriber,
                                sink=sink,
                                segment=segmenter.flush(frame_ended_at),
                            )
                            stop_flag.request_stop()
                            break

                    write_dynamic_segment(
                        args=args,
                        transcriber=transcriber,
                        sink=sink,
                        segment=segmenter.flush(last_frame_ended_at),
                    )
                else:
                    for audio_chunk in audio_source.chunks():
                        if stop_flag.should_stop:
                            break

                        if meeting_browser_has_ended(meeting_browser):
                            print("[browser] Meeting appears to have ended. Closing listener.")
                            stop_flag.request_stop()
                            break

                        if local_mic_gate and local_mic_gate.is_active():
                            continue

                        volume = rms(audio_chunk)
                        if volume < args.silence_threshold:
                            print(f"[audio] skipped low-volume chunk (rms={volume:.5f})")
                            if (
                                args.stop_after_silence_seconds > 0
                                and time.monotonic() - last_audible_at >= args.stop_after_silence_seconds
                            ):
                                print("[audio] Silence timeout reached. Closing listener.")
                                stop_flag.request_stop()
                                break
                            continue
                        last_audible_at = time.monotonic()

                        chunk_ended_at = dt.datetime.now(tz=UTC)
                        duration_seconds = len(audio_chunk) / args.sample_rate
                        chunk_started_at = chunk_ended_at - dt.timedelta(seconds=duration_seconds)
                        write_transcript_segment(
                            args=args,
                            transcriber=transcriber,
                            sink=sink,
                            audio_chunk=audio_chunk,
                            started_at=chunk_started_at,
                            ended_at=chunk_ended_at,
                            duration_seconds=duration_seconds,
                        )

    print("[bot] Stopped.")
    return 0
