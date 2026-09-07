import json
import re
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent


class ItineraryAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Itinerary Agent",
            description=(
                "Creates a practical, human-friendly, day-wise travel "
                "itinerary using information provided by the Planner, "
                "Research, Transportation, Accommodation, and Budget agents."
            )
        )

    # ============================================================
    # SAFE HELPERS
    # ============================================================

    def _safe_dict(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    def _safe_int(self, value: Any, default: int = 0) -> int:

        if isinstance(value, bool):
            return default

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):

            value = value.strip()

            match = re.search(r"\d+", value)

            if match:
                try:
                    return int(match.group())
                except ValueError:
                    pass

        return default

    # ============================================================
    # EXTRACT DURATION
    # ============================================================

    def _extract_duration_from_text(self, text: Any) -> int:

        if not isinstance(text, str):
            return 0

        text = text.lower()

        patterns = [
            r"(\d+)\s*[-]?\s*day",
            r"(\d+)\s*days",
            r"duration\s*(?:is|of|:)?\s*(\d+)",
            r"for\s*(\d+)\s*day",
        ]

        for pattern in patterns:

            match = re.search(pattern, text)

            if match:

                try:
                    value = int(match.group(1))

                    if value > 0:
                        return value

                except ValueError:
                    continue

        return 0

    # ============================================================
    # EXTRACT TRAVELERS
    # ============================================================

    def _extract_travelers_from_text(self, text: Any) -> int:

        if not isinstance(text, str):
            return 0

        text = text.lower()

        patterns = [
            r"for\s+(\d+)\s+(?:people|persons|travelers|travellers)",
            r"(\d+)\s+(?:people|persons|travelers|travellers)",
        ]

        for pattern in patterns:

            match = re.search(pattern, text)

            if match:

                try:
                    value = int(match.group(1))

                    if value > 0:
                        return value

                except ValueError:
                    continue

        return 0

    # ============================================================
    # EXTRACT BUDGET
    # ============================================================

    def _extract_budget_from_text(self, text: Any) -> float:

        if not isinstance(text, str):
            return 0

        patterns = [
            r"₹\s*([\d,]+(?:\.\d+)?)",
            r"rs\.?\s*([\d,]+(?:\.\d+)?)",
            r"rupees?\s*([\d,]+(?:\.\d+)?)",
            r"budget\s*(?:of|is|:)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        ]

        text_lower = text.lower()

        for pattern in patterns:

            match = re.search(
                pattern,
                text_lower
            )

            if match:

                try:

                    value = float(
                        match.group(1).replace(",", "")
                    )

                    if value > 0:
                        return value

                except ValueError:
                    continue

        return 0

    # ============================================================
    # EXTRACT DESTINATION
    # ============================================================

    def _extract_destination_from_text(
        self,
        text: Any
    ) -> str:

        if not isinstance(text, str):
            return ""

        patterns = [
            r"trip\s+to\s+([A-Za-z][A-Za-z .'-]+?)(?=\s+for\s+\d|\s+from\s+|\s+with\s+|\s+on\s+|\s*$)",
            r"travel\s+to\s+([A-Za-z][A-Za-z .'-]+?)(?=\s+for\s+\d|\s+from\s+|\s+with\s+|\s+on\s+|\s*$)",
            r"visit\s+([A-Za-z][A-Za-z .'-]+?)(?=\s+for\s+\d|\s+from\s+|\s+with\s+|\s+on\s+|\s*$)",
        ]

        text = text.strip()

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                destination = match.group(1).strip(" .,")

                if destination:
                    return destination

        return ""

    # ============================================================
    # EXTRACT RESEARCH PLACES
    # ============================================================

    def _extract_research_places(
        self,
        research_output: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        places = []

        attractions = research_output.get(
            "attractions",
            []
        )

        if not isinstance(attractions, list):
            return places

        for attraction in attractions:

            if not isinstance(attraction, dict):
                continue

            name = attraction.get("name", "")

            if not isinstance(name, str):
                continue

            name = name.strip()

            if not name:
                continue

            estimated_cost = attraction.get(
                "estimated_cost",
                0
            )

            if not isinstance(
                estimated_cost,
                (int, float)
            ):
                estimated_cost = 0

            cost_status = attraction.get(
                "cost_status",
                "unknown"
            )

            if not isinstance(
                cost_status,
                str
            ):
                cost_status = "unknown"

            cost_status = cost_status.strip().lower()

            if cost_status not in (
                "unknown",
                "free",
                "known"
            ):
                cost_status = "unknown"

            places.append({
                "name": name,
                "type": attraction.get(
                    "type",
                    "attraction"
                ),
                "description": attraction.get(
                    "description",
                    ""
                ),
                "estimated_cost": estimated_cost,
                "cost_status": cost_status
            })

        return places

    # ============================================================
    # PLACE LOOKUP
    # ============================================================

    def _build_place_lookup(
        self,
        research_places: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:

        lookup = {}

        for place in research_places:

            name = place.get("name", "")

            if not name:
                continue

            lookup[name.strip().lower()] = place

        return lookup

    # ============================================================
    # TRANSPORTATION
    # ============================================================

    def _extract_transportation(
        self,
        transportation_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        recommended_option = transportation_output.get(
            "recommended_option",
            {}
        )

        if not isinstance(
            recommended_option,
            dict
        ):
            recommended_option = {}

        return {
            "recommended_mode": recommended_option.get(
                "mode",
                ""
            ),
            "arrival_cost": transportation_output.get(
                "estimated_arrival_cost_for_all_travelers",
                0
            ),
            "local_transportation_cost": transportation_output.get(
                "estimated_local_transportation_cost",
                0
            ),
            "total_transportation_cost": transportation_output.get(
                "total_estimated_transportation_cost",
                0
            )
        }

    # ============================================================
    # ACCOMMODATION
    # ============================================================

    def _extract_accommodation(
        self,
        accommodation_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        recommended = accommodation_output.get(
            "recommended_option",
            {}
        )

        if not isinstance(
            recommended,
            dict
        ):
            recommended = {}

        return {
            "recommended_name": recommended.get(
                "name",
                ""
            ),
            "price_per_night": recommended.get(
                "estimated_price_per_night",
                0
            ),
            "total_cost": recommended.get(
                "estimated_total_cost",
                0
            ),
            "nights": accommodation_output.get(
                "nights",
                0
            )
        }

    # ============================================================
    # BUDGET
    # ============================================================

    def _extract_budget(
        self,
        planner_output: Dict[str, Any],
        budget_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        budget = budget_output.get(
            "budget",
            0
        )

        if not isinstance(
            budget,
            (int, float)
        ):
            budget = 0

        remaining_budget = budget_output.get(
            "remaining_budget",
            0
        )

        if not isinstance(
            remaining_budget,
            (int, float)
        ):
            remaining_budget = 0

        return {
            "budget": budget,
            "remaining_budget": remaining_budget,
            "budget_status": budget_output.get(
                "budget_status",
                ""
            )
        }

    # ============================================================
    # TRIP DETAILS
    # ============================================================

    def _extract_trip_details(
        self,
        user_request: Any,
        planner_output: Dict[str, Any],
        research_output: Dict[str, Any],
        task: str = ""
    ) -> Dict[str, Any]:

        destination = ""
        duration_days = 0
        travelers = 0
        budget = 0.0
        preferences = []

        # --------------------------------------------------------
        # Structured user request
        # --------------------------------------------------------

        if isinstance(user_request, dict):

            destination = user_request.get(
                "destination",
                ""
            )

            duration_days = self._safe_int(
                user_request.get(
                    "duration_days",
                    user_request.get(
                        "duration",
                        0
                    )
                )
            )

            travelers = self._safe_int(
                user_request.get(
                    "travelers",
                    user_request.get(
                        "number_of_travelers",
                        0
                    )
                )
            )

            try:

                budget = float(
                    user_request.get(
                        "budget",
                        0
                    ) or 0
                )

            except (
                TypeError,
                ValueError
            ):
                budget = 0.0

            preferences = user_request.get(
                "preferences",
                []
            )

        # --------------------------------------------------------
        # Planner output
        # --------------------------------------------------------

        request_analysis = planner_output.get(
            "request_analysis",
            {}
        )

        if isinstance(
            request_analysis,
            dict
        ):

            if not destination:
                destination = request_analysis.get(
                    "destination",
                    ""
                )

            if not duration_days:

                duration_days = self._safe_int(
                    request_analysis.get(
                        "duration_days",
                        request_analysis.get(
                            "duration",
                            0
                        )
                    )
                )

            if not travelers:

                travelers = self._safe_int(
                    request_analysis.get(
                        "travelers",
                        request_analysis.get(
                            "number_of_travelers",
                            0
                        )
                    )
                )

            if not budget:

                try:

                    budget = float(
                        request_analysis.get(
                            "budget",
                            0
                        ) or 0
                    )

                except (
                    TypeError,
                    ValueError
                ):
                    budget = 0.0

            if not preferences:

                preferences = request_analysis.get(
                    "preferences",
                    []
                )

            # ----------------------------------------------------
            # Planner goal fallback
            # ----------------------------------------------------

            planner_goal = request_analysis.get(
                "goal",
                ""
            )

            if isinstance(
                planner_goal,
                str
            ):

                if not duration_days:
                    duration_days = (
                        self._extract_duration_from_text(
                            planner_goal
                        )
                    )

                if not travelers:
                    travelers = (
                        self._extract_travelers_from_text(
                            planner_goal
                        )
                    )

                if not budget:
                    budget = (
                        self._extract_budget_from_text(
                            planner_goal
                        )
                    )

                if not destination:
                    destination = (
                        self._extract_destination_from_text(
                            planner_goal
                        )
                    )

        # --------------------------------------------------------
        # Original request
        # --------------------------------------------------------

        request_text = ""

        if isinstance(
            user_request,
            str
        ):

            request_text = user_request

        elif isinstance(
            user_request,
            dict
        ):

            request_text = str(user_request)

        if request_text:

            if not duration_days:
                duration_days = (
                    self._extract_duration_from_text(
                        request_text
                    )
                )

            if not travelers:
                travelers = (
                    self._extract_travelers_from_text(
                        request_text
                    )
                )

            if not budget:
                budget = (
                    self._extract_budget_from_text(
                        request_text
                    )
                )

            if not destination:
                destination = (
                    self._extract_destination_from_text(
                        request_text
                    )
                )

        # --------------------------------------------------------
        # Task fallback
        # --------------------------------------------------------

        if task:

            if not duration_days:
                duration_days = (
                    self._extract_duration_from_text(
                        task
                    )
                )

            if not travelers:
                travelers = (
                    self._extract_travelers_from_text(
                        task
                    )
                )

            if not budget:
                budget = (
                    self._extract_budget_from_text(
                        task
                    )
                )

            if not destination:
                destination = (
                    self._extract_destination_from_text(
                        task
                    )
                )

        # --------------------------------------------------------
        # Research fallback
        # --------------------------------------------------------

        if not destination:

            destination = research_output.get(
                "destination",
                ""
            )

        # --------------------------------------------------------
        # Safe defaults
        # --------------------------------------------------------

        if duration_days <= 0:
            duration_days = 0

        if travelers < 0:
            travelers = 0

        if budget < 0:
            budget = 0

        if not isinstance(
            preferences,
            list
        ):

            preferences = [
                str(preferences)
            ]

        return {
            "destination": destination,
            "duration_days": duration_days,
            "travelers": travelers,
            "budget": budget,
            "preferences": preferences
        }

    # ============================================================
    # CLEAN LLM RESPONSE
    # ============================================================

    def _clean_llm_response(
        self,
        response: Any
    ) -> str:

        if not isinstance(
            response,
            str
        ):
            response = str(response)

        response = response.strip()

        # Remove markdown fences
        response = re.sub(
            r"^```(?:json)?\s*",
            "",
            response,
            flags=re.IGNORECASE
        )

        response = re.sub(
            r"\s*```$",
            "",
            response
        )

        return response.strip()

    # ============================================================
    # PARSE JSON
    # ============================================================

    def _parse_json_response(
        self,
        response: Any
    ) -> Dict[str, Any]:

        cleaned = self._clean_llm_response(
            response
        )

        # --------------------------------------------------------
        # First attempt: direct JSON
        # --------------------------------------------------------

        try:

            result = json.loads(cleaned)

            if isinstance(
                result,
                dict
            ):
                return result

        except json.JSONDecodeError:
            pass

        # --------------------------------------------------------
        # Second attempt:
        # Find the outermost JSON object.
        #
        # This protects against the LLM adding text before/after
        # the JSON.
        # --------------------------------------------------------

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if (
            start != -1
            and end != -1
            and end > start
        ):

            candidate = cleaned[
                start:end + 1
            ]

            try:

                result = json.loads(
                    candidate
                )

                if isinstance(
                    result,
                    dict
                ):
                    return result

            except json.JSONDecodeError:
                pass

        # --------------------------------------------------------
        # If the model returned Python code, do not try to execute
        # arbitrary code. Raise a clean parsing error instead.
        # --------------------------------------------------------

        if (
            "import json" in cleaned
            or "print(json.dumps" in cleaned
            or "def " in cleaned
        ):

            raise ValueError(
                "The LLM returned Python code instead of JSON."
            )

        raise ValueError(
            "The LLM response was not valid JSON."
        )

    # ============================================================
    # VALIDATE ITINERARY
    # ============================================================

    def _validate_itinerary(
        self,
        itinerary: Any,
        duration_days: int,
        place_lookup: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        if not isinstance(
            itinerary,
            list
        ):
            itinerary = []

        validated_itinerary = []

        # --------------------------------------------------------
        # Exactly the requested number of days
        # --------------------------------------------------------

        for day_number in range(
            1,
            duration_days + 1
        ):

            matching_day = None

            for day in itinerary:

                if not isinstance(
                    day,
                    dict
                ):
                    continue

                day_value = self._safe_int(
                    day.get(
                        "day",
                        0
                    )
                )

                if day_value == day_number:

                    matching_day = day
                    break

            # ----------------------------------------------------
            # Missing day
            # ----------------------------------------------------

            if matching_day is None:

                matching_day = {
                    "day": day_number,
                    "title": f"Day {day_number}",
                    "activities": []
                }

            activities = matching_day.get(
                "activities",
                []
            )

            if not isinstance(
                activities,
                list
            ):
                activities = []

            validated_activities = []

            daily_cost = 0
            daily_has_unknown_cost = False

            # ----------------------------------------------------
            # Validate activities
            # ----------------------------------------------------

            for activity in activities:

                if not isinstance(
                    activity,
                    dict
                ):
                    continue

                place = activity.get(
                    "place",
                    ""
                )

                if not isinstance(
                    place,
                    str
                ):
                    continue

                place = place.strip()

                if not place:
                    continue

                source_place = place_lookup.get(
                    place.lower()
                )

                if source_place is None:

                    # Prevent hallucinated places.
                    continue

                # ------------------------------------------------
                # Research Agent is the source of truth for costs
                # ------------------------------------------------

                cost = source_place.get(
                    "estimated_cost",
                    0
                )

                if not isinstance(
                    cost,
                    (int, float)
                ):
                    cost = 0

                if cost < 0:
                    cost = 0

                cost_status = source_place.get(
                    "cost_status",
                    "unknown"
                )

                if not isinstance(
                    cost_status,
                    str
                ):
                    cost_status = "unknown"

                cost_status = cost_status.lower().strip()

                if cost_status not in (
                    "unknown",
                    "free",
                    "known"
                ):
                    cost_status = "unknown"

                # ------------------------------------------------
                # Human-friendly activity text
                #
                # We preserve the LLM-generated activity if it
                # exists instead of hardcoding an Ooty-specific
                # sentence.
                # ------------------------------------------------

                activity_text = activity.get(
                    "activity",
                    ""
                )

                if not isinstance(
                    activity_text,
                    str
                ):
                    activity_text = ""

                activity_text = activity_text.strip()

                if not activity_text:

                    activity_text = (
                        f"Explore {source_place['name']} "
                        "and enjoy the surroundings."
                    )

                # ------------------------------------------------
                # Time
                # ------------------------------------------------

                activity_time = activity.get(
                    "time",
                    "Daytime"
                )

                if not isinstance(
                    activity_time,
                    str
                ):
                    activity_time = "Daytime"

                activity_time = activity_time.strip()

                if not activity_time:
                    activity_time = "Daytime"

                validated_activity = {
                    "time": activity_time,
                    "place": source_place["name"],
                    "activity": activity_text,
                    "estimated_cost": cost,
                    "cost_status": cost_status
                }

                validated_activities.append(
                    validated_activity
                )

                daily_cost += cost

                if cost_status == "unknown":
                    daily_has_unknown_cost = True

            # ----------------------------------------------------
            # Human-friendly title
            # ----------------------------------------------------

            title = matching_day.get(
                "title",
                ""
            )

            if not isinstance(
                title,
                str
            ):
                title = ""

            title = title.strip()

            if not title:
                title = f"Day {day_number}"

            matching_day["day"] = day_number
            matching_day["title"] = title
            matching_day["activities"] = (
                validated_activities
            )
            matching_day["daily_estimated_cost"] = round(
                daily_cost,
                2
            )
            matching_day[
                "has_unknown_cost_activities"
            ] = daily_has_unknown_cost

            validated_itinerary.append(
                matching_day
            )

        return validated_itinerary

    # ============================================================
    # GENERATE LLM PROMPT
    # ============================================================

    def _build_prompt(
        self,
        destination: str,
        duration_days: int,
        travelers: int,
        budget: float,
        preferences: List[Any],
        research_places: List[Dict[str, Any]],
        transportation_info: Dict[str, Any],
        accommodation_info: Dict[str, Any],
        budget_info: Dict[str, Any]
    ) -> str:

        places_text = json.dumps(
            research_places,
            ensure_ascii=False,
            indent=2
        )

        transportation_text = json.dumps(
            transportation_info,
            ensure_ascii=False,
            indent=2
        )

        accommodation_text = json.dumps(
            accommodation_info,
            ensure_ascii=False,
            indent=2
        )

        budget_text = json.dumps(
            budget_info,
            ensure_ascii=False,
            indent=2
        )

        preferences_text = json.dumps(
            preferences,
            ensure_ascii=False
        )

        return f"""
You are an expert travel itinerary planner.

Your job is to create a realistic, practical and
HUMAN-FRIENDLY travel itinerary using ONLY the
information supplied by the previous agents.

Do not invent facts.

==================================================
TRIP DETAILS
==================================================

Destination:
{destination}

Duration:
{duration_days} days

Number of travelers:
{travelers}

Budget:
{budget}

Preferences:
{preferences_text}

==================================================
RESEARCH AGENT DATA
==================================================

{places_text}

==================================================
TRANSPORTATION AGENT DATA
==================================================

{transportation_text}

==================================================
ACCOMMODATION AGENT DATA
==================================================

{accommodation_text}

==================================================
BUDGET AGENT DATA
==================================================

{budget_text}

==================================================
IMPORTANT RULES
==================================================

1. Create EXACTLY {duration_days} days.

2. Day numbers must be:
   1, 2, 3 ... {duration_days}

3. Use ONLY places that appear in the
   Research Agent data.

4. Never invent attractions.

5. Never invent restaurants.

6. Never invent prices.

7. Never assume an unknown cost is free.

8. Copy estimated_cost and cost_status from the
   Research Agent data.

9. Respect the traveler's preferences.

10. Arrange activities in a logical order.

11. Avoid unnecessary repetition.

12. Keep each day practical and not overloaded.

13. Consider the transportation and accommodation
    information when deciding the flow of the trip.

14. If the user has a budget, create an itinerary
    that is sensible for that budget.

15. Do NOT calculate or modify transportation costs.

16. Do NOT calculate or modify accommodation costs.

17. daily_estimated_cost should represent ONLY the
    researched attraction/activity costs included
    for that day.

18. If an attraction has unknown cost, keep:
    estimated_cost = 0
    cost_status = "unknown"

==================================================
HUMAN-FRIENDLY WRITING
==================================================

The itinerary will be shown directly to a traveler.

Therefore:

- Do NOT write robotic text such as:
  "Visit and explore the place."

- Write natural activity descriptions.

For example, the activity should explain what the
traveler can actually do there.

Good style:

"Spend the morning walking through the gardens,
enjoying the greenery and taking photographs."

"Relax by the lake and enjoy the scenic surroundings."

"Take in the mountain views and spend some time
exploring the viewpoint."

The examples above are only writing-style examples.
Do NOT copy these examples as actual attractions.

Make the descriptions specific to the researched
place and its available description.

==================================================
DAY STRUCTURE
==================================================

Each day should normally contain 1 to 3 activities,
depending on the number of researched places and
the trip duration.

Use natural time periods such as:

Morning
Late Morning
Afternoon
Evening

Include free time when it makes sense and when the
user's preferences indicate that they want a relaxed
trip.

Do not create a fake attraction for free time.

==================================================
OUTPUT REQUIREMENT
==================================================

RETURN ONLY ONE VALID JSON OBJECT.

DO NOT return Python code.

DO NOT return JavaScript.

DO NOT return Markdown.

DO NOT use ```.

DO NOT explain your answer outside the JSON.

Your entire response MUST begin with:
{{

and end with:
}}

==================================================
EXACT JSON STRUCTURE
==================================================

{{
  "destination": "{destination}",
  "duration_days": {duration_days},
  "itinerary": [
    {{
      "day": 1,
      "title": "A natural human-friendly title",
      "activities": [
        {{
          "time": "Morning",
          "place": "Exact researched place name",
          "activity": "Natural description of what the traveler can do there.",
          "estimated_cost": 0,
          "cost_status": "unknown"
        }}
      ],
      "daily_estimated_cost": 0
    }}
  ],
  "itinerary_summary": "A short, natural summary of the complete trip.",
  "planning_notes": [
    "Useful practical planning note."
  ]
}}

Remember:

The JSON above is a STRUCTURE EXAMPLE only.

Do not invent attractions.

Use the actual researched places.

Return JSON only.
"""

    # ============================================================
    # RUN ITINERARY AGENT
    # ============================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ):

        # ========================================================
        # GET SHARED CONTEXT
        # ========================================================

        user_request = context.get(
            "original_user_request",
            context.get(
                "user_request",
                task
            )
        )

        planner_output = self._safe_dict(
            context.get(
                "planner_output",
                {}
            )
        )

        research_output = self._safe_dict(
            context.get(
                "research_output",
                {}
            )
        )

        transportation_output = self._safe_dict(
            context.get(
                "transportation_output",
                {}
            )
        )

        accommodation_output = self._safe_dict(
            context.get(
                "accommodation_output",
                {}
            )
        )

        budget_output = self._safe_dict(
            context.get(
                "budget_output",
                {}
            )
        )

        # ========================================================
        # EXTRACT TRIP DETAILS
        # ========================================================

        trip_details = self._extract_trip_details(
            user_request=user_request,
            planner_output=planner_output,
            research_output=research_output,
            task=task
        )

        destination = trip_details.get(
            "destination",
            ""
        )

        duration_days = trip_details.get(
            "duration_days",
            0
        )

        travelers = trip_details.get(
            "travelers",
            0
        )

        budget = trip_details.get(
            "budget",
            0
        )

        preferences = trip_details.get(
            "preferences",
            []
        )

        # ========================================================
        # VALIDATION
        # ========================================================

        if duration_days <= 0:

            return {
                "error": (
                    "Itinerary Agent could not determine "
                    "the trip duration from the user request."
                ),
                "destination": destination,
                "duration_days": 0,
                "itinerary": [],
                "itinerary_summary": (
                    "Trip duration is required."
                ),
                "planning_notes": [
                    "No valid trip duration was found."
                ]
            }

        if not destination:

            return {
                "error": (
                    "Itinerary Agent could not determine "
                    "the destination."
                ),
                "destination": "",
                "duration_days": duration_days,
                "itinerary": [],
                "itinerary_summary": (
                    "Destination is required."
                ),
                "planning_notes": [
                    "No destination was found."
                ]
            }

        # ========================================================
        # RESEARCH DATA
        # ========================================================

        research_places = (
            self._extract_research_places(
                research_output
            )
        )

        if not research_places:

            return {
                "error": (
                    "Itinerary Agent cannot create "
                    "an itinerary because the Research "
                    "Agent did not provide any places."
                ),
                "destination": destination,
                "duration_days": duration_days,
                "itinerary": [],
                "itinerary_summary": (
                    "No researched attractions were available."
                ),
                "planning_notes": [
                    "Research Agent returned no attractions."
                ]
            }

        place_lookup = (
            self._build_place_lookup(
                research_places
            )
        )

        # ========================================================
        # SUPPORTING AGENTS
        # ========================================================

        transportation_info = (
            self._extract_transportation(
                transportation_output
            )
        )

        accommodation_info = (
            self._extract_accommodation(
                accommodation_output
            )
        )

        budget_info = (
            self._extract_budget(
                planner_output,
                budget_output
            )
        )

        # ========================================================
        # BUILD PROMPT
        # ========================================================

        prompt = self._build_prompt(
            destination=destination,
            duration_days=duration_days,
            travelers=travelers,
            budget=budget,
            preferences=preferences,
            research_places=research_places,
            transportation_info=transportation_info,
            accommodation_info=accommodation_info,
            budget_info=budget_info
        )

        # ========================================================
        # FIRST LLM CALL
        # ========================================================

        raw_response = None

        try:

            raw_response = self.llm.generate(
                prompt
            )

            itinerary_result = (
                self._parse_json_response(
                    raw_response
                )
            )

        except Exception as first_error:

            # ====================================================
            # SECOND ATTEMPT
            #
            # This is NOT hardcoding.
            #
            # We simply tell the same LLM to correct its output.
            # ====================================================

            correction_prompt = f"""
The previous response did not follow the required
JSON-only format.

You are still the Itinerary Agent.

Generate the itinerary again using the SAME trip
information and research data from the previous prompt.

IMPORTANT:

- Return ONLY valid JSON.
- Do NOT return Python code.
- Do NOT return Markdown.
- Do NOT use code fences.
- Do NOT explain anything.
- Do NOT invent attractions.
- Use ONLY researched places.
- Create exactly {duration_days} days.
- Keep the writing natural and human-friendly.

The previous response was:

{str(raw_response)[:8000]}

Return ONLY this JSON structure:

{{
  "destination": "{destination}",
  "duration_days": {duration_days},
  "itinerary": [
    {{
      "day": 1,
      "title": "",
      "activities": [
        {{
          "time": "Morning",
          "place": "",
          "activity": "",
          "estimated_cost": 0,
          "cost_status": "unknown"
        }}
      ],
      "daily_estimated_cost": 0
    }}
  ],
  "itinerary_summary": "",
  "planning_notes": []
}}
"""

            try:

                raw_response = self.llm.generate(
                    correction_prompt
                )

                itinerary_result = (
                    self._parse_json_response(
                        raw_response
                    )
                )

            except Exception as second_error:

                return {
                    "error": (
                        "Itinerary Agent could not "
                        "generate a valid result."
                    ),
                    "details": str(second_error),
                    "first_error": str(first_error),
                    "raw_response": raw_response,
                    "destination": destination,
                    "duration_days": duration_days,
                    "travelers": travelers,
                    "budget": budget,
                    "preferences": preferences,
                    "itinerary": [],
                    "itinerary_summary": (
                        "The itinerary response "
                        "was invalid."
                    ),
                    "planning_notes": [
                        "The LLM did not return valid JSON "
                        "after two attempts."
                    ]
                }

        # ========================================================
        # TOP LEVEL VALIDATION
        # ========================================================

        if not isinstance(
            itinerary_result,
            dict
        ):

            return {
                "error": (
                    "Itinerary Agent returned "
                    "an invalid structure."
                ),
                "destination": destination,
                "duration_days": duration_days,
                "itinerary": [],
                "itinerary_summary": (
                    "Invalid itinerary structure."
                ),
                "planning_notes": []
            }

        # ========================================================
        # AUTHORITATIVE VALUES
        #
        # User/request values always win over LLM values.
        # ========================================================

        itinerary_result["destination"] = destination

        itinerary_result["duration_days"] = (
            duration_days
        )

        # ========================================================
        # VALIDATE DAYS AND ACTIVITIES
        # ========================================================

        validated_itinerary = (
            self._validate_itinerary(
                itinerary=itinerary_result.get(
                    "itinerary",
                    []
                ),
                duration_days=duration_days,
                place_lookup=place_lookup
            )
        )

        # ========================================================
        # SUMMARY
        # ========================================================

        itinerary_summary = (
            itinerary_result.get(
                "itinerary_summary",
                ""
            )
        )

        if not isinstance(
            itinerary_summary,
            str
        ):
            itinerary_summary = ""

        itinerary_summary = (
            itinerary_summary.strip()
        )

        if not itinerary_summary:

            itinerary_summary = (
                f"A {duration_days}-day trip to "
                f"{destination}, planned around the "
                f"traveler's preferences and the "
                f"researched attractions."
            )

        # ========================================================
        # PLANNING NOTES
        # ========================================================

        planning_notes = (
            itinerary_result.get(
                "planning_notes",
                []
            )
        )

        if not isinstance(
            planning_notes,
            list
        ):

            planning_notes = [
                str(planning_notes)
            ]

        planning_notes = [
            str(note).strip()
            for note in planning_notes
            if str(note).strip()
        ]

        # --------------------------------------------------------
        # Unknown-cost note
        # --------------------------------------------------------

        has_unknown_costs = any(
            day.get(
                "has_unknown_cost_activities",
                False
            )
            for day in validated_itinerary
        )

        if (
            has_unknown_costs
            and not any(
                "unknown" in note.lower()
                and "cost" in note.lower()
                for note in planning_notes
            )
        ):

            planning_notes.append(
                "Some attraction costs could not be "
                "confirmed from the available research "
                "data and are therefore shown as unknown."
            )

        # ========================================================
        # FINAL RESULT
        # ========================================================

        return {
            "destination": destination,
            "duration_days": duration_days,
            "travelers": travelers,
            "budget": budget,
            "preferences": preferences,
            "itinerary": validated_itinerary,
            "itinerary_summary": itinerary_summary,
            "planning_notes": planning_notes
        }