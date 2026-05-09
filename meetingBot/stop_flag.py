from __future__ import annotations

from typing import Any


class StopFlag:
    def __init__(self) -> None:
        self.should_stop = False

    def request_stop(self, *_: Any) -> None:
        self.should_stop = True

