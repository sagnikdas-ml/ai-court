import os
import hmac
import json
import hashlib

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

RESEARCH_CHANNEL_ID = "e7f59238-5029-45d4-9ce5-cfb67f7aa3aa"


def verify_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        print("WARNING: WEBHOOK_SECRET not set")
        return False

    if not timestamp or not signature:
        return False

    if signature.startswith("sha256="):
        signature = signature[7:]

    signed_content = (
        timestamp.encode("utf-8")
        + b"."
        + raw_body
    )

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        signed_content,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected,
        signature,
    )


@app.route("/ambiguous-webhook", methods=["POST"])
def ambiguous_webhook():
    raw_body = request.get_data()

    timestamp = request.headers.get(
        "X-Webhook-Timestamp"
    )

    signature = request.headers.get(
        "X-Webhook-Signature"
    )

    if not verify_signature(
        raw_body,
        timestamp,
        signature,
    ):
        return jsonify({
            "error": "invalid signature"
        }), 401

    payload = request.get_json()

    print("\n==========================")
    print("WEBHOOK RECEIVED")
    print("==========================")
    print(json.dumps(payload, indent=2))

    event_type = payload.get("event")
    data = payload.get("data", {})

    if event_type != "message.received":
        return jsonify({
            "status": "ignored",
            "reason": "not message.received",
        })

    channel_id = (
        data.get("channel_id")
        or data.get("channel", {}).get("id")
    )

    if channel_id != RESEARCH_CHANNEL_ID:
        return jsonify({
            "status": "ignored",
            "reason": "different channel",
        })

    author = data.get("author") or {}

    # Extra protection against qbot reacting to itself
    if author.get("type") == "agent":
        return jsonify({
            "status": "ignored",
            "reason": "agent message",
        })

    print("\nNEW HUMAN MESSAGE IN #research-team")
    print("Content:", data.get("content"))

    # For now we only prove that live events work.
    # Next step: trigger the full pipeline here.

    return jsonify({
        "status": "received"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
    )