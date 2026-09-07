/* =====================================================
   API CONFIGURATION
===================================================== */

const API_URL = "http://127.0.0.1:8000";


/* =====================================================
   DOM ELEMENTS
===================================================== */

const startLocation =
    document.getElementById("startLocation");

const tripRequest =
    document.getElementById("tripRequest");

const planButton =
    document.getElementById("planButton");

const buttonText =
    document.getElementById("buttonText");

const buttonIcon =
    document.getElementById("buttonIcon");

const charCount =
    document.getElementById("charCount");

const loadingSection =
    document.getElementById("loadingSection");

const errorSection =
    document.getElementById("errorSection");

const errorMessage =
    document.getElementById("errorMessage");

const resultSection =
    document.getElementById("resultSection");


/* =====================================================
   CHARACTER COUNTER
===================================================== */

tripRequest.addEventListener("input", function () {

    const length = tripRequest.value.length;

    charCount.textContent =
        `${length} / 2000`;

});


/* =====================================================
   PLAN BUTTON
===================================================== */

planButton.addEventListener("click", planTrip);


/* =====================================================
   ENTER KEY
===================================================== */

tripRequest.addEventListener("keydown", function (event) {

    if (
        event.key === "Enter" &&
        event.ctrlKey
    ) {

        planTrip();

    }

});


/* =====================================================
   MAIN PLAN FUNCTION
===================================================== */

async function planTrip() {

    const location =
        startLocation.value.trim();

    const request =
        tripRequest.value.trim();


    /* -----------------------------------------------
       VALIDATION
    ------------------------------------------------ */

    if (!location) {

        showError(
            "Please enter your starting location."
        );

        startLocation.focus();

        return;
    }


    if (!request) {

        showError(
            "Please describe the trip you want to plan."
        );

        tripRequest.focus();

        return;
    }


    /* -----------------------------------------------
       CLEAR OLD UI
    ------------------------------------------------ */

    hideError();

    resultSection.classList.add("hidden");

    loadingSection.classList.remove("hidden");

    planButton.disabled = true;

    buttonIcon.textContent = "⏳";

    buttonText.textContent = "Planning your trip...";


    /* -----------------------------------------------
       START PROGRESS ANIMATION
    ------------------------------------------------ */

    startProgressAnimation();


    /* -----------------------------------------------
       COMBINE LOCATION + REQUEST
    ------------------------------------------------ */

    const completeRequest =
        `Starting location: ${location}\n\n${request}`;


    /* -----------------------------------------------
       API REQUEST
    ------------------------------------------------ */

    try {

        console.log(
            "Sending request to:",
            `${API_URL}/plan-trip`
        );

        console.log(
            "Request:",
            completeRequest
        );


        const response = await fetch(
            `${API_URL}/plan-trip`,
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    request: completeRequest
                })

            }
        );


        console.log(
            "API status:",
            response.status
        );


        /* -------------------------------------------
           CHECK HTTP RESPONSE
        -------------------------------------------- */

        if (!response.ok) {

            let errorText =
                `Server returned status ${response.status}.`;

            try {

                const errorData =
                    await response.json();

                if (errorData.detail) {

                    errorText =
                        errorData.detail;

                }

            } catch (e) {

                console.log(
                    "Could not read error JSON."
                );

            }

            throw new Error(errorText);
        }


        /* -------------------------------------------
           READ JSON
        -------------------------------------------- */

        const data =
            await response.json();


        console.log(
            "Travel plan received:",
            data
        );


        /* -------------------------------------------
           VALIDATE RESULT
        -------------------------------------------- */

        if (!data) {

            throw new Error(
                "The server returned an empty response."
            );

        }


        /* -------------------------------------------
           COMPLETE PROGRESS
        -------------------------------------------- */

        completeProgress();


        /* -------------------------------------------
           SHOW RESULT
        -------------------------------------------- */

        setTimeout(() => {

            loadingSection.classList.add("hidden");

            displayTravelPlan(data);

            resetButton();

        }, 700);


    } catch (error) {

        console.error(
            "Travel planning error:",
            error
        );


        loadingSection.classList.add("hidden");

        resetButton();


        showError(
            getFriendlyErrorMessage(error)
        );

    }

}


/* =====================================================
   PROGRESS ANIMATION
===================================================== */

function startProgressAnimation() {

    const steps = [

        "progressPlanner",

        "progressResearch",

        "progressTransport",

        "progressStay",

        "progressItinerary",

        "progressBudget"

    ];


    steps.forEach((id) => {

        const element =
            document.getElementById(id);

        element.classList.remove(
            "active",
            "completed"
        );

        const check =
            element.querySelector(
                ".progress-check"
            );

        if (check) {

            check.textContent = "";

        }

    });


    let currentStep = 0;


    function activateNextStep() {

        if (currentStep >= steps.length) {

            return;

        }


        const element =
            document.getElementById(
                steps[currentStep]
            );


        element.classList.add("active");


        currentStep++;


        setTimeout(() => {

            element.classList.remove("active");

            element.classList.add("completed");


            const check =
                element.querySelector(
                    ".progress-check"
                );


            if (check) {

                check.textContent = "✓";

            }


            activateNextStep();

        }, 900);

    }


    activateNextStep();

}


/* =====================================================
   COMPLETE PROGRESS
===================================================== */

function completeProgress() {

    const steps = [

        "progressPlanner",

        "progressResearch",

        "progressTransport",

        "progressStay",

        "progressItinerary",

        "progressBudget"

    ];


    steps.forEach((id) => {

        const element =
            document.getElementById(id);

        element.classList.remove("active");

        element.classList.add("completed");


        const check =
            element.querySelector(
                ".progress-check"
            );


        if (check) {

            check.textContent = "✓";

        }

    });

}


/* =====================================================
   DISPLAY TRAVEL PLAN
===================================================== */

function displayTravelPlan(data) {

    const result = data || {};


    const title =
        result.title ||
        "Your Travel Plan";


    const introduction =
        result.introduction ||
        "Here is your personalized travel plan.";


    const summary =
        result.trip_summary || {};


    const transportation =
        result.transportation || {};


    const accommodation =
        result.accommodation || {};


    const itinerary =
        result.itinerary || [];


    const reviewStatus =
        result.review_status ||
        "unknown";


    /* -----------------------------------------------
       RESULT HTML
    ------------------------------------------------ */

    let html = `

        <div class="result-header">

            <div class="success-badge">
                ✓ Your trip is ready
            </div>

            <h2>
                ${escapeHtml(title)}
            </h2>

            <p>
                ${escapeHtml(introduction)}
            </p>

        </div>


        <!-- SUMMARY -->

        <div class="summary-grid">

            <div class="summary-card">

                <span>📍 Destination</span>

                <strong>
                    ${escapeHtml(
                        summary.destination || "-"
                    )}
                </strong>

            </div>


            <div class="summary-card">

                <span>📅 Duration</span>

                <strong>
                    ${escapeHtml(
                        summary.duration || "-"
                    )}
                </strong>

            </div>


            <div class="summary-card">

                <span>💰 Budget</span>

                <strong>
                    ₹${formatNumber(
                        summary.budget
                    )}
                </strong>

            </div>


            <div class="summary-card">

                <span>💵 Estimated Cost</span>

                <strong>
                    ₹${formatNumber(
                        summary.estimated_total_cost
                    )}
                </strong>

            </div>


            <div class="summary-card">

                <span>💸 Remaining</span>

                <strong>
                    ₹${formatNumber(
                        summary.remaining_budget
                    )}
                </strong>

            </div>


            <div class="summary-card">

                <span>✅ Budget Status</span>

                <strong>
                    ${escapeHtml(
                        formatStatus(
                            summary.budget_status
                        )
                    )}
                </strong>

            </div>

        </div>


        <!-- TRANSPORTATION -->

        <div class="result-card">

            <h3>
                🚍 Transportation
            </h3>

            <p>
                ${escapeHtml(
                    transportation.summary ||
                    "No transportation information available."
                )}
            </p>

            <div class="highlight">

                <strong>
                    Recommended:
                </strong>

                ${escapeHtml(
                    getRecommendedOption(
                        transportation.recommended_option
                    )
                )}

            </div>

        </div>


        <!-- ACCOMMODATION -->

        <div class="result-card">

            <h3>
                🏨 Accommodation
            </h3>

            <p>
                ${escapeHtml(
                    accommodation.summary ||
                    "No accommodation information available."
                )}
            </p>

            <div class="highlight">

                <strong>
                    Recommended:
                </strong>

                ${escapeHtml(
                    getRecommendedOption(
                        accommodation.recommended_option
                    )
                )}

            </div>

        </div>


        <!-- ITINERARY -->

        <div class="result-card">

            <h3>
                🗓️ Day-wise Itinerary
            </h3>

            <div class="itinerary-container">

                ${generateItinerary(itinerary)}

            </div>

        </div>


        <!-- REVIEW -->

        <div class="result-card">

            <h3>
                🔍 Plan Review
            </h3>

            <p>

                Status:

                <strong>
                    ${escapeHtml(
                        formatStatus(reviewStatus)
                    )}
                </strong>

            </p>

        </div>


        <!-- FINAL MESSAGE -->

        <div class="final-message">

            ${escapeHtml(
                result.final_message ||
                "Your travel plan is ready!"
            )}

        </div>

    `;


    resultSection.innerHTML = html;


    resultSection.classList.remove(
        "hidden"
    );


    setTimeout(() => {

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 100);

}


/* =====================================================
   ITINERARY
===================================================== */

function generateItinerary(itinerary) {

    if (
        !itinerary ||
        itinerary.length === 0
    ) {

        return `
            <p>
                No itinerary available.
            </p>
        `;

    }


    return itinerary.map(day => {

        const activities =
            day.activities || [];


        return `

            <div class="day-card">

                <div class="day-header">

                    <h4>
                        ${escapeHtml(
                            day.title ||
                            `Day ${day.day || ""}`
                        )}
                    </h4>

                </div>


                <div class="activities">

                    ${
                        activities.length
                        ?
                        activities.map(
                            activity => `

                                <div class="activity">

                                    <div class="activity-time">

                                        ${escapeHtml(
                                            activity.time || ""
                                        )}

                                    </div>


                                    <div class="activity-details">

                                        <strong>

                                            ${escapeHtml(
                                                activity.place ||
                                                "Activity"
                                            )}

                                        </strong>


                                        <p>

                                            ${escapeHtml(
                                                activity.activity ||
                                                ""
                                            )}

                                        </p>

                                    </div>

                                </div>

                            `
                        ).join("")
                        :
                        `
                            <p>
                                No activities available.
                            </p>
                        `
                    }

                </div>

            </div>

        `;

    }).join("");

}


/* =====================================================
   RECOMMENDED OPTION
===================================================== */

function getRecommendedOption(option) {

    if (!option) {

        return "-";

    }


    /*
       Sometimes backend returns a string:

       "Bus"

       Sometimes it may return an object:

       {
           mode: "Bus",
           reason: "..."
       }
    */

    if (typeof option === "string") {

        return option;

    }


    if (typeof option === "object") {

        return (
            option.name ||
            option.mode ||
            "-"
        );

    }


    return String(option);

}


/* =====================================================
   NUMBER FORMAT
===================================================== */

function formatNumber(value) {

    const number =
        Number(value || 0);


    return number.toLocaleString(
        "en-IN"
    );

}


/* =====================================================
   STATUS FORMAT
===================================================== */

function formatStatus(status) {

    if (!status) {

        return "-";

    }


    return String(status)
        .replaceAll("_", " ")
        .replace(/\b\w/g, letter =>
            letter.toUpperCase()
        );

}


/* =====================================================
   ERROR HANDLING
===================================================== */

function showError(message) {

    errorMessage.textContent =
        message;

    errorSection.classList.remove(
        "hidden"
    );

}


function hideError() {

    errorSection.classList.add(
        "hidden"
    );

}


/* =====================================================
   FRIENDLY ERROR
===================================================== */

function getFriendlyErrorMessage(error) {

    if (!error) {

        return "Something went wrong. Please try again.";

    }


    if (
        error instanceof TypeError &&
        error.message.includes("fetch")
    ) {

        return `
            Cannot connect to the TravelAI server.
            Please make sure your FastAPI server is running
            on http://127.0.0.1:8000.
        `;

    }


    return error.message ||
        "Something went wrong. Please try again.";

}


/* =====================================================
   RESET BUTTON
===================================================== */

function resetButton() {

    planButton.disabled = false;

    buttonIcon.textContent = "✈";

    buttonText.textContent =
        "Plan My Trip";

}


/* =====================================================
   HTML ESCAPE
===================================================== */

function escapeHtml(value) {

    if (value === null || value === undefined) {

        return "";

    }


    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}