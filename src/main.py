from spotify_api_interface import (
    create_and_populate_playlist,
    get_all_artists_listenned_to,
    create_track_list,
)
from true_discover import TrueDiscover, interruptionError

MAX_ERRORS = 10

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
        help="Do not include recommendations from playlist artists",
    )

    args = parser.parse_args()
    load_dotenv()  # Load environment variables from the .env file

    client_id = os.getenv("CLIENT_ID")
    if not client_id:
        logging.error("Client ID not found in the .env file.")
        exit()

    # Ensure local storage directory exists
    if not os.path.exists("../local_storage"):
        logging.info("Creating local storage directory.")
        os.makedirs("../local_storage")

    # Load access token from file
    try:
        with open("../local_storage/access_token.json", "r") as f:
            access_token = json.load(f).strip()
            logging.info("Access token successfully loaded.")
    except FileNotFoundError:
        logging.warning("access_token.json not found.")
        access_token = None
    except json.decoder.JSONDecodeError:
        logging.warning("access_token.json is empty or invalid.")
        access_token = None

    true_discover = TrueDiscover(client_id, access_token=access_token)

    # Check if the stored access token is valid
    if not true_discover.check_stored_access_token_still_valid():
        logging.info("Stored access token is invalid or expired. Starting authorization process.")
        try:
            access_token = true_discover.get_access_token_through_terminal()
            with open("../local_storage/access_token.json", "w") as f:
                json.dump(access_token, f)
                logging.info("New access token successfully saved.")
        except Exception as e:
            logging.error(f"Failed to retrieve access token: {e}")
            exit()

    resume = False
    retries_remaining = MAX_ERRORS

    if args.collect_data:
        logging.info("Starting data collection process.")
        while retries_remaining > 0:
            try:
                all_artists = true_discover.data_collection(resume=resume)
                logging.info("Data collection completed successfully.")
                break
            except interruptionError:
                logging.warning(f"Data collection interrupted. Resuming... {retries_remaining - 1} retries left.")
                resume = True
                retries_remaining -= 1

        if retries_remaining == 0:
            logging.error("Max retries reached. Data collection failed.")
            exit()

        # Save collected artist data
        try:
            with open("../local_storage/all_artists_listenned_to.json", "w") as f:
                json.dump(all_artists, f)
                logging.info("All artists data successfully saved.")
        except Exception as e:
            logging.error(f"Failed to save artist data: {e}")
            exit()
    else:
        logging.info("Loading previously collected artist data.")
        try:
            with open("../local_storage/all_artists_listenned_to.json", "r") as f:
                all_artists = json.load(f)
                logging.info("Artist data loaded successfully.")
        except FileNotFoundError:
            logging.error("Artist data file not found. Run with --collect_data to gather data first.")
            exit()
        except json.decoder.JSONDecodeError:
            logging.error("Artist data file is invalid. Run with --collect_data to gather data first.")
            exit()

    if args.create_playlist:
        logging.info("Starting playlist creation process.")
        try:
            user_href = true_discover.get_user_href()
            track_list = create_track_list(access_token, all_artists, args.no_recommendation_from_playlist_artists)

            # Save track list to file
            with open("../local_storage/track_list.json", "w") as f:
                json.dump(track_list, f)
                logging.info("Track list successfully saved.")

            # Reload track list to confirm
            with open("../local_storage/track_list.json", "r") as f:
                track_list = json.load(f)
                logging.debug("Track list successfully reloaded from file.")

            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            playlist_name = f"True Discover Weekly {now}"

            # Create and populate playlist
            create_and_populate_playlist(
                access_token,
                user_href,
                track_list,
                playlist_name=playlist_name,
                playlist_description="Get truly never-heard-before music for you!",
            )
            logging.info(f"Playlist '{playlist_name}' created successfully.")
        except Exception as e:
            logging.error(f"Failed to create playlist: {e}")
            exit()

if __name__ == "__main__":
    main()
