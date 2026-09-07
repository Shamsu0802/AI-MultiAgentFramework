import csv
import json
import os
import re
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent


class TransportationAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Transportation Agent",
            description=(
                "Plans transportation using route-based transportation "
                "fares stored in a CSV dataset. It identifies arrival "
                "options, calculates traveler-based costs, handles "
                "missing origin or duration explicitly, and estimates "
                "local transportation when sufficient information is available."
            )
        )

        # ==========================================================
        # TRANSPORTATION CSV
        # ==========================================================

        self.transportation_rates_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transportation_rates.csv"
        )

        # Fallback for your exact project structure:
        #
        # app/
        #   agents/
        #       transportation_agent.py
        #   transportation_rates.csv
        #
        # The path above resolves automatically to:
        #
        # app/transportation_rates.csv
        #
        # If your file is elsewhere, you can change only this path.

        # ==========================================================
        # COMMON LOCATION ALIASES
        # ==========================================================

        self.location_aliases = {

            "ooty": "Ooty",
            "udhagamandalam": "Ooty",
            "udagamandalam": "Ooty",

            "chennai": "Chennai",
            "madras": "Chennai",

            "coimbatore": "Coimbatore",
            "kovai": "Coimbatore",

            "madurai": "Madurai",

            "salem": "Salem",

            "erode": "Erode",

            "tiruppur": "Tiruppur",
            "tirupur": "Tiruppur",

            "trichy": "Tiruchirappalli",
            "tiruchirappalli": "Tiruchirappalli",

            "tanjore": "Thanjavur",
            "thanjavur": "Thanjavur",

            "tirunelveli": "Tirunelveli",

            "thoothukudi": "Thoothukudi",
            "tuticorin": "Thoothukudi",

            "vellore": "Vellore",

            "kanchipuram": "Kancheepuram",
            "kancheepuram": "Kancheepuram",

            "krishnagiri": "Krishnagiri",

            "dharmapuri": "Dharmapuri",

            "dindigul": "Dindigul",

            "theni": "Theni",

            "karur": "Karur",

            "namakkal": "Namakkal",

            "cuddalore": "Cuddalore",

            "villupuram": "Viluppuram",
            "viluppuram": "Viluppuram",

            "kallakurichi": "Kallakurichi",

            "perambalur": "Perambalur",

            "ariyalur": "Ariyalur",

            "pudukkottai": "Pudukkottai",

            "sivaganga": "Sivaganga",

            "ramanathapuram": "Ramanathapuram",
            "ramnad": "Ramanathapuram",

            "virudhunagar": "Virudhunagar",

            "tenkasi": "Tenkasi",

            "nagapattinam": "Nagapattinam",

            "mayiladuthurai": "Mayiladuthurai",

            "thiruvarur": "Tiruvarur",
            "tiruvarur": "Tiruvarur",

            "tiruvannamalai": "Tiruvannamalai",

            "tiruvallur": "Tiruvallur",

            "chengalpattu": "Chengalpattu",

            "ranipet": "Ranipet",

            "tirupathur": "Tirupathur",

            "nilgiris": "Nilgiris",

            # Popular tourist destinations
            "munnar": "Munnar",
            "kodaikanal": "Kodaikanal",
            "kodai": "Kodaikanal",
            "yercaud": "Yercaud",
            "pondicherry": "Puducherry",
            "puducherry": "Puducherry",
            "mahabalipuram": "Mahabalipuram",
            "mamallapuram": "Mahabalipuram",
            "rameswaram": "Rameswaram",
            "kanyakumari": "Kanyakumari",
            "wayanad": "Wayanad",
            "mysore": "Mysore",
            "mysuru": "Mysore",
            "bangalore": "Bangalore",
            "bengaluru": "Bangalore",
            "hyderabad": "Hyderabad",
            "kochi": "Kochi",
            "alleppey": "Alappuzha",
            "alappuzha": "Alappuzha",
            "goa": "Goa",
            "ootacamund": "Ooty"
        }

        # ==========================================================
        # CSV DATA CACHE
        # ==========================================================

        self.transportation_rates: List[Dict[str, Any]] = []

        self.csv_load_error: str = ""

        self.load_transportation_rates()

    # ==========================================================
    # LOAD CSV
    # ==========================================================

    def load_transportation_rates(self) -> None:
        """
        Load transportation rates from transportation_rates.csv.

        Expected CSV columns can be similar to:

        origin,destination,mode,fare

        or:

        Origin,Destination,Mode,Fare

        Additional columns are preserved.
        """

        self.transportation_rates = []
        self.csv_load_error = ""

        file_path = self.transportation_rates_file

        if not os.path.exists(file_path):
            self.csv_load_error = (
                f"Transportation rates CSV was not found at: {file_path}"
            )
            return

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    self.csv_load_error = (
                        "Transportation rates CSV does not contain headers."
                    )
                    return

                for row in reader:

                    if not row:
                        continue

                    cleaned_row = {}

                    for key, value in row.items():

                        if key is None:
                            continue

                        cleaned_key = str(key).strip()

                        cleaned_value = (
                            str(value).strip()
                            if value is not None
                            else ""
                        )

                        cleaned_row[cleaned_key] = cleaned_value

                    self.transportation_rates.append(
                        cleaned_row
                    )

        except Exception as exc:

            self.csv_load_error = (
                f"Failed to load transportation rates CSV: {exc}"
            )

    # ==========================================================
    # NORMALIZE CSV COLUMN
    # ==========================================================

    @staticmethod
    def normalize_column_name(
        column_name: str
    ) -> str:

        return re.sub(
            r"[^a-z0-9]+",
            "_",
            str(column_name).strip().lower()
        ).strip("_")

    # ==========================================================
    # GET CSV VALUE
    # ==========================================================

    def get_csv_value(
        self,
        row: Dict[str, Any],
        possible_names: List[str]
    ) -> Optional[str]:

        normalized_row = {}

        for key, value in row.items():

            normalized_key = (
                self.normalize_column_name(key)
            )

            normalized_row[normalized_key] = value

        for name in possible_names:

            normalized_name = (
                self.normalize_column_name(name)
            )

            if normalized_name in normalized_row:

                value = normalized_row[
                    normalized_name
                ]

                if value not in (
                    None,
                    ""
                ):

                    return str(value).strip()

        return None

    # ==========================================================
    # NORMALIZE LOCATION
    # ==========================================================

    def normalize_location(
        self,
        location: str
    ) -> str:

        if not location:
            return "Unknown"

        location = str(
            location
        ).strip().lower()

        location = re.sub(
            r"\s+",
            " ",
            location
        )

        location = location.strip(
            " ,.-"
        )

        location = re.sub(
            r"\b(city|district|tamil\s+nadu)\b",
            "",
            location,
            flags=re.IGNORECASE
        ).strip()

        if not location:
            return "Unknown"

        if location in self.location_aliases:

            return self.location_aliases[
                location
            ]

        return location.title()

    # ==========================================================
    # EXTRACT ORIGIN FROM TEXT
    # ==========================================================

    def extract_origin_from_text(
        self,
        user_request: str
    ) -> str:

        if not user_request:
            return "Unknown"

        text = str(
            user_request
        ).strip().lower()

        # ======================================================
        # "from Chennai to Ooty"
        # ======================================================

        patterns = [

            r"\bfrom\s+([a-zA-Z][a-zA-Z\s.-]*?)\s+to\s+",

            r"\bstarting\s+from\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"\s+(?:to|for|with|and|on)\b",

            r"\bstart(?:ing)?\s+in\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"\s+(?:to|for|with|and|on)\b",

            r"\btravell?ing\s+from\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"\s+(?:to|for|with|and|on)\b",

            r"\btravel\s+from\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"\s+(?:to|for|with|and|on)\b",

            r"\bdepart(?:ing)?\s+from\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"\s+(?:to|for|with|and|on)\b",

            r"\bleav(?:ing|e)\s+from\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"\s+(?:to|for|with|and|on)\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                candidate = match.group(
                    1
                ).strip()

                normalized = (
                    self.normalize_location(
                        candidate
                    )
                )

                if normalized != "Unknown":
                    return normalized

        # ======================================================
        # Explicit "from Chennai"
        # ======================================================

        explicit_from_pattern = (
            r"\bfrom\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"(?=\s+(?:for|with|and|on|"
            r"\d+\s*days?|\d+\s*nights?|"
            r"budget|trip|vacation|holiday|$))"
        )

        match = re.search(
            explicit_from_pattern,
            text,
            re.IGNORECASE
        )

        if match:

            candidate = match.group(
                1
            ).strip()

            normalized = (
                self.normalize_location(
                    candidate
                )
            )

            if normalized != "Unknown":
                return normalized

        # ======================================================
        # "Chennai to Ooty"
        # ======================================================

        to_match = re.search(
            r"\b(.+?)\s+to\s+(.+)",
            text,
            re.IGNORECASE
        )

        if to_match:

            possible_origin = (
                to_match.group(1).strip()
            )

            known_locations = sorted(
                self.location_aliases.keys(),
                key=len,
                reverse=True
            )

            for location in known_locations:

                if re.search(
                    rf"\b{re.escape(location)}\b",
                    possible_origin,
                    re.IGNORECASE
                ):

                    return self.normalize_location(
                        location
                    )

        # ======================================================
        # IMPORTANT:
        # Do NOT assume that any known location appearing
        # in the request is the origin.
        #
        # This prevents:
        #
        # "Plan a trip to Ooty"
        #
        # from becoming:
        #
        # Origin = Ooty
        # ======================================================

        return "Unknown"

    # ==========================================================
    # EXTRACT ORIGIN FROM PLANNER
    # ==========================================================

    def extract_origin_from_planner(
        self,
        planner_output: Dict[str, Any]
    ) -> str:

        if not isinstance(
            planner_output,
            dict
        ):
            return "Unknown"

        request_analysis = (
            planner_output.get(
                "request_analysis",
                {}
            )
        )

        if not isinstance(
            request_analysis,
            dict
        ):
            return "Unknown"

        possible_fields = [

            "origin",
            "starting_location",
            "start_location",
            "departure_location",
            "from_location",
            "source",
            "from"
        ]

        for field in possible_fields:

            value = request_analysis.get(
                field
            )

            if value:

                normalized = (
                    self.normalize_location(
                        str(value)
                    )
                )

                if normalized != "Unknown":
                    return normalized

        return "Unknown"

    # ==========================================================
    # LLM ORIGIN FALLBACK
    # ==========================================================

    def extract_origin_with_llm(
        self,
        user_request: str
    ) -> str:

        prompt = f"""
Extract the starting location from this travel request.

USER REQUEST:
{user_request}

Rules:

- Return the city/location where the traveler starts.
- Do NOT assume Chennai.
- Do NOT assume Bangalore.
- Do NOT assume Coimbatore.
- Do NOT invent a location.
- If the starting location is not mentioned, return Unknown.

Examples:

"Plan a trip from Chennai to Ooty"
=> Chennai

"Travel from Madurai to Kodaikanal"
=> Madurai

"Plan a trip to Ooty"
=> Unknown

Return ONLY JSON:

{{
    "origin": "Unknown"
}}
"""

        try:

            response = self.llm.generate(
                prompt
            )

            cleaned_response = (
                self._clean_json_response(
                    response
                )
            )

            data = json.loads(
                cleaned_response
            )

            origin = data.get(
                "origin"
            )

            if not origin:
                return "Unknown"

            return self.normalize_location(
                str(origin)
            )

        except Exception:

            return "Unknown"

    # ==========================================================
    # FINAL ORIGIN EXTRACTION
    # ==========================================================

    def extract_origin(
        self,
        user_request: str,
        planner_output: Dict[str, Any]
    ) -> str:

        origin = (
            self.extract_origin_from_text(
                user_request
            )
        )

        if origin != "Unknown":
            return origin

        origin = (
            self.extract_origin_from_planner(
                planner_output
            )
        )

        if origin != "Unknown":
            return origin

        # LLM is only used to identify a missing origin.
        # It is NOT allowed to invent one.

        origin = (
            self.extract_origin_with_llm(
                user_request
            )
        )

        if origin != "Unknown":
            return origin

        return "Unknown"

    # ==========================================================
    # EXTRACT DESTINATION FROM TEXT
    # ==========================================================

    def extract_destination_from_text(
        self,
        user_request: str
    ) -> str:

        if not user_request:
            return "Unknown"

        text = str(
            user_request
        ).strip().lower()

        # ======================================================
        # "from Chennai to Ooty"
        # ======================================================

        match = re.search(
            r"\bto\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"(?=\s+(?:for|with|and|on|"
            r"\d+\s*days?|\d+\s*nights?|"
            r"budget|trip|vacation|holiday|"
            r"with\s+a|$))",
            text,
            re.IGNORECASE
        )

        if match:

            candidate = (
                match.group(1).strip()
            )

            normalized = (
                self.normalize_location(
                    candidate
                )
            )

            if normalized != "Unknown":
                return normalized

        # ======================================================
        # "trip to Ooty"
        # ======================================================

        match = re.search(
            r"\b(?:trip|travel|visit|vacation|holiday)"
            r"\s+to\s+"
            r"([a-zA-Z][a-zA-Z\s.-]*?)"
            r"(?=\s+(?:for|with|and|on|"
            r"\d+\s*days?|\d+\s*nights?|"
            r"budget|$))",
            text,
            re.IGNORECASE
        )

        if match:

            candidate = (
                match.group(1).strip()
            )

            normalized = (
                self.normalize_location(
                    candidate
                )
            )

            if normalized != "Unknown":
                return normalized

        return "Unknown"

    # ==========================================================
    # EXTRACT DURATION
    # ==========================================================

    def extract_duration(
        self,
        user_request: str,
        planner_output: Dict[str, Any]
    ) -> Optional[int]:

        request_analysis = (
            planner_output.get(
                "request_analysis",
                {}
            )
            if isinstance(
                planner_output,
                dict
            )
            else {}
        )

        if isinstance(
            request_analysis,
            dict
        ):

            duration = (
                request_analysis.get(
                    "duration_days"
                )
            )

            if isinstance(
                duration,
                int
            ) and duration > 0:

                return duration

            if isinstance(
                duration,
                float
            ) and duration > 0:

                return int(duration)

            if isinstance(
                duration,
                str
            ):

                match = re.search(
                    r"\d+",
                    duration
                )

                if match:
                    return int(
                        match.group()
                    )

        # ======================================================
        # Direct user request
        # ======================================================

        match = re.search(
            r"(\d+)\s*[-]?\s*days?",
            str(user_request).lower()
        )

        if match:

            return int(
                match.group(1)
            )

        # ======================================================
        # IMPORTANT:
        #
        # NEVER return 1 here.
        #
        # Missing duration = None
        # ======================================================

        return None

    # ==========================================================
    # EXTRACT NUMBER OF TRAVELERS
    # ==========================================================

    def extract_travelers(
        self,
        user_request: str,
        planner_output: Dict[str, Any]
    ) -> Optional[int]:

        request_analysis = (
            planner_output.get(
                "request_analysis",
                {}
            )
            if isinstance(
                planner_output,
                dict
            )
            else {}
        )

        if isinstance(
            request_analysis,
            dict
        ):

            possible_fields = [

                "travelers",
                "number_of_travelers",
                "num_travelers",
                "number_of_people",
                "people"
            ]

            for field in possible_fields:

                value = (
                    request_analysis.get(
                        field
                    )
                )

                if isinstance(
                    value,
                    int
                ) and value > 0:

                    return value

                if isinstance(
                    value,
                    float
                ) and value > 0:

                    return int(value)

                if isinstance(
                    value,
                    str
                ):

                    match = re.search(
                        r"\d+",
                        value
                    )

                    if match:

                        number = int(
                            match.group()
                        )

                        if number > 0:
                            return number

        text = str(
            user_request
        ).lower()

        patterns = [

            r"(\d+)\s*(?:people|persons|travelers|travellers)",

            r"for\s+(\d+)\s*(?:people|persons|travelers|travellers)",

            r"(\d+)\s*(?:adults?)",

            r"(\d+)\s*(?:members?)",

            r"(\d+)\s*(?:of\s+us)"
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

        # ======================================================
        # IMPORTANT:
        #
        # Do NOT default to 1.
        # ======================================================

        return None

    # ==========================================================
    # FIND ROUTE IN CSV
    # ==========================================================

    def find_route_rates(
        self,
        origin: str,
        destination: str
    ) -> List[Dict[str, Any]]:

        if (
            not origin
            or origin == "Unknown"
            or not destination
            or destination == "Unknown"
        ):
            return []

        origin_normalized = (
            self.normalize_location(
                origin
            ).lower()
        )

        destination_normalized = (
            self.normalize_location(
                destination
            ).lower()
        )

        matches = []

        for row in self.transportation_rates:

            csv_origin = self.get_csv_value(
                row,
                [
                    "origin",
                    "from",
                    "source",
                    "starting_location"
                ]
            )

            csv_destination = self.get_csv_value(
                row,
                [
                    "destination",
                    "to",
                    "destination_location"
                ]
            )

            if not csv_origin or not csv_destination:
                continue

            csv_origin_normalized = (
                self.normalize_location(
                    csv_origin
                ).lower()
            )

            csv_destination_normalized = (
                self.normalize_location(
                    csv_destination
                ).lower()
            )

            if (
                csv_origin_normalized
                == origin_normalized
                and
                csv_destination_normalized
                == destination_normalized
            ):

                matches.append(
                    row
                )

        return matches

    # ==========================================================
    # BUILD ARRIVAL OPTIONS FROM CSV
    # ==========================================================

    def build_arrival_options_from_csv(
        self,
        route_rows: List[Dict[str, Any]],
        origin: str,
        destination: str
    ) -> List[Dict[str, Any]]:

        options = []

        for row in route_rows:

            mode = self.get_csv_value(
                row,
                [
                    "mode",
                    "transport_mode",
                    "transportation_mode",
                    "vehicle"
                ]
            )

            fare_value = self.get_csv_value(
                row,
                [
                    "fare",
                    "cost",
                    "price",
                    "estimated_cost",
                    "rate",
                    "amount"
                ]
            )

            if not mode or fare_value is None:
                continue

            fare = self.safe_number(
                fare_value,
                default=-1
            )

            if fare < 0:
                continue

            description = self.get_csv_value(
                row,
                [
                    "description",
                    "details"
                ]
            )

            if not description:

                description = (
                    f"{mode} transportation "
                    f"from {origin} to {destination}."
                )

            options.append(
                {
                    "mode": mode.title(),
                    "description": description,
                    "estimated_cost": round(
                        fare,
                        2
                    ),
                    "cost_unit": "per_person",
                    "trip_direction": "one_way",
                    "cost_type": "dataset_rate"
                }
            )

        # ======================================================
        # Remove duplicate modes
        # ======================================================

        unique_options = []
        seen_modes = set()

        for option in options:

            mode_key = (
                option["mode"].strip().lower()
            )

            if mode_key in seen_modes:
                continue

            seen_modes.add(
                mode_key
            )

            unique_options.append(
                option
            )

        return unique_options

    # ==========================================================
    # SAFE NUMBER
    # ==========================================================

    @staticmethod
    def safe_number(
        value: Any,
        default: float = 0
    ) -> float:

        if isinstance(
            value,
            bool
        ):
            return default

        if isinstance(
            value,
            (int, float)
        ):
            return float(value)

        if isinstance(
            value,
            str
        ):

            match = re.search(
                r"\d+(?:\.\d+)?",
                value.replace(
                    ",",
                    ""
                )
            )

            if match:

                try:

                    return float(
                        match.group()
                    )

                except ValueError:
                    pass

        return default

    # ==========================================================
    # CALCULATE LOCAL TRANSPORTATION
    #
    # IMPORTANT:
    # Duration is optional.
    #
    # If duration is unknown, we DO NOT calculate
    # a duration-dependent local cost.
    # ==========================================================

    def calculate_local_transportation_cost(
        self,
        destination: str,
        duration_days: Optional[int],
        attraction_count: int
    ) -> Optional[float]:

        if duration_days is None:

            return None

        duration_days = max(
            int(duration_days),
            1
        )

        attraction_count = max(
            int(attraction_count),
            0
        )

        # ======================================================
        # Base calculation
        #
        # This is only for local transportation because the CSV
        # is intended for intercity route fares.
        # ======================================================

        base_cost = (
            300 * duration_days
        )

        if attraction_count > 3:

            base_cost += (
                (attraction_count - 3) * 100
            )

        return float(
            max(
                base_cost,
                500
            )
        )

    # ==========================================================
    # BUILD LOCAL TRANSPORTATION OPTIONS
    # ==========================================================

    def build_local_transportation_options(
        self,
        destination: str,
        duration_days: Optional[int],
        attraction_count: int
    ) -> List[Dict[str, Any]]:

        if duration_days is None:

            return [
                {
                    "mode": "Local Auto / Taxi",
                    "description": (
                        f"Local transportation within "
                        f"{destination} requires the trip "
                        f"duration to calculate a trip-level "
                        f"estimate."
                    ),
                    "estimated_cost": None,
                    "cost_unit": "total_trip",
                    "cost_type": "not_calculated"
                },
                {
                    "mode": "Local Bus",
                    "description": (
                        f"Local bus transportation within "
                        f"{destination} can be estimated "
                        f"after the trip duration is specified."
                    ),
                    "estimated_cost": None,
                    "cost_unit": "total_trip",
                    "cost_type": "not_calculated"
                }
            ]

        local_cost = (
            self.calculate_local_transportation_cost(
                destination,
                duration_days,
                attraction_count
            )
        )

        return [
            {
                "mode": "Local Auto / Taxi",
                "description": (
                    f"Estimated local transportation "
                    f"within {destination} for "
                    f"{duration_days} day(s), including "
                    f"movement between attractions."
                ),
                "estimated_cost": round(
                    local_cost,
                    2
                ),
                "cost_unit": "total_trip",
                "cost_type": "rough_estimate"
            },
            {
                "mode": "Local Bus",
                "description": (
                    f"Lower-cost local public "
                    f"transportation within "
                    f"{destination}."
                ),
                "estimated_cost": round(
                    local_cost * 0.55,
                    2
                ),
                "cost_unit": "total_trip",
                "cost_type": "rough_estimate"
            }
        ]

    # ==========================================================
    # RUN TRANSPORTATION AGENT
    # ==========================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ):

        # ======================================================
        # SHARED CONTEXT
        # ======================================================

        user_request = context.get(
            "user_request"
        )

        planner_output = context.get(
            "planner_output",
            {}
        )

        research_output = context.get(
            "research_output",
            {}
        )

        if not user_request:

            user_request = task

        # ======================================================
        # CONVERT USER REQUEST TO STRING
        # ======================================================

        if isinstance(
            user_request,
            (dict, list)
        ):

            user_request_text = json.dumps(
                user_request,
                indent=2,
                ensure_ascii=False
            )

        else:

            user_request_text = str(
                user_request
            )

        # ======================================================
        # EXTRACT ORIGIN
        # ======================================================

        origin = self.extract_origin(
            user_request_text,
            planner_output
        )

        # ======================================================
        # EXTRACT DESTINATION
        # ======================================================

        destination = "Unknown"

        if isinstance(
            planner_output,
            dict
        ):

            request_analysis = (
                planner_output.get(
                    "request_analysis",
                    {}
                )
            )

            if isinstance(
                request_analysis,
                dict
            ):

                destination = (
                    request_analysis.get(
                        "destination"
                    )
                    or "Unknown"
                )

        # Research fallback

        if destination == "Unknown":

            if isinstance(
                research_output,
                dict
            ):

                destination = (
                    research_output.get(
                        "destination"
                    )
                    or "Unknown"
                )

        # Text fallback

        if destination == "Unknown":

            destination = (
                self.extract_destination_from_text(
                    user_request_text
                )
            )

        destination = self.normalize_location(
            str(destination)
        )

        # ======================================================
        # EXTRACT DURATION
        # ======================================================

        duration_days = self.extract_duration(
            user_request_text,
            planner_output
        )

        # ======================================================
        # EXTRACT TRAVELERS
        # ======================================================

        travelers = self.extract_travelers(
            user_request_text,
            planner_output
        )

        # ======================================================
        # ATTRACTION COUNT
        # ======================================================

        attractions = []

        if isinstance(
            research_output,
            dict
        ):

            attractions = (
                research_output.get(
                    "attractions",
                    []
                )
            )

        if not isinstance(
            attractions,
            list
        ):

            attractions = []

        attraction_count = len(
            attractions
        )

        # ======================================================
        # STATUS
        # ======================================================

        origin_status = (
            "provided"
            if origin != "Unknown"
            else "missing"
        )

        duration_status = (
            "provided"
            if duration_days is not None
            else "not_specified"
        )

        traveler_status = (
            "provided"
            if travelers is not None
            else "not_specified"
        )

        # ======================================================
        # IF ORIGIN IS MISSING
        #
        # DO NOT CALCULATE ROUTE COST.
        # ======================================================

        if origin == "Unknown":

            result = {

                "origin": None,

                "destination": (
                    destination
                    if destination != "Unknown"
                    else None
                ),

                "origin_status": "missing",

                "number_of_travelers":
                    travelers,

                "duration_days":
                    duration_days,

                "duration_status":
                    duration_status,

                "traveler_status":
                    traveler_status,

                "transportation_status":
                    "origin_required",

                "transportation_summary": (
                    "Starting location is required "
                    "to calculate transportation costs."
                ),

                "arrival_options": [],

                "local_transportation": [],

                "recommended_option": None,

                "estimated_arrival_cost_for_all_travelers":
                    None,

                "estimated_local_transportation_cost":
                    None,

                "total_estimated_transportation_cost":
                    None,

                "origin_warning": (
                    "Starting location was not provided. "
                    "Please enter your origin so that "
                    "transportation options and costs "
                    "can be calculated."
                ),

                "cost_notes": {

                    "arrival_cost_note": (
                        "Arrival transportation cannot "
                        "be calculated until the origin "
                        "is provided."
                    ),

                    "local_transportation_note": (
                        "Local transportation cannot be "
                        "fully estimated until the trip "
                        "duration is specified."
                    ),

                    "total_cost_note": (
                        "Total transportation cost is not "
                        "calculated because the origin "
                        "is missing."
                    ),

                    "cost_type":
                        "not_calculated",

                    "calculation_source": (
                        "Transportation fares are intended "
                        "to be read from the transportation "
                        "rates CSV dataset."
                    )
                }
            }

            return result

        # ======================================================
        # FIND ROUTE IN CSV
        # ======================================================

        route_rows = (
            self.find_route_rates(
                origin,
                destination
            )
        )

        # ======================================================
        # BUILD ARRIVAL OPTIONS
        # ======================================================

        arrival_options = (
            self.build_arrival_options_from_csv(
                route_rows,
                origin,
                destination
            )
        )

        # ======================================================
        # ROUTE NOT FOUND
        # ======================================================

        if not arrival_options:

            result = {

                "origin": origin,

                "destination": (
                    destination
                    if destination != "Unknown"
                    else None
                ),

                "origin_status":
                    "provided",

                "number_of_travelers":
                    travelers,

                "duration_days":
                    duration_days,

                "duration_status":
                    duration_status,

                "traveler_status":
                    traveler_status,

                "transportation_status":
                    "route_not_found",

                "transportation_summary": (
                    f"No transportation fare data "
                    f"was found for the route "
                    f"{origin} to {destination}."
                ),

                "arrival_options": [],

                "local_transportation": [],

                "recommended_option": None,

                "estimated_arrival_cost_for_all_travelers":
                    None,

                "estimated_local_transportation_cost":
                    None,

                "total_estimated_transportation_cost":
                    None,

                "origin_warning": "",

                "cost_notes": {

                    "arrival_cost_note": (
                        "No route fare was found in "
                        "the transportation rates "
                        "dataset."
                    ),

                    "local_transportation_note": (
                        "Local transportation depends "
                        "on the destination and trip "
                        "duration."
                    ),

                    "total_cost_note": (
                        "Total transportation cost was "
                        "not calculated because no "
                        "intercity route fare was found."
                    ),

                    "cost_type":
                        "not_calculated",

                    "calculation_source": (
                        "Transportation fares are "
                        "obtained from the transportation "
                        "rates CSV dataset."
                    )
                }
            }

            return result

        # ======================================================
        # SELECT CHEAPEST ARRIVAL OPTION
        #
        # Instead of blindly selecting Bus, choose the
        # cheapest valid dataset option.
        # ======================================================

        recommended_option = min(
            arrival_options,
            key=lambda option: option[
                "estimated_cost"
            ]
        )

        recommended_mode = (
            recommended_option["mode"]
        )

        recommended_cost = float(
            recommended_option[
                "estimated_cost"
            ]
        )

        # ======================================================
        # ARRIVAL COST
        #
        # If traveler count is unknown, do not multiply.
        # ======================================================

        if travelers is not None:

            arrival_cost_for_all_travelers = round(
                recommended_cost * travelers,
                2
            )

        else:

            arrival_cost_for_all_travelers = None

        # ======================================================
        # LOCAL TRANSPORTATION
        # ======================================================

        local_trip_cost = (
            self.calculate_local_transportation_cost(
                destination=destination,
                duration_days=duration_days,
                attraction_count=attraction_count
            )
        )

        local_transportation = (
            self.build_local_transportation_options(
                destination=destination,
                duration_days=duration_days,
                attraction_count=attraction_count
            )
        )

        # ======================================================
        # TOTAL COST
        # ======================================================

        if (
            arrival_cost_for_all_travelers is not None
            and local_trip_cost is not None
        ):

            total_transportation_cost = round(
                arrival_cost_for_all_travelers
                + local_trip_cost,
                2
            )

        else:

            total_transportation_cost = None

        # ======================================================
        # TRANSPORTATION SUMMARY
        # ======================================================

        if travelers is not None:

            traveler_text = (
                f"{travelers} traveler(s)"
            )

        else:

            traveler_text = (
                "traveler count not specified"
            )

        if duration_days is not None:

            duration_text = (
                f"{duration_days} day(s)"
            )

        else:

            duration_text = (
                "duration not specified"
            )

        if arrival_cost_for_all_travelers is not None:

            arrival_cost_text = (
                f"Estimated arrival cost for all "
                f"{travelers} traveler(s): "
                f"{arrival_cost_for_all_travelers:.0f}."
            )

        else:

            arrival_cost_text = (
                "Total arrival cost cannot be "
                "calculated until the number of "
                "travelers is specified."
            )

        if local_trip_cost is not None:

            local_cost_text = (
                f"Estimated local transportation "
                f"cost for the entire trip: "
                f"{local_trip_cost:.0f}."
            )

        else:

            local_cost_text = (
                "Local transportation cost cannot "
                "be calculated until the duration "
                "is specified."
            )

        if total_transportation_cost is not None:

            total_cost_text = (
                f"Total estimated transportation "
                f"cost for all travelers: "
                f"{total_transportation_cost:.0f}."
            )

        else:

            total_cost_text = (
                "Total transportation cost is "
                "not currently available."
            )

        transportation_summary = (
            f"Transportation planned from "
            f"{origin} to {destination} for "
            f"{traveler_text} over "
            f"{duration_text}. "
            f"Recommended arrival mode: "
            f"{recommended_mode}. "
            f"Estimated arrival cost: "
            f"{recommended_cost:.0f} per person, "
            f"one-way. "
            f"{arrival_cost_text} "
            f"{local_cost_text} "
            f"{total_cost_text}"
        )

        # ======================================================
        # TRANSPORTATION STATUS
        # ======================================================

        if travelers is None:

            transportation_status = (
                "traveler_count_required"
            )

        elif duration_days is None:

            transportation_status = (
                "planned_duration_not_specified"
            )

        else:

            transportation_status = (
                "calculated"
            )

        # ======================================================
        # FINAL RESULT
        # ======================================================

        result = {

            "origin": origin,

            "destination": destination,

            "origin_status": origin_status,

            "number_of_travelers":
                travelers,

            "duration_days":
                duration_days,

            "duration_status":
                duration_status,

            "traveler_status":
                traveler_status,

            "transportation_status":
                transportation_status,

            "transportation_summary":
                transportation_summary,

            "arrival_options":
                arrival_options,

            "local_transportation":
                local_transportation,

            "recommended_option": {

                "mode":
                    recommended_mode,

                "reason": (
                    "Selected as the lowest-cost "
                    "available intercity transportation "
                    "option in the transportation rates "
                    "dataset."
                ),

                "estimated_cost":
                    recommended_cost,

                "cost_unit":
                    "per_person",

                "trip_direction":
                    "one_way",

                "cost_type":
                    "dataset_rate"
            },

            "estimated_arrival_cost_for_all_travelers":
                arrival_cost_for_all_travelers,

            "estimated_local_transportation_cost":
                local_trip_cost,

            "total_estimated_transportation_cost":
                total_transportation_cost,

            "origin_warning": "",

            "cost_notes": {

                "arrival_cost_note": (
                    "Arrival transportation costs "
                    "are obtained from the CSV dataset "
                    "and are calculated per person "
                    "for one-way travel."
                ),

                "local_transportation_note": (
                    "Local transportation is estimated "
                    "for the entire trip. A duration "
                    "must be specified for a trip-level "
                    "estimate."
                ),

                "total_cost_note": (
                    "Total transportation cost includes "
                    "arrival transportation for all "
                    "specified travelers plus estimated "
                    "local transportation."
                ),

                "cost_type":
                    "dataset_rate",

                "calculation_source": (
                    "Intercity transportation fares "
                    "are loaded from the "
                    "transportation_rates.csv "
                    "dataset. Python performs the "
                    "calculations and does not allow "
                    "the LLM to invent transportation "
                    "fares."
                )
            }
        }

        return result

    # ==========================================================
    # ROBUST JSON CLEANER
    # ==========================================================

    @staticmethod
    def _clean_json_response(
        response: str
    ) -> str:

        if not response:

            raise ValueError(
                "Empty response from LLM."
            )

        if not isinstance(
            response,
            str
        ):

            response = str(
                response
            )

        text = response.strip()

        # ======================================================
        # REMOVE MARKDOWN FENCES
        # ======================================================

        text = re.sub(
            r"```json\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"```\s*",
            "",
            text
        )

        text = text.strip()

        # ======================================================
        # TRY ENTIRE RESPONSE
        # ======================================================

        try:

            parsed = json.loads(
                text
            )

            if isinstance(
                parsed,
                dict
            ):

                return json.dumps(
                    parsed,
                    ensure_ascii=False
                )

        except Exception:
            pass

        # ======================================================
        # FIND FIRST COMPLETE JSON OBJECT
        # ======================================================

        start_index = text.find(
            "{"
        )

        if start_index == -1:

            raise ValueError(
                "No JSON object found in LLM response."
            )

        depth = 0
        in_string = False
        escape = False

        for index in range(
            start_index,
            len(text)
        ):

            char = text[index]

            if in_string:

                if escape:

                    escape = False

                elif char == "\\":

                    escape = True

                elif char == '"':

                    in_string = False

                continue

            if char == '"':

                in_string = True

                continue

            if char == "{":

                depth += 1

            elif char == "}":

                depth -= 1

                if depth == 0:

                    candidate = text[
                        start_index:index + 1
                    ]

                    try:

                        parsed = json.loads(
                            candidate
                        )

                        if isinstance(
                            parsed,
                            dict
                        ):

                            return json.dumps(
                                parsed,
                                ensure_ascii=False
                            )

                    except json.JSONDecodeError:

                        pass

        raise ValueError(
            "Could not extract a valid JSON object "
            "from the LLM response."
        )