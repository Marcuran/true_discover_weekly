from spotify_api_interface import (
    get_access_token,
    get_token_link,
    check_access_token_valid,
    get_user_href,
    get_user_items,
    get_all_artists_from_playlists,
    spotifyAccessTokenNotValidError,
    getUserItemsInterruptedError,
    getPlaylistArtistInterrupterError,
)
import random
import string
import urllib.parse as urlparse
from urllib.parse import parse_qs
from enum import Enum
import logging

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


class true_discover:
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
        self.collection_step = collection_steps.NOT_STARTED

    def check_stored_access_token_still_valid(self):
        if self.access_token:
            try:
                return check_access_token_valid(self.access_token)
            except spotifyAccessTokenNotValidError:
                return False
        else:
            return False

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

    def collect_tracks(self, resume=False):
        try:
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
        except getUserItemsInterruptedError as e:
            self.all_top_tracks.extend(e.collected_items)
            self.all_top_tracks_offset = e.offset
            self.all_top_tracks_time_ranges_left = e.time_ranges_left

    def collect_artists(self, resume=False):
        try:
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
                self.all_top_artists = get_user_items(self.access_token, "tracks")
        except getUserItemsInterruptedError as e:
            self.all_artists.extend(e.collected_items)
            self.all_top_artists_offset = e.offset
            self.all_top_artists_time_ranges_left = e.time_ranges_left

    def collect_playlists(self, resume=False):
        try:
            if resume:
                self.all_top_playlists.extend(
                    get_user_items(
                        self.access_token,
                        "artists",
                        start_offset=self.all_top_playlists_offset,
                        time_ranges=self.all_top_playlists_time_ranges_left,
                    )
                )
            else:
                self.all_top_playlists = get_user_items(self.access_token, "tracks")
        except getUserItemsInterruptedError as e:
            self.all_top_playlists.extend(e.collected_items)
            self.all_top_playlists_offset = e.offset
            self.all_top_playlists_time_ranges_left = e.time_ranges_left

    def collect_playlists_artists(self, resume=False):
        try:
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
        except getPlaylistArtistInterrupterError as e:
            self.playlists_left = e.playlists_left
            self.playlist_collected_artists_to_add_ids = e.collected_artists_to_add_ids
            self.merged_artists.extend(e.artists_collected)
    
    def collect_missing_artists_from_top_tracks(self, resume= False):
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
                                if "top_tracks" not in merged_artist["sources"]:
                                    merged_artist.setdefault("sources", []).append("top_tracks")
                                break
        try:
            if resume:
                self.top_track_artists.extend(

                )

    

    def data_collection(self, resume=False):
        if resume == False:
            self.collection_step = collection_steps.NOT_STARTED

        if self.collection_step == collection_steps.NOT_STARTED:
            self.collection_step = collection_steps.TOP_TRACKS
            try:
                self.collect_tracks(resume=resume)
            except getUserItemsInterruptedError:
                raise interruptionError()
            resume = False

        if self.collection_step == collection_steps.TOP_TRACKS:
            self.collection_step = collection_steps.TOP_ARTISTS
            try:
                self.collect_artists(resume=resume)
            except getUserItemsInterruptedError:
                raise interruptionError()
            resume = False

        if self.collection_step == collection_steps.TOP_ARTISTS:
            self.collection_step = collection_steps.ALL_PLAYLISTS
            try:
                self.collect_playlists(resume=resume)
                for artist in self.merged_artists:
                    artist.setdefault("sources", []).append("playlists")
            except getUserItemsInterruptedError:
                raise interruptionError()
            resume = False

        if self.collection_step == collection_steps.ALL_PLAYLISTS:
            self.collection_step = collection_steps.PLAYLISTS_ARTISTS
            try:
                self.collect_playlists_artists(resume=resume)
            except getPlaylistArtistInterrupterError:
                raise interruptionError()
            resume = False

        if self.collection_step == collection_steps.PLAYLISTS_ARTISTS:
            self.collection_step = collection_steps.TOP_TRACKS_ARTISTS
            
