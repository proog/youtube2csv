import csv
import json
import os
import sys

import requests

BASEURL = "https://www.googleapis.com/youtube/v3"


def chunklist(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def getallitems(url, params):
    response = requests.get(BASEURL + url, params)
    responsejson = response.json()
    items = responsejson.get("items", [])

    if "nextPageToken" in responsejson:
        nextpageparams = params.copy()
        nextpageparams["pageToken"] = responsejson["nextPageToken"]
        items.extend(getallitems(url, nextpageparams))

    return items


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


def main():
    apikey = os.environ["YOUTUBE_API_KEY"]
    username = sys.argv[1]

    print(f"Fetching channel playlist for {username}...")
    channel = getallitems(
        "/channels",
        params={
            "key": apikey,
            "maxResults": 50,
            "forUsername": username,
            "part": "contentDetails",
        },
    )[0]
    playlistid = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Found channel playlist {playlistid}.")

    print(f"Fetching uploaded items in {playlistid}...")
    uploadeditems = getallitems(
        "/playlistItems",
        params={
            "key": apikey,
            "maxResults": 50,
            "playlistId": playlistid,
            "part": "contentDetails",
        },
    )
    videoids = [item["contentDetails"]["videoId"] for item in uploadeditems]
    print(f"Found {len(videoids)} videos in {playlistid}.")

    videos = []
    for videoidchunk in chunklist(videoids, 20):
        videosinchunk = getallitems(
            "/videos",
            params={
                "key": apikey,
                "maxResults": 50,
                "part": "id,snippet,statistics",
                "id": ",".join(videoidchunk),
            },
        )
        videos.extend(videosinchunk)
        print(f"\rFetched {len(videos)}/{len(videoids)} videos...", end="")
    print()

    filename = f"{username}.csv"
    print(f"Saving results as {filename}...")
    savecsv(filename, videos)
    print("Done.")


if __name__ == "__main__":
    main()
