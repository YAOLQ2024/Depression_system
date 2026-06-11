from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BleTransportClient:
    def __init__(
        self,
        *,
        device_name_hint: str,
        notify_char_uuid: str,
        scan_seconds: float,
        reconnect_delay_seconds: float,
    ) -> None:
        self._device_name_hint = device_name_hint
        self._notify_char_uuid = notify_char_uuid
        self._scan_seconds = scan_seconds
        self._reconnect_delay_seconds = reconnect_delay_seconds

    @staticmethod
    def _device_name(device: Any) -> str:
        return str(getattr(device, "name", "") or "").strip()

    @staticmethod
    def _device_address(device: Any) -> str:
        return str(getattr(device, "address", "") or "").strip()

    def _matches_device_hint(self, device: Any, *, local_name: str | None = None) -> bool:
        hint = self._device_name_hint.strip()
        if not hint:
            return True
        normalized_hint = hint.upper()
        candidates = [
            self._device_name(device),
            str(local_name or "").strip(),
            self._device_address(device),
        ]
        return any(candidate and normalized_hint in candidate.upper() for candidate in candidates)

    async def _discover_devices(self, scanner_cls: Any) -> list[tuple[Any, str | None]]:
        try:
            discovered = await scanner_cls.discover(timeout=self._scan_seconds, return_adv=True)
        except TypeError:
            devices = await scanner_cls.discover(timeout=self._scan_seconds)
            return [(device, None) for device in devices]

        devices_with_names: list[tuple[Any, str | None]] = []
        for item in discovered.values():
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            device, advertisement = item
            local_name = str(getattr(advertisement, "local_name", "") or "").strip() or None
            devices_with_names.append((device, local_name))
        return devices_with_names

    def _build_not_found_error(self, scanned_devices: Sequence[tuple[Any, str | None]]) -> str:
        scan_count = len(scanned_devices)
        hint = self._device_name_hint.strip()
        unnamed_count = sum(
            1
            for device, local_name in scanned_devices
            if not self._device_name(device) and not str(local_name or "").strip()
        )
        if hint and scan_count > 0 and unnamed_count == scan_count:
            return (
                f"device_not_found: scan_count={scan_count}; "
                "all advertisements are unnamed; set EEG_DEVICE_NAME_HINT to the BLE address"
            )
        if hint:
            return f"device_not_found: hint={hint}; scan_count={scan_count}"
        return f"device_not_found: scan_count={scan_count}"

    async def _sleep_until_retry(self, stop_event: threading.Event) -> None:
        timeout = max(0.5, self._reconnect_delay_seconds)
        waited = 0.0
        while waited < timeout and not stop_event.is_set():
            step = min(0.5, timeout - waited)
            await asyncio.sleep(step)
            waited += step

    async def run_forever(
        self,
        *,
        stop_event: threading.Event,
        on_packet: Callable[[bytes, str | None, datetime], None],
        on_status: Callable[[str, str | None, str | None], None],
    ) -> None:
        try:
            from bleak import BleakClient, BleakScanner
        except Exception as exc:  # pragma: no cover - exercised in runtime env
            on_status("dependency_missing", None, str(exc))
            return

        while not stop_event.is_set():
            try:
                on_status("scanning", None, None)
                devices = await self._discover_devices(BleakScanner)
                target_device = None
                for device, local_name in devices:
                    if self._matches_device_hint(device, local_name=local_name):
                        target_device = device
                        break

                if target_device is None:
                    on_status("disconnected", None, self._build_not_found_error(devices))
                    await self._sleep_until_retry(stop_event)
                    continue

                address = self._device_address(target_device)
                on_status("connecting", address, None)

                def _handle_disconnect(_: Any) -> None:
                    on_status("disconnected", address, "device_disconnected")

                async with BleakClient(target_device, disconnected_callback=_handle_disconnect, timeout=15.0) as client:
                    on_status("connected", address, None)

                    def _handle_notification(_: Any, data: bytearray) -> None:
                        try:
                            on_packet(bytes(data), address, _utcnow())
                        except Exception:
                            logger.exception("EEG host bridge packet callback failed device_id=%s", address)

                    await client.start_notify(self._notify_char_uuid, _handle_notification)
                    on_status("streaming", address, None)
                    while not stop_event.is_set() and client.is_connected:
                        await asyncio.sleep(0.5)
                    try:
                        await client.stop_notify(self._notify_char_uuid)
                    except Exception:
                        logger.warning(
                            "EEG host bridge stop_notify failed device_id=%s",
                            address,
                            exc_info=True,
                        )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("EEG host bridge BLE loop failed")
                on_status("disconnected", None, str(exc))
                await self._sleep_until_retry(stop_event)

