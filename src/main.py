from spotify_api_interface import (
    get_token,
    create_and_populate_playlist,
    get_all_artists_listenned_to,
    get_user_href,
    create_track_list,
    check_saved_access_token_valid,
)


import argparse
from dotenv import load_dotenv
import os
import logging
import json
from datetime import datetime
import sys

logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    filemode="w",
    format="%(name)s - %(levelname)s - %(message)s",
)
# Add a stream handler to log to the terminal
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Set the desired log level for terminal output
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# Add the console handler to the root logger
logging.getLogger().addHandler(console_handler)


def main():
    parser = argparse.ArgumentParser(description="User data collection and Playlist creation.")
    parser.add_argument("--collect_data", action="store_true", help="Collect new data")
    parser.add_argument("--create_playlist", action="store_true", help="Create playlist")
    parser.add_argument(
        "--no_recommendation_from_playlist_artists",
        action="store_true",
        help="do not include recommendations from playlist artists",
    )

    args = parser.parse_args()
    # Load environment variables from the .env file
    load_dotenv()

    # Access the client ID from the environment
    client_id = os.getenv("CLIENT_ID")
    if not client_id:
        logging.error("Client ID not found in the .env file.")
        exit()

    if not os.path.exists("../local_storage"):
        os.makedirs("../local_storage")
    try:
        with open("../local_storage/access_token.json", "r") as f:
            access_token = json.load(f).strip()
    except FileNotFoundError:
        logging.warning("access_token.json not found")
        access_token = "invalid token"
    except json.decoder.JSONDecodeError:
        logging.warning("access_token.json empty")
        access_token = "invalid token"

    if not check_saved_access_token_valid(access_token):
        access_token = get_token(
            client_id,
            "playlist-modify-private, \
            playlist-read-private, \
            playlist-read-collaborative, \
            user-top-read, \
            user-read-recently-played",
        )
        with open("../local_storage/access_token.json", "w") as f:
            json.dump(access_token, f)

    user_href = get_user_href(access_token)
    if args.collect_data:
        all_artists = get_all_artists_listenned_to(access_token)
        with open("../local_storage/all_artists_listenned_to.json", "w") as f:
            json.dump(all_artists, f)
    else:
        with open("../local_storage/all_artists_listenned_to.json", "r") as f:
            all_artists = json.load(f)

    if args.create_playlist:
        track_list = create_track_list(access_token, all_artists, args.no_recommendation_from_playlist_artists)
        with open("../local_storage/track_list.json", "w") as f:
            json.dump(track_list, f)
        with open("../local_storage/track_list.json", "r") as f:
            track_list = json.load(f)
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        playlist_name = "True discover weekly " + now
        create_and_populate_playlist(
            access_token,
            user_href,
            track_list,
            playlist_name=playlist_name,
            playlist_description="get truly never heard before music for you!",
        )


if __name__ == "__main__":
    main()
