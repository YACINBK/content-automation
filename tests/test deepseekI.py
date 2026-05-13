from openai import OpenAI

endpoint = "https://yassinebenkacem7836-resource.services.ai.azure.com/openai/v1/"
model_name = "DeepSeek-V3-0324"
deployment_name = "DeepSeek-V3-0324"

api_key = "F7ie6ULZIC2bUWB8nrUbd3vWoAH0Fg6aocy3EyPdRiPYXdOyqaCfJQQJ99CCACfhMk5XJ3w3AAAAACOGwfZc"

client = OpenAI(
    base_url=f"{endpoint}",
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message.content)