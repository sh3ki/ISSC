"""
Simple Philsms helper

This module provides a small helper to send SMS via the provided PhilSMS
OAuth token and API endpoint. It runs the HTTP request in a background thread
so it doesn't block the camera loop.

IMPORTANT: The provided token is included here because the user supplied it.
If you prefer, move the token into environment variables or Django `settings.py`.
"""
from threading import Thread, Lock
import requests
import time

# Configuration - prefer Django settings, fallback to environment, then hardcoded defaults
import os
try:
    from django.conf import settings as djsettings
    PHILSMS_API_BASE = getattr(djsettings, 'PHILSMS_API_BASE', os.getenv('PHILSMS_API_BASE', 'https://dashboard.philsms.com/api/v3'))
    PHILSMS_API_TOKEN = getattr(djsettings, 'PHILSMS_API_TOKEN', os.getenv('PHILSMS_API_TOKEN', '377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96'))
    PHILSMS_SENDER_ID = getattr(djsettings, 'PHILSMS_SENDER_ID', os.environ.get('PHILSMS_SENDER_ID', 'PhilSMS'))
    PHILSMS_DEFAULT_RECIPIENT = getattr(djsettings, 'PHILSMS_RECIPIENT', os.environ.get('PHILSMS_RECIPIENT', '09945349194'))
    PHILSMS_COOLDOWN = getattr(djsettings, 'PHILSMS_COOLDOWN_SECONDS', int(os.environ.get('PHILSMS_COOLDOWN_SECONDS', str(15 * 60))))
except Exception:
    # If Django settings aren't available (running as standalone script), use env or defaults
    PHILSMS_API_BASE = os.getenv('PHILSMS_API_BASE', 'https://dashboard.philsms.com/api/v3')
    PHILSMS_API_TOKEN = os.getenv('PHILSMS_API_TOKEN', '377|DT0C9GeHCgLXdNt5oxjajd3QqdLlKcqMHv5KLZcE3b45ab96')
    PHILSMS_SENDER_ID = os.environ.get('PHILSMS_SENDER_ID', 'PhilSMS')
    PHILSMS_DEFAULT_RECIPIENT = os.environ.get('PHILSMS_RECIPIENT', '09945349194')
    PHILSMS_COOLDOWN = int(os.environ.get('PHILSMS_COOLDOWN_SECONDS', str(15 * 60)))

    # Track last-sent timestamps per normalized recipient to enforce cooldown
    _last_sms_sent = {}
    _last_sms_lock = Lock()


def _normalize_ph_number(num: str):
    """Return a list of candidate recipient formats for Philippine numbers.

    Examples: '09945349194' -> ['09945349194', '+639945349194', '639945349194']
    """
    n = num.strip()
    candidates = [n]
    if n.startswith('0') and len(n) == 11:
        candidates.append('+63' + n[1:])
        candidates.append('63' + n[1:])
    # Handle numbers missing leading 0 but starting with 9 (e.g. 9945349194)
    if len(n) == 10 and n.startswith('9'):
        candidates.append('0' + n)
        candidates.append('+63' + n)
        candidates.append('63' + n)
    if n.startswith('+'):
        candidates.append(n[1:])
    return candidates


def _build_payload(to_number: str, message: str):
    """Build a payload dict including several common recipient keys.

    Some providers require 'recipient' while others use 'to' or 'msisdn'.
    Including multiple keys increases chance of acceptance.
    """
    candidates = _normalize_ph_number(to_number)
    # Prefer Philippine format without plus: 63XXXXXXXXXX (no +)
    primary = candidates[0]
    # If input was local '09xxxxxxxxx', convert to '63xxxxxxxxx'
    if primary.startswith('0') and len(candidates) > 1:
        # candidates[1] is '+63...' and candidates[2] is '63...'
        # choose the no-plus '63' format if available
        if len(candidates) > 2:
            primary = candidates[2]
        else:
            primary = candidates[1].lstrip('+')

    payload = {
        # Follow PhilSMS API exactly: 'recipient' (string), 'sender_id', 'type', 'message'
        "recipient": primary,
        "sender_id": PHILSMS_SENDER_ID,
        "type": "plain",
        "message": message,
    }
    return payload

# Public synchronous send wrapper (convenience for test script)
def send_sms_sync(to_number: str, message: str) -> bool:
    """Synchronously send an SMS and return True on success."""
    return _post_sms_sync(to_number, message)


def send_sms_sync_verbose(to_number: str, message: str):
    """Send SMS synchronously and return tuple (success, status_code, response_text).

    Use this for debugging delivery issues: it returns the HTTP status and
    the response body so you can inspect provider messages.
    """
    try:
        url = PHILSMS_API_BASE.rstrip('/') + "/sms/send"

        headers = {
            "Authorization": f"Bearer {PHILSMS_API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = _build_payload(to_number, message)
        payload = _build_payload(to_number, message)

        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        text = resp.text if resp is not None else ''
        ok = 200 <= resp.status_code < 300

        # If the provider indicates sender not authorized, retry without sender
        if not ok:
            try:
                body = text or ''
                if 'Sender ID' in body and 'not authorized' in body:
                    payload_no_sender = payload.copy()
                    payload_no_sender.pop('sender', None)
                    payload_no_sender.pop('from', None)
                    resp2 = requests.post(url, json=payload_no_sender, headers=headers, timeout=15)
                    text2 = resp2.text if resp2 is not None else ''
                    ok2 = 200 <= resp2.status_code < 300
                    return ok2, resp2.status_code, text2
            except Exception:
                pass

        return ok, resp.status_code, text
    except Exception as e:
        return False, None, str(e)


def _post_sms_sync(to_number: str, message: str) -> bool:
    """Perform the HTTP request synchronously. Returns True on success."""
    try:
        url = PHILSMS_API_BASE.rstrip('/') + "/sms/send"

        headers = {
            # Many APIs accept Bearer token; this is a best-effort header.
            "Authorization": f"Bearer {PHILSMS_API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = _build_payload(to_number, message)
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code >= 200 and resp.status_code < 300:
            return True

        # If the provider rejects the sender, retry without sender fields
        try:
            body = resp.text or ''
            if 'Sender ID' in body and 'not authorized' in body:
                # Build payload without sender/from
                payload_no_sender = payload.copy()
                payload_no_sender.pop('sender', None)
                payload_no_sender.pop('from', None)
                resp2 = requests.post(url, json=payload_no_sender, headers=headers, timeout=15)
                if resp2.status_code >= 200 and resp2.status_code < 300:
                    return True
                else:
                    try:
                        print(f"philsms: retry without sender failed {resp2.status_code}: {resp2.text}")
                    except Exception:
                        pass
                    return False

        except Exception:
            pass

        # Log original failure
        try:
            print(f"philsms: unexpected status {resp.status_code}: {resp.text}")
        except Exception:
            pass
        return False

    except Exception as e:
        print(f"philsms: exception sending sms: {e}")
        return False


def send_sms_async(to_number: str, message: str):
    """Send an SMS in a background thread. Returns immediately."""
    # Build payload early so we can determine the normalized recipient used
    try:
        payload = _build_payload(to_number, message)
        normalized_recipient = payload.get('recipient')
    except Exception:
        normalized_recipient = to_number

    # Enforce cooldown per-recipient at module level to avoid duplicate sends
    try:
        now = time.time()
        with _last_sms_lock:
            last = _last_sms_sent.get(normalized_recipient, 0)
            if now - last < PHILSMS_COOLDOWN:
                # Still in cooldown period; skip sending to avoid spam
                print(f"philsms: cooldown active for {normalized_recipient}, skipping send")
                return
    except Exception:
        # If cooldown check fails for any reason, proceed to attempt send
        pass

    def _worker():
        try:
            # Build payload for debug output (don't print the token)
            payload = _build_payload(to_number, message)
            url = PHILSMS_API_BASE.rstrip('/') + "/sms/send"

            # Use the verbose sync sender inside the worker so we can log status and body
            ok, status_code, body = send_sms_sync_verbose(to_number, message)

            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"philsms: Debug SMS send attempt at {ts}")
            try:
                # Show destination and payload (masking any sensitive fields)
                print(f"philsms: URL={url}")
                print(f"philsms: recipient candidates payload recipient={payload.get('recipient')}")
                print(f"philsms: message={message}")
            except Exception:
                pass

            # Print provider response details for debugging
            print(f"philsms: send result -> ok={ok}, status={status_code}")
            if body:
                # Truncate body to reasonable size to avoid noisy logs
                try:
                    print(f"philsms: response body={body[:200]}")
                except Exception:
                    print(f"philsms: response body (unprintable)")

            # If send succeeded, update last-sent timestamp for the normalized recipient
            try:
                if ok:
                    primary = payload.get('recipient')
                    if primary:
                        with _last_sms_lock:
                            _last_sms_sent[primary] = time.time()
            except Exception:
                pass
        except Exception as e:
            print(f"philsms: async worker exception: {e}")

    thread = Thread(target=_worker, daemon=True)
    thread.start()


if __name__ == '__main__':
    # Quick manual test when run as a script
    import argparse

    parser = argparse.ArgumentParser(description='Test PhilSMS sending')
    parser.add_argument('--to', required=False, default='09945349194', help='Destination phone number')
    parser.add_argument('--message', required=False, default='ISSC System\nTest SMS from PhilSMS helper', help='Message text')
    parser.add_argument('--sync', action='store_true', help='Send synchronously and print result')
    parser.add_argument('--verbose', action='store_true', help='Print full HTTP status and response body')

    args = parser.parse_args()

    if args.sync:
        if args.verbose:
            ok, status, body = send_sms_sync_verbose(args.to, args.message)
            print(f"send_sms_sync_verbose -> ok={ok}, status={status}, body={body}")
        else:
            ok = send_sms_sync(args.to, args.message)
            print(f"send_sms_sync returned: {ok}")
    else:
        send_sms_async(args.to, args.message)
        print("Dispatched async SMS (check logs for result)")
