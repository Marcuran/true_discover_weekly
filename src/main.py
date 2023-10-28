from spotify_api_interface import (
    get_token,
    create_and_populate_playlist,
    get_all_artists_listenned_to,
    get_user_href,
    create_track_list,
)


from dotenv import load_dotenv
import os


def main():
    # Load environment variables from the .env file
    load_dotenv()

    # Access the client ID from the environment
    client_id = os.getenv("CLIENT_ID")
    if client_id:
        print(f"Developer Client ID: {client_id}")
    else:
        print("Client ID not found in the .env file.")
        exit()
    # TODO: reduce the scope to only necessary
    access_token = get_token(
        client_id,
        "user-read-private, \
        user-read-email, \
        playlist-modify-public, \
        playlist-modify-private, \
        playlist-read-private, \
        playlist-read-collaborative, \
        user-top-read, \
        user-read-recently-played, \
        user-library-modify, \
        user-library-read",
    )
    user_href = get_user_href(access_token)
    all_artists = get_all_artists_listenned_to(access_token)
    track_list = create_track_list(access_token, all_artists)
    create_and_populate_playlist(
        access_token,
        user_href,
        track_list,
        playlist_name="True discover weekly",
        playlist_description="get truly never heard before music for you!",
    )


if __name__ == "__main__":
    main()
