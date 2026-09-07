import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.agents.base_agent import BaseAgent


class ResearchAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Research Agent",
            description=(
                "Researches any user-specified destination using the "
                "Geoapify Places API, verifies explicitly requested places "
                "within the destination area, provides descriptions for "
                "matched requested places, and suggests additional optional "
                "places separately."
            )
        )

        self.geoapify_api_key = os.getenv("GEOAPIFY_API_KEY")

        self.geoapify_base_url = "https://api.geoapify.com"

        self.request_timeout = 15

        # Maximum distance at which a requested place can be considered
        # part of the destination area.
        #
        # This prevents a place with the same name in another city/state
        # from being incorrectly selected.
        self.requested_place_max_distance_km = 75.0

    # ==============================================================
    # TEXT NORMALIZATION
    # ==============================================================

    @staticmethod
    def normalize_text(text: Any) -> str:

        if text is None:
            return ""

        text = str(text).lower().strip()

        text = re.sub(
            r"[^a-z0-9]+",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    @staticmethod
    def normalize_place_name(text: Any) -> str:

        return ResearchAgent.normalize_text(text)

    # ==============================================================
    # HAVERSINE DISTANCE
    # ==============================================================

    @staticmethod
    def calculate_distance_km(
        latitude1: float,
        longitude1: float,
        latitude2: float,
        longitude2: float
    ) -> float:

        radius = 6371.0

        lat1 = math.radians(latitude1)
        lat2 = math.radians(latitude2)

        delta_lat = math.radians(
            latitude2 - latitude1
        )

        delta_lon = math.radians(
            longitude2 - longitude1
        )

        a = (
            math.sin(delta_lat / 2) ** 2
            +
            math.cos(lat1)
            *
            math.cos(lat2)
            *
            math.sin(delta_lon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        return radius * c

    # ==============================================================
    # EXTRACT DESTINATION
    # ==============================================================

    def extract_destination(
        self,
        user_request: str,
        planner_output: Dict[str, Any],
        request_analysis: Dict[str, Any]
    ) -> Optional[str]:

        # ----------------------------------------------------------
        # 1. Planner request_analysis
        # ----------------------------------------------------------

        destination = request_analysis.get(
            "destination"
        )

        if destination:

            destination = str(
                destination
            ).strip()

            if destination:

                print(
                    "[Research Agent] Destination from planner: "
                    f"{destination}"
                )

                return destination

        # ----------------------------------------------------------
        # 2. planner_output
        # ----------------------------------------------------------

        if isinstance(
            planner_output,
            dict
        ):

            analysis = planner_output.get(
                "request_analysis",
                {}
            )

            if isinstance(
                analysis,
                dict
            ):

                destination = analysis.get(
                    "destination"
                )

                if destination:

                    destination = str(
                        destination
                    ).strip()

                    if destination:

                        print(
                            "[Research Agent] Destination from "
                            f"planner_output: {destination}"
                        )

                        return destination

        # ----------------------------------------------------------
        # 3. Regex fallback
        # ----------------------------------------------------------

        patterns = [

            r"\bto\s+([A-Za-z][A-Za-z\s\-]+?)"
            r"(?:\s+for\s+\d+|\s+from\s+|\.|,|$)",

            r"\bin\s+([A-Za-z][A-Za-z\s\-]+?)"
            r"(?:\s+for\s+\d+|\s+from\s+|\.|,|$)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                user_request,
                flags=re.IGNORECASE
            )

            if match:

                destination = match.group(
                    1
                ).strip()

                if destination:

                    print(
                        "[Research Agent] Destination extracted "
                        f"from user request: {destination}"
                    )

                    return destination

        return None

    # ==============================================================
    # EXTRACT USER REQUESTED PLACES
    # ==============================================================

    def extract_requested_places(
        self,
        user_request: str,
        request_analysis: Dict[str, Any]
    ) -> List[str]:

        requested_places: List[str] = []

        # ----------------------------------------------------------
        # 1. Planner requirements
        # ----------------------------------------------------------

        requirements = request_analysis.get(
            "requirements",
            []
        )

        if isinstance(
            requirements,
            list
        ):

            for requirement in requirements:

                if not isinstance(
                    requirement,
                    str
                ):
                    continue

                text = requirement.strip()

                if not text:
                    continue

                lower_text = text.lower()

                prefixes = [
                    "visit ",
                    "see ",
                    "explore ",
                    "go to ",
                    "go ",
                    "check out "
                ]

                place_name = text

                for prefix in prefixes:

                    if lower_text.startswith(
                        prefix
                    ):

                        place_name = text[
                            len(prefix):
                        ].strip()

                        break

                if any(
                    lower_text.startswith(prefix)
                    for prefix in prefixes
                ):

                    requested_places.append(
                        place_name
                    )

        # ----------------------------------------------------------
        # 2. Extract directly from user request if planner did not
        # provide requirements.
        # ----------------------------------------------------------

        if not requested_places:

            patterns = [

                r"visit\s+([^.;]+)",

                r"see\s+([^.;]+)",

                r"explore\s+([^.;]+)",

                r"go\s+to\s+([^.;]+)",

                r"check\s+out\s+([^.;]+)"
            ]

            for pattern in patterns:

                matches = re.findall(
                    pattern,
                    user_request,
                    flags=re.IGNORECASE
                )

                for match in matches:

                    # Split comma / "and"
                    parts = re.split(
                        r",|\band\b",
                        match,
                        flags=re.IGNORECASE
                    )

                    for part in parts:

                        place = part.strip()

                        if not place:
                            continue

                        # Remove trailing travel-related text.
                        place = re.sub(
                            r"\s+(?:for|from|during|on)\s+.*$",
                            "",
                            place,
                            flags=re.IGNORECASE
                        ).strip()

                        if place:
                            requested_places.append(
                                place
                            )

        # ----------------------------------------------------------
        # 3. Clean places
        # ----------------------------------------------------------

        unique_places = []

        seen = set()

        for place in requested_places:

            place = re.sub(
                r"\s+",
                " ",
                place.strip()
            )

            place = place.strip(
                " .,;:-"
            )

            normalized = self.normalize_place_name(
                place
            )

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            unique_places.append(
                place
            )

        print(
            "[Research Agent] Requested places: "
            f"{unique_places}"
        )

        return unique_places

    # ==============================================================
    # GET DESTINATION COORDINATES
    # ==============================================================

    def get_coordinates(
        self,
        destination: str
    ) -> Tuple[float, float]:

        url = (
            f"{self.geoapify_base_url}"
            "/v1/geocode/search"
        )

        params = {
            "text": destination,
            "limit": 5,
            "format": "json",
            "apiKey": self.geoapify_api_key
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=self.request_timeout
            )

            response.raise_for_status()

        except requests.RequestException as e:

            status_code = getattr(
                getattr(
                    e,
                    "response",
                    None
                ),
                "status_code",
                None
            )

            raise RuntimeError(
                "Geoapify geocoding request failed. "
                f"HTTP status: {status_code}. "
                f"Details: {str(e)}"
            ) from e

        try:

            data = response.json()

        except ValueError as e:

            raise RuntimeError(
                "Geoapify geocoding returned invalid JSON."
            ) from e

        results = data.get(
            "results",
            []
        )

        if not results:

            raise ValueError(
                f"Could not find coordinates for "
                f"destination '{destination}'."
            )

        # Prefer the first result that has valid coordinates.
        for result in results:

            latitude = result.get(
                "lat"
            )

            longitude = result.get(
                "lon"
            )

            if (
                latitude is not None
                and longitude is not None
            ):

                return (
                    float(latitude),
                    float(longitude)
                )

        raise ValueError(
            f"Coordinates are not available for "
            f"'{destination}'."
        )

    # ==============================================================
    # SEARCH GENERAL TOURIST PLACES
    # ==============================================================

    def get_places(
        self,
        latitude: float,
        longitude: float,
        radius: int = 15000
    ) -> Dict[str, Any]:

        url = (
            f"{self.geoapify_base_url}"
            "/v2/places"
        )

        params = {
            # Use the supported top-level tourism category. Geoapify
            # returns tourism subcategories such as attractions and sights
            # when the parent `tourism` category is requested.
            "categories": "tourism",

            "filter": (
                f"circle:{longitude},"
                f"{latitude},"
                f"{radius}"
            ),

            "bias": (
                f"proximity:{longitude},"
                f"{latitude}"
            ),

            "limit": 50,

            "apiKey": self.geoapify_api_key
        }

        print(
            "[Research Agent] Geoapify Places request categories: "
            f"{params['categories']}"
        )

        try:

            response = requests.get(
                url,
                params=params,
                timeout=self.request_timeout
            )

            response.raise_for_status()

        except requests.RequestException as e:

            status_code = getattr(
                getattr(
                    e,
                    "response",
                    None
                ),
                "status_code",
                None
            )

            response_text = ""

            if getattr(
                e,
                "response",
                None
            ) is not None:

                try:

                    response_text = (
                        e.response.text[:500]
                    )

                except Exception:
                    response_text = ""

            raise RuntimeError(
                "Geoapify Places API request failed. "
                f"HTTP status: {status_code}. "
                f"Response: {response_text}"
            ) from e

        try:

            return response.json()

        except ValueError as e:

            raise RuntimeError(
                "Geoapify Places API returned invalid JSON."
            ) from e

    # ==============================================================
    # SEARCH SPECIFIC USER REQUESTED PLACE
    # ==============================================================

    def search_specific_place(
        self,
        place_name: str,
        destination: str,
        destination_latitude: float,
        destination_longitude: float
    ) -> List[Dict[str, Any]]:

        url = (
            f"{self.geoapify_base_url}"
            "/v1/geocode/search"
        )

        search_text = (
            f"{place_name}, {destination}"
        )

        params = {
            "text": search_text,
            "limit": 10,
            "format": "json",
            "apiKey": self.geoapify_api_key
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=self.request_timeout
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as e:

            print(
                "[Research Agent] Specific place search "
                f"failed for '{place_name}': {e}"
            )

            return []

        except ValueError:

            print(
                "[Research Agent] Invalid JSON returned while "
                f"searching for '{place_name}'."
            )

            return []

        results = data.get(
            "results",
            []
        )

        if not results:
            return []

        normalized_requested = (
            self.normalize_place_name(
                place_name
            )
        )

        requested_words = set(
            normalized_requested.split()
        )

        candidates = []

        for result in results:

            name = result.get(
                "name",
                ""
            )

            if not name:
                continue

            latitude = result.get(
                "lat"
            )

            longitude = result.get(
                "lon"
            )

            if (
                latitude is None
                or longitude is None
            ):
                continue

            latitude = float(
                latitude
            )

            longitude = float(
                longitude
            )

            # ------------------------------------------------------
            # Distance validation
            #
            # This prevents:
            #
            # "Tea Factory, Ooty"
            #
            # from accidentally selecting a Tea Factory
            # hundreds of kilometres away.
            # ------------------------------------------------------

            distance = self.calculate_distance_km(
                destination_latitude,
                destination_longitude,
                latitude,
                longitude
            )

            if (
                distance
                > self.requested_place_max_distance_km
            ):

                continue

            normalized_name = (
                self.normalize_place_name(
                    name
                )
            )

            name_words = set(
                normalized_name.split()
            )

            overlap = requested_words.intersection(
                name_words
            )

            if not overlap:
                continue

            # ------------------------------------------------------
            # Matching score
            # ------------------------------------------------------

            score = 0

            if (
                normalized_name
                == normalized_requested
            ):
                score += 100

            if (
                normalized_requested
                in normalized_name
            ):
                score += 50

            if (
                normalized_name
                in normalized_requested
            ):
                score += 40

            score += (
                len(overlap) * 10
            )

            # Prefer closer results.
            score -= (
                distance * 0.2
            )

            categories = result.get(
                "category",
                []
            )

            if not isinstance(
                categories,
                list
            ):
                categories = []

            candidates.append(
                {
                    "name": name,
                    "address": result.get(
                        "formatted",
                        ""
                    ),
                    "categories": categories,
                    "type": "requested_place",
                    "latitude": latitude,
                    "longitude": longitude,
                    "place_id": result.get(
                        "place_id"
                    ),
                    "requested_place": place_name,
                    "distance_from_destination_km": round(
                        distance,
                        2
                    ),
                    "_match_score": score
                }
            )

        candidates.sort(
            key=lambda x: x.get(
                "_match_score",
                0
            ),
            reverse=True
        )

        # Remove internal score before returning.
        for candidate in candidates:

            candidate.pop(
                "_match_score",
                None
            )

        return candidates

    # ==============================================================
    # PLACE TYPE
    # ==============================================================

    def get_place_type(
        self,
        categories: List[str]
    ) -> str:

        category_text = " ".join(
            str(category).lower()
            for category in categories
        )

        if "tourism.attraction" in category_text:
            return "attraction"

        if "tourism.sights" in category_text:
            return "sight"

        if "leisure.park" in category_text:
            return "park"

        if "natural" in category_text:
            return "nature"

        return "tourist_place"

    # ==============================================================
    # NORMALIZE GEOAPIFY PLACE
    # ==============================================================

    def normalize_place(
        self,
        place: Dict[str, Any]
    ) -> Dict[str, Any]:

        categories = place.get(
            "categories",
            []
        )

        if not isinstance(
            categories,
            list
        ):
            categories = []

        return {
            "name": place.get(
                "name",
                ""
            ),
            "address": place.get(
                "address",
                ""
            ),
            "categories": categories,
            "type": place.get(
                "type",
                self.get_place_type(
                    categories
                )
            ),
            "latitude": place.get(
                "latitude"
            ),
            "longitude": place.get(
                "longitude"
            ),
            "place_id": place.get(
                "place_id"
            ),
            "requested_place": place.get(
                "requested_place"
            ),
            "distance_from_destination_km": place.get(
                "distance_from_destination_km"
            )
        }

    # ==============================================================
    # REMOVE DUPLICATES
    # ==============================================================

    def remove_duplicates(
        self,
        places: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        unique_places = []

        seen_names = set()

        for place in places:

            name = str(
                place.get(
                    "name",
                    ""
                )
            ).strip()

            if not name:
                continue

            normalized_name = (
                self.normalize_place_name(
                    name
                )
            )

            if normalized_name in seen_names:
                continue

            seen_names.add(
                normalized_name
            )

            unique_places.append(
                place
            )

        return unique_places

    # ==============================================================
    # REMOVE DUPLICATES BY REQUESTED PLACE
    #
    # Important because a requested place can be found through:
    #
    # 1. Specific geocoding search
    # 2. General Places API
    #
    # We want ONE result per requested place.
    # ==============================================================

    def remove_requested_duplicates(
        self,
        places: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        unique_places = []

        seen_requested = set()

        for place in places:

            requested = place.get(
                "requested_place"
            )

            if not requested:
                continue

            normalized_requested = (
                self.normalize_place_name(
                    requested
                )
            )

            if (
                normalized_requested
                in seen_requested
            ):
                continue

            seen_requested.add(
                normalized_requested
            )

            unique_places.append(
                place
            )

        return unique_places

    # ==============================================================
    # RANK GENERIC PLACES
    # ==============================================================

    def rank_places(
        self,
        places: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        def score(place):

            categories = place.get(
                "categories",
                []
            )

            category_text = " ".join(
                str(category).lower()
                for category in categories
            )

            score_value = 0

            if "tourism.attraction" in category_text:
                score_value += 30

            if "tourism.sights" in category_text:
                score_value += 20

            if "leisure.park" in category_text:
                score_value += 15

            if "natural" in category_text:
                score_value += 15

            if place.get(
                "address"
            ):
                score_value += 5

            if (
                place.get("latitude") is not None
                and place.get("longitude") is not None
            ):
                score_value += 5

            return score_value

        return sorted(
            places,
            key=score,
            reverse=True
        )

    # ==============================================================
    # MATCH GENERAL PLACES WITH REQUESTED PLACES
    # ==============================================================

    def match_requested_places(
        self,
        places: List[Dict[str, Any]],
        requested_places: List[str]
    ) -> List[Dict[str, Any]]:

        matched = []

        for requested in requested_places:

            requested_normalized = (
                self.normalize_place_name(
                    requested
                )
            )

            requested_words = set(
                requested_normalized.split()
            )

            best_match = None
            best_score = 0

            for place in places:

                name = str(
                    place.get(
                        "name",
                        ""
                    )
                )

                name_normalized = (
                    self.normalize_place_name(
                        name
                    )
                )

                name_words = set(
                    name_normalized.split()
                )

                overlap = requested_words.intersection(
                    name_words
                )

                if not overlap:
                    continue

                score = len(
                    overlap
                ) * 10

                if (
                    requested_normalized
                    == name_normalized
                ):
                    score += 100

                elif (
                    requested_normalized
                    in name_normalized
                ):
                    score += 50

                # Prefer places that are closer.
                distance = place.get(
                    "distance_from_destination_km"
                )

                if distance is not None:

                    score -= (
                        float(distance) * 0.2
                    )

                if score > best_score:

                    best_score = score
                    best_match = place

            if best_match:

                copied = dict(
                    best_match
                )

                copied[
                    "requested_place"
                ] = requested

                matched.append(
                    copied
                )

        return matched

    # ==============================================================
    # CREATE DESCRIPTION FOR ANY PLACE
    # ==============================================================

    def create_description(
        self,
        place: Dict[str, Any]
    ) -> str:

        name = str(
            place.get(
                "name",
                "This place"
            )
        ).strip()

        requested = place.get(
            "requested_place"
        )

        categories = place.get(
            "categories",
            []
        )

        if not isinstance(
            categories,
            list
        ):
            categories = []

        category_text = " ".join(
            str(category).lower()
            for category in categories
        )

        # ----------------------------------------------------------
        # Requested place descriptions
        # ----------------------------------------------------------

        if requested:

            if (
                "lake" in name.lower()
                or "water" in category_text
            ):

                return (
                    f"{name} is a scenic lake or "
                    "water-based attraction in the destination, "
                    "making it a suitable place for sightseeing "
                    "and relaxation."
                )

            if (
                "garden" in name.lower()
                or "park" in category_text
                or "leisure.park" in category_text
            ):

                return (
                    f"{name} is a green and peaceful attraction "
                    "in the destination, offering visitors an "
                    "opportunity to enjoy nature, sightseeing, "
                    "and relaxation."
                )

            if (
                "peak" in name.lower()
                or "hill" in name.lower()
                or "mount" in name.lower()
                or "doddabetta" in name.lower()
                or "view" in name.lower()
            ):

                return (
                    f"{name} is a scenic highland or viewpoint "
                    "in the destination, offering an opportunity "
                    "to enjoy mountain scenery and sightseeing."
                )

            if (
                "tea" in name.lower()
                or "factory" in name.lower()
                or "estate" in name.lower()
            ):

                return (
                    f"{name} is a tea-related attraction in the "
                    "destination where visitors can explore the "
                    "local tea-growing and tea-production experience."
                )

            if "museum" in name.lower():

                return (
                    f"{name} is a cultural attraction in the "
                    "destination where visitors can explore local "
                    "history, culture, or exhibits."
                )

            if (
                "temple" in name.lower()
                or "church" in name.lower()
                or "mosque" in name.lower()
            ):

                return (
                    f"{name} is a notable cultural or religious "
                    "place in the destination and can be included "
                    "for sightseeing and cultural exploration."
                )

            if (
                "natural" in category_text
                or "nature" in category_text
            ):

                return (
                    f"{name} is a natural attraction in the "
                    "destination, making it suitable for nature "
                    "viewing, sightseeing, and relaxation."
                )

            if (
                "tourism.attraction" in category_text
                or "tourism.sights" in category_text
            ):

                return (
                    f"{name} is a tourist attraction in the "
                    "destination and can be included for "
                    "sightseeing and exploration."
                )

            return (
                f"{name} is a notable place in the destination "
                "that matches the user's requested location "
                "and can be included in the trip itinerary."
            )

        # ----------------------------------------------------------
        # Optional place descriptions
        # ----------------------------------------------------------

        if (
            "park" in category_text
            or "leisure.park" in category_text
        ):

            return (
                f"Optional place you can visit in the destination: "
                f"{name} is a green space suitable for a relaxed "
                "walk and sightseeing."
            )

        if (
            "natural" in category_text
            or "nature" in category_text
        ):

            return (
                f"Optional place you can visit in the destination: "
                f"{name} is a natural attraction suitable for "
                "nature lovers and sightseeing."
            )

        if (
            "tourism.attraction" in category_text
            or "tourism.sights" in category_text
        ):

            return (
                f"Optional place you can visit in the destination: "
                f"{name} is a tourist attraction identified "
                "through Geoapify."
            )

        return (
            f"Optional place you can visit in the destination: "
            f"{name} is a tourist place identified through "
            "Geoapify."
        )

    # ==============================================================
    # BUILD FINAL ATTRACTION
    # ==============================================================

    def build_attraction(
        self,
        place: Dict[str, Any]
    ) -> Dict[str, Any]:

        requested = place.get(
            "requested_place"
        )

        is_requested = bool(
            requested
        )

        return {
            "name": place.get(
                "name",
                ""
            ),

            "type": place.get(
                "type",
                "tourist_place"
            ),

            "description": self.create_description(
                place
            ),

            "estimated_cost": 0,

            "cost_status": "unknown",

            "address": place.get(
                "address",
                ""
            ),

            "latitude": place.get(
                "latitude"
            ),

            "longitude": place.get(
                "longitude"
            ),

            "place_id": place.get(
                "place_id"
            ),

            "requested_place": requested,

            "is_requested": is_requested,

            "is_optional": not is_requested,

            "distance_from_destination_km": place.get(
                "distance_from_destination_km"
            )
        }

    # ==============================================================
    # FRONTEND PLACE FORMAT
    # ==============================================================
    #
    # The frontend only needs name, description and address.
    # Backend attractions retain additional fields for downstream
    # itinerary planning.
    # ==============================================================

    @staticmethod
    def frontend_place(
        place: Dict[str, Any]
    ) -> Dict[str, str]:

        return {
            "name": str(
                place.get("name") or ""
            ).strip(),
            "description": str(
                place.get("description") or ""
            ).strip(),
            "address": str(
                place.get("address") or ""
            ).strip()
        }

    # MAIN AGENT
    # ==============================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ):

        user_request = context.get(
            "user_request",
            task
        )

        planner_output = context.get(
            "planner_output",
            {}
        )

        request_analysis = context.get(
            "request_analysis",
            {}
        )

        print(
            "\n[Research Agent] Context keys: "
            f"{list(context.keys())}"
        )

        # ==========================================================
        # CHECK API KEY
        # ==========================================================

        if not self.geoapify_api_key:

            return {
                "error": (
                    "GEOAPIFY_API_KEY is not configured. "
                    "Please add GEOAPIFY_API_KEY to your .env file."
                )
            }

        # ==========================================================
        # EXTRACT DESTINATION
        # ==========================================================

        destination = self.extract_destination(
            user_request,
            planner_output,
            request_analysis
        )

        if not destination:

            return {
                "error": (
                    "Research Agent could not determine "
                    "the destination from the user request."
                )
            }

        print(
            "[Research Agent] Destination: "
            f"{destination}"
        )

        # ==========================================================
        # EXTRACT REQUESTED PLACES
        # ==========================================================

        requested_places = (
            self.extract_requested_places(
                user_request,
                request_analysis
            )
        )

        # ==========================================================
        # GET DESTINATION COORDINATES
        # ==========================================================

        try:

            latitude, longitude = (
                self.get_coordinates(
                    destination
                )
            )

        except (
            requests.RequestException,
            RuntimeError,
            ValueError
        ) as e:

            return {
                "error": (
                    "Geoapify API request failed "
                    "while finding destination coordinates."
                ),
                "details": str(e),
                "destination": destination
            }

        print(
            "[Research Agent] Coordinates: "
            f"{latitude}, {longitude}"
        )

        # ==========================================================
        # SEARCH REQUESTED PLACES
        # ==========================================================

        requested_results: List[
            Dict[str, Any]
        ] = []

        matched_requested_place_names = set()

        for requested_place in requested_places:

            print(
                "[Research Agent] Searching specifically for: "
                f"{requested_place}"
            )

            matches = self.search_specific_place(
                requested_place,
                destination,
                latitude,
                longitude
            )

            if matches:

                best_match = matches[0]

                requested_results.append(
                    best_match
                )

                matched_requested_place_names.add(
                    self.normalize_place_name(
                        requested_place
                    )
                )

                print(
                    "[Research Agent] Found requested place: "
                    f"{best_match['name']} "
                    f"({best_match.get('distance_from_destination_km')} km)"
                )

            else:

                print(
                    "[Research Agent] Could not find "
                    f"'{requested_place}' within the destination area."
                )

        # ==========================================================
        # GET GENERAL TOURIST PLACES
        # ==============================================================

        try:

            places_data = self.get_places(
                latitude,
                longitude
            )

        except RuntimeError as e:

            print(
                "[Research Agent] General place search failed: "
                f"{e}"
            )

            # We can still return explicitly requested places.
            requested_only = (
                self.remove_requested_duplicates(
                    requested_results
                )
            )

            attractions = [
                self.build_attraction(
                    place
                )
                for place in requested_only
            ]

            matched_details = [
                self.build_attraction(
                    place
                )
                for place in requested_only
            ]

            matched_names = [
                place.get(
                    "requested_place"
                )
                for place in requested_only
                if place.get(
                    "requested_place"
                )
            ]

            unmatched = [
                requested
                for requested in requested_places
                if self.normalize_place_name(
                    requested
                )
                not in {
                    self.normalize_place_name(
                        name
                    )
                    for name in matched_names
                }
            ]

            return {
                "destination": destination,

                "requested_places": requested_places,

                # Names only - compatibility with other agents.
                "matched_requested_place_names": (
                    matched_names
                ),

                # Full information including descriptions.
                "matched_requested_places": (
                    matched_details
                ),

                "unmatched_requested_places": (
                    unmatched
                ),

                "unmatched_requested_places_intro": (
                    (
                        "The following requested places could not be "
                        "confidently found in the destination area."
                    )
                    if unmatched
                    else
                    (
                        "No unmatched requested places. "
                        "All the places you requested were found."
                    )
                ),

                "attractions": attractions,

                "optional_places": [],

                "optional_places_intro": (
                    f"Other than the places you requested, "
                    f"you can also visit these places in {destination} "
                    f"if you have extra time."
                ),

                "activities": [],

                "research_summary": (
                    f"Research for {destination} identified "
                    f"{len(matched_names)} of "
                    f"{len(requested_places)} requested places. "
                    "Additional tourist-place research could not "
                    "be completed."
                ),

                "api_source": "Geoapify",

                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                },

                "warning": str(e)
            }

        # ==========================================================
        # PARSE GENERAL PLACES
        # ==========================================================

        features = places_data.get(
            "features",
            []
        )

        places: List[
            Dict[str, Any]
        ] = []

        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            name = properties.get(
                "name"
            )

            if not name:
                continue

            categories = properties.get(
                "categories",
                []
            )

            if not isinstance(
                categories,
                list
            ):
                categories = []

            place_latitude = properties.get(
                "lat"
            )

            place_longitude = properties.get(
                "lon"
            )

            distance = None

            if (
                place_latitude is not None
                and place_longitude is not None
            ):

                try:

                    distance = self.calculate_distance_km(
                        latitude,
                        longitude,
                        float(place_latitude),
                        float(place_longitude)
                    )

                except (
                    ValueError,
                    TypeError
                ):
                    distance = None

            place = {
                "name": name,

                "address": properties.get(
                    "formatted",
                    ""
                ),

                "categories": categories,

                "type": self.get_place_type(
                    categories
                ),

                "latitude": place_latitude,

                "longitude": place_longitude,

                "place_id": properties.get(
                    "place_id"
                ),

                "distance_from_destination_km": (
                    round(
                        distance,
                        2
                    )
                    if distance is not None
                    else None
                )
            }

            places.append(
                place
            )

        # ==========================================================
        # REMOVE GENERAL DUPLICATES
        # ==========================================================

        places = self.remove_duplicates(
            places
        )

        # ==========================================================
        # MATCH REQUESTED PLACES AGAINST GENERAL RESULTS
        # ==============================================================

        generic_requested_matches = (
            self.match_requested_places(
                places,
                requested_places
            )
        )

        # ==========================================================
        # MERGE REQUESTED RESULTS
        #
        # Specific search gets priority.
        # Generic matching only fills missing requested places.
        # ==============================================================

        all_requested_matches = []

        all_requested_matches.extend(
            requested_results
        )

        already_matched_requested = {
            self.normalize_place_name(
                place.get(
                    "requested_place",
                    ""
                )
            )
            for place in requested_results
        }

        for place in generic_requested_matches:

            requested = self.normalize_place_name(
                place.get(
                    "requested_place",
                    ""
                )
            )

            if not requested:
                continue

            if requested in already_matched_requested:
                continue

            all_requested_matches.append(
                place
            )

            already_matched_requested.add(
                requested
            )

        # One result per requested place.
        all_requested_matches = (
            self.remove_requested_duplicates(
                all_requested_matches
            )
        )

        # ==========================================================
        # FIND MATCHED REQUESTED NAMES
        # ==============================================================

        matched_requested_names = []

        for place in all_requested_matches:

            requested = place.get(
                "requested_place"
            )

            if requested:

                matched_requested_names.append(
                    requested
                )

        # ==========================================================
        # FIND UNMATCHED REQUESTED PLACES
        #
        # IMPORTANT:
        # Only the user's requested places can appear here.
        #
        # Optional places NEVER go into this list.
        # ==============================================================

        matched_normalized = {
            self.normalize_place_name(
                name
            )
            for name in matched_requested_names
        }

        unmatched_requested_places = []

        for requested in requested_places:

            normalized = (
                self.normalize_place_name(
                    requested
                )
            )

            if normalized not in matched_normalized:

                unmatched_requested_places.append(
                    requested
                )

        # ==========================================================
        # RANK OPTIONAL / GENERAL PLACES
        # ==============================================================

        ranked_places = self.rank_places(
            places
        )

        # ==========================================================
        # BUILD FINAL ATTRACTIONS
        #
        # ORDER:
        #
        # 1. Requested places
        # 2. Optional places
        # ==============================================================

        final_places: List[
            Dict[str, Any]
        ] = []

        # ----------------------------------------------------------
        # Requested places first
        # ----------------------------------------------------------

        final_places.extend(
            all_requested_matches
        )

        requested_result_names = {
            self.normalize_place_name(
                place.get(
                    "name",
                    ""
                )
            )
            for place in all_requested_matches
        }

        # ----------------------------------------------------------
        # Add optional places
        # ----------------------------------------------------------

        optional_places_raw: List[
            Dict[str, Any]
        ] = []

        for place in ranked_places:

            name_normalized = (
                self.normalize_place_name(
                    place.get(
                        "name",
                        ""
                    )
                )
            )

            if not name_normalized:
                continue

            # Do not repeat requested attractions.
            if name_normalized in requested_result_names:
                continue

            optional_places_raw.append(
                place
            )

            # Keep total output manageable.
            if len(
                optional_places_raw
            ) >= 8:

                break

        final_places.extend(
            optional_places_raw
        )

        final_places = self.remove_duplicates(
            final_places
        )

        # ==============================================================
        # BUILD ATTRACTIONS
        # ==============================================================
        #
        # IMPORTANT:
        # Do NOT put matched requested places into the generic
        # 'attractions' field. They are already returned in
        # 'matched_requested_places' with their descriptions.
        #
        # Optional places are returned separately through
        # 'optional_places'.
        #
        # 'attractions' is the backend working list for downstream
        # agents such as the Itinerary Agent. Requested places are
        # kept first, followed by optional places.
        # ==============================================================

        attractions = []

        # BUILD MATCHED REQUESTED PLACE DETAILS
        #
        # THIS IS THE IMPORTANT NEW PART.
        #
        # Each matched requested place now has:
        #
        # name
        # description
        # address
        # coordinates
        # distance
        # etc.
        # ==============================================================

        matched_requested_place_details = []

        for place in all_requested_matches:

            detail = self.build_attraction(
                place
            )

            # Make sure this is clearly marked.
            detail[
                "is_requested"
            ] = True

            detail[
                "is_optional"
            ] = False

            matched_requested_place_details.append(
                detail
            )

        # ==========================================================
        # BUILD OPTIONAL PLACES
        # ==============================================================

        optional_places = []

        for place in optional_places_raw:

            detail = self.build_attraction(
                place
            )

            detail[
                "is_requested"
            ] = False

            detail[
                "is_optional"
            ] = True

            optional_places.append(
                detail
            )

        # ==========================================================
        # BUILD BACKEND ATTRACTIONS LIST
        # ==========================================================
        #
        # Requested places first, optional places afterwards.
        # This is for downstream agents, not direct frontend display.
        # ==============================================================

        attractions = (
            matched_requested_place_details
            + optional_places
        )

        # ==========================================================
        # OPTIONAL PLACE INTRODUCTION
        # ==============================================================

        optional_places_intro = (
            f"Other than the places you requested, "
            f"you can also visit these places in {destination} "
            f"if you have extra time."
        )

        # ==========================================================
        # RESEARCH SUMMARY
        # ==============================================================

        if requested_places:

            if unmatched_requested_places:

                research_summary = (
                    f"Research for {destination} identified "
                    f"{len(matched_requested_names)} of "
                    f"{len(requested_places)} requested places. "
                    f"{len(unmatched_requested_places)} requested "
                    "place(s) could not be confidently matched "
                    "within the destination area. Additional "
                    "tourist places are provided separately as "
                    "optional suggestions."
                )

            else:

                research_summary = (
                    f"Research for {destination} successfully "
                    f"matched all {len(requested_places)} "
                    "requested places. Each matched place includes "
                    "a description and location details. Additional "
                    "nearby tourist places are provided separately "
                    "as optional suggestions."
                )

        else:

            research_summary = (
                f"Research for {destination} found "
                f"{len(optional_places)} tourist places "
                "through Geoapify. Since no specific places were "
                "requested, the results are provided as optional "
                "suggestions."
            )

        # ==========================================================
        # UNMATCHED REQUESTED PLACES MESSAGE
        # ==============================================================
        #
        # Always return a clear statement for the frontend.
        # If every requested place was found, explicitly say so.
        # If some could not be found, keep their names in the list.
        # ==============================================================

        if unmatched_requested_places:
            unmatched_requested_places_intro = (
                "The following requested places could not be "
                "confidently found in the destination area."
            )
        else:
            unmatched_requested_places_intro = (
                "No unmatched requested places. "
                "All the places you requested were found."
            )

        # FINAL RESULT
        # ==============================================================

        frontend_matched_requested_places = [
            self.frontend_place(place)
            for place in matched_requested_place_details
        ]

        frontend_optional_places = [
            self.frontend_place(place)
            for place in optional_places
        ]

        result = {

            "destination": destination,

            # ------------------------------------------------------
            # User's explicit requests
            # ------------------------------------------------------

            "requested_places": requested_places,

            # ------------------------------------------------------
            # Clean frontend objects
            # ------------------------------------------------------

            "matched_requested_places": (
                frontend_matched_requested_places
            ),

            # ------------------------------------------------------
            # Names-only compatibility field
            # ------------------------------------------------------

            "matched_requested_place_names": (
                matched_requested_names
            ),

            # ------------------------------------------------------
            # ONLY unmatched user requests
            # ------------------------------------------------------

            "unmatched_requested_places": (
                unmatched_requested_places
            ),

            "unmatched_requested_places_intro": (
                unmatched_requested_places_intro
            ),

            # ------------------------------------------------------
            # Complete attractions
            # Requested first, optional afterwards
            # ------------------------------------------------------

            "attractions": attractions,

            # ------------------------------------------------------
            # Optional places separately
            # ------------------------------------------------------

            "optional_places_intro": (
                optional_places_intro
            ),

            "optional_places": frontend_optional_places,

            "activities": [],

            "research_summary": research_summary,

            "api_source": "Geoapify",

            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            }
        }

        # ==========================================================
        # LOGGING
        # ==============================================================

        print(
            "\n[Research Agent] Research completed."
        )

        print(
            "[Research Agent] Requested places: "
            f"{requested_places}"
        )

        print(
            "[Research Agent] Matched requested places: "
            f"{matched_requested_names}"
        )

        print(
            "[Research Agent] Unmatched requested places: "
            f"{unmatched_requested_places}"
        )

        print(
            "[Research Agent] Optional places: "
            f"{[p.get('name') for p in optional_places]}"
        )

        print(
            "[Research Agent] Backend attractions available: "
            f"{len(attractions)}"
        )

        return result

    # ==============================================================
    # CLEAN JSON RESPONSE
    #
    # Kept for compatibility with BaseAgent / older code.
    # ==============================================================

    @staticmethod
    def _clean_json_response(
        response: str
    ) -> str:

        if not response:

            raise ValueError(
                "LLM returned an empty response."
            )

        cleaned_response = str(
            response
        ).strip()

        if "```json" in cleaned_response:

            cleaned_response = (
                cleaned_response
                .replace(
                    "```json",
                    ""
                )
            )

        if "```" in cleaned_response:

            cleaned_response = (
                cleaned_response
                .replace(
                    "```",
                    ""
                )
            )

        start_index = (
            cleaned_response.find(
                "{"
            )
        )

        end_index = (
            cleaned_response.rfind(
                "}"
            )
        )

        if (
            start_index == -1
            or end_index == -1
        ):

            raise ValueError(
                "LLM returned invalid JSON."
            )

        return cleaned_response[
            start_index:
            end_index + 1
        ]