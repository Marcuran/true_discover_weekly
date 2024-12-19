from spotify_api_interface import get_access_token, get_token_link, check_access_token_valid, get_user_href
import random
import string
import urllib.parse as urlparse
from urllib.parse import parse_qs

import logging

SCOPE = "playlist-modify-private, playlist-read-private, playlist-read-collaborative, user-top-read, user-read-recently-played"


class trueDiscover:
    def __init__(
        self, spotify_cliend_id: str, redirect_uri: str = "http://localhost:8888/callback", access_token: str = None
    ):
        self.spotify_client_id: str = spotify_cliend_id
        self.code_verifier: str = "".join(
            random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=128)
        )
        self.redirect_uri = redirect_uri
        self.code_verifier_storage: str = self.code_verifier
        self.access_token = access_token

    def check_stored_access_token_still_valid(self):
        return check_access_token_valid(self.access_token) if self.access_token else False

    def get_access_token(self, authorization_code: str) -> str:
        self.access_token = get_access_token(
            self.spotify_client_id, authorization_code, code_verifier=self.code_verifier, redirect_uri=self.redirect_uri
        )
        return self.access_token

    def get_token_link(self):
        return get_token_link(
            self.spotify_client_id, scope=SCOPE, code_verifier=self.code_verifier, redirect_uri=self.redirect_uri
        )

    def get_access_token_through_terminal(self) -> str:
        authorize_url = self.get_token_link()
        print(authorize_url)
        authorization_url = input("Enter the full authorization URL: ")
        parsed_url = urlparse.urlparse(authorization_url)
        query_params = parse_qs(parsed_url.query)
        self._authorization_code = query_params.get("code", [None])[0]

        # TODO be robust to this
        if not self._authorization_code:
            logging.error("Authorization code not found in the URL.")
            raise NotImplementedError

        self.access_token = self.get_access_token(authorization_code=self._authorization_code)
        return self.access_token

    def get_user_href(self):
        self.user_href = get_user_href(self.access_token)
        return self.user_href
