import sys
from pathlib import Path
from openai import OpenAI

key = Path(__file__).with_name("key.txt").read_text().strip()
client = OpenAI(api_key=key, base_url="https://api.deepseek.com")

q = " ".join(sys.argv[1:]) or "用一句话介绍你自己"
r = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": q}],
)
print(r.choices[0].message.content)
