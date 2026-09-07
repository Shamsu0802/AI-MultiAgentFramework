import re
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base_agent import BaseAgent


class BudgetAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Budget Agent",
            description=(
                "Calculates the known trip cost using transportation "
                "and accommodation expenses. Food and activities are "
                "not included in the calculated total and are clearly "
                "mentioned as additional expenses that may increase "
                "the final cost. Other personal expenses are also "
                "excluded from the calculated total. If the user does "
                "not provide a budget, affordability is not calculated."
            )
        )

    # =========================================================
    # Helper: Convert value to a safe number
    # =========================================================

    def _safe_number(
        self,
        value: Any,
        default: float = 0.0
    ) -> float:

        if isinstance(value, bool):
            return default

        if isinstance(value, (int, float)):
            return float(value)

        if value is None:
            return default

        try:
            cleaned = str(value).replace(",", "").strip()
            return float(cleaned)

        except (TypeError, ValueError):
            return default

    # =========================================================
    # Helper: Extract monetary number from text
    #
    # IMPORTANT:
    # This function only extracts a number when the text
    # explicitly contains a budget-related expression.
    # =========================================================

    def _extract_number_from_text(
        self,
        text: str
    ) -> float:

        if not text:
            return 0.0

        text = str(text).strip()

        patterns = [

            # -------------------------------------------------
            # budget of 15000
            # budget is 15000
            # budget: 15000
            # budget = 15000
            # budget 15000
            # -------------------------------------------------

            r"\bbudget\s*(?:of|is|=|:)?\s*"
            r"(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?)",

            # -------------------------------------------------
            # total budget 15000
            # trip budget 15000
            # maximum budget 15000
            # -------------------------------------------------

            r"\b(?:total|trip|maximum|max|available)\s+"
            r"budget\s*(?:of|is|=|:)?\s*"
            r"(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?)",

            # -------------------------------------------------
            # ₹15000
            # -------------------------------------------------

            r"₹\s*([\d,]+(?:\.\d+)?)",

            # -------------------------------------------------
            # Rs 15000
            # Rs. 15000
            # -------------------------------------------------

            r"\brs\.?\s*([\d,]+(?:\.\d+)?)",

            # -------------------------------------------------
            # INR 15000
            # -------------------------------------------------

            r"\binr\s*([\d,]+(?:\.\d+)?)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if not match:
                continue

            try:

                number = float(
                    match.group(1).replace(",", "")
                )

                if number > 0:
                    return number

            except (ValueError, TypeError):
                continue

        return 0.0

    # =========================================================
    # Helper: Determine whether a key is budget-related
    #
    # IMPORTANT:
    # Only these keys are allowed to provide a numeric budget.
    #
    # This prevents:
    #
    # duration_days = 3
    # travelers = 2
    #
    # from becoming:
    #
    # budget = 3
    # =========================================================

    def _is_budget_key(
        self,
        key: Any
    ) -> bool:

        if not isinstance(key, str):
            return False

        normalized = (
            key.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        budget_keys = {
            "budget",
            "total_budget",
            "trip_budget",
            "max_budget",
            "maximum_budget",
            "budget_amount",
            "budget_limit",
            "available_budget",
            "budget_value",
            "total_trip_budget",
            "maximum_trip_budget"
        }

        return normalized in budget_keys

    # =========================================================
    # Helper: Search budget safely inside nested structures
    #
    # IMPORTANT:
    #
    # We NEVER treat an arbitrary number as a budget.
    #
    # Example:
    #
    # {
    #     "duration_days": 3,
    #     "travelers": 2
    # }
    #
    # returns NO budget.
    #
    # But:
    #
    # {
    #     "budget": 15000
    # }
    #
    # returns 15000.
    # =========================================================

    def _search_budget_recursively(
        self,
        data: Any
    ) -> float:

        if data is None:
            return 0.0

        # =====================================================
        # Dictionary
        # =====================================================

        if isinstance(data, dict):

            # -------------------------------------------------
            # FIRST:
            # Check only explicit budget keys.
            # -------------------------------------------------

            for key, value in data.items():

                if self._is_budget_key(key):

                    # -----------------------------------------
                    # Numeric budget
                    # -----------------------------------------

                    if isinstance(
                        value,
                        (int, float)
                    ) and not isinstance(
                        value,
                        bool
                    ):

                        number = self._safe_number(
                            value,
                            0
                        )

                        if number > 0:
                            return number

                    # -----------------------------------------
                    # String budget
                    # -----------------------------------------

                    if isinstance(
                        value,
                        str
                    ):

                        # First try direct conversion
                        number = self._safe_number(
                            value,
                            0
                        )

                        if number > 0:
                            return number

                        # Then try extracting from text
                        number = (
                            self._extract_number_from_text(
                                value
                            )
                        )

                        if number > 0:
                            return number

                    # -----------------------------------------
                    # Nested budget object
                    # -----------------------------------------

                    if isinstance(
                        value,
                        (dict, list, tuple)
                    ):

                        number = (
                            self._search_budget_recursively(
                                value
                            )
                        )

                        if number > 0:
                            return number

            # -------------------------------------------------
            # SECOND:
            # Search text fields.
            #
            # A number is accepted ONLY if the text contains
            # an explicit budget expression.
            # -------------------------------------------------

            text_keys = {
                "goal",
                "request",
                "user_request",
                "original_request",
                "description",
                "summary",
                "text",
                "query",
                "task",
                "prompt"
            }

            for key, value in data.items():

                if (
                    isinstance(key, str)
                    and key.lower() in text_keys
                    and isinstance(value, str)
                ):

                    number = (
                        self._extract_number_from_text(
                            value
                        )
                    )

                    if number > 0:
                        return number

            # -------------------------------------------------
            # THIRD:
            # Search constraints.
            #
            # Example:
            #
            # "budget of 15000"
            #
            # is valid.
            #
            # But:
            #
            # "3 days"
            #
            # is NOT valid.
            # -------------------------------------------------

            constraints = data.get(
                "constraints"
            )

            if isinstance(
                constraints,
                list
            ):

                for constraint in constraints:

                    if isinstance(
                        constraint,
                        str
                    ):

                        number = (
                            self._extract_number_from_text(
                                constraint
                            )
                        )

                        if number > 0:
                            return number

                    elif isinstance(
                        constraint,
                        dict
                    ):

                        number = (
                            self._search_budget_recursively(
                                constraint
                            )
                        )

                        if number > 0:
                            return number

            # -------------------------------------------------
            # FOURTH:
            # Recursively inspect nested dictionaries/lists.
            #
            # IMPORTANT:
            # We DO NOT recursively inspect arbitrary numeric
            # values.
            #
            # This is the critical fix.
            # -------------------------------------------------

            for key, value in data.items():

                # Budget keys were already checked.
                if self._is_budget_key(key):
                    continue

                if isinstance(
                    value,
                    (dict, list, tuple)
                ):

                    number = (
                        self._search_budget_recursively(
                            value
                        )
                    )

                    if number > 0:
                        return number

            return 0.0

        # =====================================================
        # List / Tuple
        # =====================================================

        if isinstance(
            data,
            (list, tuple)
        ):

            for item in data:

                if isinstance(
                    item,
                    (dict, list, tuple)
                ):

                    number = (
                        self._search_budget_recursively(
                            item
                        )
                    )

                    if number > 0:
                        return number

                elif isinstance(
                    item,
                    str
                ):

                    number = (
                        self._extract_number_from_text(
                            item
                        )
                    )

                    if number > 0:
                        return number

            return 0.0

        # =====================================================
        # STRING
        # =====================================================

        if isinstance(
            data,
            str
        ):

            return self._extract_number_from_text(
                data
            )

        # =====================================================
        # IMPORTANT:
        # Arbitrary numbers are NEVER treated as budgets.
        # =====================================================

        return 0.0

    # =========================================================
    # Extract total trip budget
    #
    # Returns:
    #
    #     (budget, True)
    #
    # or
    #
    #     (None, False)
    #
    # =========================================================

    def _extract_budget(
        self,
        user_request: Any,
        planner_output: Dict[str, Any]
    ) -> Tuple[Optional[float], bool]:

        # =====================================================
        # Priority 1:
        # Direct user request
        # =====================================================

        budget = (
            self._search_budget_recursively(
                user_request
            )
        )

        if budget > 0:
            return budget, True

        # =====================================================
        # Priority 2:
        # Planner output
        # =====================================================

        budget = (
            self._search_budget_recursively(
                planner_output
            )
        )

        if budget > 0:
            return budget, True

        # =====================================================
        # No budget supplied
        # =====================================================

        return None, False

    # =========================================================
    # Count planned activities
    #
    # Activity cost is NOT calculated.
    # =========================================================

    def _count_activities(
        self,
        itinerary: List[Dict[str, Any]]
    ) -> int:

        activity_count = 0

        for day in itinerary:

            if not isinstance(
                day,
                dict
            ):
                continue

            activities = day.get(
                "activities",
                []
            )

            if not isinstance(
                activities,
                list
            ):
                continue

            for activity in activities:

                if isinstance(
                    activity,
                    dict
                ):
                    activity_count += 1

                elif activity:
                    activity_count += 1

        return activity_count

    # =========================================================
    # Run Budget Agent
    # =========================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ):

        # =====================================================
        # STEP 1: Read shared context
        # =====================================================

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

        itinerary_output = context.get(
            "itinerary_output",
            {}
        )

        # =====================================================
        # Ensure dictionaries
        # =====================================================

        if not isinstance(
            planner_output,
            dict
        ):
            planner_output = {}

        if not isinstance(
            transportation_output,
            dict
        ):
            transportation_output = {}

        if not isinstance(
            accommodation_output,
            dict
        ):
            accommodation_output = {}

        if not isinstance(
            itinerary_output,
            dict
        ):
            itinerary_output = {}

        # =====================================================
        # STEP 2: Extract user's budget
        # =====================================================

        budget, budget_provided = (
            self._extract_budget(
                user_request,
                planner_output
            )
        )

        # =====================================================
        # STEP 3: Transportation
        #
        # INCLUDED.
        # =====================================================

        transportation = self._safe_number(
            transportation_output.get(
                "total_estimated_transportation_cost",
                0
            ),
            0
        )

        # -----------------------------------------------------
        # Fallback:
        # Arrival + local transportation
        # -----------------------------------------------------

        if transportation <= 0:

            arrival_cost = self._safe_number(
                transportation_output.get(
                    "estimated_arrival_cost_for_all_travelers",
                    0
                ),
                0
            )

            local_cost = self._safe_number(
                transportation_output.get(
                    "estimated_local_transportation_cost",
                    0
                ),
                0
            )

            transportation = (
                arrival_cost
                + local_cost
            )

        transportation_available = (
            transportation > 0
        )

        # =====================================================
        # STEP 4: Accommodation
        #
        # INCLUDED.
        # =====================================================

        accommodation = 0.0
        accommodation_available = False

        recommended_option = (
            accommodation_output.get(
                "recommended_option",
                {}
            )
        )

        if not isinstance(
            recommended_option,
            dict
        ):
            recommended_option = {}

        # -----------------------------------------------------
        # First preference:
        # Recommended total cost
        # -----------------------------------------------------

        recommended_total = self._safe_number(
            recommended_option.get(
                "estimated_total_cost"
            ),
            0
        )

        if recommended_total > 0:

            accommodation = (
                recommended_total
            )

            accommodation_available = True

        # -----------------------------------------------------
        # Second preference:
        # Price × nights × rooms
        # -----------------------------------------------------

        if not accommodation_available:

            price_per_night = (
                recommended_option.get(
                    "estimated_price_per_room_per_night"
                )
            )

            if price_per_night is None:

                price_per_night = (
                    recommended_option.get(
                        "estimated_price_per_night"
                    )
                )

            price_per_night = self._safe_number(
                price_per_night,
                0
            )

            nights = self._safe_number(
                accommodation_output.get(
                    "nights",
                    0
                ),
                0
            )

            rooms_required = self._safe_number(
                accommodation_output.get(
                    "rooms_required",
                    1
                ),
                1
            )

            if rooms_required <= 0:
                rooms_required = 1

            if (
                price_per_night > 0
                and nights > 0
            ):

                accommodation = (
                    price_per_night
                    * nights
                    * rooms_required
                )

                accommodation_available = True

        # -----------------------------------------------------
        # Third preference:
        # Overall accommodation cost
        # -----------------------------------------------------

        if not accommodation_available:

            accommodation_total = self._safe_number(
                accommodation_output.get(
                    "estimated_total_accommodation_cost"
                ),
                0
            )

            if accommodation_total > 0:

                accommodation = (
                    accommodation_total
                )

                accommodation_available = True

        # -----------------------------------------------------
        # Error handling
        # -----------------------------------------------------

        if accommodation_output.get(
            "error"
        ):

            accommodation = 0.0
            accommodation_available = False

        # =====================================================
        # STEP 5: Food + Activities
        #
        # NOT INCLUDED.
        # =====================================================

        itinerary = itinerary_output.get(
            "itinerary",
            []
        )

        if not isinstance(
            itinerary,
            list
        ):
            itinerary = []

        activity_count = (
            self._count_activities(
                itinerary
            )
        )

        food_and_activities_included = False

        if activity_count > 0:

            food_and_activities_note = (
                f"Food and activities are not included in the "
                f"calculated budget total. The itinerary contains "
                f"{activity_count} planned activity/attraction(s). "
                f"Actual spending may be higher depending on "
                f"meals, attraction entry fees, and activities "
                f"selected during the trip."
            )

        else:

            food_and_activities_note = (
                "Food and activities are not included in the "
                "calculated budget total. Actual spending may "
                "be higher depending on meals and activities "
                "selected during the trip."
            )

        # =====================================================
        # STEP 6: Other expenses
        #
        # NOT INCLUDED.
        # =====================================================

        other = 0.0
        other_available = False

        other_expense_note = (
            "Other personal expenses such as shopping, "
            "souvenirs, snacks, tips, and miscellaneous "
            "expenses are not included."
        )

        # =====================================================
        # STEP 7: Calculate ONLY known costs
        #
        # transportation + accommodation
        # =====================================================

        total_estimated_cost = (
            transportation
            + accommodation
        )

        # =====================================================
        # STEP 8: Remaining budget
        #
        # If budget is absent:
        #
        # remaining_budget = None
        #
        # NOT:
        #
        # 0 - total
        # =====================================================

        if budget_provided and budget is not None:

            remaining_budget = (
                budget
                - total_estimated_cost
            )

        else:

            remaining_budget = None

        # =====================================================
        # STEP 9: Budget status
        # =====================================================

        if not budget_provided:

            budget_status = (
                "budget_not_available"
            )

            exceeded_amount = 0.0

            recommendation = (
                "The trip budget was not provided. "
                "Transportation and accommodation costs are "
                "shown, but overall trip affordability cannot "
                "be determined without a budget."
            )

        elif not accommodation_available:

            budget_status = (
                "incomplete_cost_information"
            )

            exceeded_amount = 0.0

            recommendation = (
                "Accommodation cost is unavailable. "
                "The displayed total includes only known "
                "transportation expenses and cannot be "
                "treated as the final trip cost."
            )

        elif remaining_budget is not None and remaining_budget >= 0:

            budget_status = (
                "within_known_budget"
            )

            exceeded_amount = 0.0

            recommendation = (
                "Transportation and accommodation are within "
                "the available budget. However, this is only "
                "the known trip cost. Food, activities, and "
                "other personal expenses are not included, so "
                "the actual trip cost may be higher."
            )

        else:

            budget_status = (
                "over_budget"
            )

            exceeded_amount = abs(
                remaining_budget
            )

            recommendation = (
                "Transportation and accommodation alone "
                "already exceed the available budget. "
                "Additional expenses for food, activities, "
                "and other personal spending will increase "
                "the final trip cost further."
            )

        # =====================================================
        # STEP 10: Build final result
        # =====================================================

        budget_result = {

            # -------------------------------------------------
            # Budget
            # -------------------------------------------------

            "budget": (
                round(
                    budget,
                    2
                )
                if budget_provided and budget is not None
                else None
            ),

            "budget_provided": (
                budget_provided
            ),

            # -------------------------------------------------
            # Cost breakdown
            #
            # ONLY these two are included.
            # -------------------------------------------------

            "cost_breakdown": {

                "transportation": round(
                    transportation,
                    2
                ),

                "accommodation": round(
                    accommodation,
                    2
                )
            },

            # -------------------------------------------------
            # Known trip cost
            # -------------------------------------------------

            "total_estimated_cost": round(
                total_estimated_cost,
                2
            ),

            # -------------------------------------------------
            # Remaining budget
            # -------------------------------------------------

            "remaining_budget": (
                round(
                    remaining_budget,
                    2
                )
                if remaining_budget is not None
                else None
            ),

            # -------------------------------------------------
            # Status
            # -------------------------------------------------

            "budget_status": budget_status,

            # -------------------------------------------------
            # Exceeded amount
            # -------------------------------------------------

            "exceeded_amount": round(
                exceeded_amount,
                2
            ),

            # -------------------------------------------------
            # Cost information
            # -------------------------------------------------

            "cost_information": {

                "transportation_available":
                    transportation_available,

                "accommodation_available":
                    accommodation_available,

                "food_available":
                    False,

                "activities_available":
                    activity_count > 0,

                "other_available":
                    other_available,

                "food_and_activities_included":
                    food_and_activities_included,

                "other_expenses_included":
                    False
            },

            # -------------------------------------------------
            # Notes
            # -------------------------------------------------

            "cost_notes": {

                "known_cost_note": (
                    "The calculated trip cost includes only "
                    "transportation and accommodation."
                ),

                "budget_note": (
                    "No trip budget was provided by the user. "
                    "Budget affordability cannot be determined."
                    if not budget_provided
                    else
                    "The remaining budget is calculated after "
                    "subtracting the known transportation and "
                    "accommodation costs from the user's budget."
                ),

                "food_and_activities_note":
                    food_and_activities_note,

                "other_expenses_note":
                    other_expense_note,

                "final_cost_warning": (
                    "IMPORTANT: The actual trip cost may exceed "
                    "the calculated amount because food, "
                    "activities, and other personal expenses "
                    "are not included."
                )
            },

            # -------------------------------------------------
            # Recommendation
            # -------------------------------------------------

            "recommendation":
                recommendation
        }

        return budget_result