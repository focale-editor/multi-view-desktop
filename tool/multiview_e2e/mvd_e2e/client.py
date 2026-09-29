"""HTTP client for the example app E2E harness (POST /rpc)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

# Mirrors example ViewAnimationConfig open/close (150ms) + harness pad (120ms).
DEFAULT_OPEN_SETTLE_MS = 270
DEFAULT_CLOSE_SETTLE_MS = 270


class E2eError(RuntimeError):
    pass


class MvdE2eClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9876",
        timeout: float = 60.0,
        *,
        open_settle_ms: int = DEFAULT_OPEN_SETTLE_MS,
        close_settle_ms: int = DEFAULT_CLOSE_SETTLE_MS,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.open_settle_ms = open_settle_ms
        self.close_settle_ms = close_settle_ms

    def wait_ready(self, timeout: float = 60.0, interval: float = 0.25) -> None:
        deadline = time.time() + timeout
        last: Exception | None = None
        while time.time() < deadline:
            try:
                self.health()
                return
            except Exception as exc:  # noqa: BLE001 — poll until up
                last = exc
                time.sleep(interval)
        raise E2eError(f"Harness not ready at {self.base_url}: {last}")

    def health(self) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def call(self, method: str, **params: Any) -> Any:
        payload = json.dumps({"method": method, "params": params}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/rpc",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError as decode_exc:
                raise E2eError(f"HTTP {exc.code}: {raw}") from decode_exc
            raise E2eError(body.get("error") or raw) from exc

        if not body.get("ok"):
            raise E2eError(body.get("error") or str(body))
        return body.get("result")

    def _with_settle(
        self,
        params: dict[str, Any],
        *,
        default_settle: int,
        animation_ms: int | None,
        settle_ms: int | None,
    ) -> dict[str, Any]:
        out = dict(params)
        if animation_ms is not None:
            out["animationMs"] = animation_ms
        if settle_ms is not None:
            out["settleMs"] = settle_ms
        elif "settleMs" not in out:
            # Server adds pad if only animationMs set; if neither, pass default settle.
            if animation_ms is None:
                out["settleMs"] = default_settle
        return out

    # ---- convenience wrappers ----

    def ping(self) -> dict[str, Any]:
        return self.call("ping")

    def snapshot(self) -> dict[str, Any]:
        return self.call("snapshot")

    def get_window_state(self, view_id: int) -> dict[str, Any]:
        return dict(self.call("get_window_state", viewId=view_id))

    def create_window(
        self,
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
        **kwargs: Any,
    ) -> int:
        params = self._with_settle(
            kwargs,
            default_settle=self.open_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return int(self.call("create_window", **params)["viewId"])

    def create_window_full(
        self,
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        params = self._with_settle(
            kwargs,
            default_settle=self.open_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return dict(self.call("create_window", **params))

    def create_windows(
        self,
        count: int,
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
        **kwargs: Any,
    ) -> list[int]:
        params = self._with_settle(
            {"count": count, **kwargs},
            default_settle=self.open_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return [int(x) for x in self.call("create_windows", **params)["viewIds"]]

    def close_window(
        self,
        view_id: int,
        *,
        confirm_close: bool | None = None,
        confirm_timeout_ms: int | None = None,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
    ) -> bool:
        params: dict[str, Any] = {"viewId": view_id}
        if confirm_close is not None:
            params["confirmClose"] = confirm_close
        if confirm_timeout_ms is not None:
            params["confirmTimeoutMs"] = confirm_timeout_ms
        params = self._with_settle(
            params,
            default_settle=self.close_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return bool(self.call("close_window", **params)["closed"])

    def answer_close_confirm(
        self,
        *,
        accept: bool,
        timeout_ms: int | None = None,
    ) -> bool:
        params: dict[str, Any] = {"accept": accept}
        if timeout_ms is not None:
            params["timeoutMs"] = timeout_ms
        return bool(self.call("answer_close_confirm", **params)["answered"])

    def close_windows(
        self,
        view_ids: list[int],
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        params = self._with_settle(
            {"viewIds": view_ids},
            default_settle=self.close_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return list(self.call("close_windows", **params)["results"])

    def set_window_flags(self, view_id: int, **flags: Any) -> dict[str, Any]:
        return dict(self.call("set_window_flags", viewId=view_id, **flags))

    def set_close_mode(self, mode: str) -> str:
        return str(self.call("set_close_mode", mode=mode)["closeMode"])

    def close_app(
        self,
        mode: str | None = None,
        *,
        confirm_close: bool | None = None,
        confirm_timeout_ms: int | None = None,
    ) -> bool:
        params: dict[str, Any] = {}
        if mode is not None:
            params["mode"] = mode
        if confirm_close is not None:
            params["confirmClose"] = confirm_close
        if confirm_timeout_ms is not None:
            params["confirmTimeoutMs"] = confirm_timeout_ms
        return bool(self.call("close_app", **params)["allClosed"])

    def set_prevent_close(self, view_id: int, value: bool) -> None:
        self.call("set_prevent_close", viewId=view_id, value=value)

    def cancel_cascade(self, view_id: int) -> None:
        self.call("cancel_cascade", viewId=view_id)

    def open_os_dialog(
        self,
        parent_id: int,
        *,
        modal: bool = True,
        title: str | None = None,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
        **kwargs: Any,
    ) -> int:
        params: dict[str, Any] = {"parentId": parent_id, "modal": modal, **kwargs}
        if title is not None:
            params["title"] = title
        params = self._with_settle(
            params,
            default_settle=self.open_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return int(self.call("open_os_dialog", **params)["dialogId"])

    def open_os_dialog_full(
        self,
        parent_id: int,
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        params = self._with_settle(
            {"parentId": parent_id, **kwargs},
            default_settle=self.open_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return dict(self.call("open_os_dialog", **params))

    def close_dialog(
        self,
        dialog_id: int,
        result: str | None = "ok",
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
    ) -> bool:
        params: dict[str, Any] = {"dialogId": dialog_id}
        if result is not None:
            params["result"] = result
        params = self._with_settle(
            params,
            default_settle=self.close_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return bool(self.call("close_dialog", **params)["closed"])

    def open_overlay_dialog(
        self,
        parent_id: int,
        *,
        settle_ms: int | None = None,
    ) -> None:
        params = self._with_settle(
            {"parentId": parent_id},
            default_settle=self.open_settle_ms,
            animation_ms=None,
            settle_ms=settle_ms,
        )
        self.call("open_overlay_dialog", **params)

    def open_popup(
        self,
        parent_id: int,
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
    ) -> None:
        params = self._with_settle(
            {"parentId": parent_id},
            default_settle=self.open_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        self.call("open_popup", **params)

    def close_popup(
        self,
        parent_id: int,
        *,
        animation_ms: int | None = None,
        settle_ms: int | None = None,
    ) -> bool:
        params = self._with_settle(
            {"parentId": parent_id},
            default_settle=self.close_settle_ms,
            animation_ms=animation_ms,
            settle_ms=settle_ms,
        )
        return bool(self.call("close_popup", **params)["closed"])

    def wait_ms(self, ms: int) -> None:
        self.call("wait_ms", ms=ms)

    def wait_open_settle(self, settle_ms: int | None = None) -> None:
        self.call("wait_open_settle", settleMs=settle_ms or self.open_settle_ms)

    def wait_close_settle(self, settle_ms: int | None = None) -> None:
        self.call("wait_close_settle", settleMs=settle_ms or self.close_settle_ms)

    def assert_alive(self) -> None:
        self.ping()

    def primary_window_id(self) -> int:
        windows = self.snapshot()["windows"]
        assert windows, "expected at least the primary window"
        return int(windows[0])
