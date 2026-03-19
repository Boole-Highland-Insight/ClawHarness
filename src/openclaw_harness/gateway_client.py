from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from time import perf_counter_ns, time
from typing import Any
from uuid import uuid4

import websockets

from .device_identity import DeviceIdentity, build_device_auth_payload_v3, sign_device_payload


class GatewayError(RuntimeError):
    """Raised when the gateway returns an error payload."""


@dataclass(slots=True)
class GatewayResponse:
    id: str
    ok: bool
    payload: dict[str, Any] | None
    error: Any


class GatewayClient:
    def __init__(
        self,
        *,
        url: str,
        token: str,
        role: str,
        instance_id: str,
        device_identity: DeviceIdentity | None = None,
    ) -> None:
        self.url = url
        self.token = token
        self.role = role
        self.instance_id = instance_id
        self.device_identity = device_identity
        self._ws: websockets.ClientConnection | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending: dict[str, asyncio.Future[GatewayResponse]] = {}
        self._challenge_nonce: asyncio.Future[str] | None = None

    async def connect(self) -> float:
        started = perf_counter_ns()
        loop = asyncio.get_running_loop()
        self._challenge_nonce = loop.create_future()
        self._ws = await websockets.connect(self.url, open_timeout=8, max_size=10_000_000)
        self._reader_task = asyncio.create_task(self._reader())
        nonce = await asyncio.wait_for(self._challenge_nonce, timeout=5)
        signed_at_ms = int(time() * 1000)
        client_id = "gateway-client"
        client_mode = "backend"
        platform = "linux"
        scopes = ["operator.admin"]
        device = None
        if self.device_identity is not None:
            payload = build_device_auth_payload_v3(
                device_id=self.device_identity.device_id,
                client_id=client_id,
                client_mode=client_mode,
                role=self.role,
                scopes=scopes,
                signed_at_ms=signed_at_ms,
                token=self.token,
                nonce=nonce,
                platform=platform,
                device_family=None,
            )
            device = {
                "id": self.device_identity.device_id,
                "publicKey": self.device_identity.public_key_raw,
                "signature": sign_device_payload(self.device_identity.private_key_pem, payload),
                "signedAt": signed_at_ms,
                "nonce": nonce,
            }
        response = await self.request(
            "connect",
            {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": client_id,
                    "displayName": "openclaw benchmark harness",
                    "version": "0.1.0",
                    "platform": platform,
                    "mode": client_mode,
                    "instanceId": self.instance_id,
                },
                "locale": "en-US",
                "userAgent": "openclaw-client-harness",
                "role": self.role,
                "scopes": scopes,
                "caps": [],
                "auth": {"token": self.token},
                "device": device,
            },
            timeout_ms=12_000,
        )
        if not response.ok:
            raise GatewayError(f"connect failed: {response.error}")
        return (perf_counter_ns() - started) / 1_000_000.0

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        self._ws = None
        self._reader_task = None
        if self._challenge_nonce is not None and not self._challenge_nonce.done():
            self._challenge_nonce.cancel()
        self._challenge_nonce = None
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_ms: int = 8_000,
    ) -> GatewayResponse:
        if self._ws is None:
            raise RuntimeError("gateway websocket is not connected")
        request_id = str(uuid4())
        frame = {"type": "req", "id": request_id, "method": method}
        if params is not None:
            frame["params"] = params
        loop = asyncio.get_running_loop()
        future: asyncio.Future[GatewayResponse] = loop.create_future()
        self._pending[request_id] = future
        await self._ws.send(json.dumps(frame))
        try:
            return await asyncio.wait_for(future, timeout_ms / 1000.0)
        finally:
            self._pending.pop(request_id, None)

    async def send_chat(
        self,
        *,
        session_key: str,
        message: str,
        run_id: str,
        timeout_ms: int,
    ) -> GatewayResponse:
        return await self.request(
            "chat.send",
            {
                "sessionKey": session_key,
                "message": message,
                "idempotencyKey": run_id,
                "timeoutMs": timeout_ms,
            },
            timeout_ms=timeout_ms + 5_000,
        )

    async def wait_for_agent(self, *, run_id: str, timeout_ms: int) -> GatewayResponse:
        return await self.request(
            "agent.wait",
            {
                "runId": run_id,
                "timeoutMs": timeout_ms,
            },
            timeout_ms=timeout_ms + 5_000,
        )

    async def load_history(self, *, session_key: str, limit: int) -> GatewayResponse:
        return await self.request(
            "chat.history",
            {
                "sessionKey": session_key,
                "limit": limit,
            },
            timeout_ms=12_000,
        )

    async def _reader(self) -> None:
        assert self._ws is not None
        try:
            async for raw_message in self._ws:
                if not isinstance(raw_message, str):
                    continue
                try:
                    payload = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "event":
                    if payload.get("event") == "connect.challenge":
                        event_payload = payload.get("payload")
                        nonce = ""
                        if isinstance(event_payload, dict):
                            raw_nonce = event_payload.get("nonce")
                            if isinstance(raw_nonce, str):
                                nonce = raw_nonce.strip()
                        if not nonce:
                            if self._challenge_nonce is not None and not self._challenge_nonce.done():
                                self._challenge_nonce.set_exception(
                                    GatewayError("connect challenge did not include a nonce"),
                                )
                            continue
                        if self._challenge_nonce is not None and not self._challenge_nonce.done():
                            self._challenge_nonce.set_result(nonce)
                    continue
                if payload.get("type") != "res":
                    continue
                request_id = str(payload.get("id", ""))
                pending = self._pending.get(request_id)
                if pending is None or pending.done():
                    continue
                pending.set_result(
                    GatewayResponse(
                        id=request_id,
                        ok=bool(payload.get("ok")),
                        payload=payload.get("payload"),
                        error=payload.get("error"),
                    ),
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if self._challenge_nonce is not None and not self._challenge_nonce.done():
                self._challenge_nonce.set_exception(exc)
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(exc)
