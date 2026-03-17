#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


TARGET_FILE = "out/main/index.js"


def load_asar_header(asar_path: Path):
    with asar_path.open("rb") as f:
        f.seek(12)
        header_size = int.from_bytes(f.read(4), "little")
        f.seek(16)
        header = json.loads(f.read(header_size))
    return header_size, header


def get_file_meta(header: dict, path: str):
    cur = header
    for part in path.split("/"):
        cur = cur["files"][part]
    return cur


def read_file_from_asar(asar_path: Path, path: str) -> tuple[int, bytes]:
    header_size, header = load_asar_header(asar_path)
    meta = get_file_meta(header, path)
    offset = 16 + header_size + int(meta["offset"])
    with asar_path.open("rb") as f:
        f.seek(offset)
        data = f.read(meta["size"])
    return offset, data


def replace_section(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        raise RuntimeError(f"start marker not found: {start_marker}")
    end = text.find(end_marker, start)
    if end == -1:
        raise RuntimeError(f"end marker not found after {start_marker}: {end_marker}")
    return text[:start] + replacement + text[end:]


def patch_main_js(text: str) -> str:
    restart_gateway = """async function restartGateway(events, context) {
  debugLog(events, `restartGateway enter: ${restartContextLabel(context)}, usingExternalGateway=${usingExternalGateway}, hasLiveChild=${isGatewayProcessAlive()}`);
  stopping = false;
  await stopGateway();
  stopping = false;
  await startGateway(events);
  debugLog(events, "restartGateway completed");
}
"""

    force_restart_gateway = """async function forceRestartGateway(events, context) {
  events?.onLog?.("[GatewayManager] Force-restarting gateway...");
  debugLog(events, `forceRestartGateway enter: ${restartContextLabel(context)}, hasLiveChild=${isGatewayProcessAlive()}, usingExternalGateway=${usingExternalGateway}`);
  stopping = false;
  await stopGateway();
  stopping = false;
  gatewayProcess = null;
  embeddedGatewayToken = null;
  gatewayReady = false;
  gatewayStarting = false;
  usingExternalGateway = false;
  await startGateway(events);
  debugLog(events, "forceRestartGateway completed");
}
"""

    start_gateway = """async function startGateway(events) {
  if (stopping) return;
  const startAttemptId = ++startAttemptSeq;
  activeStartAttemptId = startAttemptId;
  debugLog(
    events,
    `startGateway enter: attempt=${startAttemptId}, pid=${process.pid}, platform=${process.platform}, app.isPackaged=${require$$1$3.app.isPackaged}, port=${GATEWAY_PORT}, healthUrl=${HEALTH_URL}, healthPollMs=${HEALTH_POLL_MS}, healthTimeoutMs=${HEALTH_TIMEOUT_MS}`
  );
  gatewayStarting = true;
  gatewayReady = false;
  lastStartError = null;
  recentStderr = [];
  embeddedGatewayToken = null;
  usingExternalGateway = false;
  const remoteModels = getRemoteModelList(events);
  sanitizeOpenclawConfig(events, remoteModels);
  syncSettingsCatalog(remoteModels, events);
  debugLog(events, "startGateway step=0a ensureBuiltinSkills");
  ensureBuiltinSkills(events);
  debugLog(events, "startGateway step=0b preRegisterDevice");
  preRegisterDevice(events);
  const alreadyRunning = await isGatewayAlreadyRunning(events);
  debugLog(events, `startGateway step=1 alreadyRunning=${alreadyRunning}`);
  if (alreadyRunning) {
    events?.onLog?.("[GatewayManager] Healthy gateway detected on port " + GATEWAY_PORT + ", using external gateway");
    debugLog(events, "startGateway external_gateway mode: skipping embedded gateway spawn");
    gatewayProcess = null;
    gatewayReady = true;
    gatewayStarting = false;
    usingExternalGateway = true;
    embeddedGatewayToken = null;
    events?.onReady?.();
    return;
  }
  gatewayProcess = null;
  gatewayReady = false;
  gatewayStarting = false;
  usingExternalGateway = false;
  embeddedGatewayToken = null;
  const msg = `[GatewayManager] External gateway is not available on port ${GATEWAY_PORT}; embedded gateway autostart is disabled.`;
  lastStartError = msg;
  events?.onError?.(msg);
  debugLog(events, `startGateway abort: ${msg}`);
}
"""

    updated = replace_section(
        text,
        "async function startGateway(events) {",
        "function stopGateway() {",
        start_gateway,
    )
    updated = replace_section(
        updated,
        "async function restartGateway(events, context) {",
        "async function forceRestartGateway(events, context) {",
        restart_gateway,
    )
    updated = replace_section(
        updated,
        "async function forceRestartGateway(events, context) {",
        "function waitForPortFree(events) {",
        force_restart_gateway,
    )
    return updated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("asar_path", type=Path)
    parser.add_argument("--backup", type=Path, required=False)
    args = parser.parse_args()

    asar_path = args.asar_path.expanduser().resolve()
    offset, raw = read_file_from_asar(asar_path, TARGET_FILE)
    original = raw.decode("utf-8")
    patched = patch_main_js(original)
    patched_bytes = patched.encode("utf-8")
    if len(patched_bytes) > len(raw):
        raise RuntimeError(f"patched file grew by {len(patched_bytes) - len(raw)} bytes; in-place patch unsafe")
    padded = patched_bytes + (b" " * (len(raw) - len(patched_bytes)))

    if args.backup:
        backup = args.backup.expanduser().resolve()
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(asar_path.read_bytes())

    with asar_path.open("r+b") as f:
        f.seek(offset)
        f.write(padded)

    print(f"Patched {asar_path}")
    print(f"Target: {TARGET_FILE}")
    print(f"Original size: {len(raw)}")
    print(f"Patched size: {len(patched_bytes)}")
    print(f"Padding bytes: {len(raw) - len(patched_bytes)}")


if __name__ == "__main__":
    main()
