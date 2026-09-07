import json
import re
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent


class ResponseAgent(BaseAgent):
    """
    Response Agent

    Responsibility:
    - Collect outputs from all previous agents.
    - Create a human-friendly final travel plan.
    - Preserve Budget Agent as the budget source of truth.
    - Preserve Review Agent as the review source of truth.
    - Do not perform new research.
    - Do not invent travel information.
    - Do not recalculate the budget.
    - Do not create a new itinerary.
    """

    def __init__(self):
        super().__init__(
            name="Response Agent",
            description=(
                "Creates a clear, human-friendly final travel "
                "plan using the outputs of the previous travel "
                "planning agents."
            )
        )

    # ==========================================================
    # SAFE HELPERS
    # ==========================================================

    @staticmethod
    def _safe_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value).strip()

    @staticmethod
    def _safe_number(
        value: Any,
        default: float = 0
    ) -> float:

        if isinstance(value, bool):
            return default

        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):

            cleaned = (
                value
                .replace(",", "")
                .replace("₹", "")
                .strip()
            )

            match = re.search(
                r"-?\d+(?:\.\d+)?",
                cleaned
            )

            if match:
                try:
                    return float(match.group())
                except ValueError:
                    pass

        return default

    # ==========================================================
    # REVIEW STATUS
    # ==========================================================

    @staticmethod
    def _normalize_review_status(
        value: Any
    ) -> str:

        if value is None:
            return ""

        status = str(value).strip().lower()

        status = status.replace("-", "_")
        status = status.replace(" ", "_")

        if status in {
            "approved",
            "approve",
            "ready",
            "accepted",
            "ok",
            "valid"
        }:
            return "approved"

        if status in {
            "needs_revision",
            "need_revision",
            "revision_required",
            "requires_revision",
            "needs_changes",
            "needs_change",
            "revise"
        }:
            return "needs_revision"

        return ""

    # ==========================================================
    # JSON SERIALIZATION
    # ==========================================================

    @staticmethod
    def _json_dump(value: Any) -> str:

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str
            )
        except Exception:
            return "{}"

    # ==========================================================
    # COMPACT TEXT
    # ==========================================================

    @staticmethod
    def _compact_text(
        value: Any,
        max_length: int = 700
    ) -> str:

        text = ResponseAgent._safe_text(value)

        if len(text) <= max_length:
            return text

        return text[:max_length].rstrip() + "..."

    # ==========================================================
    # PLANNER
    # ==========================================================

    def _compact_planner(
        self,
        planner_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        planner_output = self._safe_dict(
            planner_output
        )

        analysis = self._safe_dict(
            planner_output.get(
                "request_analysis"
            )
        )

        result = {}

        for key in [
            "goal",
            "destination",
            "origin",
            "duration_days",
            "travelers",
            "budget",
            "preferences",
            "requirements",
            "constraints"
        ]:

            if key not in analysis:
                continue

            value = analysis.get(key)

            if isinstance(value, str):
                result[key] = self._compact_text(
                    value,
                    500
                )

            elif isinstance(value, list):
                result[key] = value[:10]

            else:
                result[key] = value

        return result

    # ==========================================================
    # RESEARCH
    # ==========================================================

    def _compact_research(
        self,
        research_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        research_output = self._safe_dict(
            research_output
        )

        result = {}

        for key in [
            "destination",
            "attractions",
            "places",
            "research_summary",
            "recommendations",
            "findings"
        ]:

            if key not in research_output:
                continue

            value = research_output.get(key)

            if isinstance(value, list):
                result[key] = value[:12]

            elif isinstance(value, dict):
                result[key] = value

            else:
                result[key] = self._compact_text(
                    value,
                    1000
                )

        return result

    # ==========================================================
    # TRANSPORTATION
    # ==========================================================

    def _compact_transportation(
        self,
        transportation_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        transportation_output = self._safe_dict(
            transportation_output
        )

        result = {}

        for key in [
            "origin",
            "destination",
            "recommended_option",
            "transportation_summary",
            "recommended_mode",
            "arrival_mode",
            "departure_mode"
        ]:

            if key not in transportation_output:
                continue

            value = transportation_output.get(key)

            if isinstance(value, dict):

                compact_option = {}

                for option_key in [
                    "mode",
                    "type",
                    "name",
                    "description",
                    "summary",
                    "arrival_mode",
                    "departure_mode"
                ]:

                    if option_key in value:
                        compact_option[
                            option_key
                        ] = value.get(option_key)

                result[key] = (
                    compact_option
                    if compact_option
                    else value
                )

            else:

                result[key] = self._compact_text(
                    value,
                    600
                )

        return result

    # ==========================================================
    # ACCOMMODATION
    # ==========================================================

    def _compact_accommodation(
        self,
        accommodation_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        accommodation_output = self._safe_dict(
            accommodation_output
        )

        result = {}

        for key in [
            "destination",
            "accommodation_summary",
            "summary",
            "recommended_option",
            "accommodation_options",
            "recommendations",
            "price_note"
        ]:

            if key not in accommodation_output:
                continue

            value = accommodation_output.get(key)

            if key == "accommodation_options":

                if isinstance(value, list):

                    compact_options = []

                    for option in value[:5]:

                        if isinstance(option, dict):

                            compact_option = {}

                            for option_key in [
                                "name",
                                "type",
                                "description",
                                "location",
                                "estimated_price_per_night",
                                "estimated_total_cost"
                            ]:

                                if option_key in option:
                                    compact_option[
                                        option_key
                                    ] = option.get(
                                        option_key
                                    )

                            compact_options.append(
                                compact_option
                            )

                        else:

                            compact_options.append(
                                str(option)
                            )

                    result[key] = compact_options

                continue

            if isinstance(value, dict):
                result[key] = value

            elif isinstance(value, list):
                result[key] = value[:8]

            else:
                result[key] = self._compact_text(
                    value,
                    700
                )

        return result

    # ==========================================================
    # ITINERARY
    # ==========================================================

    def _compact_itinerary(
        self,
        itinerary_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        itinerary_output = self._safe_dict(
            itinerary_output
        )

        result = {}

        for key in [
            "destination",
            "duration_days",
            "travelers",
            "preferences"
        ]:

            if key in itinerary_output:
                result[key] = itinerary_output.get(key)

        raw_itinerary = itinerary_output.get(
            "itinerary",
            []
        )

        if not isinstance(
            raw_itinerary,
            list
        ):
            raw_itinerary = []

        itinerary = []

        for day in raw_itinerary:

            if not isinstance(day, dict):
                continue

            clean_day = {}

            if "day" in day:
                clean_day["day"] = day.get("day")

            if "title" in day:
                clean_day["title"] = day.get("title")

            activities = day.get(
                "activities",
                []
            )

            if not isinstance(
                activities,
                list
            ):
                activities = []

            clean_activities = []

            for activity in activities:

                if not isinstance(
                    activity,
                    dict
                ):
                    continue

                clean_activity = {}

                for key in [
                    "time",
                    "place",
                    "activity"
                ]:

                    if key in activity:
                        clean_activity[key] = (
                            activity.get(key)
                        )

                clean_activities.append(
                    clean_activity
                )

            clean_day["activities"] = (
                clean_activities
            )

            itinerary.append(
                clean_day
            )

        result["itinerary"] = itinerary

        summary = itinerary_output.get(
            "itinerary_summary"
        )

        if summary:
            result["itinerary_summary"] = (
                self._compact_text(
                    summary,
                    700
                )
            )

        return result

    # ==========================================================
    # BUDGET
    # ==========================================================

    def _compact_budget(
        self,
        budget_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        budget_output = self._safe_dict(
            budget_output
        )

        result = {}

        for key in [
            "budget",
            "total_estimated_cost",
            "remaining_budget",
            "budget_status"
        ]:

            if key in budget_output:
                result[key] = budget_output.get(key)

        return result

    # ==========================================================
    # REVIEW
    # ==========================================================

    def _compact_review(
        self,
        review_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        review_output = self._safe_dict(
            review_output
        )

        status = self._normalize_review_status(
            review_output.get(
                "review_status"
            )
        )

        result = {
            "review_status": status
        }

        issues = review_output.get(
            "issues",
            []
        )

        if isinstance(issues, list):

            result["issues"] = [
                self._compact_text(
                    issue,
                    300
                )
                for issue in issues[:8]
                if issue
            ]

        strengths = review_output.get(
            "strengths",
            []
        )

        if isinstance(strengths, list):

            result["strengths"] = [
                self._compact_text(
                    strength,
                    300
                )
                for strength in strengths[:8]
                if strength
            ]

        return result

    # ==========================================================
    # COLLECT OUTPUTS
    # ==========================================================

    def _get_agent_outputs(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:

        return {
            "planner": self._compact_planner(
                context.get(
                    "planner_output",
                    {}
                )
            ),

            "research": self._compact_research(
                context.get(
                    "research_output",
                    {}
                )
            ),

            "transportation": (
                self._compact_transportation(
                    context.get(
                        "transportation_output",
                        {}
                    )
                )
            ),

            "accommodation": (
                self._compact_accommodation(
                    context.get(
                        "accommodation_output",
                        {}
                    )
                )
            ),

            "itinerary": self._compact_itinerary(
                context.get(
                    "itinerary_output",
                    {}
                )
            ),

            "budget": self._compact_budget(
                context.get(
                    "budget_output",
                    {}
                )
            ),

            "review": self._compact_review(
                context.get(
                    "review_output",
                    {}
                )
            )
        }

    # ==========================================================
    # LLM PROMPT
    # ==========================================================

    def _build_prompt(
        self,
        user_request: Any,
        agent_outputs: Dict[str, Dict[str, Any]]
    ) -> str:

        user_text = self._compact_text(
            user_request,
            1000
        )

        compact_source = self._json_dump(
            agent_outputs
        )

        return f"""
You are the final Response Agent of a multi-agent travel planner.

Create a clear, friendly travel plan using ONLY the information
provided by the previous agents.

USER REQUEST:
{user_text}

AGENT INFORMATION:
{compact_source}

RULES:

1. Do not perform new research.
2. Do not invent places.
3. Do not invent hotels.
4. Do not invent prices.
5. Do not recalculate the budget.
6. Do not create a different itinerary.
7. Use the supplied itinerary.
8. Use Budget Agent values as the budget source of truth.
9. Use Review Agent status as the review source of truth.
10. Do not mention agents.
11. Do not mention JSON.
12. Do not mention LLMs.
13. Do not show internal processing.
14. Do not show activity entry costs.
15. Do not show cost_status.
16. Keep the language simple and natural.
17. Make the final result useful to an actual traveler.

Return ONLY valid JSON.

Required structure:

{{
    "title": "",
    "introduction": "",

    "trip_summary": {{
        "destination": "",
        "duration": "",
        "travelers": 0,
        "budget": 0,
        "estimated_total_cost": 0,
        "remaining_budget": 0,
        "budget_status": ""
    }},

    "transportation": {{
        "summary": "",
        "recommended_option": ""
    }},

    "accommodation": {{
        "summary": "",
        "recommended_option": ""
    }},

    "itinerary": [
        {{
            "day": 1,
            "title": "",
            "activities": [
                {{
                    "time": "",
                    "place": "",
                    "activity": ""
                }}
            ]
        }}
    ],

    "important_notes": [],

    "review_status": "",

    "final_message": ""
}}

Return ONLY the JSON object.
No Markdown.
No code fences.
No explanation.
"""

    # ==========================================================
    # ROBUST JSON EXTRACTION
    # ==========================================================

    @staticmethod
    def _extract_json(
        response: Any
    ) -> Dict[str, Any]:

        if response is None:
            raise ValueError(
                "LLM returned an empty response."
            )

        if isinstance(response, dict):
            return response

        cleaned = str(
            response
        ).strip()

        if not cleaned:
            raise ValueError(
                "LLM returned an empty response."
            )

        cleaned = re.sub(
            r"```(?:json)?",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = (
            cleaned
            .replace("```", "")
            .strip()
        )

        try:

            parsed = json.loads(
                cleaned
            )

            if isinstance(
                parsed,
                dict
            ):
                return parsed

        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")

        if start == -1:
            raise ValueError(
                "No JSON object found in LLM response."
            )

        depth = 0
        in_string = False
        escaped = False
        end = -1

        for index in range(
            start,
            len(cleaned)
        ):

            char = cleaned[index]

            if escaped:
                escaped = False
                continue

            if char == "\\" and in_string:
                escaped = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1

            elif char == "}":

                depth -= 1

                if depth == 0:
                    end = index
                    break

        if end == -1:
            raise ValueError(
                "LLM returned incomplete JSON."
            )

        json_text = cleaned[
            start:end + 1
        ]

        try:

            parsed = json.loads(
                json_text
            )

            if isinstance(
                parsed,
                dict
            ):
                return parsed

        except json.JSONDecodeError:

            repaired = json_text

            repaired = re.sub(
                r",\s*([}\]])",
                r"\1",
                repaired
            )

            repaired = re.sub(
                r"\bTrue\b",
                "true",
                repaired
            )

            repaired = re.sub(
                r"\bFalse\b",
                "false",
                repaired
            )

            repaired = re.sub(
                r"\bNone\b",
                "null",
                repaired
            )

            try:

                parsed = json.loads(
                    repaired
                )

                if isinstance(
                    parsed,
                    dict
                ):
                    return parsed

            except json.JSONDecodeError:
                pass

        raise ValueError(
            "LLM response must be a valid JSON object."
        )

    # ==========================================================
    # HUMAN-FRIENDLY RESPONSE BUILDER
    # ==========================================================

    def _build_human_friendly_response(
        self,
        result: Dict[str, Any]
    ) -> str:

        lines = []

        title = self._safe_text(
            result.get(
                "title",
                "Your Travel Plan"
            )
        )

        introduction = self._safe_text(
            result.get(
                "introduction",
                ""
            )
        )

        summary = self._safe_dict(
            result.get(
                "trip_summary",
                {}
            )
        )

        transportation = self._safe_dict(
            result.get(
                "transportation",
                {}
            )
        )

        accommodation = self._safe_dict(
            result.get(
                "accommodation",
                {}
            )
        )

        itinerary = self._safe_list(
            result.get(
                "itinerary",
                []
            )
        )

        notes = self._safe_list(
            result.get(
                "important_notes",
                []
            )
        )

        # ------------------------------------------------------
        # TITLE
        # ------------------------------------------------------

        lines.append(
            f"🌿 {title}"
        )

        lines.append(
            "=" * 60
        )

        if introduction:
            lines.append(
                introduction
            )

        lines.append("")

        # ------------------------------------------------------
        # TRIP SUMMARY
        # ------------------------------------------------------

        lines.append(
            "📌 TRIP SUMMARY"
        )

        destination = self._safe_text(
            summary.get(
                "destination"
            )
        )

        duration = self._safe_text(
            summary.get(
                "duration"
            )
        )

        travelers = summary.get(
            "travelers"
        )

        budget = summary.get(
            "budget"
        )

        total_cost = summary.get(
            "estimated_total_cost"
        )

        remaining = summary.get(
            "remaining_budget"
        )

        budget_status = self._safe_text(
            summary.get(
                "budget_status"
            )
        )

        if destination:
            lines.append(
                f"📍 Destination: {destination}"
            )

        if duration:
            lines.append(
                f"📅 Duration: {duration}"
            )

        if travelers:
            lines.append(
                f"👥 Travelers: {travelers}"
            )

        if budget:
            lines.append(
                f"💰 Budget: ₹{self._format_number(budget)}"
            )

        if total_cost:
            lines.append(
                "💵 Estimated total: "
                f"₹{self._format_number(total_cost)}"
            )

        if remaining:
            lines.append(
                "💚 Remaining budget: "
                f"₹{self._format_number(remaining)}"
            )

        if budget_status:
            lines.append(
                f"📊 Budget status: {budget_status}"
            )

        lines.append("")

        # ------------------------------------------------------
        # TRANSPORTATION
        # ------------------------------------------------------

        lines.append(
            "🚌 TRANSPORTATION"
        )

        transport_summary = self._safe_text(
            transportation.get(
                "summary"
            )
        )

        transport_option = self._safe_text(
            transportation.get(
                "recommended_option"
            )
        )

        if transport_summary:
            lines.append(
                f"• {transport_summary}"
            )

        if transport_option:
            lines.append(
                f"• Recommended: {transport_option}"
            )

        lines.append("")

        # ------------------------------------------------------
        # ACCOMMODATION
        # ------------------------------------------------------

        lines.append(
            "🏨 ACCOMMODATION"
        )

        accommodation_summary = self._safe_text(
            accommodation.get(
                "summary"
            )
        )

        accommodation_option = self._safe_text(
            accommodation.get(
                "recommended_option"
            )
        )

        if accommodation_summary:
            lines.append(
                f"• {accommodation_summary}"
            )

        if accommodation_option:
            lines.append(
                f"• Recommended: {accommodation_option}"
            )

        lines.append("")

        # ------------------------------------------------------
        # ITINERARY
        # ------------------------------------------------------

        lines.append(
            "🗺️ DAY-WISE ITINERARY"
        )

        for day in itinerary:

            if not isinstance(
                day,
                dict
            ):
                continue

            day_number = day.get(
                "day",
                ""
            )

            day_title = self._safe_text(
                day.get(
                    "title",
                    ""
                )
            )

            if day_title:
                lines.append(
                    f"\n📅 DAY {day_number} — {day_title}"
                )

            else:
                lines.append(
                    f"\n📅 DAY {day_number}"
                )

            activities = self._safe_list(
                day.get(
                    "activities",
                    []
                )
            )

            for activity in activities:

                if not isinstance(
                    activity,
                    dict
                ):
                    continue

                time = self._safe_text(
                    activity.get(
                        "time",
                        ""
                    )
                )

                place = self._safe_text(
                    activity.get(
                        "place",
                        ""
                    )
                )

                activity_text = self._safe_text(
                    activity.get(
                        "activity",
                        ""
                    )
                )

                if time and place:
                    lines.append(
                        f"   🕐 {time} — {place}"
                    )

                elif place:
                    lines.append(
                        f"   📍 {place}"
                    )

                if activity_text:
                    lines.append(
                        f"      {activity_text}"
                    )

        # ------------------------------------------------------
        # IMPORTANT NOTES
        # ------------------------------------------------------

        if notes:

            lines.append("")

            lines.append(
                "📌 IMPORTANT NOTES"
            )

            for note in notes:

                note_text = self._safe_text(
                    note
                )

                if note_text:
                    lines.append(
                        f"• {note_text}"
                    )

        # ------------------------------------------------------
        # FINAL MESSAGE
        # ------------------------------------------------------

        final_message = self._safe_text(
            result.get(
                "final_message",
                ""
            )
        )

        if final_message:

            lines.append("")

            lines.append(
                "=" * 60
            )

            lines.append(
                f"✨ {final_message}"
            )

        return "\n".join(lines).strip()

    # ==========================================================
    # NUMBER FORMATTER
    # ==========================================================

    @staticmethod
    def _format_number(
        value: Any
    ) -> str:

        number = ResponseAgent._safe_number(
            value,
            0
        )

        if number == int(number):
            return f"{int(number):,}"

        return f"{number:,.2f}"

    # ==========================================================
    # NORMALIZE RESULT
    # ==========================================================

    def _normalize_result(
        self,
        result: Dict[str, Any],
        planner_output: Dict[str, Any],
        budget_output: Dict[str, Any],
        review_output: Dict[str, Any],
        accommodation_output: Dict[str, Any],
        itinerary_output: Dict[str, Any]
    ) -> Dict[str, Any]:

        result = self._safe_dict(
            result
        )

        planner_output = self._safe_dict(
            planner_output
        )

        budget_output = self._safe_dict(
            budget_output
        )

        review_output = self._safe_dict(
            review_output
        )

        accommodation_output = self._safe_dict(
            accommodation_output
        )

        itinerary_output = self._safe_dict(
            itinerary_output
        )

        # ======================================================
        # DEFAULTS
        # ======================================================

        if not result.get("title"):
            result["title"] = (
                "Your Travel Plan"
            )

        if not result.get("introduction"):
            result["introduction"] = (
                "Here is your personalized travel plan."
            )

        if not isinstance(
            result.get("trip_summary"),
            dict
        ):
            result["trip_summary"] = {}

        if not isinstance(
            result.get("transportation"),
            dict
        ):
            result["transportation"] = {}

        if not isinstance(
            result.get("accommodation"),
            dict
        ):
            result["accommodation"] = {}

        if not isinstance(
            result.get("itinerary"),
            list
        ):
            result["itinerary"] = []

        if not isinstance(
            result.get("important_notes"),
            list
        ):
            result["important_notes"] = []

        # ======================================================
        # PLANNER FALLBACK
        # ======================================================

        planner_analysis = self._safe_dict(
            planner_output.get(
                "request_analysis"
            )
        )

        trip_summary = result[
            "trip_summary"
        ]

        if not trip_summary.get(
            "destination"
        ):

            trip_summary[
                "destination"
            ] = planner_analysis.get(
                "destination",
                ""
            )

        if not trip_summary.get(
            "duration"
        ):

            duration_days = planner_analysis.get(
                "duration_days"
            )

            if duration_days:
                trip_summary[
                    "duration"
                ] = (
                    f"{duration_days} days"
                )

        if not trip_summary.get(
            "travelers"
        ):

            trip_summary[
                "travelers"
            ] = planner_analysis.get(
                "travelers",
                0
            )

        # ======================================================
        # BUDGET SOURCE OF TRUTH
        # ======================================================

        trip_summary[
            "budget"
        ] = budget_output.get(
            "budget",
            planner_analysis.get(
                "budget",
                0
            )
        )

        trip_summary[
            "estimated_total_cost"
        ] = budget_output.get(
            "total_estimated_cost",
            0
        )

        trip_summary[
            "remaining_budget"
        ] = budget_output.get(
            "remaining_budget",
            0
        )

        trip_summary[
            "budget_status"
        ] = budget_output.get(
            "budget_status",
            ""
        )

        # ======================================================
        # ITINERARY FALLBACK
        # ======================================================

        if not result["itinerary"]:

            compact_itinerary = (
                self._compact_itinerary(
                    itinerary_output
                )
            )

            result["itinerary"] = (
                compact_itinerary.get(
                    "itinerary",
                    []
                )
            )

        # ======================================================
        # CLEAN ITINERARY
        # ======================================================

        cleaned_itinerary = []

        for day in result["itinerary"]:

            if not isinstance(
                day,
                dict
            ):
                continue

            clean_day = {
                "day": day.get(
                    "day",
                    ""
                ),
                "title": day.get(
                    "title",
                    ""
                ),
                "activities": []
            }

            activities = day.get(
                "activities",
                []
            )

            if not isinstance(
                activities,
                list
            ):
                activities = []

            for activity in activities:

                if not isinstance(
                    activity,
                    dict
                ):
                    continue

                clean_day[
                    "activities"
                ].append(
                    {
                        "time": activity.get(
                            "time",
                            ""
                        ),
                        "place": activity.get(
                            "place",
                            ""
                        ),
                        "activity": activity.get(
                            "activity",
                            ""
                        )
                    }
                )

            cleaned_itinerary.append(
                clean_day
            )

        result["itinerary"] = (
            cleaned_itinerary
        )

        # ======================================================
        # ACCOMMODATION FALLBACK
        # ======================================================

        accommodation = result[
            "accommodation"
        ]

        if not accommodation.get(
            "summary"
        ):

            summary = accommodation_output.get(
                "accommodation_summary",
                accommodation_output.get(
                    "summary",
                    ""
                )
            )

            if summary:
                accommodation[
                    "summary"
                ] = self._safe_text(
                    summary
                )

        if not accommodation.get(
            "recommended_option"
        ):

            recommended = (
                accommodation_output.get(
                    "recommended_option"
                )
            )

            if isinstance(
                recommended,
                dict
            ):

                name = recommended.get(
                    "name"
                )

                if name:
                    accommodation[
                        "recommended_option"
                    ] = str(name)

            elif recommended:

                accommodation[
                    "recommended_option"
                ] = self._safe_text(
                    recommended
                )

        # ======================================================
        # TRANSPORTATION FALLBACK
        # ======================================================

        transportation = result[
            "transportation"
        ]

        transportation_output = self._safe_dict(
            context_placeholder()
        )

        # The LLM normally provides this.
        # We do not invent transportation data here.

        if not transportation.get(
            "summary"
        ):
            transportation[
                "summary"
            ] = ""

        if not transportation.get(
            "recommended_option"
        ):
            transportation[
                "recommended_option"
            ] = ""

        # ======================================================
        # REVIEW SOURCE OF TRUTH
        # ======================================================

        authoritative_status = (
            self._normalize_review_status(
                review_output.get(
                    "review_status"
                )
            )
        )

        if authoritative_status:
            result[
                "review_status"
            ] = authoritative_status

        else:
            result[
                "review_status"
            ] = "needs_revision"

        # ======================================================
        # REVIEW ISSUES
        # ======================================================

        review_issues = review_output.get(
            "issues",
            []
        )

        if isinstance(
            review_issues,
            list
        ):

            existing = {
                str(note).strip().lower()
                for note in result[
                    "important_notes"
                ]
            }

            for issue in review_issues:

                text = self._safe_text(
                    issue
                )

                if (
                    text
                    and text.lower()
                    not in existing
                ):

                    result[
                        "important_notes"
                    ].append(
                        text
                    )

                    existing.add(
                        text.lower()
                    )

        # ======================================================
        # CLEAN NOTES
        # ======================================================

        result[
            "important_notes"
        ] = [
            str(note).strip()
            for note in result[
                "important_notes"
            ]
            if str(note).strip()
        ]

        # ======================================================
        # FINAL MESSAGE
        # ======================================================

        if result[
            "review_status"
        ] == "approved":

            result[
                "final_message"
            ] = (
                "Your travel plan is ready. "
                "Have a wonderful trip!"
            )

        else:

            result[
                "final_message"
            ] = (
                "Your travel plan needs a few "
                "changes before it can be finalized."
            )

        # ======================================================
        # HUMAN-FRIENDLY OUTPUT
        # ======================================================

        result[
            "human_friendly_response"
        ] = self._build_human_friendly_response(
            result
        )

        return result

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ):

        if not isinstance(
            context,
            dict
        ):
            context = {}

        user_request = context.get(
            "user_request",
            task
        )

        # ------------------------------------------------------
        # Previous agent outputs
        # ------------------------------------------------------

        agent_outputs = (
            self._get_agent_outputs(
                context
            )
        )

        planner_output = self._safe_dict(
            context.get(
                "planner_output",
                {}
            )
        )

        itinerary_output = self._safe_dict(
            context.get(
                "itinerary_output",
                {}
            )
        )

        budget_output = self._safe_dict(
            context.get(
                "budget_output",
                {}
            )
        )

        review_output = self._safe_dict(
            context.get(
                "review_output",
                {}
            )
        )

        accommodation_output = self._safe_dict(
            context.get(
                "accommodation_output",
                {}
            )
        )

        # ------------------------------------------------------
        # Build prompt
        # ------------------------------------------------------

        prompt = self._build_prompt(
            user_request=user_request,
            agent_outputs=agent_outputs
        )

        print(
            f"[Response Agent] "
            f"Preparing final travel response..."
        )

        # ------------------------------------------------------
        # LLM
        # ------------------------------------------------------

        try:

            response = self.llm.generate(
                prompt
            )

        except Exception as first_error:

            print(
                "[Response Agent] "
                f"Generation failed: {first_error}"
            )

            retry_prompt = self._build_retry_prompt(
                user_request,
                agent_outputs
            )

            try:

                response = self.llm.generate(
                    retry_prompt
                )

            except Exception as retry_error:

                print(
                    "[Response Agent] "
                    f"Retry failed: {retry_error}"
                )

                return {
                    "error": (
                        "Response Agent could not "
                        "generate the final response."
                    ),
                    "details": str(
                        retry_error
                    )
                }

        # ------------------------------------------------------
        # Parse
        # ------------------------------------------------------

        try:

            response_result = (
                self._extract_json(
                    response
                )
            )

        except Exception as parse_error:

            print(
                "[Response Agent] "
                f"Could not parse response: "
                f"{parse_error}"
            )

            repair_prompt = f"""
Convert this into valid JSON.

Return ONLY JSON.

Required keys:
title,
introduction,
trip_summary,
transportation,
accommodation,
itinerary,
important_notes,
review_status,
final_message

Response:
{self._compact_text(response, 5000)}
"""

            try:

                repaired_response = (
                    self.llm.generate(
                        repair_prompt
                    )
                )

                response_result = (
                    self._extract_json(
                        repaired_response
                    )
                )

            except Exception as repair_error:

                print(
                    "[Response Agent] "
                    f"Final parsing failed: "
                    f"{repair_error}"
                )

                return {
                    "error": (
                        "Response Agent could not "
                        "generate a valid final result."
                    ),
                    "details": str(
                        repair_error
                    )
                }

        # ------------------------------------------------------
        # Normalize
        # ------------------------------------------------------

        final_result = (
            self._normalize_result(
                result=response_result,
                planner_output=planner_output,
                budget_output=budget_output,
                review_output=review_output,
                accommodation_output=(
                    accommodation_output
                ),
                itinerary_output=(
                    itinerary_output
                )
            )
        )

        return final_result

    # ==========================================================
    # RETRY PROMPT
    # ==========================================================

    def _build_retry_prompt(
        self,
        user_request: Any,
        agent_outputs: Dict[str, Dict[str, Any]]
    ) -> str:

        itinerary = agent_outputs.get(
            "itinerary",
            {}
        )

        transportation = agent_outputs.get(
            "transportation",
            {}
        )

        accommodation = agent_outputs.get(
            "accommodation",
            {}
        )

        budget = agent_outputs.get(
            "budget",
            {}
        )

        review = agent_outputs.get(
            "review",
            {}
        )

        return f"""
Create a simple human-friendly travel plan.

User request:
{self._compact_text(user_request, 500)}

Itinerary:
{self._json_dump(itinerary)}

Transportation:
{self._json_dump(transportation)}

Accommodation:
{self._json_dump(accommodation)}

Budget:
{self._json_dump(budget)}

Review:
{self._json_dump(review)}

Return ONLY valid JSON:

{{
    "title": "",
    "introduction": "",

    "trip_summary": {{
        "destination": "",
        "duration": "",
        "travelers": 0,
        "budget": 0,
        "estimated_total_cost": 0,
        "remaining_budget": 0,
        "budget_status": ""
    }},

    "transportation": {{
        "summary": "",
        "recommended_option": ""
    }},

    "accommodation": {{
        "summary": "",
        "recommended_option": ""
    }},

    "itinerary": [],

    "important_notes": [],

    "review_status": "",

    "final_message": ""
}}

Do not invent information.
Do not recalculate the budget.
Do not invent hotels.
Do not show activity entry costs.
Do not use Markdown.
"""


# ==============================================================
# SAFE PLACEHOLDER
# ==============================================================

def context_placeholder():
    """
    Kept only for compatibility with the existing code structure.
    It does not contain travel information.
    """
    return {}