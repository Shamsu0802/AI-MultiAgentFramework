import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.llm.llm_manager import LLMManager


class BaseAgent(ABC):

    def __init__(
        self,
        name: str,
        description: str
    ):
        """
        Base class for all agents.

        Every specialized agent inherits from this class.

        The BaseAgent is responsible for:
        - Initializing the agent
        - Providing the LLM manager
        - Executing the agent
        - Measuring execution time
        - Handling exceptions
        - Returning a consistent execution result
        """

        self.name = name
        self.description = description
        self.llm = LLMManager()

    # ======================================================
    # COMMON AGENT EXECUTION
    # ======================================================

    def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        """
        Common execution method used by every agent.

        The specialized agent implements:

            run(task, context)

        BaseAgent.execute() wraps that result into a
        consistent structure for the Orchestrator.
        """

        start_time = time.time()

        # --------------------------------------------------
        # Normalize context
        # --------------------------------------------------

        if context is None:
            context = {}

        if not isinstance(context, dict):
            context = {}

        # ==================================================
        # DISPLAY AGENT START
        # ==================================================

        print("\n")
        print("=" * 60)
        print(f"🤖 AGENT: {self.name}")
        print("=" * 60)

        print(f"📌 TASK:")
        print(task)

        print("-" * 60)

        print(
            f"📥 CONTEXT KEYS: "
            f"{list(context.keys())}"
        )

        print("=" * 60)

        # ==================================================
        # EXECUTE AGENT
        # ==================================================

        try:

            # --------------------------------------------------
            # Call specialized agent
            # --------------------------------------------------

            result = self.run(
                task,
                context
            )

            # --------------------------------------------------
            # Calculate execution time
            # --------------------------------------------------

            execution_time = round(
                time.time() - start_time,
                3
            )

            # ==================================================
            # DEBUG RESULT
            # ==================================================

            print("\n")
            print("=" * 60)
            print(f"🔍 {self.name} RAW RESULT")
            print("=" * 60)

            print(
                f"Result type: {type(result)}"
            )

            print(
                "Result:"
            )

            print(result)

            print("=" * 60)

            # --------------------------------------------------
            # Handle None result
            # --------------------------------------------------

            if result is None:

                print(
                    f"⚠️ {self.name} returned None."
                )

                return {
                    "agent": self.name,
                    "status": "failed",
                    "task": task,
                    "output": None,
                    "error": (
                        f"{self.name} returned "
                        "no output."
                    ),
                    "execution_time": execution_time
                }

            # ==================================================
            # HANDLE EXPLICIT AGENT ERROR
            # ==================================================

            if (
                isinstance(result, dict)
                and "error" in result
            ):

                print("\n")
                print(
                    f"❌ {self.name} returned an error."
                )

                print(
                    f"Error: {result.get('error')}"
                )

                return {
                    "agent": self.name,
                    "status": "failed",
                    "task": task,

                    # Preserve the complete result.
                    #
                    # This is important because the
                    # orchestrator can inspect the exact
                    # error returned by the agent.
                    "output": result,

                    "error": result.get(
                        "error"
                    ),

                    "execution_time": execution_time
                }

            # ==================================================
            # SUCCESS
            # ==================================================

            print("\n")
            print("=" * 60)
            print(f"✅ {self.name} COMPLETED")
            print("=" * 60)

            print(
                f"⏱️ Execution time: "
                f"{execution_time}s"
            )

            print(
                f"📤 OUTPUT TYPE: "
                f"{type(result).__name__}"
            )

            print(
                "📤 OUTPUT:"
            )

            print(result)

            print("=" * 60)

            # --------------------------------------------------
            # IMPORTANT:
            #
            # Preserve the EXACT result returned by run().
            #
            # For Planner Agent this should remain:
            #
            # {
            #     "request_analysis": {...},
            #     "subtasks": [...]
            # }
            #
            # Do not modify or flatten it.
            # --------------------------------------------------

            return {
                "agent": self.name,
                "status": "completed",
                "task": task,
                "output": result,
                "execution_time": execution_time
            }

        # ==================================================
        # UNEXPECTED EXCEPTION
        # ==================================================

        except Exception as e:

            execution_time = round(
                time.time() - start_time,
                3
            )

            print("\n")
            print("=" * 60)
            print(f"❌ {self.name} FAILED")
            print("=" * 60)

            print(
                f"Error: {str(e)}"
            )

            print(
                f"⏱️ Execution time: "
                f"{execution_time}s"
            )

            # --------------------------------------------------
            # Print complete traceback server-side
            # --------------------------------------------------

            print("\n🔎 TRACEBACK:")
            print(
                traceback.format_exc()
            )

            print("=" * 60)

            return {
                "agent": self.name,
                "status": "failed",
                "task": task,

                # No valid agent output was produced.
                "output": None,

                "error": str(e),

                "execution_time": execution_time
            }

    # ======================================================
    # ABSTRACT RUN METHOD
    # ======================================================

    @abstractmethod
    def run(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Any:

        """
        Each specialized agent must implement
        its own logic here.

        Example:

            def run(self, task, context):

                ...

                return {
                    "some": "result"
                }

        BaseAgent.execute() will preserve that
        returned object exactly.
        """

        pass