"""
===============================================================================
Webhook Receiver Example (FastAPI)
===============================================================================

WHAT IS A WEBHOOK?
-------------------
A webhook is an HTTP-based communication mechanism used to notify a receiving
server (this app) of an event that occurred in another system (the sender).
Instead of polling or requesting updates repeatedly, webhooks allow the sender
to push real-time data to your server by making an HTTP POST request.

Example use case:
- A sensor platform wants to notify your app when new sensor data is recorded.
- It sends a POST request to `/webhook` with a JSON body containing the data.

WHAT IS THE SIGNATURE AND WHY DO WE NEED IT?
--------------------------------------------
To ensure the webhook is truly sent by a trusted source and not tampered with,
we use an HMAC (Hash-based Message Authentication Code) signature.

The sender and receiver share a **secret key** (called `UserSecret.secret` in this system).
The sender:
1. Takes the raw JSON payload (before encoding or parsing),
2. Computes the HMAC SHA-256 signature using the shared secret,
3. Sends this signature in the HTTP header `X-Hub-Signature-256`.

The receiver (this FastAPI route):
1. Extracts the same raw body and re-computes the expected signature,
2. Compares it against the signature provided in the header,
3. If they match → the request is authenticated and trusted.
   If they don’t → the request is rejected (403 Forbidden).

This protects against:
- Payload tampering in transit
- Forged requests from malicious third parties

WHAT IS THE AUTHENTICATION SYSTEM?
-----------------------------------
The authentication is **stateless and signature-based**.
There is no password or token in the body.
The only authentication is done via the signed message header:
`X-Hub-Signature-256: sha256=<signature-hash>`

The hash is derived from:
- The exact body of the request
- The secret known only to sender and receiver

The system does **not** authenticate users via JWT or sessions here — it relies
solely on the trust of the secret and HMAC computation.

WHAT IS THE COMPOSITION OF THE PAYLOAD?
----------------------------------------
The payload (request body) is expected to be a **JSON** document with relevant
event data. For example, if the webhook is about a new sensor reading, the
payload might look like:

{
  "event": "sensor_data_received",
  "timestamp": "2025-07-03T12:00:00Z",
  "sensor_id": "UUID-1234...",
  "data": {
    "temperature": 24.5,
    "humidity": 60.0,
    "pm2_5": 12.4
  }
}

This structure can vary depending on what your backend is integrated with.
You can customize this route to extract and store the data once signature
verification passes.

===============================================================================
"""

from fastapi import FastAPI, Request, Header, HTTPException
import hmac
import hashlib
import json
import uuid
from typing import Optional

app = FastAPI()

# --------------------------------------------------------------------
# SHARED SECRET (REQUIRED FOR HMAC SIGNATURE VALIDATION)
# This should be kept secret and match the one used by the webhook sender.
# Usually taken from the "UserSecret.secret" field and encoded as UTF-8.
# --------------------------------------------------------------------
SHARED_SECRET = b"dow67o_lK-6o9ZJ0ySFE2ol4fkOF2iKF"

# --------------------------------------------------------------------
# USER ID (OPTIONAL, FOR LOGGING OR AUDIT PURPOSES)
# Can be used to identify the source of the webhook or include it in logs.
# --------------------------------------------------------------------
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Receives and verifies incoming webhook POST requests.

    The sender should:
    - Sign the raw request body using HMAC-SHA256 and the shared secret.
    - Include the signature in the header `X-Hub-Signature-256` in the format: sha256=...

    This endpoint:
    - Extracts and logs the body and headers.
    - Recomputes the HMAC signature using the same shared secret.
    - Verifies that the received and expected signatures match.
    """

    try:
        # ------------------------------------------------------------
        # Step 1: Read raw body bytes from the incoming HTTP request.
        # ------------------------------------------------------------
        raw_body = await request.body()

        # ------------------------------------------------------------
        # Step 2: Debug log headers and payload for visibility.
        # ------------------------------------------------------------
        print("\n--- Webhook Received ---")
        print("Headers:", dict(request.headers))
        print("Payload:", raw_body.decode("utf-8"))

        # ------------------------------------------------------------
        # Step 3: Validate presence of signature header.
        # If missing, reject with HTTP 400 (Bad Request).
        # ------------------------------------------------------------
        if not x_hub_signature_256:
            raise HTTPException(status_code=400, detail="Missing X-Hub-Signature-256 header.")

        # ------------------------------------------------------------
        # Step 4: Recompute the expected HMAC SHA-256 signature.
        # Format it as 'sha256=...' to match GitHub-style headers.
        # ------------------------------------------------------------
        expected_sig = hmac.new(SHARED_SECRET, raw_body, hashlib.sha256).hexdigest()
        expected_sig_header = f"sha256={expected_sig}"

        # ------------------------------------------------------------
        # Step 5: Log both signatures for comparison.
        # Useful for debugging and ensuring the format matches.
        # ------------------------------------------------------------
        print("Computed Signature:", expected_sig_header)
        print("Received Signature:", x_hub_signature_256)

        # ------------------------------------------------------------
        # Step 6: Securely compare the received and expected signatures.
        # Uses `compare_digest()` to prevent timing attacks.
        # If they don't match, reject with HTTP 403 (Forbidden).
        # ------------------------------------------------------------
        if not hmac.compare_digest(expected_sig_header, x_hub_signature_256):
            print("Signature mismatch detected. Webhook rejected.")
            raise HTTPException(status_code=403, detail="Invalid signature.")

        # ------------------------------------------------------------
        # Step 7: If signature matches, continue processing the webhook.
        # For now, we simply return a success status.
        # ------------------------------------------------------------
        print("Signature verified successfully.")
        return {"status": "ok", "user_id": str(USER_ID)}

    except Exception as e:
        # ------------------------------------------------------------
        # Step 8: Catch-all for any unexpected errors.
        # Logs the exception and returns HTTP 500 (Internal Server Error).
        # ------------------------------------------------------------
        print("Error while processing webhook:", str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed.")
