import sys
import os
import time
import datetime
import collections
import threading
import queue
import argparse
import json
import ssl
import urllib.request
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
import sounddevice as sd
import webrtcvad
import psutil

# Audio settings
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000.0))  # 480 samples
CHUNK_BYTES = FRAME_SIZE * 2  # 960 bytes


def channels_for_device(device_index) -> int:
    """How many input channels to open for the selected device.

    For an Aggregate Device (mic + BlackHole) this is >1, so we capture every
    channel and mix them to mono — that's how we hear BOTH sides of a call.
    """
    try:
        info = sd.query_devices(device_index if device_index is not None else None, 'input')
        ch = int(info.get('max_input_channels', 1) or 1)
        return max(1, min(ch, 8))
    except Exception:
        return 1


def mix_to_mono_bytes(frame) -> bytes:
    """Downmix a captured int16 frame (samples x channels) to mono 16-bit PCM.

    We SUM channels (with clipping) rather than average, so loudness is
    preserved when some channels are silent (e.g. mic active + BlackHole idle
    when in-person), while still capturing the remote party when BlackHole
    carries the call's audio.
    """
    arr = np.asarray(frame)
    if arr.ndim == 1:
        mono = arr
    elif arr.shape[1] == 1:
        mono = arr[:, 0]
    else:
        mono = np.clip(arr.astype(np.int32).sum(axis=1), -32768, 32767).astype(np.int16)
    return np.ascontiguousarray(mono.astype('<i2')).tobytes()


def channel_energy(frame) -> np.ndarray:
    """Per-channel acoustic energy (sum of squares) for a captured int16 frame.

    Used to attribute an utterance to the louder source on a multi-channel
    aggregate device — e.g. your mic vs. the remote call audio on BlackHole —
    so we can label utterances "You" vs "Guest" on a call.
    """
    arr = np.asarray(frame)
    if arr.ndim == 1:
        arr = arr[:, None]
    sq = arr.astype(np.float64) ** 2
    return sq.sum(axis=0)  # shape: (channels,)


def parse_channel_set(env_value: str, default: List[int]) -> List[int]:
    """Parses a comma-separated channel list like '0' or '1,2' from env."""
    if not env_value:
        return default
    out = []
    for tok in env_value.split(","):
        tok = tok.strip()
        if tok.isdigit():
            out.append(int(tok))
    return out or default
SILENCE_DURATION_S = 0.6
SILENCE_FRAMES_THRESHOLD = int(SILENCE_DURATION_S / (FRAME_DURATION_MS / 1000.0))  # 20 frames
MIN_SPEECH_FRAMES = 3
MIN_UTTERANCE_S = 0.3
MIN_UTTERANCE_FRAMES = int(MIN_UTTERANCE_S / (FRAME_DURATION_MS / 1000.0))

# Lifecycle & Detection settings
APP_POLL_INTERVAL_S = 4.0
SUSTAINED_SPEECH_TRIGGER_S = 5.0
SUSTAINED_SPEECH_FRAMES = int(SUSTAINED_SPEECH_TRIGGER_S / (FRAME_DURATION_MS / 1000.0))  # ~167 frames
SILENCE_TIMEOUT_S = 90.0
PREFERRED_DEVICE_KEYWORDS = ["understudy", "aggregate", "blackhole"]
MEETING_APP_PATTERNS = ["zoom", "microsoft teams", "teams", "webex", "cisco webex"]


def get_ssl_context() -> ssl.SSLContext:
    """Creates an SSL context using certifi CA bundle if available."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


SSL_CONTEXT = get_ssl_context()


def post_json(endpoint: str, payload: dict, timeout: float = 3.0) -> Optional[dict]:
    """Posts JSON payload to the agent server using certifi SSL context."""
    server_url = os.getenv("AGENT_SERVER_URL", "http://localhost:8000").rstrip("/")
    url = f"{server_url}/{endpoint.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except Exception:
        return None


def get_json(endpoint: str, timeout: float = 2.0) -> Optional[dict]:
    """GETs JSON from the agent server using certifi SSL context."""
    server_url = os.getenv("AGENT_SERVER_URL", "http://localhost:8000").rstrip("/")
    url = f"{server_url}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except Exception:
        return None


_capture_cache = {"active": False, "at": 0.0}

def is_capturing(meeting_id: str) -> bool:
    """Polls the backend capture flag (cached ~1s). Muted (False) by default so
    small talk before/after the meeting is never transcribed. On error, keeps the
    last known value."""
    now = time.monotonic()
    if now - _capture_cache["at"] < 1.0:
        return _capture_cache["active"]
    mid = meeting_id or os.getenv("MEETING_ID", "demo-meeting")
    res = get_json(f"/meetings/{mid}/capture")
    if res is not None and "active" in res:
        _capture_cache["active"] = bool(res["active"])
    _capture_cache["at"] = now
    return _capture_cache["active"]


def on_utterance(text: str, meeting_id: Optional[str] = None, speaker: str = "Speaker"):
    """Called when a finalized utterance is transcribed."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    mid = meeting_id or os.getenv("MEETING_ID", "demo-meeting")
    endpoint = f"/meetings/{mid}/utterance"
    payload = {"speaker": speaker, "text": text, "ts": timestamp}
    res = post_json(endpoint, payload)
    if res is not None:
        print(f"[{timestamp}] (Server Synced) {text}")
    else:
        print(f"[{timestamp}] {text}")


def get_input_devices() -> List[Tuple[int, Dict[str, Any]]]:
    """Returns a list of (device_index, device_dict) for all devices with max_input_channels > 0."""
    try:
        devices = sd.query_devices()
    except Exception as e:
        print(f"Error querying audio devices: {e}", file=sys.stderr)
        return []

    input_devs = []
    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            input_devs.append((idx, dev))
    return input_devs


def list_input_devices():
    """Prints all available audio input devices and exits."""
    input_devs = get_input_devices()
    print("Available Audio Input Devices:")
    if not input_devs:
        print("  (No input devices found)")
        return

    default_idx = None
    try:
        if sd.default.device and sd.default.device[0] is not None:
            default_idx = sd.default.device[0]
    except Exception:
        pass

    for idx, dev in input_devs:
        is_default = " (default)" if (idx == default_idx) else ""
        channels = dev.get("max_input_channels", 1)
        name = dev.get("name", "Unknown")
        print(f"  [{idx}] {name} ({channels} in){is_default}")


def resolve_input_device(device_query: Optional[str] = None) -> Tuple[Optional[int], str]:
    """Resolves which input device to use based on:
    1. Explicit argument or AUDIO_DEVICE env var (substring match).
    2. Auto-prefer device containing 'Understudy', 'Aggregate', or 'BlackHole'.
    3. Fallback to default input device (microphone).
    Returns (device_index, device_name).
    """
    input_devs = get_input_devices()
    if not input_devs:
        print("[Audio] Warning: No audio input devices found. Using system default.", file=sys.stderr)
        return None, "Default"

    # 1. Explicit override or AUDIO_DEVICE env var
    query = (device_query or os.getenv("AUDIO_DEVICE", "")).strip()
    if query:
        if query.isdigit():
            idx_int = int(query)
            for idx, dev in input_devs:
                if idx == idx_int:
                    dev_name = dev.get("name", f"Device {idx}")
                    print(f"[Audio] Selected input device [{idx}]: {dev_name} (index match)")
                    return idx, dev_name

        query_lower = query.lower()
        for idx, dev in input_devs:
            if query_lower in dev.get("name", "").lower():
                dev_name = dev.get("name", f"Device {idx}")
                print(f"[Audio] Selected input device [{idx}]: {dev_name} (matched '{query}')")
                return idx, dev_name
        print(f"[Audio] Warning: No input device matched '{query}'. Falling back to auto-selection.", file=sys.stderr)

    # 2. Auto-prefer Understudy, Aggregate, or BlackHole
    for idx, dev in input_devs:
        dev_name_lower = dev.get("name", "").lower()
        if any(pref in dev_name_lower for pref in PREFERRED_DEVICE_KEYWORDS):
            dev_name = dev.get("name", f"Device {idx}")
            print(f"[Audio] Selected system-audio device [{idx}]: {dev_name} (auto-preferred)")
            return idx, dev_name

    # 3. Default input device
    default_idx = None
    try:
        if sd.default.device and sd.default.device[0] is not None:
            default_idx = sd.default.device[0]
    except Exception:
        pass

    if default_idx is not None:
        for idx, dev in input_devs:
            if idx == default_idx:
                dev_name = dev.get("name", f"Device {idx}")
                print(f"[Audio] Selected default input device [{idx}]: {dev_name}")
                return idx, dev_name

    # Fallback to first available input device
    first_idx, first_dev = input_devs[0]
    first_name = first_dev.get("name", f"Device {first_idx}")
    print(f"[Audio] Selected fallback input device [{first_idx}]: {first_name}")
    return first_idx, first_name


def detect_meeting_app() -> Tuple[bool, Optional[str]]:
    """Detects running meeting apps via psutil process names/cmdlines.
    Returns (is_running, app_name_or_none).
    """
    for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
        try:
            name = (proc.info.get('name') or '').lower()
            exe = (proc.info.get('exe') or '').lower()
            
            for pattern in MEETING_APP_PATTERNS:
                if pattern in name or pattern in exe:
                    return True, proc.info.get('name') or pattern
            
            cmdline = proc.info.get('cmdline')
            if cmdline:
                cmd_str = " ".join(cmdline).lower()
                for pattern in MEETING_APP_PATTERNS:
                    if pattern in cmd_str:
                        return True, proc.info.get('name') or pattern
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    return False, None


def start_meeting_lifecycle(reason: str) -> str:
    """Generates a new timestamped meeting_id and issues POST /meetings/{id}/start."""
    meeting_id = os.getenv("MEETING_ID_FIXED") or datetime.datetime.now().strftime("meeting-%Y%m%d-%H%M%S")
    os.environ["MEETING_ID"] = meeting_id
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [State Transition] ARMED -> IN MEETING ({meeting_id}) [Reason: {reason}]")
    payload = {
        "title": f"Meeting {datetime.datetime.now().strftime('%b %d %H:%M')}",
        "status": "live",
        "startedAt": timestamp,
    }
    res = post_json(f"/meetings/{meeting_id}/start", payload)
    if res is not None:
        print(f"[{timestamp}] [Server Synced] Started meeting session: {meeting_id}")
    return meeting_id


def end_meeting_lifecycle(meeting_id: str, reason: str):
    """Issues POST /meetings/{id}/end and logs transition back to ARMED."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [State Transition] IN MEETING ({meeting_id}) -> ENDED [Reason: {reason}]")
    res = post_json(f"/meetings/{meeting_id}/end", {})
    if res is not None:
        print(f"[{timestamp}] [Server Synced] Ended meeting session: {meeting_id}")
    print(f"[{timestamp}] [State Transition] ENDED -> ARMED")


# Whisper commonly hallucinates these short phrases on silence / low-energy
# audio (end-of-utterance tails, room noise). Drop them so they never post.
_HALLUCINATION_PHRASES = {
    "bye", "bye bye", "goodbye", "thank you", "thanks", "thank you very much",
    "thanks for watching", "thank you for watching", "please subscribe",
    "you", "okay", "ok", "so", "yeah", "hmm", "mm", "uh", "um", "peace",
    "the end", "see you", "see you next time", "have a good one",
}


def _is_hallucination(text: str) -> bool:
    """True if a transcript is just a known Whisper silence-hallucination."""
    norm = "".join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()
    return norm in _HALLUCINATION_PHRASES


def transcription_worker(q: queue.Queue, model_name: str = "base.en"):
    """Background worker that continuously transcribes audio buffers."""
    print(f"Loading faster-whisper model ({model_name})...")
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    print("Model loaded. Ready to transcribe.")
    
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
            
        try:
            speaker = "Speaker"
            if isinstance(item, tuple):
                if len(item) == 3:
                    buffer, meeting_id, speaker = item
                else:
                    buffer, meeting_id = item
            else:
                buffer = item
                meeting_id = None

            if len(buffer) < MIN_UTTERANCE_FRAMES:
                continue

            audio_data = b"".join(buffer)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            segments, _ = model.transcribe(
                audio_np,
                beam_size=5,
                language="en",
                condition_on_previous_text=False,
                vad_filter=True,
                no_speech_threshold=0.6,
                log_prob_threshold=-1.0,
            )
            # Keep only segments the model is confident are real speech — this
            # drops silence segments that would otherwise hallucinate "Bye" etc.
            text = "".join(
                s.text for s in segments if getattr(s, "no_speech_prob", 0.0) < 0.6
            ).strip()

            if text and not _is_hallucination(text):
                on_utterance(text, meeting_id, speaker)
            elif text:
                print(f"[filtered hallucination] {text!r}", file=sys.stderr)
        except Exception as e:
            print(f"Transcription error: {e}", file=sys.stderr)
        finally:
            q.task_done()


def listen_manual(device_index: Optional[int], model_name: str = "base.en"):
    """Continuous manual capture mode (no auto-lifecycle / auto-detection)."""
    vad = webrtcvad.Vad(2)
    transcription_queue = queue.Queue()
    worker = threading.Thread(
        target=transcription_worker, 
        args=(transcription_queue, model_name), 
        daemon=True
    )
    worker.start()

    meeting_id = os.getenv("MEETING_ID", "demo-meeting")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Manual mode active for meeting: {meeting_id}")
    print("Listening... (Press Ctrl+C to stop)")

    # Speaker attribution for calls: your mic vs the remote party on BlackHole.
    # On a multi-channel aggregate device, YOU_CHANNELS carry your mic and the
    # rest carry the call audio, so we label the louder source "You" vs "Guest".
    n_ch = channels_for_device(device_index)
    you_channels = parse_channel_set(os.getenv("SPEAKER_YOU_CHANNELS", ""), [0])
    you_channels = [c for c in you_channels if c < n_ch]
    guest_channels = [c for c in range(n_ch) if c not in you_channels]
    diarize = len(guest_channels) > 0
    if diarize:
        print(f"[Audio] Speaker labels ON — You=ch{you_channels}, Guest=ch{guest_channels}")

    audio_buffer = []
    recent_frames = collections.deque(maxlen=MIN_SPEECH_FRAMES)
    silence_frames = 0
    consecutive_speech_frames = 0
    in_speech = False
    was_capturing = None
    you_energy = 0.0
    guest_energy = 0.0

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            dtype='int16',
            channels=channels_for_device(device_index),
            device=device_index,
            callback=None
        ) as stream:
            while True:
                frame_data, overflowed = stream.read(FRAME_SIZE)
                if overflowed:
                    print("Warning: Audio buffer overflow", file=sys.stderr)

                # Mute gate: when capture is paused, drop audio entirely (no VAD,
                # no buffering, no transcription) so small talk is never recorded.
                capturing = is_capturing(meeting_id)
                if capturing != was_capturing:
                    ts_now = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts_now}] {'● RECORDING' if capturing else '⏸ PAUSED (muted)'}")
                    was_capturing = capturing
                if not capturing:
                    if in_speech or audio_buffer:
                        audio_buffer = []
                        in_speech = False
                        silence_frames = 0
                        consecutive_speech_frames = 0
                    recent_frames.clear()
                    continue

                raw_bytes = mix_to_mono_bytes(frame_data)

                # Per-frame energy split (for You/Guest attribution on a call).
                frame_you = frame_guest = 0.0
                if diarize:
                    e = channel_energy(frame_data)
                    if e.shape[0] >= n_ch:
                        frame_you = float(sum(e[c] for c in you_channels))
                        frame_guest = float(sum(e[c] for c in guest_channels))

                try:
                    is_speech = vad.is_speech(raw_bytes, SAMPLE_RATE)
                except Exception as e:
                    print(f"VAD error: {e}", file=sys.stderr)
                    continue

                if is_speech:
                    consecutive_speech_frames += 1
                    recent_frames.append(raw_bytes)
                    if not in_speech and consecutive_speech_frames >= MIN_SPEECH_FRAMES:
                        in_speech = True
                        you_energy = 0.0
                        guest_energy = 0.0
                        audio_buffer.extend(recent_frames)
                    elif in_speech:
                        audio_buffer.append(raw_bytes)
                    if in_speech:
                        you_energy += frame_you
                        guest_energy += frame_guest
                    silence_frames = 0
                else:
                    consecutive_speech_frames = 0
                    recent_frames.append(raw_bytes)
                    if in_speech:
                        audio_buffer.append(raw_bytes)
                        silence_frames += 1
                        if silence_frames > SILENCE_FRAMES_THRESHOLD:
                            speaker = "Speaker"
                            if diarize:
                                speaker = "You" if you_energy >= guest_energy else "Guest"
                            transcription_queue.put((audio_buffer, meeting_id, speaker))
                            audio_buffer = []
                            in_speech = False
                            silence_frames = 0
    except KeyboardInterrupt:
        print("\nStopping listener. Draining transcription queue...")
    except Exception as e:
        print(f"\nListener error: {e}", file=sys.stderr)
    finally:
        transcription_queue.put(None)
        worker.join()
        print("Listener stopped cleanly.")


def listen_auto(device_index: Optional[int], model_name: str = "base.en"):
    """Automatic meeting lifecycle listener.
    Starts in ARMED state, polls for meeting apps (~every 4s) or sustained speech (>5s),
    auto-starts meeting, transcribes speech, and auto-ends on meeting app close or >90s silence.
    """
    vad = webrtcvad.Vad(2)
    transcription_queue = queue.Queue()
    worker = threading.Thread(
        target=transcription_worker, 
        args=(transcription_queue, model_name), 
        daemon=True
    )
    worker.start()

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Listener started in ARMED state. Waiting for meeting app or speech...")
    print("Listening... (Press Ctrl+C to stop)")

    state = "ARMED"  # "ARMED" or "IN_MEETING"
    current_meeting_id: Optional[str] = None
    meeting_app_was_detected = False
    last_app_poll_time = 0.0
    last_speech_time = time.time()

    # VAD & buffering state
    audio_buffer = []
    recent_frames = collections.deque(maxlen=MIN_SPEECH_FRAMES)
    silence_frames = 0
    consecutive_speech_frames = 0
    in_speech = False

    # Armed sustained-speech tracking
    armed_speech_frames = 0
    armed_silence_frames = 0
    armed_audio_buffer = []

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            dtype='int16',
            channels=channels_for_device(device_index),
            device=device_index,
            callback=None
        ) as stream:
            while True:
                frame_data, overflowed = stream.read(FRAME_SIZE)
                if overflowed:
                    print("Warning: Audio buffer overflow", file=sys.stderr)

                raw_bytes = mix_to_mono_bytes(frame_data)
                try:
                    is_speech = vad.is_speech(raw_bytes, SAMPLE_RATE)
                except Exception as e:
                    print(f"VAD error: {e}", file=sys.stderr)
                    continue

                now = time.time()

                # Periodic app polling (~every 4s)
                poll_due = (now - last_app_poll_time >= APP_POLL_INTERVAL_S)
                app_running = False
                app_name = None
                if poll_due:
                    app_running, app_name = detect_meeting_app()
                    last_app_poll_time = now

                # ----------------------------------------------------
                # STATE: ARMED
                # ----------------------------------------------------
                if state == "ARMED":
                    # Check 1: Running meeting app detected
                    if poll_due and app_running:
                        current_meeting_id = start_meeting_lifecycle(reason=f"Meeting app '{app_name}' detected")
                        meeting_app_was_detected = True
                        state = "IN_MEETING"
                        last_speech_time = now
                        in_speech = False
                        audio_buffer = []
                        recent_frames.clear()
                        silence_frames = 0
                        consecutive_speech_frames = 0
                        armed_speech_frames = 0
                        armed_silence_frames = 0
                        armed_audio_buffer = []
                        continue

                    # Check 2: Sustained speech detected (> 5s)
                    if is_speech:
                        armed_speech_frames += 1
                        armed_silence_frames = 0
                        armed_audio_buffer.append(raw_bytes)

                        if armed_speech_frames >= SUSTAINED_SPEECH_FRAMES:
                            current_meeting_id = start_meeting_lifecycle(reason="Sustained speech detected (>5s)")
                            meeting_app_was_detected = False
                            state = "IN_MEETING"
                            last_speech_time = now
                            in_speech = True
                            # Preserve speech from the 5s trigger window
                            audio_buffer = list(armed_audio_buffer)
                            recent_frames.clear()
                            consecutive_speech_frames = MIN_SPEECH_FRAMES
                            silence_frames = 0
                            armed_speech_frames = 0
                            armed_silence_frames = 0
                            armed_audio_buffer = []
                    else:
                        if armed_speech_frames > 0:
                            armed_silence_frames += 1
                            # If silent for > 1.2s while accumulating sustained speech in ARMED, reset
                            if armed_silence_frames > int(1.2 / (FRAME_DURATION_MS / 1000.0)):
                                armed_speech_frames = 0
                                armed_silence_frames = 0
                                armed_audio_buffer = []

                # ----------------------------------------------------
                # STATE: IN_MEETING
                # ----------------------------------------------------
                elif state == "IN_MEETING":
                    if is_speech:
                        last_speech_time = now

                    # Check app presence during meeting
                    if poll_due and app_running:
                        meeting_app_was_detected = True

                    # Termination Condition 1: Meeting app was detected but has now closed
                    end_meeting = False
                    end_reason = ""

                    if poll_due and meeting_app_was_detected and not app_running:
                        end_meeting = True
                        end_reason = "Meeting app closed"

                    # Termination Condition 2: Continuous silence > 90s
                    if not end_meeting and (now - last_speech_time >= SILENCE_TIMEOUT_S):
                        end_meeting = True
                        end_reason = f"Silence exceeded {SILENCE_TIMEOUT_S:.0f}s"

                    if end_meeting:
                        # Flush any active speech buffer
                        if in_speech and len(audio_buffer) >= MIN_UTTERANCE_FRAMES:
                            transcription_queue.put((audio_buffer, current_meeting_id))
                        
                        if current_meeting_id:
                            end_meeting_lifecycle(current_meeting_id, end_reason)

                        # Return to ARMED
                        state = "ARMED"
                        current_meeting_id = None
                        meeting_app_was_detected = False
                        in_speech = False
                        audio_buffer = []
                        recent_frames.clear()
                        silence_frames = 0
                        consecutive_speech_frames = 0
                        armed_speech_frames = 0
                        armed_silence_frames = 0
                        armed_audio_buffer = []
                        last_speech_time = now
                        continue

                    # Active audio capture & chunking
                    if is_speech:
                        consecutive_speech_frames += 1
                        recent_frames.append(raw_bytes)
                        if not in_speech and consecutive_speech_frames >= MIN_SPEECH_FRAMES:
                            in_speech = True
                            audio_buffer.extend(recent_frames)
                        elif in_speech:
                            audio_buffer.append(raw_bytes)
                        silence_frames = 0
                    else:
                        consecutive_speech_frames = 0
                        recent_frames.append(raw_bytes)
                        if in_speech:
                            audio_buffer.append(raw_bytes)
                            silence_frames += 1
                            if silence_frames > SILENCE_FRAMES_THRESHOLD:
                                transcription_queue.put((audio_buffer, current_meeting_id))
                                audio_buffer = []
                                in_speech = False
                                silence_frames = 0

    except KeyboardInterrupt:
        print("\nStopping listener...")
        if state == "IN_MEETING" and current_meeting_id:
            end_meeting_lifecycle(current_meeting_id, "User interrupted (Ctrl+C)")
    except Exception as e:
        print(f"\nListener error: {e}", file=sys.stderr)
        if state == "IN_MEETING" and current_meeting_id:
            end_meeting_lifecycle(current_meeting_id, f"Error: {e}")
    finally:
        print("Draining transcription queue...")
        transcription_queue.put(None)
        worker.join()
        print("Listener stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Understudy Audio Listener")
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List all available audio input devices and exit",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Audio input device name or index (defaults to AUDIO_DEVICE env, preferred system-audio, or default mic)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Run in manual continuous capture mode (bypass meeting auto-detection / auto-lifecycle)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("LISTENER_MODEL", "base.en"),
        help="faster-whisper model name to load (default: LISTENER_MODEL env or base.en)",
    )
    args = parser.parse_args()

    if args.list_devices:
        list_input_devices()
        sys.exit(0)

    device_idx, device_name = resolve_input_device(args.device)

    if args.manual:
        listen_manual(device_index=device_idx, model_name=args.model)
    else:
        listen_auto(device_index=device_idx, model_name=args.model)


if __name__ == "__main__":
    main()

