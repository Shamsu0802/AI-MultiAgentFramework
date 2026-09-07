import re
from typing import Any, Dict

from app.agents.base_agent import BaseAgent


class ReviewAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Review Agent",
            description=(
                "Performs a final validation of the travel plan using "
                "the outputs produced by the Planner, Transportation, "
                "Accommodation, Budget, and Itinerary agents."
            )
        )

    def run(self, task: str, context: Dict[str, Any]):

        # ==========================================================
        # GET DATA FROM SHARED CONTEXT
        # ==========================================================

        user_request = context.get(
            "user_request",
            task
        )

        planner_output = context.get(
            "planner_output",
            {}
        )

        transportation_output = context.get(
            "transportation_output",
            {}
        )

        accommodation_output = context.get(
            "accommodation_output",
            {}
        )

        budget_output = context.get(
            "budget_output",
            {}
        )

        itinerary_output = context.get(
            "itinerary_output",
            {}
        )

        # Make sure outputs are dictionaries
        if not isinstance(planner_output, dict):
            planner_output = {}

        if not isinstance(transportation_output, dict):
            transportation_output = {}

        if not isinstance(accommodation_output, dict):
            accommodation_output = {}

        if not isinstance(budget_output, dict):
            budget_output = {}

        if not isinstance(itinerary_output, dict):
            itinerary_output = {}

        # ==========================================================
        # PLANNER INFORMATION
        # ==========================================================

        planner_analysis = planner_output.get(
            "request_analysis",
            {}
        )

        if not isinstance(planner_analysis, dict):
            planner_analysis = {}

        planner_goal = planner_analysis.get(
            "goal",
            ""
        )

        if not isinstance(planner_goal, str):
            planner_goal = ""

        preferences = planner_analysis.get(
            "preferences",
            []
        )

        if not isinstance(preferences, list):
            preferences = []

        # ==========================================================
        # COMBINED REQUEST
        # ==========================================================

        combined_request = (
            f"{user_request} {planner_goal}"
        ).strip()

        combined_lower = combined_request.lower()

        # ==========================================================
        # DESTINATION
        # ==========================================================

        destination = ""

        structured_destinations = [
            planner_analysis.get("destination"),
            transportation_output.get("destination"),
            itinerary_output.get("destination"),
            accommodation_output.get("destination")
        ]

        for value in structured_destinations:

            if isinstance(value, str) and value.strip():
                destination = value.strip()
                break

        # Fallback: "from Chennai to Ooty"
        if not destination:

            destination_match = re.search(
                r"\bfrom\s+[A-Za-z][A-Za-z\s-]*?\s+to\s+"
                r"([A-Za-z][A-Za-z\s-]*?)"
                r"(?:\s+for\s+\d|\s+with\s+a|\s*$|[.,])",
                combined_request,
                re.IGNORECASE
            )

            if destination_match:

                destination = (
                    destination_match.group(1)
                    .strip()
                    .rstrip(".,")
                )

        # Fallback: "trip to Ooty"
        if not destination:

            destination_match = re.search(
                r"\bto\s+([A-Za-z][A-Za-z\s-]*?)"
                r"(?:\s+for\s+\d|\s+with\s+a|\s*$|[.,])",
                combined_request,
                re.IGNORECASE
            )

            if destination_match:

                destination = (
                    destination_match.group(1)
                    .strip()
                    .rstrip(".,")
                )

        # ==========================================================
        # REQUESTED DAYS
        # ==========================================================

        requested_days = None

        # First: Itinerary Agent
        itinerary_duration = itinerary_output.get(
            "duration_days"
        )

        if isinstance(
            itinerary_duration,
            (int, float)
        ):
            requested_days = int(
                itinerary_duration
            )

        # Second: Planner Agent
        if requested_days is None:

            planner_duration = planner_analysis.get(
                "duration_days"
            )

            if isinstance(
                planner_duration,
                (int, float)
            ):
                requested_days = int(
                    planner_duration
                )

        # Third: User request
        if requested_days is None:

            duration_match = re.search(
                r"\b(\d+)\s*(?:day|days|night|nights)\b",
                combined_lower
            )

            if duration_match:

                requested_days = int(
                    duration_match.group(1)
                )

        # ==========================================================
        # REQUESTED BUDGET
        # ==========================================================

        requested_budget = None

        budget_candidates = [
            planner_analysis.get("budget"),
            planner_output.get("budget"),
            budget_output.get("budget"),
            budget_output.get("available_budget"),
            budget_output.get("total_budget"),
            budget_output.get("requested_budget")
        ]

        for candidate in budget_candidates:

            if isinstance(candidate, (int, float)):

                if candidate > 0:

                    requested_budget = float(candidate)
                    break

            elif isinstance(candidate, str):

                numbers = re.findall(
                    r"\d+(?:\.\d+)?",
                    candidate.replace(",", "")
                )

                if numbers:

                    value = float(numbers[0])

                    if value > 0:
                        requested_budget = value
                        break

        # Fallback: extract budget from request
        if requested_budget is None:

            budget_match = re.search(
                r"(?:budget\s*(?:of|is|:)?\s*₹?\s*|₹\s*)"
                r"([0-9]+(?:\.[0-9]+)?)",
                combined_request,
                re.IGNORECASE
            )

            if budget_match:

                requested_budget = float(
                    budget_match.group(1)
                )

        # ==========================================================
        # BASIC REQUIREMENTS
        # ==========================================================

        destination_available = bool(
            destination
        )

        duration_available = (
            requested_days is not None
            and requested_days > 0
        )

        budget_available = (
            requested_budget is not None
            and requested_budget > 0
        )

        requirements_met = (
            destination_available
            and duration_available
            and budget_available
        )

        # ==========================================================
        # TRANSPORTATION CHECK
        # ==========================================================

        transportation_available = False

        if transportation_output:

            transportation_summary = (
                transportation_output.get(
                    "transportation_summary"
                )
            )

            recommended_option = (
                transportation_output.get(
                    "recommended_option"
                )
            )

            total_transport_cost = (
                transportation_output.get(
                    "total_estimated_transportation_cost"
                )
            )

            if transportation_summary:

                transportation_available = True

            elif (
                isinstance(
                    recommended_option,
                    dict
                )
                and recommended_option
            ):

                transportation_available = True

            elif isinstance(
                total_transport_cost,
                (int, float)
            ):

                transportation_available = True

        # ==========================================================
        # ACCOMMODATION CHECK
        # ==========================================================

        accommodation_options = (
            accommodation_output.get(
                "accommodation_options",
                []
            )
        )

        if not isinstance(
            accommodation_options,
            list
        ):
            accommodation_options = []

        recommended_accommodation = (
            accommodation_output.get(
                "recommended_option",
                {}
            )
        )

        if not isinstance(
            recommended_accommodation,
            dict
        ):
            recommended_accommodation = {}

        accommodation_available = False

        if accommodation_options:

            accommodation_available = True

        elif recommended_accommodation.get("name"):

            accommodation_available = True

        elif accommodation_output:

            # Some accommodation agents return a summary
            # rather than a list of options.
            accommodation_available = True

        # ==========================================================
        # ITINERARY CHECK
        # ==========================================================

        itinerary = itinerary_output.get(
            "itinerary",
            []
        )

        if not isinstance(
            itinerary,
            list
        ):
            itinerary = []

        itinerary_days = set()

        for item in itinerary:

            if not isinstance(item, dict):
                continue

            day_number = item.get("day")

            if isinstance(day_number, int):

                itinerary_days.add(day_number)

            elif isinstance(day_number, float):

                itinerary_days.add(
                    int(day_number)
                )

            elif isinstance(day_number, str):

                # Handles values such as:
                # "1"
                # "Day 1"
                match = re.search(
                    r"\d+",
                    day_number
                )

                if match:

                    itinerary_days.add(
                        int(match.group())
                    )

        itinerary_complete = False

        if requested_days is not None:

            required_days = set(
                range(
                    1,
                    requested_days + 1
                )
            )

            itinerary_complete = (
                required_days.issubset(
                    itinerary_days
                )
            )

        # ==========================================================
        # PREFERENCE CHECK
        # ==========================================================

        itinerary_text = str(
            itinerary_output
        ).lower()

        preferences_followed = True

        preference_matches = []

        if preferences:

            preferences_followed = False

            for preference in preferences:

                if not isinstance(
                    preference,
                    str
                ):
                    continue

                preference_lower = (
                    preference.lower().strip()
                )

                # Nature
                if preference_lower in {
                    "nature",
                    "nature travel",
                    "nature sightseeing"
                }:

                    nature_keywords = [
                        "nature",
                        "garden",
                        "park",
                        "viewpoint",
                        "scenic",
                        "tea",
                        "flowers",
                        "plants",
                        "lake",
                        "hill",
                        "forest",
                        "waterfall",
                        "wildlife",
                        "mountain"
                    ]

                    if any(
                        keyword in itinerary_text
                        for keyword in nature_keywords
                    ):

                        preferences_followed = True

                        preference_matches.append(
                            "nature"
                        )

                # Sightseeing
                elif preference_lower in {
                    "sightseeing",
                    "sight seeing",
                    "tourism",
                    "tourist attractions"
                }:

                    sightseeing_keywords = [
                        "visit",
                        "explore",
                        "sightseeing",
                        "viewpoint",
                        "garden",
                        "park",
                        "attraction",
                        "tea",
                        "lake",
                        "museum",
                        "temple"
                    ]

                    if any(
                        keyword in itinerary_text
                        for keyword in sightseeing_keywords
                    ):

                        preferences_followed = True

                        preference_matches.append(
                            "sightseeing"
                        )

                # Generic preference
                elif (
                    preference_lower
                    and preference_lower
                    in itinerary_text
                ):

                    preferences_followed = True

                    preference_matches.append(
                        preference_lower
                    )

        if not preferences:

            preferences_followed = True

        # ==========================================================
        # BUDGET INFORMATION
        # ==========================================================

        total_estimated_cost = (
            budget_output.get(
                "total_estimated_cost"
            )
        )

        remaining_budget = (
            budget_output.get(
                "remaining_budget"
            )
        )

        # Try alternative names used by different Budget Agent
        # implementations.
        if not isinstance(
            total_estimated_cost,
            (int, float)
        ):

            for key in [
                "total_cost",
                "estimated_total",
                "total_trip_cost",
                "calculated_total"
            ]:

                value = budget_output.get(key)

                if isinstance(
                    value,
                    (int, float)
                ):

                    total_estimated_cost = value
                    break

        if not isinstance(
            remaining_budget,
            (int, float)
        ):

            for key in [
                "budget_remaining",
                "remaining",
                "balance"
            ]:

                value = budget_output.get(key)

                if isinstance(
                    value,
                    (int, float)
                ):

                    remaining_budget = value
                    break

        # ==========================================================
        # DETERMINE BUDGET STATUS
        # ==========================================================

        budget_status = budget_output.get(
            "budget_status"
        )

        # ----------------------------------------------------------
        # IMPORTANT FIX
        #
        # If Budget Agent does not explicitly return budget_status,
        # derive it from the actual numbers.
        # ----------------------------------------------------------

        if not isinstance(
            budget_status,
            str
        ) or not budget_status.strip():

            if (
                isinstance(
                    requested_budget,
                    (int, float)
                )
                and isinstance(
                    total_estimated_cost,
                    (int, float)
                )
            ):

                if total_estimated_cost <= requested_budget:

                    budget_status = "within_budget"

                else:

                    budget_status = "over_budget"

            elif (
                isinstance(
                    requested_budget,
                    (int, float)
                )
                and isinstance(
                    remaining_budget,
                    (int, float)
                )
            ):

                if remaining_budget >= 0:

                    budget_status = "within_budget"

                else:

                    budget_status = "over_budget"

            else:

                # Do not immediately reject the plan.
                # We only mark the status as unknown if there
                # is genuinely no usable budget information.
                budget_status = "unknown"

        budget_status = budget_status.strip().lower()

        # ==========================================================
        # COST INFORMATION
        # ==========================================================

        cost_breakdown = budget_output.get(
            "cost_breakdown",
            {}
        )

        if not isinstance(
            cost_breakdown,
            dict
        ):
            cost_breakdown = {}

        cost_information = budget_output.get(
            "cost_information",
            {}
        )

        if not isinstance(
            cost_information,
            dict
        ):
            cost_information = {}

        accommodation_cost_available = (
            cost_information.get(
                "accommodation_available",
                True
            )
        )

        food_cost_available = (
            cost_information.get(
                "food_available",
                True
            )
        )

        activities_cost_available = (
            cost_information.get(
                "activities_available",
                True
            )
        )

        other_cost_available = (
            cost_information.get(
                "other_available",
                True
            )
        )

        # ==========================================================
        # KNOWN COST CHECK
        # ==========================================================

        known_cost_exceeds_budget = False

        if (
            isinstance(
                requested_budget,
                (int, float)
            )
            and isinstance(
                total_estimated_cost,
                (int, float)
            )
        ):

            known_cost_exceeds_budget = (
                total_estimated_cost
                > requested_budget
            )

        # ==========================================================
        # BUDGET COMPLIANCE
        # ==========================================================

        if known_cost_exceeds_budget:

            budget_compliant = False

        elif budget_status == "over_budget":

            budget_compliant = False

        elif budget_status == "within_budget":

            budget_compliant = True

        elif (
            isinstance(
                requested_budget,
                (int, float)
            )
            and isinstance(
                remaining_budget,
                (int, float)
            )
            and remaining_budget >= 0
        ):

            budget_compliant = True

        else:

            # Unknown budget information should not automatically
            # make an otherwise valid itinerary fail.
            #
            # This is especially useful when the Budget Agent
            # returns a calculated plan without an explicit
            # "budget_status" field.
            budget_compliant = True

        # ==========================================================
        # PRACTICAL BUDGET ISSUE
        # ==========================================================

        practical_budget_issue = False

        if (
            budget_compliant
            and isinstance(
                requested_budget,
                (int, float)
            )
            and requested_budget > 0
            and isinstance(
                remaining_budget,
                (int, float)
            )
        ):

            if remaining_budget < (
                requested_budget * 0.20
            ):

                practical_budget_issue = True

        # ==========================================================
        # BUILD ISSUES AND STRENGTHS
        # ==========================================================

        issues = []
        strengths = []

        # ==========================================================
        # REQUIREMENTS
        # ==========================================================

        if requirements_met:

            strengths.append(
                "Destination, trip duration, and budget "
                "are available."
            )

        else:

            if not destination_available:

                issues.append(
                    "Destination is missing from "
                    "the travel request."
                )

            if not duration_available:

                issues.append(
                    "Trip duration is missing from "
                    "the travel request."
                )

            if not budget_available:

                issues.append(
                    "Budget is missing from "
                    "the travel request."
                )

        # ==========================================================
        # TRANSPORTATION
        # ==========================================================

        if transportation_available:

            strengths.append(
                "Transportation information is available."
            )

        else:

            issues.append(
                "Transportation information is missing."
            )

        # ==========================================================
        # ACCOMMODATION
        # ==========================================================

        if accommodation_available:

            strengths.append(
                "Accommodation options are available."
            )

        else:

            issues.append(
                "Accommodation information is missing."
            )

        # ==========================================================
        # ITINERARY
        # ==========================================================

        if itinerary_complete:

            strengths.append(
                f"The itinerary contains all requested "
                f"{requested_days}-day entries."
            )

        else:

            if requested_days is not None:

                missing_days = sorted(
                    set(
                        range(
                            1,
                            requested_days + 1
                        )
                    )
                    - itinerary_days
                )

                if missing_days:

                    issues.append(
                        "Missing itinerary entries "
                        "for day(s): "
                        + ", ".join(
                            str(day)
                            for day in missing_days
                        )
                        + "."
                    )

            else:

                issues.append(
                    "The requested trip duration "
                    "could not be determined."
                )

        # ==========================================================
        # PREFERENCES
        # ==========================================================

        if preferences_followed:

            if preference_matches:

                unique_matches = list(
                    dict.fromkeys(
                        preference_matches
                    )
                )

                strengths.append(
                    "User preferences are reflected "
                    "in the itinerary: "
                    + ", ".join(
                        unique_matches
                    )
                    + "."
                )

            else:

                strengths.append(
                    "User preferences are reflected "
                    "in the itinerary."
                )

        else:

            issues.append(
                "The itinerary does not clearly reflect "
                "the user's stated preferences."
            )

        # ==========================================================
        # BUDGET RESULT
        # ==========================================================

        if budget_status == "within_budget":

            strengths.append(
                "The estimated trip cost is within "
                "the available budget."
            )

        elif budget_status == "over_budget":

            issues.append(
                "The estimated trip cost exceeds "
                "the available budget."
            )

        elif budget_status == "unknown":

            # This is only a warning now.
            # It does NOT automatically fail the review.
            issues.append(
                "The Budget Agent did not provide enough "
                "information to independently confirm the "
                "final budget status."
            )

        # ==========================================================
        # PRACTICAL BUDGET WARNING
        # ==========================================================

        if practical_budget_issue:

            if isinstance(
                remaining_budget,
                (int, float)
            ):

                remaining_text = (
                    f"₹{round(remaining_budget, 2)}"
                )

                issues.append(
                    f"Only {remaining_text} remains after "
                    "the known expenses."
                )

            issues.append(
                "Consider keeping some additional buffer "
                "for food and other incidental expenses."
            )

        # ==========================================================
        # FINAL DECISION
        # ==========================================================

        all_checks_passed = (
            requirements_met
            and budget_compliant
            and itinerary_complete
            and transportation_available
            and accommodation_available
            and preferences_followed
        )

        if all_checks_passed:

            review_status = "approved"

        else:

            review_status = "needs_revision"

        # ==========================================================
        # REVIEW SUMMARY
        # ==========================================================

        if review_status == "approved":

            review_summary = (
                "The travel plan covers the requested "
                "destination, duration, budget, "
                "transportation, accommodation, itinerary, "
                "and preferences."
            )

            recommendation = (
                "The travel plan is ready to be presented "
                "to the user."
            )

        elif budget_status == "over_budget":

            review_summary = (
                "The travel plan needs adjustment because "
                "the estimated expenses exceed the "
                "available budget."
            )

            recommendation = (
                "Reduce transportation, accommodation, "
                "or other trip expenses."
            )

        elif not requirements_met:

            review_summary = (
                "The travel plan is missing one or more "
                "required trip details."
            )

            recommendation = (
                "Complete the missing trip requirements "
                "before finalizing the plan."
            )

        elif not itinerary_complete:

            review_summary = (
                "The travel plan does not contain a "
                "complete itinerary for the requested "
                "trip duration."
            )

            recommendation = (
                "Complete the missing itinerary days."
            )

        else:

            review_summary = (
                "The travel plan has one or more issues "
                "that should be addressed before it "
                "is finalized."
            )

            recommendation = (
                "Review the listed issues and finalize "
                "the plan."
            )

        # ==========================================================
        # FINAL RESULT
        # ==========================================================

        review_result = {

            "review_status": review_status,

            "checks": {

                "requirements_met":
                    requirements_met,

                "budget_compliant":
                    budget_compliant,

                "itinerary_complete":
                    itinerary_complete,

                "transportation_available":
                    transportation_available,

                "accommodation_available":
                    accommodation_available,

                "preferences_followed":
                    preferences_followed
            },

            "issues": issues,

            "strengths": strengths,

            "review_summary": review_summary,

            "recommendation": recommendation
        }

        return review_result