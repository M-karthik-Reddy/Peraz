import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import csv
import logging

# 1. Obtain a named logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()  # reads the .env file into os.environ

app = Flask(__name__)

LEADS_FILE = "leads.csv"

TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")
OWNER_WHATSAPP_TO = os.environ.get("OWNER_WHATSAPP_TO", "whatsapp:+918125232790")  # TEST NUMBER

def log_lead(data):
    file_exists = os.path.isfile(LEADS_FILE)
    with open(LEADS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "name", "phone", "org", "product", "qty", "message"])
        writer.writerow([
            datetime.now().isoformat(), data.get("name"), data.get("phone"),
            data.get("org"), data.get("product"), data.get("qty"), data.get("message")
        ])

def send_whatsapp_via_twilio(data):
    if not (TWILIO_SID and TWILIO_AUTH and TWILIO_WHATSAPP_FROM):
        return False, "Twilio not configured"
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_AUTH)
        body = (
            f"New Quote Request\n"
            f"Name: {data.get('name')}\n"
            f"Phone: {data.get('phone')}\n"
            f"Org: {data.get('org') or '-'}\n"
            f"Product: {data.get('product') or '-'}\n"
            f"Qty: {data.get('qty')}\n"
            f"Message: {data.get('message') or '-'}"
        )
        logger.error("FROM = %r", TWILIO_WHATSAPP_FROM)
        logger.error("TO   = %r", OWNER_WHATSAPP_TO)
        msg = client.messages.create(from_=TWILIO_WHATSAPP_FROM, to=OWNER_WHATSAPP_TO, body=body)
        
        return True, msg.sid
    except Exception as e:
        return False, str(e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

@app.route("/submit-quote", methods=["POST"])
def submit_quote():
    data = request.get_json(force=True)

    if not data.get("name") or not data.get("phone"):
        return jsonify({"ok": False, "error": "Name and phone required"}), 400

    log_lead(data)

    sent, info = send_whatsapp_via_twilio(data)

    if not sent:
        logger.error("=" * 60)
        logger.error("Twilio WhatsApp sending failed")
        logger.error("Reason: %s", info)
        logger.error("Request Data: %s", data)
        logger.error("=" * 60)

        return jsonify({
            "ok": False,
            "sent_via_twilio": False,
            "error": info
        }), 502

    logger.info("Twilio WhatsApp sent successfully. SID: %s", info)

    return jsonify({
        "ok": True,
        "sent_via_twilio": True,
        "info": info
    })

if __name__ == "__main__":
    app.run(debug=True)