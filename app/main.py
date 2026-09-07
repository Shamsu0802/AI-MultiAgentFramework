from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.agents.transportation_agent import TransportationAgent
from app.agents.accommodation_agent import AccommodationAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.itinerary_agent import ItineraryAgent
from app.agents.review_agent import ReviewAgent
from app.agents.response_agent import ResponseAgent

from app.core.agent_registry import AgentRegistry
from app.core.orchestrator import Orchestrator
from app.memory.shared_memory import SharedMemory


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Multi-Agent Travel Planner",
    description="Multi-agent AI application for intelligent travel planning",
    version="1.0.0"
)
# ============================================================
# DESTINATION IMAGE FILES
# ============================================================
# Serve images stored inside:
#
# Final_pro/
# └── frontend/
#     └── public/
#         └── destinations/
#
# Example:
# frontend/public/destinations/ooty/1.jpg
#
# will be available at:
# http://127.0.0.1:8000/destinations/ooty/1.jpg 
# ============================================================ 
 
PROJECT_ROOT = Path(__file__).resolve().parent.parent 
 
DESTINATIONS_DIR = ( 
    PROJECT_ROOT 
    / "frontend" 
    / "public" 
    / "destinations" 
) 
 
if DESTINATIONS_DIR.exists(): 
    app.mount( 
        "/destinations", 
        StaticFiles(directory=str(DESTINATIONS_DIR)), 
        name="destinations" 
    ) 
else: 
    print( 
        f"WARNING: Destination images folder not found: " 
        f"{DESTINATIONS_DIR}" 
    ) 
 
# ============================================================ 
# CORS CONFIGURATION 
# ============================================================ 
# Allows the HTML/CSS/JavaScript frontend to communicate 
# with the FastAPI backend. 
# 
# This supports: 
# - Opening frontend directly from the browser 
# - VS Code Live Server 
# - localhost frontend servers 
# ============================================================ 
 
app.add_middleware( 
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=False, 
    allow_methods=["*"], 
    allow_headers=["*"], 
) 
 
 
# ============================================================ 
# AGENT REGISTRY 
# ============================================================ 
 
registry = AgentRegistry() 
 
 
# ============================================================ 
# PLANNER AGENT 
# ============================================================ 
 
planner = PlannerAgent() 
 
registry.register( 
    name=planner.name, 
    description=planner.description, 
    agent_class=PlannerAgent 
) 
 
 
# ============================================================ 
# RESEARCH AGENT 
# ============================================================ 
 
research = ResearchAgent() 
 
registry.register( 
    name=research.name, 
    description=research.description, 
    agent_class=ResearchAgent 
) 
 
 
# ============================================================ 
# TRANSPORTATION AGENT 
# ============================================================ 
 
transportation = TransportationAgent() 
 
registry.register( 
    name=transportation.name, 
    description=transportation.description, 
    agent_class=TransportationAgent 
) 
 
 
# ============================================================ 
# ACCOMMODATION AGENT 
# ============================================================ 
 
accommodation = AccommodationAgent() 
 
registry.register( 
    name=accommodation.name, 
    description=accommodation.description, 
    agent_class=AccommodationAgent 
) 
 
 
# ============================================================ 
# BUDGET AGENT 
# ============================================================ 
 
budget = BudgetAgent() 
 
registry.register( 
    name=budget.name, 
    description=budget.description, 
    agent_class=BudgetAgent 
) 
 
 
# ============================================================ 
# ITINERARY AGENT 
# ============================================================ 
 
itinerary = ItineraryAgent() 
 
registry.register( 
    name=itinerary.name, 
    description=itinerary.description, 
    agent_class=ItineraryAgent 
) 
 
 
# ============================================================ 
# REVIEW AGENT 
# ============================================================ 
 
review = ReviewAgent() 
 
registry.register( 
    name=review.name, 
    description=review.description, 
    agent_class=ReviewAgent 
) 
 
 
# ============================================================ 
# RESPONSE AGENT 
# ============================================================ 
 
response_agent = ResponseAgent() 
 
registry.register( 
    name=response_agent.name, 
    description=response_agent.description, 
    agent_class=ResponseAgent 
) 
 
 
# ============================================================ 
# SHARED MEMORY 
# ============================================================ 
 
memory = SharedMemory() 
 
 
# ============================================================ 
# ORCHESTRATOR 
# ============================================================ 
 
orchestrator = Orchestrator( 
    registry=registry, 
    memory=memory 
) 
 
 
# ============================================================ 
# ROOT ENDPOINT 
# ============================================================ 
 
@app.get("/") 
def root(): 
 
    return { 
        "message": "AI Multi-Agent Travel Planner is running", 
        "status": "online", 
        "version": "1.0.0" 
    } 
 
 
# ============================================================ 
# HEALTH CHECK 
# ============================================================ 
 
@app.get("/health") 
def health_check(): 
 
    return { 
        "status": "healthy", 
        "service": "AI Multi-Agent Travel Planner" 
    } 
 
 
# ============================================================ 
# LIST REGISTERED AGENTS 
# ============================================================ 
 
@app.get("/agents") 
def list_agents(): 
 
    return { 
        "count": registry.count(), 
        "agents": registry.list_agents() 
    } 
 
 
# ============================================================ 
# PLAN TRIP 
# ============================================================ 
 
@app.post("/plan-trip") 
def plan_trip(request: Dict[str, Any]): 
 
    # -------------------------------------------------------- 
    # Get user request 
    # -------------------------------------------------------- 
 
    user_request = request.get("request") 
 
    # -------------------------------------------------------- 
    # Validate request 
    # -------------------------------------------------------- 
 
    if not user_request: 
 
        return { 
            "success": False, 
            "error": "Request field is required." 
        } 
 
    # -------------------------------------------------------- 
    # Make sure request is a string 
    # -------------------------------------------------------- 
 
    if not isinstance(user_request, str): 
 
        return { 
            "success": False, 
            "error": "Request must be a string." 
        } 
 
    # -------------------------------------------------------- 
    # Remove unnecessary spaces 
    # -------------------------------------------------------- 
 
    user_request = user_request.strip() 
 
    if not user_request: 
 
        return { 
            "success": False, 
            "error": "Request cannot be empty." 
        } 
 
    # -------------------------------------------------------- 
    # Run multi-agent orchestration 
    # -------------------------------------------------------- 
 
    try: 
 
        result = orchestrator.run( 
            user_request 
        ) 
 
        return result 
 
    except Exception as e: 
 
        # ---------------------------------------------------- 
        # Handle unexpected backend errors 
        # ---------------------------------------------------- 
 
        return { 
            "success": False, 
            "error": "Failed to generate travel plan.", 
            "details": str(e) 
        }  