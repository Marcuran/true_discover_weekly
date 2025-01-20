import unittest
from unittest.mock import patch, MagicMock
import json
import string
from src.spotify_api_interface import (
    check_access_token_valid,
    get_token_link,
    get_access_token,
    get_user_href,
    create_playlist,
    get_user_playlist,
    create_and_populate_playlist,
    get_user_items_page,
    get_user_items,
    get_all_tracks_from_playlists,
    get_all_artists_from_playlists,
    get_artists_info_from_artist_ids,
    get_recommendation_from_genre_and_artist,
    create_track_list,
    spotifyAccessTokenNotValidError,
    getUserItemsInterruptedError,
    SPOTIFY_ACCESS_TOKEN_NOT_VALID_ERROR_CODE
)

class TestSpotifyFunctions(unittest.TestCase):
    @patch("requests.get")
    def test_check_access_token_valid(self, mock_get):
        # Mocking a valid token response
        mock_get.return_value.status_code = 200
        access_token = "valid_token"
        self.assertTrue(check_access_token_valid(access_token))

        # Mocking an invalid token response
        mock_get.return_value.status_code = SPOTIFY_ACCESS_TOKEN_NOT_VALID_ERROR_CODE
        with self.assertRaises(spotifyAccessTokenNotValidError):
            check_access_token_valid(access_token)

    def test_get_token_link(self):
        client_id = "client_id"
        scope = "scope"
        code_verifier = "code_verifier"
        url = get_token_link(client_id, scope, code_verifier)
        self.assertIn("https://accounts.spotify.com/authorize", url)
        self.assertIn(client_id, url)

    @patch("requests.post")
    def test_get_access_token(self, mock_post):
        # Mocking a successful token response
        mock_post.return_value.json.return_value = {"access_token": "test_token"}
        access_token = get_access_token("client_id", "auth_code", "http://localhost", "code_verifier")
        self.assertEqual(access_token, "test_token")

    @patch("requests.get")
    def test_get_user_href(self, mock_get):
        # Mocking a successful user href fetch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"href": "test_href"}
        href = get_user_href("valid_token")
        self.assertEqual(href, "test_href")

    @patch("requests.post")
    def test_create_playlist(self, mock_post):
        # Mocking a successful playlist creation
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": "playlist_id"}
        playlist_id = create_playlist("valid_token", "user_href", "Test Playlist", "Description")
        self.assertEqual(playlist_id, "playlist_id")

    @patch("requests.get")
    def test_get_user_playlist(self, mock_get):
        # Mocking a successful playlist fetch
        mock_get.return_value.json.return_value = {"items": [{"id": "playlist1"}, {"id": "playlist2"}]}
        playlists = get_user_playlist("valid_token", 0)
        self.assertEqual(len(playlists), 2)

    @patch("requests.get")
    def test_get_user_items_page(self, mock_get):
        # Mocking a successful items fetch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"items": [{"id": "item1"}, {"id": "item2"}]}
        items = get_user_items_page("valid_token", "tracks", 10, 0)
        self.assertEqual(len(items), 2)

    @patch("requests.get")
    def test_get_all_tracks_from_playlists(self, mock_get):
        # Mocking track fetch
        mock_get.return_value.json.return_value = {"items": [{"track": {"id": "track1"}}, {"track": {"id": "track2"}}]}
        playlists = [{"tracks": {"href": "test_href"}}]
        tracks = get_all_tracks_from_playlists("valid_token", playlists)
        self.assertEqual(len(tracks), 2)

    @patch("requests.get")
    def test_get_recommendation_from_genre_and_artist(self, mock_get):
        # Mocking recommendations fetch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"tracks": [{"name": "Track1"}, {"name": "Track2"}]}
        tracks = get_recommendation_from_genre_and_artist("valid_token", "pop", "artist1")
        self.assertEqual(len(tracks), 2)
    
    @patch("src.spotify_api_interface.get_user_items_page")
    def test_access_token_error_handling(self, mock_get_user_items_page):
        # Mock `get_user_items_page` to raise `spotifyAccessTokenNotValidError` on the second call
        def mock_get_page(access_token, item_type, limit, offset, time_range):
            if offset == 2 and time_range == "medium_term":
                raise spotifyAccessTokenNotValidError()
            return [{"id": f"{time_range}_item{offset+i}"} for i in range(limit)]

        mock_get_user_items_page.side_effect = mock_get_page

        # Parameters for the test
        access_token = "valid_token"
        item_type = "tracks"
        limit = 2
        total_limit = 4
        start_offset = 0
        time_ranges = ["short_term", "medium_term"]

        # Capture the raised exception
        with self.assertRaises(getUserItemsInterruptedError) as context:
            get_user_items(
                access_token, 
                item_type, 
                limit=limit, 
                total_limit=total_limit, 
                start_offset=start_offset, 
                time_ranges=time_ranges,
                sleep_between_requests=0
            )

        exception = context.exception

        # Verify the exception has the correct attributes
        self.assertEqual(exception.collected_items, [{"id": "short_term_item0"}, {"id": "short_term_item1"}, {"id": "short_term_item2"}, {"id": "short_term_item3"}, {"id": "medium_term_item0"},{"id":"medium_term_item1"}])
        self.assertEqual(exception.offset, 2)
        self.assertEqual(exception.time_ranges_left, ["medium_term"])

    @patch("src.spotify_api_interface.get_user_items_page")
    def test_resume_correct_offset_and_time_ranges(self, mock_get_user_items_page):
        # Mock `get_user_items_page` to simulate fetching items
        def mock_get_page(access_token, item_type, limit, offset, time_range):
            return [{"id": f"{time_range}_item{offset+i}"} for i in range(limit)]

        mock_get_user_items_page.side_effect = mock_get_page

        # Simulate resuming from specific offset and time ranges
        access_token = "valid_token"
        item_type = "tracks"
        limit = 2
        total_limit = 4
        start_offset = 2
        time_ranges = ["medium_term", "long_term"]

        # Run the function
        result = get_user_items(
            access_token,
            item_type,
            limit=limit,
            total_limit=total_limit,
            start_offset=start_offset,
            time_ranges=time_ranges,
            sleep_between_requests=0
        )

        # Verify the correct calls were made
        expected_calls = [
            (access_token, item_type, limit, 2, "medium_term"),
            (access_token, item_type, limit, 0, "long_term"),
            (access_token, item_type, limit, 2, "long_term"),
        ]
        actual_calls = [call.args for call in mock_get_user_items_page.call_args_list]
        self.assertEqual(actual_calls, expected_calls)

        # Verify the resulting items
        self.assertEqual(result, [
            {"id": "medium_term_item2"}, {"id": "medium_term_item3"},
            {"id": "long_term_item0"}, {"id": "long_term_item1"}, {"id": "long_term_item2"},{"id": "long_term_item3"}
        ])

if __name__ == "__main__":
    unittest.main()
