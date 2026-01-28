"""
Generate a LiveKit token for testing in LiveKit Meet
"""
import os
from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv()
load_dotenv(".env.local")

# Get your LiveKit credentials
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    print("Error: LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env.local")
    exit(1)

# Create a token for a test participant
token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

# Set identity and room name
token.with_identity("test-user")
token.with_name("Test User")

# Grant permissions to join any room
token.with_grants(api.VideoGrants(
    room_join=True,
    room="test-room",  # You can change this to any room name
    can_publish=True,
    can_subscribe=True,
))

# Generate the JWT token
jwt_token = token.to_jwt()

print("\n" + "="*60)
print("LiveKit Token Generated!")
print("="*60)
print(f"\nToken: {jwt_token}")
print("\nCopy this token and paste it into LiveKit Meet.")
print("="*60 + "\n")
