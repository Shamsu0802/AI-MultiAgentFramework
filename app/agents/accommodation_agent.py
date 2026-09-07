import re
import requests
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base_agent import BaseAgent


class AccommodationAgent(BaseAgent):
    """
    Accommodation Agent

    Responsibilities:
    1. Extract destination, duration, travelers and budget.
    2. Search real accommodation information using OpenStreetMap.
    3. Estimate accommodation costs deterministically.
    4. Return structured information for downstream agents.

    IMPORTANT:
    Trip information is extracted using a strict priority order.

    Priority:
        1. Explicit values in the raw user request
        2. Deterministic outputs from other agents
        3. Planner Agent output
        4. Structured context
        5. Safe fallback

    This prevents an incorrect Planner Agent value such as
    duration_days=1 from overriding an explicit user request
    such as "3 days".
    """

    def __init__(self):
        super().__init__(
            name="Accommodation Agent",
            description=(
                "Finds suitable accommodation options using "
                "OpenStreetMap data and provides estimated "
                "accommodation costs."
            )
        )

        # ======================================================
        # APIs
        # ======================================================

        self.nominatim_url = (
            "https://nominatim.openstreetmap.org/search"
        )

        self.overpass_urls = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"
        ]

        self.headers = {
            "User-Agent": "MultiAgentTravelPlanner/1.0"
        }

        # Maximum real accommodation options returned
        self.max_results = 5

        self.valid_accommodation_types = {
            "hotel",
            "guest_house",
            "hostel",
            "motel",
            "chalet",
            "apartment"
        }

    # ==========================================================
    # SAFE NUMBER
    # ==========================================================

    @staticmethod
    def _safe_number(
        value: Any,
        default: float = 0
    ) -> float:

        if isinstance(value, bool):
            return default

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()

            match = re.search(
                r"\d+(?:\.\d+)?",
                cleaned
            )

            if match:
                try:
                    return float(match.group())
                except ValueError:
                    pass

        return default

    # ==========================================================
    # SAFE INTEGER
    # ==========================================================

    @staticmethod
    def _safe_integer(
        value: Any,
        default: int = 0
    ) -> int:

        if isinstance(value, bool):
            return default

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):

            match = re.search(
                r"\d+",
                value
            )

            if match:
                try:
                    return int(match.group())
                except ValueError:
                    pass

        return default

    # ==========================================================
    # NORMALIZE TEXT
    # ==========================================================

    @staticmethod
    def _normalize_text(value: Any) -> str:

        if value is None:
            return ""

        return str(value).strip()

    # ==========================================================
    # DESTINATION EXTRACTION
    # ==========================================================

    def _extract_destination_from_text(
        self,
        text: str
    ) -> str:
        """Extract the destination only, never the origin suffix.

        Handles requests such as:
          - "3 days in Ooty for 2 people"
          - "trip from Chennai to Ooty for 3 days"
          - "travel to Ooty from Chennai for 3 days"
          - "Chennai to Ooty, 3 days, 2 travelers"
          - "destination: Ooty"
        """
        if not text:
            return ""

        text = str(text).strip()

        # Most specific destination forms first.  The look-ahead includes
        # "from" so a phrase like "to Ooty from Chennai" returns only Ooty.
        patterns = [
            r"\b(?:trip|travel|visit|vacation|holiday)\s+to\s+"
            r"([A-Za-z][A-Za-z .'-]*?)"
            r"(?=\s+(?:from|for|with|and|on|in|during|starting|leaving)\b|"
            r"\s+\d+\s*(?:days?|nights?|people|persons?|travelers?|travellers?)\b|"
            r"[,.;]|$)",

            r"\b(?:go|going|traveling|travelling)\s+to\s+"
            r"([A-Za-z][A-Za-z .'-]*?)"
            r"(?=\s+(?:from|for|with|and|on|in|during|starting|leaving)\b|"
            r"\s+\d+\s*(?:days?|nights?|people|persons?|travelers?|travellers?)\b|"
            r"[,.;]|$)",

            r"\bdestination\s*[:=-]\s*"
            r"([A-Za-z][A-Za-z .'-]*?)"
            r"(?=\s+(?:from|for|with|and|on|in|during)\b|[,.;]|$)",

            # "3 days in Ooty" / "vacation in Ooty"
            r"\b(?:in|at)\s+"
            r"([A-Za-z][A-Za-z .'-]*?)"
            r"(?=\s+(?:from|for|with|and|on|in|during|budget)\b|"
            r"\s+\d+\s*(?:days?|nights?|people|persons?|travelers?|travellers?)\b|"
            r"[,.;]|$)",

            # "to Ooty from Chennai"
            r"\bto\s+"
            r"([A-Za-z][A-Za-z .'-]*?)"
            r"(?=\s+(?:from|for|with|and|on|in|during|starting|leaving)\b|"
            r"\s+\d+\s*(?:days?|nights?|people|persons?|travelers?|travellers?)\b|"
            r"[,.;]|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                destination = match.group(1).strip(" ,.-")
                if destination:
                    # Defensive cleanup for malformed captures such as
                    # "Ooty from Chennai".  Keep only the destination side.
                    destination = re.split(
                        r"\s+(?:from|starting\s+from|leaving\s+from)\s+",
                        destination,
                        maxsplit=1,
                        flags=re.IGNORECASE
                    )[0].strip(" ,.-")
                    if destination:
                        return destination

        # Explicit origin -> destination form, e.g. "Chennai to Ooty".
        match = re.search(
            r"\bfrom\s+[A-Za-z][A-Za-z .'-]*?\s+to\s+"
            r"([A-Za-z][A-Za-z .'-]*?)"
            r"(?=\s+(?:for|with|and|on|in|during|from)\b|"
            r"\s+\d+\s*(?:days?|nights?|people|persons?|travelers?|travellers?)\b|"
            r"[,.;]|$)",
            text,
            re.IGNORECASE
        )
        if match:
            destination = match.group(1).strip(" ,.-")
            if destination:
                return destination

        return ""

    # ==========================================================
    # DESTINATION
    # ==========================================================

    def _get_destination(
        self,
        user_request: Any,
        planner_output: Dict[str, Any],
        research_output: Dict[str, Any],
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:

        context = context or {}

        # ------------------------------------------------------
        # 1. RAW USER REQUEST HAS HIGHEST PRIORITY
        # ------------------------------------------------------

        if isinstance(user_request, str):

            destination = (
                self._extract_destination_from_text(
                    user_request
                )
            )

            if destination:
                return destination

        # ------------------------------------------------------
        # 2. STRUCTURED USER REQUEST
        # ------------------------------------------------------

        if isinstance(user_request, dict):

            for field in [
                "destination",
                "place",
                "location"
            ]:

                value = user_request.get(field)

                if value:
                    return self._normalize_text(value)

        # ------------------------------------------------------
        # 3. RESEARCH OUTPUT
        # ------------------------------------------------------

        if isinstance(research_output, dict):

            destination = research_output.get(
                "destination",
                ""
            )

            if destination:
                return self._normalize_text(
                    destination
                )

        # ------------------------------------------------------
        # 4. OTHER AGENT OUTPUTS
        # ------------------------------------------------------

        for key in [
            "transportation_output",
            "itinerary_output",
            "budget_output",
            "review_output"
        ]:

            output = context.get(key)

            if isinstance(output, dict):

                destination = output.get(
                    "destination",
                    ""
                )

                if destination:
                    return self._normalize_text(
                        destination
                    )

        # ------------------------------------------------------
        # 5. PLANNER OUTPUT
        # ------------------------------------------------------

        if isinstance(planner_output, dict):

            request_analysis = planner_output.get(
                "request_analysis",
                {}
            )

            if isinstance(request_analysis, dict):

                destination = request_analysis.get(
                    "destination",
                    ""
                )

                if destination:
                    return self._normalize_text(
                        destination
                    )

        # ------------------------------------------------------
        # 6. TASK / FALLBACK TEXT
        # ------------------------------------------------------

        destination = (
            self._extract_destination_from_text(
                str(task or "")
            )
        )

        return destination

    # ==========================================================
    # DURATION FROM RAW TEXT
    # ==========================================================

    def _extract_duration_from_text(
        self,
        text: str
    ) -> int:

        if not text:
            return 0

        patterns = [

            # 3 days
            r"\b(\d+)\s*days?\b",

            # 3-day trip
            r"\b(\d+)\s*[-]?\s*day\s+"
            r"(?:trip|travel|vacation|holiday)\b",

            # trip for 3 days
            r"\bfor\s+(\d+)\s*days?\b",

            # stay for 3 days
            r"\bstay\s+for\s+(\d+)\s*days?\b",

            # duration: 3
            r"\bduration\s*[:=-]\s*(\d+)",

            # 3 nights -> convert to 4 days
            r"\b(\d+)\s*nights?\b"
        ]

        for index, pattern in enumerate(patterns):

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                value = int(
                    match.group(1)
                )

                if value > 0:

                    # If user explicitly says nights,
                    # convert nights to days.
                    if index == len(patterns) - 1:
                        return value + 1

                    return value

        return 0

    # ==========================================================
    # DURATION
    # ==========================================================

    def _get_duration(
        self,
        user_request: Any,
        planner_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> int:

        context = context or {}

        # ======================================================
        # IMPORTANT:
        # RAW USER REQUEST FIRST
        # ======================================================

        if isinstance(user_request, str):

            duration = (
                self._extract_duration_from_text(
                    user_request
                )
            )

            if duration > 0:

                print(
                    "[Accommodation Agent] "
                    f"Duration extracted from user request: "
                    f"{duration} day(s)"
                )

                return duration

        # ======================================================
        # STRUCTURED USER REQUEST
        # ======================================================

        if isinstance(user_request, dict):

            for field in [
                "duration_days",
                "duration",
                "days"
            ]:

                duration = self._safe_integer(
                    user_request.get(field),
                    0
                )

                if duration > 0:
                    return duration

        # ======================================================
        # DETERMINISTIC TRANSPORTATION OUTPUT
        # ======================================================

        transportation_output = context.get(
            "transportation_output",
            {}
        )

        if isinstance(
            transportation_output,
            dict
        ):

            for field in [
                "duration_days",
                "trip_duration_days",
                "days"
            ]:

                duration = self._safe_integer(
                    transportation_output.get(field),
                    0
                )

                if duration > 0:

                    print(
                        "[Accommodation Agent] "
                        f"Duration obtained from "
                        f"Transportation Agent: "
                        f"{duration} day(s)"
                    )

                    return duration

        # ======================================================
        # RESEARCH OUTPUT
        # ======================================================

        research_output = context.get(
            "research_output",
            {}
        )

        if isinstance(
            research_output,
            dict
        ):

            for field in [
                "duration_days",
                "trip_duration_days",
                "days"
            ]:

                duration = self._safe_integer(
                    research_output.get(field),
                    0
                )

                if duration > 0:
                    return duration

        # ======================================================
        # PLANNER OUTPUT - FALLBACK ONLY
        # ======================================================

        if isinstance(
            planner_output,
            dict
        ):

            request_analysis = planner_output.get(
                "request_analysis",
                {}
            )

            if isinstance(
                request_analysis,
                dict
            ):

                for field in [
                    "duration_days",
                    "duration",
                    "days"
                ]:

                    duration = self._safe_integer(
                        request_analysis.get(field),
                        0
                    )

                    if duration > 0:

                        print(
                            "[Accommodation Agent] "
                            f"Using Planner duration: "
                            f"{duration} day(s)"
                        )

                        return duration

        # ======================================================
        # TASK TEXT
        # ======================================================

        duration = (
            self._extract_duration_from_text(
                str(context.get("task", ""))
            )
        )

        if duration > 0:
            return duration

        # ======================================================
        # SAFE DEFAULT
        # ======================================================
        # Do not invent a trip duration. The caller will surface a clear
        # validation error instead of producing a misleading 0-night stay.
        return 0

    # ==========================================================
    # TRAVELERS FROM RAW TEXT
    # ==========================================================

    def _extract_travelers_from_text(
        self,
        text: str
    ) -> int:

        if not text:
            return 0

        patterns = [

            # 2 travelers
            r"\b(\d+)\s*"
            r"(?:travelers?|travellers?)\b",

            # 2 people
            r"\b(\d+)\s*people\b",

            # 2 persons
            r"\b(\d+)\s*persons?\b",

            # 2 adults
            r"\b(\d+)\s*adults?\b",

            # for 2
            r"\bfor\s+(\d+)\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                number = int(
                    match.group(1)
                )

                if number > 0:
                    return number

        return 0

    # ==========================================================
    # TRAVELERS
    # ==========================================================

    def _get_travelers(
        self,
        user_request: Any,
        planner_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> int:

        context = context or {}

        # ======================================================
        # 1. RAW USER REQUEST FIRST
        # ======================================================

        if isinstance(
            user_request,
            str
        ):

            travelers = (
                self._extract_travelers_from_text(
                    user_request
                )
            )

            if travelers > 0:

                print(
                    "[Accommodation Agent] "
                    f"Travelers extracted from "
                    f"user request: {travelers}"
                )

                return travelers

        # ======================================================
        # 2. STRUCTURED USER REQUEST
        # ======================================================

        if isinstance(
            user_request,
            dict
        ):

            for field in [
                "travelers",
                "number_of_travelers",
                "num_travelers",
                "number_of_people",
                "people"
            ]:

                value = self._safe_integer(
                    user_request.get(field),
                    0
                )

                if value > 0:
                    return value

        # ======================================================
        # 3. TRANSPORTATION AGENT
        # ======================================================

        transportation_output = context.get(
            "transportation_output",
            {}
        )

        if isinstance(
            transportation_output,
            dict
        ):

            for field in [
                "number_of_travelers",
                "travelers",
                "num_travelers",
                "number_of_people"
            ]:

                value = self._safe_integer(
                    transportation_output.get(field),
                    0
                )

                if value > 0:

                    print(
                        "[Accommodation Agent] "
                        f"Travelers obtained from "
                        f"Transportation Agent: {value}"
                    )

                    return value

        # ======================================================
        # 4. RESEARCH OUTPUT
        # ======================================================

        research_output = context.get(
            "research_output",
            {}
        )

        if isinstance(
            research_output,
            dict
        ):

            for field in [
                "number_of_travelers",
                "travelers",
                "num_travelers"
            ]:

                value = self._safe_integer(
                    research_output.get(field),
                    0
                )

                if value > 0:
                    return value

        # ======================================================
        # 5. PLANNER OUTPUT - FALLBACK
        # ======================================================

        if isinstance(
            planner_output,
            dict
        ):

            request_analysis = planner_output.get(
                "request_analysis",
                {}
            )

            if isinstance(
                request_analysis,
                dict
            ):

                for field in [
                    "travelers",
                    "number_of_travelers",
                    "num_travelers",
                    "number_of_people",
                    "people"
                ]:

                    value = self._safe_integer(
                        request_analysis.get(field),
                        0
                    )

                    if value > 0:

                        print(
                            "[Accommodation Agent] "
                            f"Using Planner travelers: "
                            f"{value}"
                        )

                        return value

        # ======================================================
        # SAFE DEFAULT
        # ======================================================
        # Do not invent the number of travelers.
        return 0

    # ==========================================================
    # BUDGET
    # ==========================================================

    def _extract_budget_from_text(
        self,
        text: str
    ) -> float:

        if not text:
            return 0

        patterns = [

            r"budget\s*(?:of|is|:)?\s*"
            r"(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?)",

            r"(?:₹|rs\.?|inr)\s*"
            r"([\d,]+(?:\.\d+)?)",

            r"\b(\d+(?:,\d+)*)\s*"
            r"(?:rupees|rs)\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                budget = self._safe_number(
                    match.group(1),
                    0
                )

                if budget > 0:
                    return budget

        return 0

    # ==========================================================
    # BUDGET
    # ==========================================================

    def _get_budget(
        self,
        user_request: Any,
        planner_output: Dict[str, Any]
    ) -> float:

        # ------------------------------------------------------
        # RAW USER REQUEST
        # ------------------------------------------------------

        if isinstance(
            user_request,
            str
        ):

            budget = (
                self._extract_budget_from_text(
                    user_request
                )
            )

            if budget > 0:
                return budget

        # ------------------------------------------------------
        # STRUCTURED USER REQUEST
        # ------------------------------------------------------

        if isinstance(
            user_request,
            dict
        ):

            for field in [
                "budget",
                "total_budget",
                "trip_budget"
            ]:

                value = self._safe_number(
                    user_request.get(field),
                    0
                )

                if value > 0:
                    return value

        # ------------------------------------------------------
        # PLANNER
        # ------------------------------------------------------

        if isinstance(
            planner_output,
            dict
        ):

            request_analysis = planner_output.get(
                "request_analysis",
                {}
            )

            if isinstance(
                request_analysis,
                dict
            ):

                for field in [
                    "budget",
                    "total_budget",
                    "trip_budget"
                ]:

                    value = self._safe_number(
                        request_analysis.get(field),
                        0
                    )

                    if value > 0:
                        return value

        return 0

    # ==========================================================
    # GET COORDINATES
    # ==========================================================

    def _get_coordinates(
        self,
        destination: str
    ) -> Optional[Tuple[float, float]]:

        if not destination:
            return None

        try:

            params = {
                "q": f"{destination}, India",
                "format": "json",
                "limit": 1
            }

            response = requests.get(
                self.nominatim_url,
                params=params,
                headers=self.headers,
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            if not data:
                return None

            latitude = float(
                data[0]["lat"]
            )

            longitude = float(
                data[0]["lon"]
            )

            return latitude, longitude

        except Exception as e:

            print(
                "[Accommodation Agent] "
                f"Geocoding failed: {e}"
            )

            return None

    # ==========================================================
    # SEARCH USING OVERPASS
    # ==========================================================

    def _search_overpass(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:

        query = f"""
        [out:json][timeout:15];

        (
            nwr["tourism"="hotel"]
            (around:10000,{latitude},{longitude});

            nwr["tourism"="hostel"]
            (around:10000,{latitude},{longitude});

            nwr["tourism"="guest_house"]
            (around:10000,{latitude},{longitude});

            nwr["tourism"="motel"]
            (around:10000,{latitude},{longitude});

            nwr["tourism"="chalet"]
            (around:10000,{latitude},{longitude});

            nwr["tourism"="apartment"]
            (around:10000,{latitude},{longitude});
        );

        out center tags;
        """

        for url in self.overpass_urls:

            try:

                print(
                    "[Accommodation Agent] "
                    f"Trying Overpass: {url}"
                )

                response = requests.post(
                    url,
                    data=query,
                    headers=self.headers,
                    timeout=20
                )

                response.raise_for_status()

                data = response.json()

                accommodations = []

                for element in data.get(
                    "elements",
                    []
                ):

                    tags = element.get(
                        "tags",
                        {}
                    )

                    name = tags.get(
                        "name"
                    )

                    if not name:
                        continue

                    # --------------------------------------------------
                    # Coordinates
                    # --------------------------------------------------

                    if (
                        "lat" in element
                        and "lon" in element
                    ):

                        latitude_value = (
                            element["lat"]
                        )

                        longitude_value = (
                            element["lon"]
                        )

                    elif "center" in element:

                        latitude_value = (
                            element["center"].get(
                                "lat"
                            )
                        )

                        longitude_value = (
                            element["center"].get(
                                "lon"
                            )
                        )

                    else:

                        latitude_value = None
                        longitude_value = None

                    # --------------------------------------------------
                    # Address
                    # --------------------------------------------------

                    address_parts = []

                    for key in [
                        "addr:housenumber",
                        "addr:street",
                        "addr:suburb",
                        "addr:city",
                        "addr:postcode",
                        "addr:state",
                        "addr:country"
                    ]:

                        if tags.get(key):

                            address_parts.append(
                                tags[key]
                            )

                    accommodation_type = (
                        tags.get(
                            "tourism",
                            "hotel"
                        )
                    )

                    if (
                        accommodation_type
                        not in self.valid_accommodation_types
                    ):
                        continue

                    accommodations.append(
                        {
                            "name": name,
                            "type": accommodation_type,
                            "description": tags.get(
                                "description",
                                ""
                            ),
                            "stars": tags.get(
                                "stars",
                                ""
                            ),
                            "address": ", ".join(
                                address_parts
                            ),
                            "latitude": latitude_value,
                            "longitude": longitude_value
                        }
                    )

                if accommodations:

                    return self._remove_duplicates(
                        accommodations
                    )

            except Exception as e:

                print(
                    "[Accommodation Agent] "
                    f"Overpass failed: {e}"
                )

        return []

    # ==========================================================
    # NOMINATIM FALLBACK
    # ==========================================================

    def _search_nominatim(
        self,
        destination: str
    ) -> List[Dict[str, Any]]:

        accommodations = []

        search_queries = [
            f"hotels in {destination}, India",
            f"guest houses in {destination}, India",
            f"hostels in {destination}, India",
            f"motels in {destination}, India"
        ]

        for query in search_queries:

            try:

                params = {
                    "q": query,
                    "format": "json",
                    "limit": 10,
                    "addressdetails": 1
                }

                response = requests.get(
                    self.nominatim_url,
                    params=params,
                    headers=self.headers,
                    timeout=10
                )

                response.raise_for_status()

                data = response.json()

                for item in data:

                    item_class = str(
                        item.get(
                            "class",
                            ""
                        )
                    ).strip().lower()

                    item_type = str(
                        item.get(
                            "type",
                            ""
                        )
                    ).strip().lower()

                    if item_class != "tourism":
                        continue

                    if (
                        item_type
                        not in self.valid_accommodation_types
                    ):
                        continue

                    name = item.get(
                        "name"
                    )

                    if not name:

                        display_name = item.get(
                            "display_name",
                            ""
                        )

                        name = (
                            display_name.split(",")[0]
                            if display_name
                            else ""
                        )

                    if not name:
                        continue

                    accommodations.append(
                        {
                            "name": name,
                            "type": item_type,
                            "description": (
                                f"Accommodation in "
                                f"{destination}."
                            ),
                            "stars": "",
                            "address": item.get(
                                "display_name",
                                ""
                            ),
                            "latitude": self._safe_number(
                                item.get("lat"),
                                0
                            ),
                            "longitude": self._safe_number(
                                item.get("lon"),
                                0
                            )
                        }
                    )

            except Exception as e:

                print(
                    "[Accommodation Agent] "
                    f"Nominatim search failed: {e}"
                )

        return self._remove_duplicates(
            accommodations
        )

    # ==========================================================
    # REMOVE DUPLICATES
    # ==========================================================

    @staticmethod
    def _remove_duplicates(
        accommodations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        unique = []
        seen = set()

        for accommodation in accommodations:

            name = str(
                accommodation.get(
                    "name",
                    ""
                )
            ).strip()

            normalized = name.lower()

            if (
                name
                and normalized not in seen
            ):

                seen.add(normalized)

                unique.append(
                    accommodation
                )

        return unique

    # ==========================================================
    # PRICE ESTIMATION
    # ==========================================================

    def _estimate_price(
        self,
        accommodation: Dict[str, Any]
    ) -> float:

        accommodation_type = str(
            accommodation.get(
                "type",
                "hotel"
            )
        ).lower()

        stars = self._safe_number(
            accommodation.get(
                "stars",
                0
            ),
            0
        )

        # ------------------------------------------------------
        # Base rough price per room per night
        # ------------------------------------------------------

        if "hostel" in accommodation_type:

            price = 800

        elif "guest" in accommodation_type:

            price = 1200

        elif "motel" in accommodation_type:

            price = 1400

        elif "chalet" in accommodation_type:

            price = 2000

        elif "apartment" in accommodation_type:

            price = 1800

        else:

            price = 1500

        # ------------------------------------------------------
        # Star adjustment
        # ------------------------------------------------------

        if stars >= 5:

            price = 3500

        elif stars >= 4:

            price = 2500

        elif stars >= 3:

            price = 1800

        elif stars >= 2:

            price = 1500

        return float(price)

    # ==========================================================
    # ROOMS REQUIRED
    # ==========================================================

    @staticmethod
    def _calculate_rooms_required(
        travelers: int
    ) -> int:

        travelers = max(
            int(travelers),
            1
        )

        # Assume maximum 2 travelers per room.
        return max(
            1,
            (travelers + 1) // 2
        )

    # ==========================================================
    # GENERIC ACCOMMODATION ESTIMATE
    # ==========================================================

    def _estimate_generic_accommodation(
        self,
        destination: str,
        travelers: int,
        nights: int
    ) -> Dict[str, Any]:

        rooms_required = (
            self._calculate_rooms_required(
                travelers
            )
        )

        estimated_price_per_room = 1500

        estimated_total = (
            estimated_price_per_room
            * rooms_required
            * nights
        )

        return {
            "name": "Budget Hotel / Guest House",
            "type": "generic_estimate",
            "rooms_required": rooms_required,
            "estimated_price_per_room_per_night": (
                estimated_price_per_room
            ),
            "estimated_total_cost": round(
                estimated_total,
                2
            ),
            "price_type": "generic_estimate",
            "verified": False,
            "reason": (
                "No verified live accommodation listing "
                "was available. A generic budget accommodation "
                "estimate is provided only for trip-cost "
                "calculation."
            )
        }

    # ==========================================================
    # CREATE REAL OPTIONS
    # ==========================================================

    def _create_options(
        self,
        accommodation_data: List[Dict[str, Any]],
        nights: int,
        travelers: int
    ) -> List[Dict[str, Any]]:

        options = []

        rooms_required = (
            self._calculate_rooms_required(
                travelers
            )
        )

        for accommodation in accommodation_data[
            :self.max_results
        ]:

            price = self._estimate_price(
                accommodation
            )

            # Deterministic calculation.
            total = round(
                price
                * rooms_required
                * nights,
                2
            )

            options.append(
                {
                    "name": accommodation.get(
                        "name",
                        ""
                    ),
                    "type": accommodation.get(
                        "type",
                        "hotel"
                    ),
                    "rooms_required": rooms_required,
                    "estimated_price_per_room_per_night": (
                        price
                    ),
                    "estimated_total_cost": total,
                    "price_type": "rough_estimate",
                    "verified": True,
                    "address": accommodation.get(
                        "address",
                        ""
                    )
                }
            )

        return options

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ):

        # ======================================================
        # CONTEXT
        # ======================================================

        user_request = context.get(
            "user_request",
            task
        )

        planner_output = context.get(
            "planner_output",
            {}
        )

        research_output = context.get(
            "research_output",
            {}
        )

        # ======================================================
        # EXTRACT TRIP INFORMATION
        # ======================================================

        destination = self._get_destination(
            user_request=user_request,
            planner_output=planner_output,
            research_output=research_output,
            task=task,
            context=context
        )

        duration_days = self._get_duration(
            user_request=user_request,
            planner_output=planner_output,
            context=context
        )

        travelers = self._get_travelers(
            user_request=user_request,
            planner_output=planner_output,
            context=context
        )

        budget = self._get_budget(
            user_request=user_request,
            planner_output=planner_output
        )

        # ======================================================
        # CRITICAL VALIDATION
        # ======================================================

        duration_days = int(duration_days or 0)
        travelers = int(travelers or 0)

        if duration_days <= 0:
            return {
                "error": "Trip duration could not be identified from the user request.",
                "destination": destination,
                "nights": 0,
                "number_of_travelers": max(travelers, 0),
                "rooms_required": self._calculate_rooms_required(travelers) if travelers > 0 else 0,
                "accommodation_options": [],
                "recommended_option": {},
                "accommodation_budget_estimate": 0,
                "accommodation_summary": "Accommodation cannot be calculated until the trip duration is known.",
                "price_note": "No duration was invented by the Accommodation Agent.",
                "data_source": "Validation",
                "trip_duration_days": 0,
                "total_trip_budget": budget,
                "verified_accommodation_found": False
            }

        if travelers <= 0:
            return {
                "error": "Number of travelers could not be identified from the user request.",
                "destination": destination,
                "nights": max(duration_days - 1, 0),
                "number_of_travelers": 0,
                "rooms_required": 0,
                "accommodation_options": [],
                "recommended_option": {},
                "accommodation_budget_estimate": 0,
                "accommodation_summary": "Accommodation cannot be calculated until the number of travelers is known.",
                "price_note": "No traveler count was invented by the Accommodation Agent.",
                "data_source": "Validation",
                "trip_duration_days": duration_days,
                "total_trip_budget": budget,
                "verified_accommodation_found": False
            }

        # ======================================================
        # NIGHTS
        #
        # 1 day  -> 0 nights
        # 2 days -> 1 night
        # 3 days -> 2 nights
        # 4 days -> 3 nights
        # ======================================================

        nights = max(
            duration_days - 1,
            0
        )

        rooms_required = (
            self._calculate_rooms_required(
                travelers
            )
        )

        print(
            "\n"
            "[Accommodation Agent] "
            "FINAL TRIP INFORMATION"
        )

        print(
            "[Accommodation Agent] "
            f"Destination: {destination}"
        )

        print(
            "[Accommodation Agent] "
            f"Duration: {duration_days} day(s)"
        )

        print(
            "[Accommodation Agent] "
            f"Nights: {nights}"
        )

        print(
            "[Accommodation Agent] "
            f"Travelers: {travelers}"
        )

        print(
            "[Accommodation Agent] "
            f"Rooms required: {rooms_required}"
        )

        print(
            "[Accommodation Agent] "
            f"Budget: ₹{budget}"
        )

        # ======================================================
        # DESTINATION VALIDATION
        # ======================================================

        if not destination:

            return {
                "error": (
                    "Destination could not be identified."
                ),
                "destination": "",
                "nights": nights,
                "number_of_travelers": travelers,
                "rooms_required": rooms_required,
                "accommodation_options": [],
                "recommended_option": {},
                "accommodation_budget_estimate": 0,
                "trip_duration_days": duration_days,
                "total_trip_budget": budget
            }

        # ======================================================
        # SEARCH
        # ======================================================

        print(
            "[Accommodation Agent] "
            f"Searching accommodations in "
            f"{destination}"
        )

        coordinates = self._get_coordinates(
            destination
        )

        accommodation_data = []

        source_used = "none"

        # ======================================================
        # OVERPASS
        # ======================================================

        if coordinates:

            latitude, longitude = coordinates

            print(
                "[Accommodation Agent] "
                f"Coordinates: "
                f"{latitude}, {longitude}"
            )

            accommodation_data = (
                self._search_overpass(
                    latitude,
                    longitude
                )
            )

            if accommodation_data:

                source_used = (
                    "OpenStreetMap"
                )

        # ======================================================
        # NOMINATIM FALLBACK
        # ======================================================

        if not accommodation_data:

            print(
                "[Accommodation Agent] "
                "Trying Nominatim..."
            )

            accommodation_data = (
                self._search_nominatim(
                    destination
                )
            )

            if accommodation_data:

                source_used = (
                    "OpenStreetMap"
                )

        # ======================================================
        # REAL ACCOMMODATION DATA
        # ======================================================

        if accommodation_data:

            options = self._create_options(
                accommodation_data,
                nights,
                travelers
            )

            if options:

                # --------------------------------------------------
                # IMPORTANT:
                # Cheapest total cost is selected.
                # --------------------------------------------------

                recommended = min(
                    options,
                    key=lambda option:
                    option[
                        "estimated_total_cost"
                    ]
                )

                recommended_option = {
                    "name": recommended[
                        "name"
                    ],
                    "type": recommended[
                        "type"
                    ],
                    "rooms_required": recommended[
                        "rooms_required"
                    ],
                    "estimated_price_per_room_per_night": (
                        recommended[
                            "estimated_price_per_room_per_night"
                        ]
                    ),
                    "estimated_total_cost": (
                        recommended[
                            "estimated_total_cost"
                        ]
                    ),
                    "verified": True,
                    "reason": (
                        "Selected as the lowest "
                        "estimated-cost verified "
                        "accommodation option."
                    )
                }

                result = {

                    "destination": destination,

                    "nights": nights,

                    "number_of_travelers": travelers,

                    "rooms_required": (
                        recommended[
                            "rooms_required"
                        ]
                    ),

                    "accommodation_options": (
                        options
                    ),

                    "recommended_option": (
                        recommended_option
                    ),

                    "accommodation_budget_estimate": (
                        recommended[
                            "estimated_total_cost"
                        ]
                    ),

                    "accommodation_summary": (
                        f"Found {len(options)} "
                        f"accommodation option(s) in "
                        f"{destination} for "
                        f"{nights} night(s)."
                    ),

                    "price_note": (
                        "Prices are rough estimated "
                        "room rates. OpenStreetMap "
                        "does not provide live booking "
                        "prices."
                    ),

                    "data_source": source_used,

                    "trip_duration_days": (
                        duration_days
                    ),

                    "total_trip_budget": budget,

                    "verified_accommodation_found": (
                        True
                    )
                }

                return result

        # ======================================================
        # NO REAL ACCOMMODATION DATA
        # ======================================================

        generic_option = (
            self._estimate_generic_accommodation(
                destination=destination,
                travelers=travelers,
                nights=nights
            )
        )

        generic_total = (
            generic_option[
                "estimated_total_cost"
            ]
        )

        print(
            "[Accommodation Agent] "
            "No verified accommodation listing found."
        )

        print(
            "[Accommodation Agent] "
            f"Using generic accommodation estimate: "
            f"₹{generic_total}"
        )

        return {

            "destination": destination,

            "nights": nights,

            "number_of_travelers": travelers,

            "rooms_required": (
                generic_option[
                    "rooms_required"
                ]
            ),

            "accommodation_options": [],

            "recommended_option": (
                generic_option
            ),

            "accommodation_budget_estimate": (
                generic_total
            ),

            "accommodation_summary": (
                f"No verified live hotel listings "
                f"were available for {destination}. "
                f"A generic budget accommodation "
                f"estimate has been provided for "
                f"{nights} night(s)."
            ),

            "price_note": (
                "This is a generic accommodation "
                "budget estimate, not a live hotel "
                "booking price. No hotel name has "
                "been invented."
            ),

            "data_source": (
                "Generic accommodation estimate"
            ),

            "trip_duration_days": (
                duration_days
            ),

            "total_trip_budget": budget,

            "verified_accommodation_found": (
                False
            )
        }
