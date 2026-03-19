from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any


HARNESS_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IDENTITY_PATH = HARNESS_ROOT / ".state" / "device.json"


@dataclass(slots=True)
class DeviceIdentity:
    device_id: str
    public_key_pem: str
    private_key_pem: str
    public_key_raw: str


def load_or_create_device_identity(path: Path | None = None) -> DeviceIdentity:
    identity_path = (path or DEFAULT_IDENTITY_PATH).resolve()
    if identity_path.exists():
        stored = _load_identity(identity_path)
        if stored is not None:
            return stored
    created = _generate_identity()
    _write_identity(identity_path, created)
    return created


def sign_device_payload(private_key_pem: str, payload: str) -> str:
    result = _run_node_script(
        r"""
const crypto = require("node:crypto");
const fs = require("node:fs");

function base64UrlEncode(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

const input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
const key = crypto.createPrivateKey(input.privateKeyPem);
const signature = crypto.sign(null, Buffer.from(input.payload, "utf8"), key);
process.stdout.write(JSON.stringify({ signature: base64UrlEncode(signature) }));
""",
        {"privateKeyPem": private_key_pem, "payload": payload},
    )
    signature = result.get("signature")
    if not isinstance(signature, str) or not signature:
        raise RuntimeError("node did not return a device signature")
    return signature


def build_device_auth_payload_v3(
    *,
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
    signed_at_ms: int,
    token: str | None,
    nonce: str,
    platform: str | None,
    device_family: str | None,
) -> str:
    return "|".join(
        [
            "v3",
            device_id,
            client_id,
            client_mode,
            role,
            ",".join(scopes),
            str(signed_at_ms),
            token or "",
            nonce,
            _normalize_device_metadata(platform),
            _normalize_device_metadata(device_family),
        ],
    )


def _load_identity(path: Path) -> DeviceIdentity | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    public_key_pem = raw.get("publicKeyPem")
    private_key_pem = raw.get("privateKeyPem")
    if not isinstance(public_key_pem, str) or not isinstance(private_key_pem, str):
        return None
    public_key_raw = raw.get("publicKeyRaw")
    if not isinstance(public_key_raw, str) or not public_key_raw:
        public_key_raw = _derive_public_key_raw(public_key_pem)
    device_id = _device_id_from_public_key_raw(public_key_raw)
    stored_device_id = raw.get("deviceId")
    identity = DeviceIdentity(
        device_id=device_id,
        public_key_pem=public_key_pem,
        private_key_pem=private_key_pem,
        public_key_raw=public_key_raw,
    )
    if stored_device_id != device_id or raw.get("publicKeyRaw") != public_key_raw:
        _write_identity(path, identity)
    return identity


def _generate_identity() -> DeviceIdentity:
    result = _run_node_script(
        r"""
const crypto = require("node:crypto");

function base64UrlEncode(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

const prefix = Buffer.from("302a300506032b6570032100", "hex");
const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
const publicKeyPem = publicKey.export({ type: "spki", format: "pem" }).toString();
const privateKeyPem = privateKey.export({ type: "pkcs8", format: "pem" }).toString();
const spki = publicKey.export({ type: "spki", format: "der" });
const publicKeyRaw =
  spki.length === prefix.length + 32 && spki.subarray(0, prefix.length).equals(prefix)
    ? spki.subarray(prefix.length)
    : spki;

process.stdout.write(
  JSON.stringify({
    publicKeyPem,
    privateKeyPem,
    publicKeyRaw: base64UrlEncode(publicKeyRaw),
  }),
);
""",
        {},
    )
    public_key_pem = result.get("publicKeyPem")
    private_key_pem = result.get("privateKeyPem")
    public_key_raw = result.get("publicKeyRaw")
    if not isinstance(public_key_pem, str) or not isinstance(private_key_pem, str):
        raise RuntimeError("node did not return a usable device identity")
    if not isinstance(public_key_raw, str) or not public_key_raw:
        raise RuntimeError("node did not return the raw device public key")
    return DeviceIdentity(
        device_id=_device_id_from_public_key_raw(public_key_raw),
        public_key_pem=public_key_pem,
        private_key_pem=private_key_pem,
        public_key_raw=public_key_raw,
    )


def _derive_public_key_raw(public_key_pem: str) -> str:
    result = _run_node_script(
        r"""
const crypto = require("node:crypto");
const fs = require("node:fs");

function base64UrlEncode(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

const prefix = Buffer.from("302a300506032b6570032100", "hex");
const input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
const key = crypto.createPublicKey(input.publicKeyPem);
const spki = key.export({ type: "spki", format: "der" });
const publicKeyRaw =
  spki.length === prefix.length + 32 && spki.subarray(0, prefix.length).equals(prefix)
    ? spki.subarray(prefix.length)
    : spki;

process.stdout.write(JSON.stringify({ publicKeyRaw: base64UrlEncode(publicKeyRaw) }));
""",
        {"publicKeyPem": public_key_pem},
    )
    public_key_raw = result.get("publicKeyRaw")
    if not isinstance(public_key_raw, str) or not public_key_raw:
        raise RuntimeError("node did not return the raw device public key")
    return public_key_raw


def _device_id_from_public_key_raw(public_key_raw: str) -> str:
    return hashlib.sha256(_base64url_decode(public_key_raw)).hexdigest()


def _write_identity(path: Path, identity: DeviceIdentity) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "deviceId": identity.device_id,
        "publicKeyPem": identity.public_key_pem,
        "privateKeyPem": identity.private_key_pem,
        "publicKeyRaw": identity.public_key_raw,
        "createdAtMs": int(time() * 1000),
    }
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _base64url_decode(value: str) -> bytes:
    normalized = value.replace("-", "+").replace("_", "/")
    padded = normalized + ("=" * ((4 - len(normalized) % 4) % 4))
    return base64.b64decode(padded)


def _normalize_device_metadata(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def _run_node_script(script: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"node helper failed: {result.stderr.strip() or result.stdout.strip()}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"node helper returned invalid JSON: {result.stdout!r}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("node helper returned a non-object payload")
    return parsed
