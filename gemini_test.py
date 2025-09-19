from google import genai
from dotenv import load_dotenv 
import os

load_dotenv()

client = genai.Client( api_key=os.getenv('GEMINI_API_KEY') )

response = client.models.generate_content(
  model="gemini-2.5-flash", contents="Quiero un resumen sobre AAPL. Si se trata de un par de trading, solo incluye informacion sobre el activo. Ve al grano, solo quiero informacion lo menos verbosa posible. No uses negritas."
)
print(response.text)

print("Thoughts tokens:",response.usage_metadata.thoughts_token_count)
print("Output tokens:",response.usage_metadata.candidates_token_count)