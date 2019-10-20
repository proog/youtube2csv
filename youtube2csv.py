import csv
import json
import os
import sys

import requests

BASEURL = "https://www.googleapis.com/youtube/v3"


def chunklist(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def unpaginateitems(url, params):
    response = requests.get(BASEURL + url, params)
    responsejson = response.json()
    yield from responsejson.get("items", [])

    if responsejson.get("nextPageToken", None):
        nextpageparams = params.copy()
        nextpageparams["pageToken"] = responsejson["nextPageToken"]
        yield from unpaginateitems(url, nextpageparams)


def savecsv(filename, videos):
    flattenedvideos = (
        {
            "id": v["id"],
            "publishedAt": v["snippet"]["publishedAt"],
            "title": v["snippet"]["title"],
            "tags": ",".join(v["snippet"].get("tags", "")),
            "views": v["statistics"].get("viewCount", 0),
            "likes": v["statistics"].get("likeCount", 0),
            "dislikes": v["statistics"].get("dislikeCount", 0),
            "comments": v["statistics"].get("commentCount", 0),
        }
        for v in videos
    )

    with open(filename, "w") as csvfile:
        fieldnames = [
            "id",
            "title",
            "publishedAt",
            "views",
            "likes",
            "dislikes",
            "comments",
            "tags",
        ]
        writer = csv.DictWriter(csvfile, fieldnames)
        writer.writeheader(),
        writer.writerows(flattenedvideos)


if __name__ == "__main__":
    APIKEY = os.environ["YOUTUBE_API_KEY"]
    username = sys.argv[1]

    print(f"Fetching channel playlist for {username}...")
    channel = next(
        unpaginateitems(
            "/channels",
            params={"key": APIKEY, "forUsername": username, "part": "contentDetails"},
        )
    )
    playlistid = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Found channel playlist {playlistid}.")

    print(f"Finding videos in {playlistid}...")
    playlistitems = unpaginateitems(
        "/playlistItems",
        params={
            "key": APIKEY,
            "maxResults": 50,
            "playlistId": playlistid,
            "part": "contentDetails",
        },
    )
    videoids = []
    for playlistitem in playlistitems:
        videoids.append(playlistitem["contentDetails"]["videoId"])
        print(f"\rFound {len(videoids)} videos...", end="")
    print()

    videos = []
    for chunk in chunklist(videoids, 50):
        videos.extend(
            unpaginateitems(
                "/videos",
                params={
                    "key": APIKEY,
                    "maxResults": 50,
                    "part": "id,snippet,statistics",
                    "id": ",".join(chunk),
                },
            )
        )
        print(f"\rFetched {len(videos)}/{len(videoids)} videos...", end="")
    print()

    filename = f"{username}.csv"
    print(f"Saving results as {filename}...")
    savecsv(filename, videos)
    print("Done.")
