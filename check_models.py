import os

from openai import OpenAI

api_key = os.environ.get("GROQ_API_KEY")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

print("Fetching available models from Groq...")
try:
    models = client.models.list()
    print("\nACTIVE MODELS FOR YOUR KEY:")
    for m in models.data:
        print(f"- {m.id}")
except Exception as e:
    print(f"Error fetching models: {e}")