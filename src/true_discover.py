import logging
from spotify_api_interface import (
    get_access_token,
    get_token_link,
    check_access_token_valid,
    get_user_href,
    get_user_items,
    get_all_artists_from_playlists,
    get_artists_info_from_artist_ids,
    spotifyAccessTokenNotValidError,
    getUserItemsInterruptedError,
    getPlaylistArtistInterruptedError,
    collectMissingArtistsInterruptedError,
)
import random
import string
import urllib.parse as urlparse
from urllib.parse import parse_qs
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format="%(asctime)s - %(levelname)s - %(message)s",
)

SCOPE = "playlist-modify-private, playlist-read-private, playlist-read-collaborative, user-top-read, user-read-recently-played"

class collection_steps(Enum):
    """Enumeration for process steps."""
    NOT_STARTED = "Collection not started"
    TOP_TRACKS = "Getting user top tracks"
    TOP_ARTISTS = "Getting user top artists"
    ALL_PLAYLISTS = "Getting user playlists"
    PLAYLISTS_ARTISTS = "Getting all playlist artists"
    TOP_TRACKS_ARTISTS = "Getting all top tracks artists"
    MERGING_ARTISTS = "Merging all artists"

class interruptionError(Exception):
    def __init__(self):
        pass

class TrueDiscover:
    def __init__(self, spotify_cliend_id: str, redirect_uri: str = "http://localhost:8888/callback", access_token: str = None):
        self.spotify_client_id: str = spotify_cliend_id
        self.code_verifier: str = "".join(
            random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=128)
        )
        self.redirect_uri = redirect_uri
        self.code_verifier_storage: str = self.code_verifier
        self.access_token = access_token
        self.collection_step = collection_steps.NOT_STARTED
        self.all_top_tracks = []
        self.all_top_artists = []
        self.merged_artists = []
        logging.info("Initialized TrueDiscover instance.")

    def check_stored_access_token_still_valid(self):
        if self.access_token:
            try:
                valid = check_access_token_valid(self.access_token)
                logging.info("Access token is valid.")
                return valid
            except spotifyAccessTokenNotValidError:
                logging.warning("Access token is not valid.")
                return False
        else:
            logging.warning("No access token provided.")
            return False

    def get_access_token(self, authorization_code: str) -> str:
        logging.info("Requesting access token with authorization code.")
        self.access_token = get_access_token(
            self.spotify_client_id, authorization_code, code_verifier=self.code_verifier, redirect_uri=self.redirect_uri
        )
        logging.info("Access token retrieved successfully.")
        return self.access_token

    def get_token_link(self):
        logging.info("Generating token link.")
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

        if not self._authorization_code:
            logging.error("Authorization code not found in the URL.")
            raise NotImplementedError

        logging.info("Authorization code retrieved. Requesting access token.")
        self.access_token = self.get_access_token(authorization_code=self._authorization_code)
        return self.access_token

    def get_user_href(self):
        logging.info("Fetching user href.")
        self.user_href = get_user_href(self.access_token)
        logging.debug(f"User href: {self.user_href}")
        return self.user_href

    def collect_tracks(self, resume=False):
        try:
            logging.info("Collecting user tracks.")
            if resume:
                self.all_top_tracks.extend(
                    get_user_items(
                        self.access_token,
                        "tracks",
                        start_offset=self.all_top_tracks_offset,
                        time_ranges=self.all_top_tracks_time_ranges_left,
                    )
                )
            else:
                self.all_top_tracks = get_user_items(self.access_token, "tracks")
            logging.info("User tracks collected successfully.")
        except getUserItemsInterruptedError as e:
            logging.error("Error while collecting tracks. Partial data collected.")
            self.all_top_tracks.extend(e.collected_items)
            self.all_top_tracks_offset = e.offset
            self.all_top_tracks_time_ranges_left = e.time_ranges_left
    def collect_artists(self, resume=False):
        try:
            logging.info("Collecting user artists.")
            if resume:
                self.all_top_artists.extend(
                    get_user_items(
                        self.access_token,
                        "artists",
                        start_offset=self.all_top_artists_offset,
                        time_ranges=self.all_top_artists_time_ranges_left,
                    )
                )
            else:
                self.all_top_artists = get_user_items(self.access_token, "artists")
            logging.info("User artists collected successfully.")
        except getUserItemsInterruptedError as e:
            logging.error("Error while collecting artists. Partial data collected.")
            self.all_top_artists.extend(e.collected_items)
            self.all_top_artists_offset = e.offset
            self.all_top_artists_time_ranges_left = e.time_ranges_left

    def collect_playlists(self, resume=False):
        try:
            logging.info("Collecting user playlists.")
            if resume:
                self.all_top_playlists.extend(
                    get_user_items(
                        self.access_token,
                        "playlists",
                        start_offset=self.all_top_playlists_offset,
                        time_ranges=self.all_top_playlists_time_ranges_left,
                    )
                )
            else:
                self.all_top_playlists = get_user_items(self.access_token, "playlists")
            logging.info("User playlists collected successfully.")
        except getUserItemsInterruptedError as e:
            logging.error("Error while collecting playlists. Partial data collected.")
            self.all_top_playlists.extend(e.collected_items)
            self.all_top_playlists_offset = e.offset
            self.all_top_playlists_time_ranges_left = e.time_ranges_left

    def collect_playlists_artists(self, resume=False):
        try:
            logging.info("Collecting artists from playlists.")
            if resume:
                self.merged_artists.extend(
                    get_all_artists_from_playlists(
                        self.access_token,
                        playlists=self.playlists_left,
                        all_artists_to_add=self.playlist_collected_artists_to_add_ids,
                    )
                )
            else:
                self.merged_artists = get_all_artists_from_playlists(self.access_token, self.all_top_playlists)
            logging.info("Artists from playlists collected successfully.")
        except getPlaylistArtistInterruptedError as e:
            logging.error("Error while collecting playlist artists. Partial data collected.")
            self.playlists_left = e.playlists_left
            self.playlist_collected_artists_to_add_ids = e.collected_artists_to_add_ids
            self.merged_artists.extend(e.artists_collected)

    def collect_missing_artists_from_top_tracks(self, resume=False):
        logging.info("Collecting missing artists from top tracks.")
        if not resume:
            temp_id = [artist["id"] for artist in self.merged_artists]
            unique_artists_ids = set(temp_id)
            artist_ids_missing_full_info = []

            for track in self.all_top_tracks:
                for artist in track.get("artists", []):
                    artist_id = artist["id"]
                    if artist_id not in unique_artists_ids:
                        unique_artists_ids.add(artist_id)
                        artist_ids_missing_full_info.append(artist_id)
                    else:
                        for merged_artist in self.merged_artists:
                            if merged_artist["id"] == artist_id:
                                if "top_tracks" not in merged_artist.get("sources", []):
                                    merged_artist.setdefault("sources", []).append("top_tracks")
                                break
            self.artist_ids_missing_full_info = artist_ids_missing_full_info
        try:
            artists_from_top_tracks = get_artists_info_from_artist_ids(self.access_token, self.artist_ids_missing_full_info)
            for artist in artists_from_top_tracks:
                artist.setdefault("sources", []).append("top_tracks")
                self.merged_artists.append(artist)
            logging.info("Missing artists from top tracks collected successfully.")
        except collectMissingArtistsInterruptedError as e:
            logging.error("Error while collecting missing artists from top tracks.")
            raise e

    def data_collection(self, resume=False):
        logging.info("Starting data collection process.")
        if not resume:
            self.collection_step = collection_steps.NOT_STARTED

        try:
            if self.collection_step == collection_steps.NOT_STARTED:
                self.collection_step = collection_steps.TOP_TRACKS
                self.collect_tracks(resume=resume)
                resume = False

            if self.collection_step == collection_steps.TOP_TRACKS:
                self.collection_step = collection_steps.TOP_ARTISTS
                self.collect_artists(resume=resume)
                resume = False

            if self.collection_step == collection_steps.TOP_ARTISTS:
                self.collection_step = collection_steps.ALL_PLAYLISTS
                self.collect_playlists(resume=resume)
                for artist in self.merged_artists:
                    artist.setdefault("sources", []).append("playlists")
                resume = False

            if self.collection_step == collection_steps.ALL_PLAYLISTS:
                self.collection_step = collection_steps.PLAYLISTS_ARTISTS
                self.collect_playlists_artists(resume=resume)
                resume = False

            if self.collection_step == collection_steps.PLAYLISTS_ARTISTS:
                self.collection_step = collection_steps.TOP_TRACKS_ARTISTS
                self.collect_missing_artists_from_top_tracks(resume=resume)
                resume = False

            logging.info("Data collection completed successfully.")
        except interruptionError:
            logging.warning("Data collection interrupted.")
            raise
