from __future__ import annotations

import argparse
import email
import imaplib
import os
import re
import sys
import time
from email.message import Message
from pathlib import Path

OTP_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


def _extract_otp(text: str) -> str:
    match = OTP_PATTERN.search(text or "")
    return match.group(1) if match else ""


def _read_from_file(path: str) -> str:
    data = Path(path).read_text(encoding="utf-8", errors="replace")
    return _extract_otp(data)


def _read_from_stdin() -> str:
    data = sys.stdin.read()
    return _extract_otp(data)


def _decode_email_body(message_obj: Message) -> str:
    if message_obj.is_multipart():
        chunks: list[str] = []
        for part in message_obj.walk():
            if str(part.get_content_type() or "") != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            if not isinstance(payload, (bytes, bytearray)):
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                chunks.append(payload.decode(charset, errors="replace"))
            except Exception:
                chunks.append(payload.decode("utf-8", errors="replace"))
        return "\n".join(chunks)

    payload = message_obj.get_payload(decode=True)
    if not isinstance(payload, (bytes, bytearray)):
        return str(message_obj.get_payload() or "")
    charset = message_obj.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _fetch_from_custom_source(email: str) -> str:
    """Fetch OTP from IMAP inbox using OTP_IMAP_* environment variables."""
    host = os.getenv("OTP_IMAP_HOST", "").strip()
    username = os.getenv("OTP_IMAP_USERNAME", "").strip()
    password = os.getenv("OTP_IMAP_PASSWORD", "")
    mailbox = os.getenv("OTP_IMAP_MAILBOX", "INBOX").strip() or "INBOX"
    from_filter = os.getenv("OTP_IMAP_FROM", "").strip()
    subject_filter = os.getenv("OTP_IMAP_SUBJECT", "WorldLinco").strip()
    timeout_seconds = int(os.getenv("OTP_IMAP_TIMEOUT_SECONDS", "180") or "180")
    poll_interval = float(os.getenv("OTP_IMAP_POLL_INTERVAL_SECONDS", "5") or "5")

    if not (host and username and password):
        return ""

    search_terms = ["ALL"]
    if from_filter:
        search_terms += ["FROM", f'"{from_filter}"']
    if subject_filter:
        search_terms += ["SUBJECT", f'"{subject_filter}"']

    # Prefer target email if available so reused mailboxes can disambiguate messages.
    target_email = str(email or "").strip().lower()
    deadline = time.monotonic() + max(1, timeout_seconds)

    while time.monotonic() < deadline:
        try:
            with imaplib.IMAP4_SSL(host) as imap:
                imap.login(username, password)
                imap.select(mailbox)
                status, data = imap.search(None, *search_terms)
                if status != "OK":
                    time.sleep(poll_interval)
                    continue

                msg_ids = (data[0] or b"").split()
                for msg_id in reversed(msg_ids[-20:]):
                    fetch_status, fetched = imap.fetch(
                        msg_id.decode("ascii", errors="ignore"),
                        "(RFC822)",
                    )
                    if fetch_status != "OK" or not fetched:
                        continue
                    chunk = fetched[0] if fetched else None
                    raw_msg = (
                        chunk[1]
                        if isinstance(chunk, tuple)
                        and len(chunk) > 1
                        and isinstance(chunk[1], bytes)
                        else b""
                    )
                    if not raw_msg:
                        continue

                    message_obj = email.message_from_bytes(raw_msg)
                    to_header = str(message_obj.get("To") or "").lower()
                    cc_header = str(message_obj.get("Cc") or "").lower()
                    if target_email and target_email not in to_header and target_email not in cc_header:
                        continue

                    body = _decode_email_body(message_obj)
                    otp = _extract_otp(body)
                    if otp:
                        return otp
        except Exception:
            pass

        time.sleep(poll_interval)

    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print only a 6-digit OTP to stdout for e2e runner integration.",
    )
    parser.add_argument("--email", default="", help="Target email for OTP lookup")
    parser.add_argument(
        "--otp",
        default="",
        help="Direct OTP override (useful for smoke checks)",
    )
    parser.add_argument(
        "--input-file",
        default="",
        help="Read text from file and extract first 6-digit OTP",
    )
    parser.add_argument(
        "--from-stdin",
        action="store_true",
        help="Read text from stdin and extract first 6-digit OTP",
    )
    args = parser.parse_args()

    otp = ""

    if args.otp:
        otp = _extract_otp(args.otp)
    elif args.input_file:
        otp = _read_from_file(args.input_file)
    elif args.from_stdin:
        otp = _read_from_stdin()
    else:
        otp = _fetch_from_custom_source(args.email)

    if not otp:
        print("OTP_NOT_FOUND", file=sys.stderr)
        return 1

    # IMPORTANT: print OTP only (no prefixes/suffixes) for --otp-fetch-command.
    print(otp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
