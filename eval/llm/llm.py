from openai import OpenAI
import json

config = json.load(open("config//llm//openai.json"))

client = OpenAI(
  base_url=config['api_base'],
  api_key=config['api_key'],
)

def llm(prompt):
    completion = client.chat.completions.create(
        model=config['model_name'],
        messages=[
            {
            "role": "user",
            "content": f"{prompt}"
            }
        ],
        temperature=config.get('temperature', 0.6),
    )
    return completion.choices[0].message.content




