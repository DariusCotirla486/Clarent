from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from meetingBot.segments import TranscriptSegment


class TranscriptSink:
    def __init__(
        self,
        output_path: Path,
        api_url: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self.output_path = output_path
        self.api_url = api_url
        self.api_token = api_token
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, segment: TranscriptSegment) -> None:
        line = json.dumps(asdict(segment), ensure_ascii=False)
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

        if self.api_url:
            self._post(segment)

    def _post(self, segment: TranscriptSegment) -> None:
        body = json.dumps(asdict(segment)).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        request = urllib.request.Request(
            self.api_url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status >= 300:
                    print(
                        f"[api] Transcript POST returned HTTP {response.status}",
                        file=sys.stderr,
                    )
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"[api] Could not POST transcript segment: {exc}", file=sys.stderr)

