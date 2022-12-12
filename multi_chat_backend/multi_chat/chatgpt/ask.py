# Builtins
import json
import uuid
from typing import AsyncGenerator, Optional, Tuple

# import cfscrape
# Requests
import httpx


async def ask(
        auth_token: Tuple,
        prompt: str,
        conversation_id: str or None,
        previous_convo_id: str or None,
        proxies: str or dict or None,
        user_agent: Optional[str] = None,
        chat_cf_clearance: Optional[str] = None,
) -> AsyncGenerator[Tuple[str, str, str], None]:
    auth_token, expiry = auth_token

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}',
        'Accept': 'text/event-stream',
        'Referer': 'https://chat.openai.com/chat',
        'Origin': 'https://chat.openai.com',
        'User-Agent': user_agent,
        'X-OpenAI-Assistant-App-Id': ''
    }

    if previous_convo_id is None:
        previous_convo_id = str(uuid.uuid4())

    if conversation_id is not None and len(conversation_id) == 0:
        # Empty string
        conversation_id = None # type: ignore
    # print("Conversation ID:", conversation_id)
    # print("Previous Conversation ID:", previous_convo_id)

    data = {
        "action": "variant",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": {"content_type": "text", "parts": [str(prompt)]},
            }
        ],
        "conversation_id": conversation_id,
        "parent_message_id": previous_convo_id,
        "model": "text-davinci-002-render"
    }

    if proxies is not None:
        if isinstance(proxies, str):
            proxies = {'http': proxies, 'https': proxies} # type: ignore

    async with httpx.AsyncClient(proxies=proxies, transport=httpx.AsyncHTTPTransport(retries=5)) as session: # type: ignore

        async with session.stream(
            'POST',
            url="https://chat.openai.com/backend-api/conversation",
            headers=headers,
            data=json.dumps(data),  # type: ignore
            cookies={
                "cf_clearance": chat_cf_clearance,
            } if chat_cf_clearance is not None else None,
            timeout=360,
        ) as response:
            if response.status_code == 200:
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

                    if len(as_json["message"]["content"]["parts"]) > 0:
                        yield (
                            as_json["message"]["content"]["parts"][0],
                            as_json["message"]["id"],
                            as_json["conversation_id"],
                        )
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



