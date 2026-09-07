import json
import re
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Planner Agent",
            description=(
                "Analyzes the user's request, extracts all important "
                "travel information, breaks the request into meaningful "
                "subtasks, dynamically selects the required registered "
                "agents, and determines execution order and dependencies."
            )
        )

    # ==========================================================
    # MAIN PLANNER
    # ==========================================================

    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:

        # ------------------------------------------------------
        # Get available agents
        # ------------------------------------------------------

        available_agents = context.get(
            "available_agents",
            []
        )

        if not isinstance(available_agents, list):
            return {
                "error": "Invalid available_agents supplied to Planner Agent."
            }

        if not available_agents:
            return {
                "error": (
                    "No agents are currently registered "
                    "in the Agent Registry."
                )
            }

        # ------------------------------------------------------
        # Preserve original request
        # ------------------------------------------------------

        original_request = (
            context.get("original_user_request")
            or context.get("user_request")
            or task
        )

        if not isinstance(original_request, str):
            original_request = str(original_request)

        # ------------------------------------------------------
        # Build registered-agent information
        # ------------------------------------------------------

        agent_information_lines = []

        for agent in available_agents:

            if not isinstance(agent, dict):
                continue

            agent_name = str(
                agent.get("name", "")
            ).strip()

            description = str(
                agent.get("description", "")
            ).strip()

            if agent_name:
                agent_information_lines.append(
                    f"- {agent_name}: {description}"
                )

        agent_information = "\n".join(
            agent_information_lines
        )

        if not agent_information:
            return {
                "error": (
                    "Agent Registry returned no valid "
                    "agent information."
                )
            }

        # ======================================================
        # PLANNER PROMPT
        # ======================================================

        prompt = f"""
You are the Planner Agent in a Multi-Agent Travel Planning System.

Your ONLY job is to analyze the user's request and create a
valid execution plan for the registered agents.

You MUST dynamically select only the agents that are actually
needed.

============================================================
REGISTERED AGENTS
============================================================

{agent_information}

============================================================
ORIGINAL USER REQUEST
============================================================

{original_request}

============================================================
SOURCE OF TRUTH
============================================================

The ORIGINAL USER REQUEST is the source of truth.

You MUST preserve every important piece of information
explicitly provided by the user.

NEVER invent missing information.

============================================================
REQUIRED STRUCTURED TRAVEL INFORMATION
============================================================

request_analysis MUST contain:

- goal
- origin
- destination
- duration_days
- travelers
- budget
- requirements
- constraints
- preferences

Rules:

origin:
    Starting location explicitly provided by the user.
    Use null if missing.

destination:
    Destination explicitly provided by the user.
    Use null if missing.

duration_days:
    Explicit number of trip days.
    Use 0 if missing.
    NEVER invent a duration.

travelers:
    Explicit number of travelers.
    Use 0 if missing.

budget:
    Explicit total budget.
    Use 0 if missing.

============================================================
IMPORTANT
============================================================

For:

"Plan a trip to Ooty from Chennai for 2 members"

Use:

"origin": "Chennai"
"destination": "Ooty"
"duration_days": 0
"travelers": 2
"budget": 0

DO NOT invent:

"duration_days": 3

For:

"Plan a 4-day trip to Ooty from Chennai for 2 people
with a budget of 20000"

Use:

"origin": "Chennai"
"destination": "Ooty"
"duration_days": 4
"travelers": 2
"budget": 20000

============================================================
REQUIREMENTS
============================================================

Put explicit things the user wants the system to do or include
inside requirements.

Examples:

- Visit Ooty Lake
- Visit Botanical Garden
- Visit Doddabetta Peak
- Travel by bus
- Use local taxis
- Stay in a private room
- Stay near Ooty town

============================================================
CONSTRAINTS
============================================================

Put explicit limitations, restrictions, maximums, exclusions,
or things the user says to avoid inside constraints.

Examples:

- Total trip cost must not exceed 20000
- Food expenses must stay within 3000
- Avoid luxury hotels
- Avoid expensive activities
- Do not create a very packed itinerary

IMPORTANT:

"avoid luxury hotels"

is a CONSTRAINT, not a preference.

"food expenses within 3000"

is a CONSTRAINT, not a preference.

============================================================
PREFERENCES
============================================================

Put positive travel preferences inside preferences.

Examples:

- Nature
- Sightseeing
- Peaceful places
- Budget-friendly accommodation
- Free time each day

Do NOT treat a negative statement as a positive preference.

For example:

"Avoid luxury hotels"

must NOT become:

"luxury"

under preferences.

============================================================
DO NOT LOSE SPECIFIC ACTIVITIES
============================================================

If the user explicitly mentions places or activities,
preserve them.

For example:

"Ooty Lake, Botanical Garden, Doddabetta Peak and Tea Factory"

must appear in requirements or another appropriate field.

============================================================
AGENT SELECTION RULES
============================================================

You may select ONLY agents listed in REGISTERED AGENTS.

You MUST NOT:

- invent an agent
- rename an agent
- create an agent
- select Planner Agent
- select an unnecessary agent

Select an agent only when its responsibility is relevant
to the user's request.

============================================================
DEPENDENCY RULES
============================================================

depends_on MUST contain STEP NUMBERS ONLY.

Example:

Step 1 = Research Agent
Step 2 = Transportation Agent

If Transportation Agent requires Research Agent:

"depends_on": [1]

Never put agent names inside depends_on.

Dependencies must:

- refer only to earlier steps
- refer to existing steps
- never refer to the same step
- never create circular dependencies
- only be used when the output is actually required

============================================================
TRAVEL INFORMATION FLOW
============================================================

Use the registered agent descriptions to determine
the actual workflow.

A possible workflow is:

Research Agent
    ↓
Transportation Agent
    ↓
Accommodation Agent
    ↓
Itinerary Agent
    ↓
Budget Agent
    ↓
Review Agent
    ↓
Response Agent

This is only an example.

Do NOT blindly use this sequence.

If agents can work independently:

"depends_on": []

If an agent requires another agent's output,
add the appropriate earlier step number.

============================================================
IMPORTANT AGENT ORDER RULES
============================================================

If Itinerary Agent contributes to Budget Agent:

Budget Agent MUST come after Itinerary Agent.

If Review Agent validates the itinerary and budget:

Review Agent MUST come after the relevant planning agents.

If Response Agent uses the reviewed final plan:

Response Agent MUST come after Review Agent.

============================================================
PARALLELIZATION
============================================================

Use:

"parallelizable": true

when the agent can execute independently after its
dependencies are complete.

Use:

"parallelizable": false

when the agent requires another agent's output.

============================================================
OUTPUT FORMAT
============================================================

Return EXACTLY ONE JSON OBJECT.

Do NOT return:

- explanations
- reasoning
- Markdown
- code fences
- ```json
- multiple JSON objects

Return ONLY valid JSON.

Structure:

{{
    "request_analysis": {{
        "goal": "",
        "origin": null,
        "destination": null,
        "duration_days": 0,
        "travelers": 0,
        "budget": 0,
        "requirements": [],
        "constraints": [],
        "preferences": []
    }},
    "subtasks": [
        {{
            "step": 1,
            "task": "",
            "agent": "",
            "reason": "",
            "depends_on": [],
            "parallelizable": false
        }}
    ]
}}

============================================================
FINAL VALIDATION
============================================================

Before returning:

1. Preserve origin.
2. Preserve destination.
3. Preserve duration if provided.
4. Preserve travelers if provided.
5. Preserve budget if provided.
6. Do not invent missing values.
7. Preserve explicit requirements.
8. Preserve explicit constraints.
9. Preserve explicit preferences.
10. Do not classify negative constraints as preferences.
11. All agents must exist in REGISTERED AGENTS.
12. Planner Agent must not be selected.
13. At least one subtask must exist.
14. Step numbers must start at 1.
15. Step numbers must be sequential.
16. Dependencies must contain integers only.
17. Dependencies must reference earlier steps only.
18. No circular dependencies.
19. Return ONLY ONE JSON OBJECT.
"""

        # ======================================================
        # CALL LLM
        # ======================================================

        try:

            response = self.llm.generate(
                prompt
            )

        except Exception as e:

            return {
                "error": "Planner LLM call failed.",
                "details": str(e)
            }

        # ======================================================
        # PARSE RESPONSE
        # ======================================================

        try:

            planner_result = (
                self._parse_planner_response(
                    response
                )
            )

            # --------------------------------------------------
            # Normalize and preserve original request information
            # BEFORE validation
            # --------------------------------------------------

            planner_result[
                "request_analysis"
            ] = self._normalize_request_analysis(
                planner_result.get(
                    "request_analysis",
                    {}
                ),
                original_request
            )

            # --------------------------------------------------
            # Validate
            # --------------------------------------------------

            self._validate_planner_result(
                planner_result,
                available_agents,
                original_request
            )

            # --------------------------------------------------
            # Sort subtasks
            # --------------------------------------------------

            planner_result["subtasks"] = sorted(
                planner_result["subtasks"],
                key=lambda item: item["step"]
            )

            return planner_result

        except (
            json.JSONDecodeError,
            ValueError,
            TypeError
        ) as e:

            # --------------------------------------------------
            # IMPORTANT DEBUG INFORMATION
            # --------------------------------------------------

            print("\n❌ Planner Agent validation failed.")
            print("   Error:", str(e))

            return {
                "error": (
                    "Planner Agent could not generate "
                    "a valid dynamic execution plan."
                ),
                "details": str(e)
            }

    # ==========================================================
    # PARSE PLANNER RESPONSE
    # ==========================================================

    def _parse_planner_response(
        self,
        response: Any
    ) -> Dict[str, Any]:

        # ======================================================
        # 1. Already-parsed dictionary
        # ======================================================
        if isinstance(response, dict):
            return response

        if not isinstance(response, str):
            raise ValueError(
                "Planner LLM response must be a string or dictionary."
            )

        cleaned = response.strip()

        if not cleaned:
            raise ValueError(
                "Planner LLM returned an empty response."
            )

        # ======================================================
        # 2. Remove Markdown code fences
        #    The LLM may sometimes return ```json ... ``` even
        #    though the prompt explicitly asks for plain JSON.
        # ======================================================
        cleaned = re.sub(
            r"```\s*(?:json|JSON)?\s*",
            "",
            cleaned
        )
        cleaned = cleaned.replace("```", "").strip()

        # ======================================================
        # 3. First try parsing the complete response directly
        # ======================================================
        try:
            parsed = json.loads(cleaned)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

        # ======================================================
        # 4. Extract all JSON objects from explanatory text
        # ======================================================
        json_objects = self._extract_json_objects(cleaned)

        if not json_objects:
            raise json.JSONDecodeError(
                "No valid JSON object found",
                cleaned,
                0
            )

        # ======================================================
        # 5. Prefer a complete planner object
        # ======================================================
        valid_candidates = []

        for candidate in json_objects:
            if not isinstance(candidate, dict):
                continue

            if "request_analysis" not in candidate:
                continue

            if "subtasks" not in candidate:
                continue

            if not isinstance(candidate.get("subtasks"), list):
                continue

            valid_candidates.append(candidate)

        if valid_candidates:

            def candidate_score(candidate: Dict[str, Any]):
                analysis = candidate.get("request_analysis", {})
                score = 0

                if isinstance(analysis, dict):
                    if str(analysis.get("goal", "")).strip():
                        score += 10

                    structured_fields = [
                        "origin",
                        "destination",
                        "duration_days",
                        "travelers",
                        "budget"
                    ]

                    for field in structured_fields:
                        if field in analysis:
                            score += 2

                score += len(candidate.get("subtasks", []))
                return score

            return max(
                valid_candidates,
                key=candidate_score
            )

        # ======================================================
        # 6. FALLBACK FOR THE EXACT FAILURE THAT CAN OCCUR
        #
        # Sometimes the LLM ignores the instruction to return one
        # JSON object and produces two separate JSON objects: one
        # containing request_analysis and another containing
        # subtasks.
        #
        # Example:
        #
        # {
        #     "request_analysis": {...}
        # }
        #
        # {
        #     "subtasks": [...]
        # }
        #
        # These are combined below into the planner structure
        # expected by the rest of the application.
        # ======================================================
        request_analysis = None
        subtasks = None

        # ------------------------------------------------------
        # Find request_analysis
        # ------------------------------------------------------
        for candidate in json_objects:
            if not isinstance(candidate, dict):
                continue

            candidate_analysis = candidate.get(
                "request_analysis"
            )

            if isinstance(candidate_analysis, dict):
                request_analysis = candidate_analysis
                break

        # ------------------------------------------------------
        # Find subtasks
        # ------------------------------------------------------
        for candidate in json_objects:
            if not isinstance(candidate, dict):
                continue

            candidate_subtasks = candidate.get(
                "subtasks"
            )

            if not isinstance(candidate_subtasks, list):
                continue

            # Accept the list only when it resembles the
            # planner's subtask structure.
            looks_like_subtasks = True

            for subtask in candidate_subtasks:
                if not isinstance(subtask, dict):
                    looks_like_subtasks = False
                    break

                if "step" not in subtask or "agent" not in subtask:
                    looks_like_subtasks = False
                    break

            if looks_like_subtasks:
                subtasks = candidate_subtasks
                break

        # ======================================================
        # 7. Combine compatible pieces
        # ======================================================
        if (
            isinstance(request_analysis, dict)
            and isinstance(subtasks, list)
        ):
            return {
                "request_analysis": request_analysis,
                "subtasks": subtasks
            }

        # ======================================================
        # 8. Nothing usable was found
        # ======================================================
        raise ValueError(
            "No usable planner JSON object was found. "
            "The LLM response did not contain a complete planner "
            "object or compatible request_analysis and subtasks objects."
        )

    # ==========================================================
    # EXTRACT JSON OBJECTS
    # ==========================================================

    def _extract_json_objects(
        self,
        text: str
    ) -> List[Dict[str, Any]]:

        objects: List[Dict[str, Any]] = []

        decoder = json.JSONDecoder()

        index = 0

        while index < len(text):

            start = text.find(
                "{",
                index
            )

            if start == -1:
                break

            try:

                obj, end = decoder.raw_decode(
                    text[start:]
                )

                if isinstance(
                    obj,
                    dict
                ):

                    objects.append(
                        obj
                    )

                index = start + end

            except json.JSONDecodeError:

                index = start + 1

        return objects

    # ==========================================================
    # NORMALIZE REQUEST ANALYSIS
    # ==========================================================

    def _normalize_request_analysis(
        self,
        analysis: Dict[str, Any],
        original_request: str
    ) -> Dict[str, Any]:

        if not isinstance(
            analysis,
            dict
        ):

            analysis = {}

        # ------------------------------------------------------
        # Basic fields
        # ------------------------------------------------------

        goal = analysis.get(
            "goal",
            ""
        )

        requirements = analysis.get(
            "requirements",
            []
        )

        constraints = analysis.get(
            "constraints",
            []
        )

        preferences = analysis.get(
            "preferences",
            []
        )

        if not isinstance(
            goal,
            str
        ):

            goal = str(goal)

        if not isinstance(
            requirements,
            list
        ):

            requirements = [
                str(requirements)
            ]

        if not isinstance(
            constraints,
            list
        ):

            constraints = [
                str(constraints)
            ]

        if not isinstance(
            preferences,
            list
        ):

            preferences = [
                str(preferences)
            ]

        # ------------------------------------------------------
        # Extract travel information from original request
        # ------------------------------------------------------

        extracted = self._extract_travel_information(
            original_request
        )

        # ------------------------------------------------------
        # Origin
        # ------------------------------------------------------

        origin = analysis.get(
            "origin"
        )

        if not origin:
            origin = extracted["origin"]

        if origin:
            origin = str(origin).strip()
        else:
            origin = None

        # ------------------------------------------------------
        # Destination
        # ------------------------------------------------------

        destination = analysis.get(
            "destination"
        )

        if not destination:
            destination = extracted["destination"]

        if destination:
            destination = str(destination).strip()
        else:
            destination = None

        # ------------------------------------------------------
        # Duration
        # ------------------------------------------------------

        duration_days = analysis.get(
            "duration_days",
            0
        )

        if (
            isinstance(duration_days, bool)
            or not isinstance(
                duration_days,
                (int, float)
            )
        ):

            duration_days = extracted[
                "duration_days"
            ]

        # If LLM returned 0 but original request contains a
        # duration, use the original request.
        if (
            duration_days == 0
            and extracted["duration_days"] > 0
        ):

            duration_days = extracted[
                "duration_days"
            ]

        duration_days = int(
            duration_days
        )

        # ------------------------------------------------------
        # Travelers
        # ------------------------------------------------------

        travelers = analysis.get(
            "travelers",
            0
        )

        if (
            isinstance(travelers, bool)
            or not isinstance(
                travelers,
                (int, float)
            )
            or travelers <= 0
        ):

            travelers = extracted[
                "travelers"
            ]

        travelers = int(
            travelers
        )

        # ------------------------------------------------------
        # Budget
        # ------------------------------------------------------

        budget = analysis.get(
            "budget",
            0
        )

        if (
            isinstance(budget, bool)
            or not isinstance(
                budget,
                (int, float)
            )
            or budget < 0
        ):

            budget = extracted[
                "budget"
            ]

        # If LLM returned 0 but original request has a budget,
        # use the original request.
        if (
            budget == 0
            and extracted["budget"] > 0
        ):

            budget = extracted[
                "budget"
            ]

        budget = float(
            budget
        )

        # ------------------------------------------------------
        # Preserve explicit information from original request
        # ------------------------------------------------------

        explicit_preferences = (
            self._extract_explicit_preferences(
                original_request
            )
        )

        explicit_constraints = (
            self._extract_explicit_constraints(
                original_request
            )
        )

        explicit_requirements = (
            self._extract_explicit_requirements(
                original_request
            )
        )

        # ------------------------------------------------------
        # Merge without duplicates
        # ------------------------------------------------------

        requirements = self._merge_unique(
            requirements,
            explicit_requirements
        )

        constraints = self._merge_unique(
            constraints,
            explicit_constraints
        )

        preferences = self._merge_unique(
            preferences,
            explicit_preferences
        )

        # ------------------------------------------------------
        # Remove negative preferences accidentally generated
        # by the LLM.
        # ------------------------------------------------------

        preferences = self._remove_negative_preferences(
            preferences,
            original_request
        )

        # ------------------------------------------------------
        # Goal fallback
        # ------------------------------------------------------

        if not goal.strip():
            goal = original_request.strip()

        return {
            "goal": goal.strip(),
            "origin": origin,
            "destination": destination,
            "duration_days": duration_days,
            "travelers": travelers,
            "budget": budget,
            "requirements": requirements,
            "constraints": constraints,
            "preferences": preferences
        }

    # ==========================================================
    # EXTRACT STRUCTURED TRAVEL INFORMATION
    # ==========================================================

    def _extract_travel_information(
        self,
        text: str
    ) -> Dict[str, Any]:

        result = {
            "origin": None,
            "destination": None,
            "duration_days": 0,
            "travelers": 0,
            "budget": 0.0
        }

        if not isinstance(
            text,
            str
        ):

            return result

        cleaned = text.strip()

        if not cleaned:
            return result

        # ------------------------------------------------------
        # Origin + destination
        # ------------------------------------------------------

        route_match = re.search(
            r"\bfrom\s+([A-Za-z][A-Za-z\s.-]*?)"
            r"\s+to\s+([A-Za-z][A-Za-z\s.-]*?)"
            r"(?=\s+(?:for|with|within|on|in|under|budget|and|,|\.|$))",
            cleaned,
            re.IGNORECASE
        )

        if route_match:

            origin = route_match.group(
                1
            ).strip()

            destination = route_match.group(
                2
            ).strip()

            if origin:
                result["origin"] = origin

            if destination:
                result["destination"] = destination

        # ------------------------------------------------------
        # Destination fallback
        # ------------------------------------------------------

        if not result["destination"]:

            destination_match = re.search(
                r"\b(?:trip|travel|journey|vacation|holiday)"
                r"\s+to\s+([A-Za-z][A-Za-z\s.-]*?)"
                r"(?=\s+(?:from|for|with|within|on|in|under|budget|and|,|\.|$))",
                cleaned,
                re.IGNORECASE
            )

            if destination_match:

                destination = (
                    destination_match.group(1)
                    .strip()
                )

                if destination:
                    result["destination"] = destination

        # ------------------------------------------------------
        # Duration
        # ------------------------------------------------------

        duration_match = re.search(
            r"\b(\d+)\s*[- ]?\s*days?\b",
            cleaned,
            re.IGNORECASE
        )

        if duration_match:

            result["duration_days"] = int(
                duration_match.group(1)
            )

        # ------------------------------------------------------
        # Travelers
        # ------------------------------------------------------

        traveler_patterns = [
            r"\bfor\s+(\d+)\s*"
            r"(?:members?|people|persons?|travelers?|travellers?)\b",

            r"\b(\d+)\s*"
            r"(?:members?|people|persons?|travelers?|travellers?)\b",

            r"\bfor\s+(\d+)\b"
        ]

        for pattern in traveler_patterns:

            traveler_match = re.search(
                pattern,
                cleaned,
                re.IGNORECASE
            )

            if traveler_match:

                result["travelers"] = int(
                    traveler_match.group(1)
                )

                break

        # ------------------------------------------------------
        # Budget
        # ------------------------------------------------------

        budget_patterns = [
            r"(?:budget|cost|spend|price)"
            r"\s*(?:of|is|:)?\s*"
            r"(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?)",

            r"\bunder\s+"
            r"(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?)",

            r"(?:₹|rs\.?|inr)\s*"
            r"([\d,]+(?:\.\d+)?)"
        ]

        for pattern in budget_patterns:

            budget_match = re.search(
                pattern,
                cleaned,
                re.IGNORECASE
            )

            if budget_match:

                budget_string = (
                    budget_match.group(1)
                    .replace(",", "")
                )

                try:

                    result["budget"] = float(
                        budget_string
                    )

                except ValueError:
                    pass

                break

        return result

    # ==========================================================
    # EXPLICIT PREFERENCE EXTRACTION
    # ==========================================================

    def _extract_explicit_preferences(
        self,
        text: str
    ) -> List[str]:

        preferences = []

        text_lower = text.lower()

        # ------------------------------------------------------
        # Positive preference patterns
        # ------------------------------------------------------

        positive_patterns = {
            "nature": [
                r"\bprefer\s+nature\b",
                r"\bnature\s+places?\b",
                r"\bnature\b"
            ],

            "sightseeing": [
                r"\bprefer\s+sightseeing\b",
                r"\bsightseeing\b"
            ],

            "adventure": [
                r"\bprefer\s+adventure\b",
                r"\badventure\b"
            ],

            "beach": [
                r"\bprefer\s+beaches?\b",
                r"\bbeaches?\b"
            ],

            "historical": [
                r"\bprefer\s+historical\b",
                r"\bhistorical\s+places?\b"
            ],

            "wildlife": [
                r"\bprefer\s+wildlife\b",
                r"\bwildlife\b"
            ],

            "shopping": [
                r"\bprefer\s+shopping\b",
                r"\bshopping\b"
            ],

            "relaxation": [
                r"\bprefer\s+relaxation\b",
                r"\brelaxing\b",
                r"\bpeaceful\b"
            ],

            "budget-friendly": [
                r"\bbudget[- ]friendly\b"
            ],

            "free time": [
                r"\bfree\s+time\b"
            ]
        }

        for preference, patterns in positive_patterns.items():

            for pattern in patterns:

                if re.search(
                    pattern,
                    text_lower
                ):

                    # ------------------------------------------
                    # Do not classify it as positive if it is
                    # explicitly negated.
                    # ------------------------------------------

                    if re.search(
                        rf"\b(?:avoid|no|not|don't|do not)\s+"
                        rf"(?:\w+\s+){{0,2}}"
                        rf"{re.escape(preference.split()[0])}",
                        text_lower
                    ):
                        continue

                    preferences.append(
                        preference
                    )

                    break

        return preferences

    # ==========================================================
    # EXPLICIT CONSTRAINT EXTRACTION
    # ==========================================================

    def _extract_explicit_constraints(
        self,
        text: str
    ) -> List[str]:

        constraints = []

        text_lower = text.lower()

        # ------------------------------------------------------
        # Avoid statements
        # ------------------------------------------------------

        avoid_matches = re.findall(
            r"\bavoid\s+([^.!?]+)",
            text,
            re.IGNORECASE
        )

        for match in avoid_matches:

            sentence = match.strip()

            # Split common conjunctions
            parts = re.split(
                r"\s+and\s+",
                sentence,
                flags=re.IGNORECASE
            )

            for part in parts:

                part = part.strip(
                    " ,"
                )

                if part:

                    constraints.append(
                        f"Avoid {part}"
                    )

        # ------------------------------------------------------
        # "must not exceed"
        # ------------------------------------------------------

        exceed_match = re.search(
            r"(?:must\s+not\s+exceed|not\s+exceed)"
            r"\s+(?:₹|rs\.?|inr)?\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        if exceed_match:

            amount = (
                exceed_match.group(1)
                .replace(",", "")
            )

            constraints.append(
                f"Total trip cost must not exceed {amount}"
            )

        # ------------------------------------------------------
        # Food budget
        # ------------------------------------------------------

        food_match = re.search(
            r"food\s+(?:expenses?|budget|cost)"
            r".*?"
            r"(?:within|under|below|of)"
            r"\s+(?:₹|rs\.?|inr)?\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        if food_match:

            amount = (
                food_match.group(1)
                .replace(",", "")
            )

            constraints.append(
                f"Food expenses must stay within {amount}"
            )

        # ------------------------------------------------------
        # Not packed / free time
        # ------------------------------------------------------

        if re.search(
            r"\b(?:not|don't|do not)\s+"
            r"(?:want\s+)?(?:a\s+)?very\s+packed\s+itinerary\b",
            text_lower
        ):

            constraints.append(
                "Do not create a very packed itinerary"
            )

        return constraints

    # ==========================================================
    # EXPLICIT REQUIREMENT EXTRACTION
    # ==========================================================

    def _extract_explicit_requirements(
        self,
        text: str
    ) -> List[str]:

        requirements = []

        # ------------------------------------------------------
        # Known Ooty-style attractions
        # ------------------------------------------------------

        known_places = [
            "Ooty Lake",
            "Botanical Garden",
            "Doddabetta Peak",
            "Tea Factory"
        ]

        for place in known_places:

            if re.search(
                re.escape(place),
                text,
                re.IGNORECASE
            ):

                requirements.append(
                    f"Visit {place}"
                )

        # ------------------------------------------------------
        # Bus transportation
        # ------------------------------------------------------

        if re.search(
            r"\btravel\s+by\s+bus\b",
            text,
            re.IGNORECASE
        ):

            requirements.append(
                "Travel by bus"
            )

        # ------------------------------------------------------
        # Local taxi
        # ------------------------------------------------------

        if re.search(
            r"\blocal\s+taxi(?:s)?\b",
            text,
            re.IGNORECASE
        ):

            requirements.append(
                "Use local taxis for sightseeing"
            )

        # ------------------------------------------------------
        # Private room
        # ------------------------------------------------------

        if re.search(
            r"\bprivate\s+room\b",
            text,
            re.IGNORECASE
        ):

            requirements.append(
                "Stay in a private room"
            )

        # ------------------------------------------------------
        # Near destination/town
        # ------------------------------------------------------

        if re.search(
            r"\bnear\s+Ooty\s+town\b",
            text,
            re.IGNORECASE
        ):

            requirements.append(
                "Stay near Ooty town"
            )

        return requirements

    # ==========================================================
    # MERGE UNIQUE VALUES
    # ==========================================================

    def _merge_unique(
        self,
        existing: List[Any],
        additions: List[Any]
    ) -> List[str]:

        result = []

        seen = set()

        for item in (
            list(existing or [])
            + list(additions or [])
        ):

            item_string = str(
                item
            ).strip()

            if not item_string:
                continue

            key = item_string.lower()

            if key not in seen:

                seen.add(key)

                result.append(
                    item_string
                )

        return result

    # ==========================================================
    # REMOVE NEGATIVE PREFERENCES
    # ==========================================================

    def _remove_negative_preferences(
        self,
        preferences: List[str],
        original_request: str
    ) -> List[str]:

        cleaned_preferences = []

        text_lower = original_request.lower()

        for preference in preferences:

            preference_lower = (
                str(preference).lower().strip()
            )

            # --------------------------------------------------
            # Explicit negative statements
            # --------------------------------------------------

            negative_patterns = [
                rf"\bavoid\s+(?:\w+\s+){{0,2}}"
                rf"{re.escape(preference_lower)}\b",

                rf"\bdo\s+not\s+(?:want\s+)?"
                rf"(?:\w+\s+){{0,2}}"
                rf"{re.escape(preference_lower)}\b",

                rf"\bdon't\s+(?:want\s+)?"
                rf"(?:\w+\s+){{0,2}}"
                rf"{re.escape(preference_lower)}\b",

                rf"\bno\s+(?:\w+\s+)?"
                rf"{re.escape(preference_lower)}\b"
            ]

            is_negative = any(
                re.search(
                    pattern,
                    text_lower
                )
                for pattern in negative_patterns
            )

            if is_negative:
                continue

            # --------------------------------------------------
            # Food is not automatically a preference.
            # It may be a constraint.
            # --------------------------------------------------

            if preference_lower == "food":

                if re.search(
                    r"food\s+(?:expenses?|budget|cost)",
                    text_lower
                ):

                    continue

            cleaned_preferences.append(
                preference
            )

        return self._merge_unique(
            [],
            cleaned_preferences
        )

    # ==========================================================
    # VALIDATE PLANNER RESULT
    # ==========================================================

    def _validate_planner_result(
        self,
        planner_result: Dict[str, Any],
        available_agents: List[Dict[str, Any]],
        task: str
    ):

        # ------------------------------------------------------
        # Top-level validation
        # ------------------------------------------------------

        if not isinstance(
            planner_result,
            dict
        ):

            raise ValueError(
                "Planner result must be an object."
            )

        if "request_analysis" not in planner_result:

            raise ValueError(
                "Missing 'request_analysis'."
            )

        if "subtasks" not in planner_result:

            raise ValueError(
                "Missing 'subtasks'."
            )

        # ------------------------------------------------------
        # Request analysis
        # ------------------------------------------------------

        request_analysis = (
            planner_result[
                "request_analysis"
            ]
        )

        if not isinstance(
            request_analysis,
            dict
        ):

            raise ValueError(
                "'request_analysis' must be an object."
            )

        required_analysis_fields = [
            "goal",
            "origin",
            "destination",
            "duration_days",
            "travelers",
            "budget",
            "requirements",
            "constraints",
            "preferences"
        ]

        for field in required_analysis_fields:

            if field not in request_analysis:

                raise ValueError(
                    f"Missing request analysis field: {field}"
                )

        # ------------------------------------------------------
        # Goal
        # ------------------------------------------------------

        goal = request_analysis.get(
            "goal"
        )

        if not isinstance(
            goal,
            str
        ):

            raise ValueError(
                "'request_analysis.goal' must be a string."
            )

        if not goal.strip():

            raise ValueError(
                "'request_analysis.goal' cannot be empty."
            )

        # ------------------------------------------------------
        # Origin
        # ------------------------------------------------------

        origin = request_analysis.get(
            "origin"
        )

        if (
            origin is not None
            and not isinstance(origin, str)
        ):

            raise ValueError(
                "'request_analysis.origin' must be "
                "a string or null."
            )

        # ------------------------------------------------------
        # Destination
        # ------------------------------------------------------

        destination = request_analysis.get(
            "destination"
        )

        if (
            destination is not None
            and not isinstance(destination, str)
        ):

            raise ValueError(
                "'request_analysis.destination' must be "
                "a string or null."
            )

        # ------------------------------------------------------
        # Duration
        # ------------------------------------------------------

        duration_days = request_analysis.get(
            "duration_days"
        )

        if (
            isinstance(duration_days, bool)
            or not isinstance(
                duration_days,
                int
            )
        ):

            raise ValueError(
                "'request_analysis.duration_days' must "
                "be an integer."
            )

        if duration_days < 0:

            raise ValueError(
                "'request_analysis.duration_days' cannot "
                "be negative."
            )

        # ------------------------------------------------------
        # Travelers
        # ------------------------------------------------------

        travelers = request_analysis.get(
            "travelers"
        )

        if (
            isinstance(travelers, bool)
            or not isinstance(
                travelers,
                int
            )
        ):

            raise ValueError(
                "'request_analysis.travelers' must "
                "be an integer."
            )

        if travelers < 0:

            raise ValueError(
                "'request_analysis.travelers' cannot "
                "be negative."
            )

        # ------------------------------------------------------
        # Budget
        # ------------------------------------------------------

        budget = request_analysis.get(
            "budget"
        )

        if (
            isinstance(budget, bool)
            or not isinstance(
                budget,
                (int, float)
            )
        ):

            raise ValueError(
                "'request_analysis.budget' must "
                "be a number."
            )

        if budget < 0:

            raise ValueError(
                "'request_analysis.budget' cannot "
                "be negative."
            )

        # ------------------------------------------------------
        # Lists
        # ------------------------------------------------------

        for field in [
            "requirements",
            "constraints",
            "preferences"
        ]:

            if not isinstance(
                request_analysis[field],
                list
            ):

                raise ValueError(
                    f"'{field}' must be a list."
                )

        # ------------------------------------------------------
        # Subtasks
        # ------------------------------------------------------

        subtasks = planner_result[
            "subtasks"
        ]

        if not isinstance(
            subtasks,
            list
        ):

            raise ValueError(
                "'subtasks' must be a list."
            )

        if not subtasks:

            raise ValueError(
                "Planner generated no subtasks."
            )

        # ------------------------------------------------------
        # Registered agent names
        # ------------------------------------------------------

        registered_agent_names = {
            agent.get("name")
            for agent in available_agents
            if isinstance(agent, dict)
        }

        # ------------------------------------------------------
        # Required subtask fields
        # ------------------------------------------------------

        required_subtask_fields = [
            "step",
            "task",
            "agent",
            "reason",
            "depends_on",
            "parallelizable"
        ]

        step_numbers = set()

        # ------------------------------------------------------
        # Validate each subtask
        # ------------------------------------------------------

        for subtask in subtasks:

            if not isinstance(
                subtask,
                dict
            ):

                raise ValueError(
                    "Each subtask must be an object."
                )

            for field in required_subtask_fields:

                if field not in subtask:

                    raise ValueError(
                        f"Missing subtask field: {field}"
                    )

            # --------------------------------------------------
            # Step
            # --------------------------------------------------

            step = subtask[
                "step"
            ]

            if (
                isinstance(step, bool)
                or not isinstance(
                    step,
                    int
                )
            ):

                raise ValueError(
                    "Subtask 'step' must be an integer."
                )

            if step <= 0:

                raise ValueError(
                    "Step numbers must start from 1."
                )

            if step in step_numbers:

                raise ValueError(
                    f"Duplicate step number: {step}"
                )

            step_numbers.add(
                step
            )

            # --------------------------------------------------
            # Task
            # --------------------------------------------------

            subtask_task = subtask[
                "task"
            ]

            if (
                not isinstance(
                    subtask_task,
                    str
                )
                or not subtask_task.strip()
            ):

                raise ValueError(
                    f"Step {step} has an invalid task."
                )

            # --------------------------------------------------
            # Agent
            # --------------------------------------------------

            selected_agent = subtask[
                "agent"
            ]

            if (
                not isinstance(
                    selected_agent,
                    str
                )
                or not selected_agent.strip()
            ):

                raise ValueError(
                    f"Step {step} has an invalid agent."
                )

            if selected_agent not in registered_agent_names:

                raise ValueError(
                    "Planner selected unregistered "
                    f"agent: {selected_agent}"
                )

            if selected_agent == self.name:

                raise ValueError(
                    "Planner Agent cannot appear "
                    "inside its own subtasks."
                )

            # --------------------------------------------------
            # Reason
            # --------------------------------------------------

            if not isinstance(
                subtask["reason"],
                str
            ):

                raise ValueError(
                    f"Step {step} reason must be a string."
                )

            # --------------------------------------------------
            # Dependencies
            # --------------------------------------------------

            depends_on = subtask[
                "depends_on"
            ]

            if not isinstance(
                depends_on,
                list
            ):

                raise ValueError(
                    f"Step {step} 'depends_on' "
                    "must be a list."
                )

            for dependency in depends_on:

                if (
                    isinstance(
                        dependency,
                        bool
                    )
                    or not isinstance(
                        dependency,
                        int
                    )
                ):

                    raise ValueError(
                        "Dependencies must contain "
                        "step numbers only."
                    )

                if dependency == step:

                    raise ValueError(
                        f"Step {step} cannot depend "
                        "on itself."
                    )

            # --------------------------------------------------
            # Parallelizable
            # --------------------------------------------------

            parallelizable = subtask[
                "parallelizable"
            ]

            if not isinstance(
                parallelizable,
                bool
            ):

                raise ValueError(
                    f"Step {step} 'parallelizable' "
                    "must be true or false."
                )

        # ------------------------------------------------------
        # Validate sequential steps
        # ------------------------------------------------------

        expected_steps = set(
            range(
                1,
                len(subtasks) + 1
            )
        )

        if step_numbers != expected_steps:

            raise ValueError(
                "Subtask steps must be sequential "
                "starting from 1."
            )

        # ------------------------------------------------------
        # Validate dependencies
        # ------------------------------------------------------

        for subtask in subtasks:

            step = subtask[
                "step"
            ]

            for dependency in subtask[
                "depends_on"
            ]:

                if dependency not in step_numbers:

                    raise ValueError(
                        f"Step {step} depends on "
                        f"non-existing step {dependency}."
                    )

                if dependency >= step:

                    raise ValueError(
                        f"Step {step} has invalid dependency "
                        f"{dependency}. Dependencies must "
                        "refer to earlier steps."
                    )

        # ------------------------------------------------------
        # Validate preferences
        # ------------------------------------------------------

        self._validate_preferences(
            task,
            request_analysis
        )

    # ==========================================================
    # PREFERENCE VALIDATION
    # ==========================================================

    def _validate_preferences(
        self,
        task: str,
        request_analysis: Dict[str, Any]
    ):

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # Only validate POSITIVE preferences.
        #
        # Do not classify:
        #
        # "avoid luxury"
        # "food budget"
        # "avoid expensive activities"
        #
        # as preferences.
        # ------------------------------------------------------

        explicit_preferences = (
            self._extract_explicit_preferences(
                task
            )
        )

        if not explicit_preferences:
            return

        planner_preferences = [
            str(preference).lower().strip()
            for preference in request_analysis.get(
                "preferences",
                []
            )
        ]

        missing_preferences = []

        for preference in explicit_preferences:

            matched = any(
                (
                    preference.lower() in planner_preference
                    or
                    planner_preference in preference.lower()
                )
                for planner_preference
                in planner_preferences
            )

            if not matched:

                missing_preferences.append(
                    preference
                )

        if missing_preferences:

            raise ValueError(
                "Planner did not preserve explicit "
                "user preferences: "
                f"{missing_preferences}"
            )