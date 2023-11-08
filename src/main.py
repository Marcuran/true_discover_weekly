from spotify_api_interface import (
    get_token,
    create_and_populate_playlist,
    get_all_artists_listenned_to,
    get_user_href,
    create_track_list,
)


from dotenv import load_dotenv
import os
import logging
import json
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

def main():
    # Load environment variables from the .env file
    load_dotenv()

    # Access the client ID from the environment
    client_id = os.getenv("CLIENT_ID")
    if not client_id:
        logging.error("Client ID not found in the .env file.")
        exit()
    access_token = get_token(
        client_id,
        "playlist-modify-private, \
        playlist-read-private, \
        playlist-read-collaborative, \
        user-top-read, \
        user-read-recently-played",
    )

    with open("access_token.json", "w") as f:
        json.dump(access_token, f)
    with open("access_token.json", "r") as f:
        access_token = json.load(f).strip()

    user_href = get_user_href(access_token)
    all_artists = get_all_artists_listenned_to(access_token)
    track_list = create_track_list(access_token, all_artists)
    with open("track_list.json", "w") as f:
        json.dump(track_list, f)
    with open("track_list.json", "r") as f:
        track_list = json.load(f)
    create_and_populate_playlist(
        access_token,
        user_href,
        track_list,
        playlist_name="True discover weekly",
        playlist_description="get truly never heard before music for you!",
    )


if __name__ == "__main__":
    main()
