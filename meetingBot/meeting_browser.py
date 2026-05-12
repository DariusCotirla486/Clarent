from __future__ import annotations

import json
import base64
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

from meetingBot.utils import (
    TEAMS_BROWSER_JOIN_BUTTONS,
    TEAMS_CAMERA_LABELS,
    TEAMS_JOIN_BUTTONS,
    TEAMS_MICROPHONE_LABELS,
    TEAMS_NAME_INPUT_SELECTORS,
    TEAMS_NO_AUDIO_VIDEO_BUTTONS,
    TEAMS_WAITING_ROOM_PHRASES,
)


class MeetingBrowser:
    def __init__(
        self,
        meeting_url: str,
        platform: str,
        display_name: str,
        headless: bool,
        browser_profile: str | None,
        start_minimized: bool,
        grant_media_permissions: bool,
        deny_media_permission_prompts: bool,
        block_native_app_prompts: bool,
        prefer_zoom_web_client_url: bool,
    ) -> None:
        self.original_meeting_url = meeting_url
        self.meeting_url = self._normalize_meeting_url(
            meeting_url,
            platform,
            prefer_zoom_web_client_url,
            display_name,
        )
        self.platform = platform
        self.display_name = display_name
        self.headless = headless
        self.browser_profile = browser_profile
        self.start_minimized = start_minimized
        self.grant_media_permissions = grant_media_permissions
        self.deny_media_permission_prompts = deny_media_permission_prompts
        self.block_native_app_prompts = block_native_app_prompts
        self.prefer_zoom_web_client_url = prefer_zoom_web_client_url
        self.playwright: Any = None
        self.context: Any = None
        self.browser: Any = None
        self.page: Any = None
        self.join_attempted_at: float | None = None
        self.runtime_browser_profile: str | None = None

    def __enter__(self) -> "MeetingBrowser":
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise SystemExit(
                "Missing dependency: playwright. Install it with "
                "`pip install playwright` and then run "
                "`python -m playwright install chromium`."
            ) from exc

        self.PlaywrightTimeoutError = PlaywrightTimeoutError
        self.playwright = sync_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--autoplay-policy=no-user-gesture-required",
        ]
        if self.start_minimized:
            launch_args.append("--start-minimized")
        if self.grant_media_permissions:
            launch_args.extend(
                [
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                ]
            )
        elif self.deny_media_permission_prompts:
            launch_args.append("--deny-permission-prompts")

        permissions = ["microphone", "camera"] if self.grant_media_permissions else []

        effective_profile = self.browser_profile
        if not effective_profile and self.block_native_app_prompts:
            effective_profile = self._prepare_bot_browser_profile()
            self.runtime_browser_profile = effective_profile

        if effective_profile:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=effective_profile,
                headless=self.headless,
                args=launch_args,
                viewport={"width": 1280, "height": 820},
                permissions=permissions,
            )
        else:
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=launch_args,
            )
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 820},
                permissions=permissions,
            )

        self.page = self.context.new_page()
        if self.block_native_app_prompts:
            self._install_external_protocol_blocker()
        print(f"[browser] Opening meeting URL for platform '{self.platform}'...")
        self.page.goto(self.meeting_url, wait_until="domcontentloaded", timeout=90_000)
        self._dismiss_browser_prompt()
        self._try_join()
        return self

    def __exit__(self, *_: Any) -> None:
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _try_join(self) -> None:
        self.join_attempted_at = time.monotonic()
        time.sleep(1)
        self._dismiss_browser_prompt()
        if self.platform == "google-meet":
            self._try_join_google_meet()
        elif self.platform == "teams":
            self._try_join_teams()
        elif self.platform == "zoom":
            self._try_join_zoom()
        elif self.platform == "jitsi":
            self._fill_display_name(["input[placeholder*='name']", "input[aria-label*='name']"])
            self._click_any_label(["Mute microphone", "Turn off microphone"])
            self._click_any_label(["Turn off camera"])
            self._click_any_text(["Join meeting", "Join"])
        else:
            self._fill_display_name(["input[placeholder*='name']", "input[aria-label*='name']"])
            self._click_any_label(["Turn off microphone", "Mute microphone"])
            self._click_any_label(["Turn off camera"])
            self._click_any_text(["Continue", "Ask to join", "Join now", "Join", "Enter meeting"])

        print(
            "[browser] Join flow attempted. If the platform asks for host approval, "
            "admit the bot in the meeting UI."
        )

    def meeting_has_ended(self) -> bool:
        if not self.page or self.page.is_closed():
            return True

        if self.join_attempted_at and time.monotonic() - self.join_attempted_at < 20:
            return False
        if self._looks_waiting_for_admission():
            return False

        ended_phrases = [
            "you left the meeting",
            "you've left the meeting",
            "you have left the meeting",
            "you left the call",
            "you have left the call",
            "meeting ended",
            "the meeting has ended",
            "this meeting has been ended by host",
            "the host has ended this meeting",
            "has ended this meeting",
            "has ended for everyone",
            "call ended",
            "rejoin",
            "return to home screen",
        ]

        try:
            body_text = self.page.locator("body").inner_text(timeout=500).lower()
        except Exception:
            return False

        return any(phrase in body_text for phrase in ended_phrases)

    def _try_join_google_meet(self) -> None:
        self._dismiss_browser_prompt()
        self._click_any_text(
            [
                "Continue without microphone and camera",
                "Continue without mic and camera",
                "Continue without microphone",
                "Join without microphone and camera",
                "Join without mic and camera",
                "Block microphone and camera",
                "Continue",
                "Dismiss",
            ],
            timeout_ms=700,
        )
        self._fill_display_name(["input[aria-label='Your name']", "input[placeholder='Your name']"])
        self._click_any_label(["Turn off microphone"])
        self._click_any_label(["Turn off camera"])
        self._click_any_text(["Ask to join", "Join now", "Join"], timeout_ms=1_500)

    def _try_join_teams(self) -> None:
        deadline = time.monotonic() + 60
        continued_in_browser = False
        continued_without_media = False

        while time.monotonic() < deadline:
            if self._looks_joined() or self._looks_waiting_for_admission():
                return

            self._dismiss_browser_prompt()
            if not continued_in_browser:
                continued_in_browser = self._click_any_button_text(
                    TEAMS_BROWSER_JOIN_BUTTONS,
                    timeout_ms=500,
                )
                time.sleep(0.3)
                continue

            if not continued_without_media:
                continued_without_media = self._click_any_button_text(
                    TEAMS_NO_AUDIO_VIDEO_BUTTONS,
                    timeout_ms=700,
                )
                if continued_without_media:
                    time.sleep(0.3)
                    continue

            name_filled = self._fill_display_name(
                TEAMS_NAME_INPUT_SELECTORS,
                timeout_ms=700,
            )
            if name_filled and self._click_any_button_text(TEAMS_JOIN_BUTTONS, timeout_ms=700):
                self._finish_teams_join_after_click()
                return

            time.sleep(0.25)

    def _finish_teams_join_after_click(self) -> None:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if self._looks_joined() or self._looks_waiting_for_admission():
                return

            self._dismiss_browser_prompt()
            self._click_any_button_text(TEAMS_NO_AUDIO_VIDEO_BUTTONS, timeout_ms=250)
            self._click_any_button_text(TEAMS_JOIN_BUTTONS, timeout_ms=300)
            time.sleep(0.25)

    def _try_join_zoom(self) -> None:
        deadline = time.monotonic() + 60
        requested_admission = False
        joining_seen_at: float | None = None
        retried_original_link = False
        reloaded_join_screen = False
        while (
            time.monotonic() < deadline
            and not self._looks_joined()
            and not self._looks_waiting_for_admission()
            and not requested_admission
        ):
            if self._looks_zoom_joining_screen():
                if joining_seen_at is None:
                    joining_seen_at = time.monotonic()
                elif time.monotonic() - joining_seen_at > 8:
                    if self.page.url != self.original_meeting_url and not retried_original_link:
                        print("[browser] Zoom join screen looks stuck. Retrying original Zoom link.")
                        self.page.goto(
                            self.original_meeting_url,
                            wait_until="domcontentloaded",
                            timeout=60_000,
                        )
                        self._dismiss_browser_prompt()
                        retried_original_link = True
                        joining_seen_at = None
                        continue
                    if not reloaded_join_screen:
                        print("[browser] Zoom join screen still stuck. Reloading once.")
                        self.page.reload(wait_until="domcontentloaded", timeout=60_000)
                        self._dismiss_browser_prompt()
                        reloaded_join_screen = True
                        joining_seen_at = None
                        continue
            else:
                joining_seen_at = None

            self._dismiss_browser_prompt()
            self._accept_cookies()
            self._click_any_text(
                [
                    "Join from Your Browser",
                    "Join from your browser",
                    "Join from Browser",
                    "Launch Meeting",
                    "Launch meeting",
                ],
                timeout_ms=500,
            )
            self._dismiss_browser_prompt()
            self._click_any_text(
                [
                    "Join from Your Browser",
                    "Join from your browser",
                    "Join from Browser",
                ],
                timeout_ms=500,
            )
            self._fill_display_name(
                [
                    "input#inputname",
                    "input#input-for-name",
                    "input[name='username']",
                    "input[placeholder*='Your Name']",
                    "input[placeholder*='name']",
                    "input[aria-label*='Name']",
                    "input[aria-label*='name']",
                ],
                timeout_ms=250,
            )
            self._mute_zoom_microphone()
            self._click_any_text(
                [
                    "Join without microphone",
                    "Join without audio",
                    "Continue without microphone",
                    "Continue without audio",
                ],
                timeout_ms=700,
            )
            requested_admission = self._click_any_text(["Join", "Join Meeting"], timeout_ms=700)
            if requested_admission:
                time.sleep(2)
                break
            time.sleep(0.25)

    def _accept_cookies(self) -> bool:
        if self._click_any_selector(
            [
                "#onetrust-accept-btn-handler",
                "button#onetrust-accept-btn-handler",
                "button[data-testid='cookie-policy-manage-dialog-accept-button']",
            ],
            timeout_ms=800,
        ):
            return True

        return self._click_any_text(
            [
                "Accept Cookies",
                "Accept All Cookies",
                "Accept all cookies",
                "Accept",
                "I Agree",
                "Agree and Proceed",
            ],
            timeout_ms=800,
        )

    def _mute_zoom_microphone(self) -> None:
        self._click_any_selector(
            [
                "button[aria-label*='mute']",
                "button[aria-label*='Mute']",
                "button[aria-label*='microphone']",
                "button[aria-label*='Microphone']",
            ],
            timeout_ms=1_000,
        )
        self._click_any_text(["Mute", "Join without audio"], timeout_ms=1_000)

    def _fill_display_name(self, selectors: list[str], timeout_ms: int = 500) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=timeout_ms)
                locator.fill(self.display_name)
                return True
            except self.PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        return False

    def _click_any_label(self, labels: list[str], timeout_ms: int = 1_500) -> bool:
        for label in labels:
            try:
                button = self.page.get_by_label(label, exact=False).first
                button.click(timeout=timeout_ms)
                time.sleep(0.2)
                return True
            except Exception:
                continue
        return False

    def _click_any_selector(self, selectors: list[str], timeout_ms: int = 2_000) -> bool:
        for selector in selectors:
            try:
                self.page.locator(selector).first.click(timeout=timeout_ms)
                time.sleep(0.5)
                return True
            except Exception:
                continue
        return False

    def _click_any_text(self, labels: list[str], timeout_ms: int = 2_000) -> bool:
        for label in labels:
            try:
                button = self.page.get_by_role("button", name=label, exact=False).first
                button.click(timeout=timeout_ms)
                time.sleep(0.2)
                return True
            except Exception:
                try:
                    self.page.get_by_text(label, exact=False).first.click(timeout=timeout_ms)
                    time.sleep(0.2)
                    return True
                except Exception:
                    continue
        return False

    def _click_any_button_text(self, labels: list[str], timeout_ms: int = 1_000) -> bool:
        for label in labels:
            try:
                button = self.page.get_by_role("button", name=label, exact=False).first
                button.click(timeout=timeout_ms)
                time.sleep(0.1)
                return True
            except Exception:
                try:
                    link = self.page.get_by_role("link", name=label, exact=False).first
                    link.click(timeout=timeout_ms)
                    time.sleep(0.1)
                    return True
                except Exception:
                    continue
        return False

    def _has_visible_selector(self, selectors: list[str], timeout_ms: int = 150) -> bool:
        for selector in selectors:
            try:
                if self.page.locator(selector).first.is_visible(timeout=timeout_ms):
                    return True
            except Exception:
                continue
        return False

    def _looks_joined(self) -> bool:
        joined_labels = [
            "Leave",
            "Leave meeting",
            "Hang up",
            "End call",
            "More actions",
            "Participants",
        ]
        joined_selectors = [
            "button[data-tid='call-hangup']",
            "button[aria-label*='Leave']",
            "button[aria-label*='Hang up']",
            "button[aria-label*='Participants']",
        ]
        for selector in joined_selectors:
            try:
                if self.page.locator(selector).first.is_visible(timeout=150):
                    return True
            except Exception:
                continue

        for label in joined_labels:
            try:
                if self.page.get_by_label(label, exact=False).first.is_visible(timeout=150):
                    return True
            except Exception:
                continue

        return False

    def _looks_waiting_for_admission(self) -> bool:
        waiting_phrases = [
            "please wait",
            "host will let you in",
            "waiting for the host",
            "waiting for host",
            "when the meeting starts",
            *TEAMS_WAITING_ROOM_PHRASES,
        ]
        try:
            body_text = self.page.locator("body").inner_text(timeout=300).lower()
        except Exception:
            return False

        return any(phrase in body_text for phrase in waiting_phrases)

    def _looks_zoom_joining_screen(self) -> bool:
        if self.platform != "zoom":
            return False
        try:
            body_text = self.page.locator("body").inner_text(timeout=300).lower()
        except Exception:
            return False

        return "joining meeting" in body_text or "joining..." in body_text

    def _dismiss_browser_prompt(self) -> None:
        try:
            self.page.keyboard.press("Escape")
            time.sleep(0.2)
        except Exception:
            pass
        if sys.platform.startswith("win"):
            try:
                import ctypes

                user32 = ctypes.windll.user32
                user32.keybd_event(0x1B, 0, 0, 0)
                user32.keybd_event(0x1B, 0, 2, 0)
                time.sleep(0.1)
            except Exception:
                pass

    def _install_external_protocol_blocker(self) -> None:
        self.page.add_init_script(
            """
            (() => {
              const blockedSchemes = [
                "msteams:",
                "zoommtg:",
                "zoomus:",
                "zoomphonecall:"
              ];
              const isBlocked = (value) => {
                try {
                  const text = String(value || "").trim().toLowerCase();
                  return blockedSchemes.some((scheme) => text.startsWith(scheme));
                } catch (_) {
                  return false;
                }
              };
              const originalOpen = window.open;
              window.open = function(url, ...rest) {
                if (isBlocked(url)) {
                  return null;
                }
                return originalOpen.call(window, url, ...rest);
              };
              document.addEventListener("click", (event) => {
                const link = event.target && event.target.closest
                  ? event.target.closest("a[href]")
                  : null;
                if (link && isBlocked(link.href)) {
                  event.preventDefault();
                  event.stopImmediatePropagation();
                }
              }, true);
            })();
            """
        )

    def _prepare_bot_browser_profile(self) -> str:
        profile_dir = Path(__file__).resolve().parents[1] / ".meeting_bot_browser_profile"
        default_dir = profile_dir / "Default"
        default_dir.mkdir(parents=True, exist_ok=True)

        blocked_protocols = {
            "msteams": True,
            "zoommtg": True,
            "zoomus": True,
            "zoomphonecall": True,
        }
        for path in [profile_dir / "Local State", default_dir / "Preferences"]:
            data = self._read_json_file(path)
            protocol_handler = data.setdefault("protocol_handler", {})
            excluded_schemes = protocol_handler.setdefault("excluded_schemes", {})
            excluded_schemes.update(blocked_protocols)
            path.write_text(json.dumps(data), encoding="utf-8")

        return str(profile_dir)

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _normalize_meeting_url(
        meeting_url: str,
        platform: str,
        prefer_zoom_web_client_url: bool,
        display_name: str,
    ) -> str:
        if platform != "zoom" or not prefer_zoom_web_client_url:
            return meeting_url

        parsed = urllib.parse.urlparse(meeting_url)
        match = re.search(r"/(?:j|s|wc/join|wc)/(\d+)", parsed.path)
        if not match:
            return meeting_url

        meeting_id = match.group(1)
        encoded_name = base64.b64encode(display_name.encode("utf-8")).decode("ascii")
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        query["prefer"] = "1"
        query["un"] = encoded_name
        web_path = f"/wc/{meeting_id}/join"
        normalized = parsed._replace(
            path=web_path,
            query=urllib.parse.urlencode(query),
        )
        return urllib.parse.urlunparse(normalized)


def meeting_browser_has_ended(meeting_browser: Any) -> bool:
    return bool(meeting_browser and meeting_browser.meeting_has_ended())
