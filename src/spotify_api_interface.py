import random
import string
import urllib.parse as urlparse
from urllib.parse import parse_qs, urlencode
import hashlib
import base64
import requests
import time
import logging
import json

LENGTH = 16
code_verifier = "".join(
    random.choices(
        string.ascii_uppercase + string.ascii_lowercase + string.digits, k=128
    )
)
authorization_code = None

def check_saved_access_token_valid(access_token: str, url: str = "https://api.spotify.com/v1/me"):
    private_info_url = url
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(private_info_url, headers=headers)
    if response.status_code == 200:
        logging.info("saved access token still valid")
        return True
    elif response.status_code == 401:
        logging.info("saved access token not valid, need to request a new one")
        return False
    else:
        logging.error("Response: %s", response.text)
        exit()


def get_token(
    client_id: str, scope: str, redirect_uri="http://localhost:8888/callback"
):
    """
    Generates an authorization URL and prompts the user to input the
    full URL with the authorization code.
    Retrieves an access token using the authorization code.

    Args:
        client_id (str): Client ID obtained from the Spotify
            Developer Dashboard.
        scope (str): Scopes required for accessing
            Spotify API endpoints.
        redirect_uri (str): Redirect URI specified in the
            Spotify Developer Dashboard.

    Returns:
        access_token (str): Access token if the authorization is successful,
            None otherwise.
    """
    global authorization_code

    letters_and_digits = string.ascii_letters + string.digits
    state = "".join(random.choice(letters_and_digits) for _ in range(LENGTH))
    code_verifier_storage = code_verifier
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode())
                                 .digest())
        .decode()
        .rstrip("=")
    )

    args = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }

    query_string = urlencode(args)
    authorize_url = "https://accounts.spotify.com/authorize?" + query_string

    print(authorize_url)

    authorization_url = input("Enter the full authorization URL: ")
    parsed_url = urlparse.urlparse(authorization_url)
    query_params = parse_qs(parsed_url.query)
    authorization_code = query_params.get("code", [None])[0]

    if not authorization_code:
        logging.error("Authorization code not found in the URL.")
        return None

    token_url = "https://accounts.spotify.com/api/token"

    token_params = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier_storage,
    }

    response = requests.post(token_url, data=token_params)
    response_data = response.json()

    access_token = response_data.get("access_token")
    return access_token


def get_user_href(access_token: str, url: str = "https://api.spotify.com/v1/me"):
    """
    Retrieves the user's href (Spotify API endpoint) using the access token.

    Args:
        access_token (str): Access token for authenticating API requests.

    Returns:
        str: User's href (Spotify API endpoint).
    """
    private_info_url = url
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(private_info_url, headers=headers)
    if response.status_code == 200:
        logging.info("href fetched successfully")
        response_data = response.json()
        return response_data["href"]
    else:
        logging.error("Failed to get user href")
        logging.error("Response: %s", response.text)
        exit()


def create_and_populate_playlist(
    access_token,
    user_href,
    tracks,
    playlist_name="Hello world!",
    playlist_description="Hello world!",
    public=False,
):
    # Create the playlist
    playlist_id = create_playlist(
        access_token, user_href, playlist_name, playlist_description, public
    )
    time.sleep(5)
    if playlist_id:
        # Add tracks to the created playlist
        add_tracks_url = f"{user_href}/playlists/{playlist_id}/tracks"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        track_ids = [track["id"] for track in tracks]
        track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]

        if len(track_uris) > 5:
            track_uris = track_uris[0:100]
        track_data = {"uris": track_uris}
        response = requests.post(
            add_tracks_url,
            headers=headers,
            json=track_data
            )

        if response.status_code == 201:
            logging.info("Tracks added to the playlist successfully")
        else:
            logging.error("Failed to add tracks to the playlist")
            logging.error("Response: %s", response.text)
    else:
        logging.error("Failed to create the playlist")


def create_playlist(
    access_token,
    user_href,
    playlist_name="Hello world!",
    playlist_description="Hello world!",
    public=False,
):
    """
    Creates a playlist using the user's href and returns the playlist ID.

    Args:
        access_token (str): Access token for authenticating API requests.
        playlist_name (str, optional): Name of the playlist.
            Defaults to "Hello world!".
        playlist_description (str, optional): Description of the playlist.
            Defaults to "Hello world!".
        public (bool, optional): Indicates if the playlist should be
            public or not. Defaults to False.

    Returns:
        str: Playlist ID of the created playlist.
    """
    playlist_creation_url = f"{user_href}/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    playlist_info = {
        "name": playlist_name,
        "description": playlist_description,
        "public": public,
    }
    response = requests.post(
        playlist_creation_url,
        headers=headers,
        json=playlist_info)

    response_data = response.json()
    if response.status_code == 201:
        response_data = response.json()
    else:
        # Request failed
        logging.error("Request failed with status code: %s %s", response.status_code, response.text)
        exit()
    return response_data["id"]


def get_user_playlist(access_token, offset, limit=20, url: str = "https://api.spotify.com/v1/me/playlists"):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    params = {"limit": limit, "offset": offset}
    playlist_url = url
    response = requests.get(playlist_url, headers=headers, params=params)
    response_data = response.json()
    return response_data.get("items", [])


def get_user_items(access_token, item_type, limit=20, total_limit=10000):
    """
    Retrieves the user's top items (tracks or artists) with pagination support.

    Args:
        access_token (str): Access token for authenticating API requests.
        user_href (str): User's Spotify API endpoint.
        item_type (str): Type of items to retrieve ('tracks' or 'artists').
        limit (int, optional): The maximum number of items to retrieve
            per request. Defaults to 20.
        total_limit (int, optional): The maximum number of total
        items to retrieve. Defaults to 10000.

    Returns:
        list: A list of dictionaries representing the user's top items.
    """
    unique_item_ids = set()
    unique_items = []

    time_ranges = ["short_term", "medium_term", "long_term"]
    for time_range in time_ranges:
        for offset in range(0, total_limit, limit):
            time.sleep(5)
            items = get_user_items_page(
                access_token, item_type, limit, offset, time_range
            )
            for item in items:
                item_id = item["id"]
                if item_id not in unique_item_ids:
                    unique_item_ids.add(item_id)
                    unique_items.append(item)

            if len(items) < limit:
                break

    return unique_items


def get_user_items_page(
    access_token, item_type, limit, offset, time_range="medium_term", base_url: str = "https://api.spotify.com/v1/me/"
):
    if item_type in ["tracks", "artists"]:
        params = {
            "limit": limit, 
            "offset": offset, 
            "time_range": time_range
        }
        url = f"{base_url}top/{item_type}"
    elif item_type == "playlists":
        params = {
            "limit": limit,
            "offset": offset,
        }
        url = f"{base_url}{item_type}"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(url, headers=headers, params=params)
    response_data = response.json()
    return response_data.get("items", [])


def get_all_tracks_from_playlists(access_token, playlists):
    unique_tracks = []
    unique_track_ids = []
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    for playlist in playlists:
        time.sleep(5)
        href = playlist["tracks"]["href"]
        response = requests.get(href, headers=headers)
        response_data = response.json()
        tracks = response_data.get("items", [])
        for track in tracks:
            try:
                track_id = track["track"]["id"]
                if track_id not in unique_track_ids:
                    unique_track_ids.append(track_id)
                    unique_tracks.append(track["track"])
            except TypeError as e:
                logging.error("Error: %s", e)

    return unique_tracks
 
#TODO reduce the number of requests needed to the minimum, it is to high and after 2 runs it exceeds the rate
def get_all_artists_from_playlists(access_token, playlists):
    unique_artist_hrefs = []
    unique_artists = []
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    max_number_of_tracks_to_return = 50

    for playlist in playlists:
        href = playlist["tracks"]["href"]
        number_of_tracks = playlist["tracks"]["total"]
        tracks_in_playlist = []
        i = 0
        #get all the tracks in the playlist
        for i in range(number_of_tracks//max_number_of_tracks_to_return):
            offset = max_number_of_tracks_to_return*i
            params = {"limit": max_number_of_tracks_to_return, "offset": offset}
            response = requests.get(href, params=params, headers=headers)
            response_data = response.json()
            tracks_in_playlist.extend(response_data.get("items", []))
        offset = max_number_of_tracks_to_return*(i+1)
        limit = number_of_tracks%max_number_of_tracks_to_return
        params = {"limit": limit, "offset": offset}
        response = requests.get(href, params=params, headers=headers)
        response_data = response.json()
        tracks_in_playlist.extend(response_data.get("items", []))
    
        #get all artists in the tracks present in the playlist
        for track in tracks_in_playlist:
            track_artists = track["track"]["artists"]
            for artist in track_artists:
                artist_href = artist["href"]
                if artist_href is None:
                    print(artist["name"], " href : ", artist_href, " from playlist ", playlist["name"]," already in list of artists in playlists")
                elif artist_href not in unique_artist_hrefs:
                    time.sleep(0.5)
                    unique_artist_hrefs.append(artist_href)
                    response = requests.get(artist_href, headers=headers)
                    if response.status_code == 200:
                        try:
                            artist_info = response.json()
                            unique_artists.append(artist_info)
                        except requests.exceptions.JSONDecodeError as e:
                            logging.error("Error: %s", e)
                    else:
                        # Request failed
                        logging.error("Request failed with status code: %s %s", response.status_code, response.text)
                        exit()
                else:
                    print(artist["name"], " from playlist ", playlist["name"]," already in list of artists in playlists")
        time.sleep(5)

    return unique_artists


def get_artists_info_from_artist_hrefs(access_token, artist_hrefs):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    artist_list = []
    for artist_href in artist_hrefs:
        response = requests.get(artist_href, headers=headers)
        if response.status_code == 200:
            artist_list.append(response.json())
        else:
            # Request failed
            logging.error("Request failed with status code: %s %s", response.status_code, response.text)
            exit()
    
    return artist_list


def get_all_artists_listenned_to(access_token):
    
    logging.info("getting all top tracks ...")
    all_top_tracks = get_user_items(access_token, "tracks")
    with open("../local_storage/all_top_tracks.json", "w") as f:
        json.dump(all_top_tracks, f)
    # with open("../local_storage/all_top_tracks.json", "r") as f:
    #     all_top_tracks = json.load(f)

    logging.info("getting all top artists ...")
    all_top_artists = get_user_items(access_token, "artists")
    for artist in all_top_artists:    
        artist.setdefault("sources", []).append("top_artists")
    with open("../local_storage/all_top_artists.json", "w") as f:
        json.dump(all_top_artists, f)
    # with open("../local_storage/all_top_artists.json", "r") as f:
    #     all_top_artists = json.load(f)

    logging.info("getting all playlists ...")
    all_playlists = get_user_items(access_token, "playlists")
    with open("../local_storage/all_playlists.json", "w") as f:
        json.dump(all_playlists, f)
    # with open("../local_storage/all_playlists.json", "r") as f:
    #     all_playlists = json.load(f)

    logging.info("getting all playlist artists ...")
    all_playlists_artists = get_all_artists_from_playlists(
        access_token,
        all_playlists
    )
    for artist in merged_artists:
        artist.setdefault("sources", []).append("playlists")
    with open("../local_storage/all_playlists_artists.json", "w") as f:
        json.dump(all_playlists_artists, f)
    # with open("../local_storage/all_playlists_artists.json", "r") as f:
    #     all_playlists_artists = json.load(f)
    
    merged_artists = all_playlists_artists
     
    temp_hrefs = [artist["href"] for artist in merged_artists]
    unique_artists_hrefs = set(temp_hrefs)
    artist_hrefs_missing_full_info = []

    for track in all_top_tracks:
        for artist in track.get("artists", []):
            artist_href = artist["href"]
            if artist_href not in unique_artists_hrefs:
                unique_artists_hrefs.add(artist_href)
                artist_hrefs_missing_full_info.append(artist_href)
            else:
                for merged_artist in merged_artists:
                    if merged_artist["href"] == artist_href :
                        if "top_tracks" not in merged_artist["sources"]:
                            merged_artist.setdefault("sources", []).append("top_tracks")
                        break

    artists_from_top_tracks = get_artists_info_from_artist_hrefs(access_token, artist_hrefs_missing_full_info)
    for artist in artists_from_top_tracks:
        artist.setdefault("sources", []).append("top_tracks")
    with open("../local_storage/artists_from_top_tracks.json", "w") as f:
        json.dump(artists_from_top_tracks, f)
    with open("../local_storage/artists_from_top_tracks.json", "r") as f:
        artists_from_top_tracks = json.load(f)
    
    for artist in artists_from_top_tracks:
        merged_artists.append(artist)

    for artist in all_top_artists:
        artist_href = artist["href"]
        if artist_href not in unique_artists_hrefs:
            unique_artists_hrefs.add(artist_href)
            merged_artists.append(artist)
        else:
            for merged_artist in merged_artists:
                if merged_artist["href"] == artist_href:
                    merged_artist.setdefault("sources", []).append("top_artists")
                    break

    return merged_artists


def get_recommendation_from_genre_and_artist(access_token, genre, artist, recommendation_url: str ="https://api.spotify.com/v1/recommendations"):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    params = {}
    params["seed_artists"] = artist
    params["seed_genres"] = genre
    params["limit"] = 5

    response = requests.get(recommendation_url, headers=headers, params=params)

    if response.status_code == 200:
        response_data = response.json()
        recommended_tracks = response_data
        return recommended_tracks["tracks"]
    else:
        # Request failed
        logging.error("Recommendation request failed with status code: %s, %s", response.status_code, response.text)
        exit()


def create_track_list(access_token, all_artists, no_recommendation_from_playlist_artists, length=100):
    genres_dict = {}
    for artist in all_artists:
        if "genres" in artist and artist["genres"]:
            for genre in artist["genres"]:
                if genre not in genres_dict.keys():
                    genres_dict[genre] = [ [
                        artist["id"],
                        artist["name"],
                        artist["sources"]
                    ]]
                else:
                    genres_dict[genre].append([artist["id"],artist["name"],artist["sources"]])
    all_artists_ids = [artist["id"] for artist in all_artists]
    logging.info("number of music genres %s", len(genres_dict))
    logging.info("number of artist ids %s", len(all_artists_ids))

    track_list = []
    artists_in_track_list_already = []
    logging.info("cooking playlist ... (it will take at least 100s)")
    for _ in range(50):
        choice_not_valid = True
        while choice_not_valid: 
            random_genre = random.choice(list(genres_dict.keys()))  
            random_artist = random.choice(genres_dict[random_genre])
            random_artist_id = random_artist[0]
            random_artist_name = random_artist[1]
            random_artist_sources = random_artist[2]
            if no_recommendation_from_playlist_artists:
                if random_artist_sources == ["playlists"]:
                    choice_not_valid = True
                else:
                    choice_not_valid = False
            else:
                choice_not_valid = False
        recommended_tracks = get_recommendation_from_genre_and_artist(
            access_token, random_genre, random_artist_id
        )
        logging.info(
            "artist sources %s", random_artist_sources
        )

        for track in recommended_tracks:
            recommended_artist_ids_in_track = [
                artist_in_track["id"] for artist_in_track in track["artists"]
            ]
            add_track = True
            for recommended_artist_id_in_track in recommended_artist_ids_in_track: # noqa: E501, E261
                if recommended_artist_id_in_track in artists_in_track_list_already:
                    add_track = False
                    logging.info(
                        "%s not added (artist already in generated tracklist)", track["name"]
                    )
                elif recommended_artist_id_in_track in all_artists_ids and add_track:
                    add_track = False
                    logging.info(
                        "%s not added (artist already in list of listened artists)", track["name"]
                    ) 
                elif track in track_list and add_track:
                    add_track = False
                    logging.info(
                        "%s not added (track already in generated tracklist)", track["name"]
                    )
            if add_track:
                track_list.append(track)
                logging.info(
                    "%s recommended from %s , %s, added", track["name"], random_genre, random_artist_name
                )
                for artist_id in recommended_artist_ids_in_track:
                    artists_in_track_list_already.append(artist_id)

        if len(track_list) > length:
            break
        time.sleep(5)
    logging.info("cooking finished :)")
    return track_list
