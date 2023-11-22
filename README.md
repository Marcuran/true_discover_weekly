# True Music Discovery

This script will allow you to get a true new music discovery! An improved version of your Discovery Weekly

## Before you start

* Log into the dashboard using your Spotify account (https://developer.spotify.com/dashboard).
* Create a new project using your account with only Web API enabled
* Add "http://localhost:8888/callback" and "http://localhost:8888" to the redirect uris

## Installation

Recommended --> Create a local environment
```bash
pip install -r requirements.txt
```

## Running the code

1. rename the template.env file into .env
2. copy your Client id you can find in the Web API dashboard of your project
3. paste it in the /src/.env
4. in a terminal from src run: 
```python src/main.py --collect_data --create_playlist```
5. Click on the link provided
6. Approve the connection
7. Copy the url when you will have approved the connection
8. Let the cook cook :) 

## License

Distributed under the MIT License. See LICENSE for more information.