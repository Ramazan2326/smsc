from sdk import SMSC
from dotenv import load_dotenv

import os

load_dotenv()


auth_token: str = os.getenv("auth_token")
client = SMSC(auth_token, sending_type=12)
phones = [os.getenv("phone")]
message = "Hello World!"

result = client.send_sms(phones=phones, message=message)
print(result)