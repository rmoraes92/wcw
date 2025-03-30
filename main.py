import asyncio
import sys
import aiohttp
from bs4 import BeautifulSoup
from glom import glom, Path
import json
import csv
from typing import List, Dict, Any
from logger import setup_logger

logger = setup_logger()


async def fetch_watchlist(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch the HTML content of the watchlist page."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            else:
                logger.error(f"Error: Received status code {response.status}")
                return ""
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return ""


def extract_movie_data(html_content: str) -> List[Dict[str, Any]]:
    """Extract movie data from the HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Find the script tag that contains the watchlist data
    script_tags = soup.find_all(
        "script", attrs={"id": "__NEXT_DATA__"}, type="application/json"
    )

    if not script_tags:
        return []

    try:
        data = json.loads(script_tags[0].string)
    except json.JSONDecodeError as ex:
        logger.error(f"err while deserializing __NEXT_DATA__: {ex}")
        return []

    ret = []

    # props.pageProps.mainColumnData.predefinedList.titleListItemSearch.edges[*].listItem.titleText.text

    for script in script_tags:
        try:
            # Check if this is the script containing our watchlist data
            edges = glom(
                data,
                Path(
                    "props",
                    "pageProps",
                    "mainColumnData",
                    "predefinedList",
                    "titleListItemSearch",
                    "edges",
                ),
                default=[],
            )
            for edge in edges:
                titletext = glom(
                    edge, Path("listItem", "titleText", "text"), default=None
                )
                releaseYear = glom(
                    edge,
                    Path("listItem", "releaseYear", "year"),
                    default=None,
                )
                if not titletext:
                    continue
                movie_data = {
                    "title": titletext,
                    "year": releaseYear,
                }
                ret.append(movie_data)

        except Exception as e:
            logger.warning(f"err while extracting data: {e}")
            continue

    return ret


def save_to_csv(
    movies: List[Dict[str, Any]], filename: str = "imdb_watchlist.csv"
) -> None:
    """Save the extracted movie data to a CSV file."""
    if not movies:
        logger.info("No movie data to save")
        return

    try:
        with open(filename, "w", newline="", encoding="utf-8") as file:
            fieldnames = movies[0].keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(movies)

        logger.info(f"Successfully saved {len(movies)} movies to {filename}")
    except Exception as e:
        logger.info(f"Error saving to CSV: {e}")


async def main():
    """Main function to execute the watchlist scraping."""
    watchlist_url = (
        sys.argv[1]
    )

    async with aiohttp.ClientSession() as session:
        html_content = await fetch_watchlist(session, watchlist_url)

    if html_content:
        movies = extract_movie_data(html_content)

        if movies:
            logger.info(f"Found {len(movies)} movies in watchlist")

            # Print first few movies
            # for i, movie in enumerate(movies[:5]):
            #     logger.info(f"{i+1}. {movie['title']} ({movie['year']}) - Rating: {movie['rating']}")

            # Save data to CSV
            save_to_csv(movies)
        else:
            logger.info("No movies found in watchlist")
    else:
        logger.warning("Failed to fetch watchlist data")


if __name__ == "__main__":
    asyncio.run(main())
