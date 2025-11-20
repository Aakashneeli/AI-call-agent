import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Configuration
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
my_number = os.getenv('MY_PHONE_NUMBER')
# Use the hardcoded URL for now as requested, or fetch from env if we added it.
# Let's use the one the user provided.
ngrok_url = "https://kip-proadoption-rachele.ngrok-free.dev" 

if not account_sid or not auth_token:
    print("Error: Twilio credentials not found in .env")
    exit(1)

print(f"Initiating call from {twilio_number} to {my_number}...")
print(f"Webhook URL: {ngrok_url}/voice")

client = Client(account_sid, auth_token)

try:
    call = client.calls.create(
        url=f"{ngrok_url}/voice",
        to=my_number,
        from_=twilio_number
    )
    print(f"Call initiated! SID: {call.sid}")
    print("Check your phone!")
except Exception as e:
    print(f"Error creating call: {e}")
