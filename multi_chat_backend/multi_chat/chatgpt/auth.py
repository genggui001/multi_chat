# Builtins
import base64
import json
import os
import re
import time
import urllib.parse
from io import BytesIO
from typing import Optional, Tuple

# Fancy stuff
import colorama
# Client (Thank you!.. https://github.com/FlorianREGAZ)
import tls_client
# BeautifulSoup
from colorama import Fore
# Local
from pychatgpt.classes import exceptions as Exceptions
# Svg lib
# Svg lib
from tls_client.cookies import RequestsCookieJar

colorama.init(autoreset=True)

class Auth:
    def __init__(
        self, 
        email_address: str, 
        password: str, 
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        chat_cf_clearance: Optional[str] = None,
    ):
        self.email_address = email_address
        self.password = password
        self.proxy = proxy
        self.__session = tls_client.Session(
            client_identifier="chrome_105"
        )

        self.user_agent = user_agent
        self.__session.cookies = RequestsCookieJar()
        self.__session.cookies.set(
            name="cf_clearance",
            value=chat_cf_clearance,
        )

        self.__session.cookies.set(
            name="__Secure-next-auth.session-token",
            value=password,
        )


    def create_token(self):
        print(f"{Fore.GREEN}[OpenAI][9] {Fore.WHITE}"
              f"Attempting to get access token from: https://chat.openai.com/api/auth/session")
        url = "https://chat.openai.com/api/auth/session"
        headers = {
            "Connection": "keep-alive",
            "Accept": "*/*",
            "User-Agent": self.user_agent,
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Referer": "https://chat.openai.com/chat",
            "Accept-Encoding": "gzip, deflate, br",
        }
        response = self.__session.get(url, headers=headers)
        is_200 = response.status_code == 200
        if is_200:
            print(f"{Fore.GREEN}[OpenAI][9] {Fore.GREEN}Request was successful")
            if 'json' in response.headers['Content-Type']:
                json_response = response.json()
                access_token = json_response['accessToken']
                # expires = json_response['expires']
                print(f"{Fore.GREEN}[OpenAI][9] {Fore.WHITE}Access Token: {Fore.GREEN}{access_token}")
                # print(f"{Fore.GREEN}[OpenAI][9] {Fore.WHITE}Expires: {Fore.GREEN}{expires}")
                
                return access_token, int(time.time() + 3600)

            else:
                raise Exceptions.Auth0Exception(f"{Fore.GREEN}[OpenAI][9] {Fore.WHITE}Access Token: {Fore.RED}Not found, "
                                                f"Please try again with a proxy (or use a new proxy if you are using one)")
        else:
            raise Exceptions.Auth0Exception(f"{Fore.GREEN}[OpenAI][9] {Fore.WHITE}Access Token: {Fore.RED}Not found, "
                                            f"Please try again with a proxy (or use a new proxy if you are using one)")