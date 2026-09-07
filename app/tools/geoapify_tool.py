import os
import requests


class GeoapifyTool:

    def __init__(self):
        self.api_key = os.getenv("GEOAPIFY_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEOAPIFY_API_KEY is not set."
            )

        self.base_url = (
            "https://api.geoapify.com/v2/places"
        )

    def search_places(
        self,
        latitude: float,
        longitude: float,
        category: str = "tourism",
        radius: int = 5000,
        limit: int = 10
    ):

        params = {
            "categories": category,
            "filter": (
                f"circle:{longitude},"
                f"{latitude},"
                f"{radius}"
            ),
            "limit": limit,
            "apiKey": self.api_key
        }

        response = requests.get(
            self.base_url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        places = []

        for feature in data.get(
            "features",
            []
        ):

            properties = feature.get(
                "properties",
                {}
            )

            places.append({
                "name": properties.get(
                    "name",
                    "Unknown"
                ),
                "address": properties.get(
                    "formatted",
                    ""
                ),
                "latitude": properties.get(
                    "lat"
                ),
                "longitude": properties.get(
                    "lon"
                ),
                "categories": properties.get(
                    "categories",
                    []
                )
            })

        return places