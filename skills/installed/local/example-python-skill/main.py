import json
import os

payload = json.loads(os.environ.get("SKILL_INPUT", "{}"))
print("Hello from sample skill!", payload)
