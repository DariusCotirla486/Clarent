from __future__ import annotations

import re
import time
import urllib.parse
from typing import Any


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
    ) -> None:
        self.meeting_url = self._normalize_meeting_url(meeting_url, platform)
        self.platform = platform
        self.display_name = display_name
        self.headless = headless
        self.browser_profile = browser_profile
        self.start_minimized = start_minimized
        self.grant_media_permissions = grant_media_permissions
        self.deny_media_permission_prompts = deny_media_permission_prompts
        self.block_native_app_prompts = block_native_app_prompts
        self.playwright: Any = None
        self.context: Any = None
        self.browser: Any = None
        self.page: Any = None
        self.join_attempted_at: float | None = None

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

        if self.browser_profile:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.browser_profile,
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
        for _ in range(3):
            self._dismiss_browser_prompt()
            if self._click_any_text(
                [
                    "Continue on this browser",
                    "Join on the web instead",
                    "Join on the web",
                    "Use the web app instead",
                ],
                timeout_ms=900,
            ):
                break
            time.sleep(0.5)

        self._fill_display_name(
            [
                "input[placeholder*='name']",
                "input[data-tid='prejoin-display-name-input']",
                "input[id*='username']",
            ]
        )
        self._click_any_label(["Turn off microphone", "Microphone"])
        self._click_any_label(["Turn off camera", "Camera"])
        self._click_any_text(["Join now", "Join"], timeout_ms=1_500)

    def _try_join_zoom(self) -> None:
        self._accept_cookies()
        for _ in range(2):
            self._dismiss_browser_prompt()
            self._click_any_text(
                [
                    "Cancel",
                    "Join from Your Browser",
                    "Join from your browser",
                    "Join from Browser",
                ],
                timeout_ms=900,
            )
            self._accept_cookies()
            time.sleep(0.5)

        self._fill_display_name(
            [
                "input#inputname",
                "input#input-for-name",
                "input[name='username']",
                "input[placeholder*='Your Name']",
                "input[placeholder*='name']",
                "input[aria-label*='Name']",
                "input[aria-label*='name']",
            ]
        )
        self._mute_zoom_microphone()
        self._click_any_text(["Join", "Join Meeting"], timeout_ms=1_500)

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

    def _fill_display_name(self, selectors: list[str]) -> None:
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=2_500)
                locator.fill(self.display_name)
                return
            except self.PlaywrightTimeoutError:
                continue
            except Exception:
                continue

    def _click_any_label(self, labels: list[str]) -> bool:
        for label in labels:
            try:
                button = self.page.get_by_label(label, exact=False).first
                button.click(timeout=1_500)
                time.sleep(0.5)
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
                time.sleep(1)
                return True
            except Exception:
                try:
                    self.page.get_by_text(label, exact=False).first.click(timeout=timeout_ms)
                    time.sleep(1)
                    return True
                except Exception:
                    continue
        return False

    def _dismiss_browser_prompt(self) -> None:
        try:
            self.page.keyboard.press("Escape")
            time.sleep(0.2)
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

    @staticmethod
    def _normalize_meeting_url(meeting_url: str, platform: str) -> str:
        if platform != "zoom":
            return meeting_url

        parsed = urllib.parse.urlparse(meeting_url)
        match = re.search(r"/(?:j|s)/(\d+)", parsed.path)
        if not match or "/wc/join/" in parsed.path:
            return meeting_url

        meeting_id = match.group(1)
        web_path = f"/wc/join/{meeting_id}"
        normalized = parsed._replace(path=web_path)
        return urllib.parse.urlunparse(normalized)


def meeting_browser_has_ended(meeting_browser: Any) -> bool:
    return bool(meeting_browser and meeting_browser.meeting_has_ended())
