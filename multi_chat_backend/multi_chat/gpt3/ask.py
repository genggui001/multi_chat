# Builtins
import json
import uuid
from typing import AsyncGenerator, Optional, Tuple

# import cfscrape
# Requests
import httpx


async def ask(
        auth_token: str,
        prompt: str,
) -> AsyncGenerator[str, None]:

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}',
    }

    data = {
        "model": "text-davinci-003",
        "prompt": prompt,
        "max_tokens": 2048,
        "temperature": 0.9,
        "top_p": 0.1,
        "n": 1,
        "stream": True,
        "logprobs": None,
        "stop": "\n\n"
    }

    async with httpx.AsyncClient(proxies=None, transport=httpx.AsyncHTTPTransport(retries=5)) as session: # type: ignore

        async with session.stream(
            'POST',
            url="https://api.openai.com/v1/completions",
            headers=headers,
            data=json.dumps(data),  # type: ignore
            timeout=360,
        ) as response:
            if response.status_code == 200:
                re_text = ""
                async for line in response.aiter_lines():
                    line = line.rstrip()

                    if len(line) == 0:
                        continue

                    if line[:6] == "data: ":
                        line = line[6:]

                    if line == "[DONE]":
                        break

                    if len(line) == 0:
                        continue
                    
                    as_json = json.loads(line)

                    if len(as_json["choices"][0]["text"]) > 0:
                        re_text += as_json["choices"][0]["text"]
                        yield re_text
            else:
                r_text = await response.aread()
                r_text = r_text.decode('utf8')

                if response.status_code == 401:
                    raise Exception(f"[Status Code] 401 | [Response Text] {r_text}")
                elif response.status_code >= 500:
                    print(">> Looks like the server is either overloaded or down. Try again later.")
                    raise Exception(f"[Status Code] {response.status_code} | [Response Text] {r_text}")
                else:
                    raise Exception(f"[Status Code] {response.status_code} | [Response Text] {r_text}")



