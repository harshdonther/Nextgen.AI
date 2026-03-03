from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from pathlib import Path
from functools import wraps
import os
import importlib
import json
import secrets
from urllib.parse import urlencode
from urllib.request import Request, urlopen

app = Flask(__name__)
app.secret_key = "dev-secret-key"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
DB_PATH = Path(__file__).resolve().parent / "database.db"


@app.context_processor
def inject_asset_versions():
    static_dir = Path(app.static_folder or (Path(__file__).resolve().parent / "static"))
    css_file = static_dir / "style.css"
    try:
        css_version = int(css_file.stat().st_mtime)
    except OSError:
        css_version = 1
    return {"css_version": css_version}


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def get_google_oauth_config():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip() or session.get("google_client_id", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip() or session.get("google_client_secret", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def is_google_oauth_configured():
    cfg = get_google_oauth_config()
    return bool(cfg["client_id"] and cfg["client_secret"])


def google_redirect_uri():
    cfg = get_google_oauth_config()
    return cfg["redirect_uri"] or url_for("google_callback", _external=True)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", error="Please login first."))
        return view_func(*args, **kwargs)

    return wrapped_view


def call_llm(system_prompt, user_prompt):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI")
        client = OpenAI(api_key=api_key)
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = (getattr(response, "output_text", "") or "").strip()
            return text or None
        except Exception:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return completion.choices[0].message.content.strip()
    except Exception:
        return None


def call_llm_chat(messages):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI")
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return None


def llm_to_list(text):
    cleaned = []
    for line in text.splitlines():
        item = line.strip().lstrip("-").strip()
        if item:
            cleaned.append(item)
    return cleaned[:12]


def tool_prompt_from_form(config, form_data):
    lines = [f"Tool: {config['title']}"]
    for field in config["fields"]:
        value = form_data.get(field["name"], "").strip()
        if value:
            lines.append(f"{field['label']}: {value}")
    return "\n".join(lines)


def fallback_chat_reply(message):
    text = message.lower().strip()
    if "exam" in text or "syllabus" in text:
        return (
            "Share your subject, exam date, and syllabus topics. "
            "I will return priority units, likely question patterns, and a 7-day revision plan."
        )
    if "resume" in text or "job" in text:
        return (
            "Send your role, key tasks, and measurable impact. "
            "I will rewrite them into ATS-friendly bullets with action verbs and metrics."
        )
    if "budget" in text or "money" in text:
        return (
            "Give me monthly income, fixed costs, and savings target. "
            "I will generate a realistic split and cut-back recommendations."
        )
    return (
        "I can help with study plans, exam prep, resumes, budgets, fitness, captions, and travel planning. "
        "Tell me your exact goal and constraints, and I will give a step-by-step plan. "
        "For stronger logic answers, set OPENAI_API_KEY so live model responses are enabled."
    )


AI_TOOL_CONFIG = {
    "resume-bullets": {
        "title": "Resume Bullet Generator",
        "description": "Turn your role details into strong resume bullet points.",
        "button_text": "Generate Bullets",
        "fields": [
            {"name": "role", "label": "Role", "type": "text", "placeholder": "e.g., Sales Intern"},
            {"name": "task", "label": "Main Task", "type": "text", "placeholder": "e.g., Lead generation"},
            {"name": "impact", "label": "Impact", "type": "text", "placeholder": "e.g., Increased qualified leads by 20%"},
        ],
    },
    "study-planner": {
        "title": "Study Planner",
        "description": "Create a focused weekly plan from subjects and available hours.",
        "button_text": "Generate Plan",
        "fields": [
            {"name": "subjects", "label": "Subjects", "type": "text", "placeholder": "e.g., Math, Physics, Chemistry"},
            {"name": "hours", "label": "Hours per Day", "type": "text", "placeholder": "e.g., 3"},
            {"name": "exam_date", "label": "Exam Date", "type": "text", "placeholder": "e.g., 2026-06-10"},
        ],
    },
    "budget-planner": {
        "title": "Budget Planner",
        "description": "Get a simple monthly budget allocation plan.",
        "button_text": "Build Budget",
        "fields": [
            {"name": "income", "label": "Monthly Income", "type": "text", "placeholder": "e.g., 50000"},
            {"name": "rent", "label": "Rent/Fixed Cost", "type": "text", "placeholder": "e.g., 15000"},
            {"name": "goal", "label": "Savings Goal", "type": "text", "placeholder": "e.g., 10000"},
        ],
    },
    "meal-planner": {
        "title": "Meal Planner",
        "description": "Generate a simple daily meal plan for your goal.",
        "button_text": "Generate Meals",
        "fields": [
            {"name": "goal", "label": "Goal", "type": "text", "placeholder": "e.g., Weight loss"},
            {"name": "diet", "label": "Diet Preference", "type": "text", "placeholder": "e.g., Vegetarian"},
            {"name": "restrictions", "label": "Restrictions", "type": "text", "placeholder": "e.g., No dairy"},
        ],
    },
    "workout-builder": {
        "title": "Workout Builder",
        "description": "Create a weekly workout split from your fitness target.",
        "button_text": "Build Workout",
        "fields": [
            {"name": "goal", "label": "Fitness Goal", "type": "text", "placeholder": "e.g., Gain muscle"},
            {"name": "days", "label": "Days per Week", "type": "text", "placeholder": "e.g., 4"},
            {"name": "level", "label": "Experience Level", "type": "text", "placeholder": "e.g., Beginner"},
        ],
    },
    "trip-planner": {
        "title": "Trip Itinerary Planner",
        "description": "Build a day-wise travel itinerary quickly.",
        "button_text": "Generate Itinerary",
        "fields": [
            {"name": "destination", "label": "Destination", "type": "text", "placeholder": "e.g., Jaipur"},
            {"name": "days", "label": "Number of Days", "type": "text", "placeholder": "e.g., 3"},
            {"name": "budget", "label": "Budget Type", "type": "text", "placeholder": "e.g., Medium"},
        ],
    },
    "meeting-notes": {
        "title": "Meeting Notes Organizer",
        "description": "Convert rough notes into clear summary and action items.",
        "button_text": "Organize Notes",
        "fields": [
            {"name": "notes", "label": "Raw Meeting Notes", "type": "textarea", "placeholder": "Paste notes here..."},
        ],
    },
    "code-explainer": {
        "title": "Code Explainer",
        "description": "Get a plain-English explanation for code snippets.",
        "button_text": "Explain Code",
        "fields": [
            {"name": "language", "label": "Language", "type": "text", "placeholder": "e.g., Python"},
            {"name": "code", "label": "Code Snippet", "type": "textarea", "placeholder": "Paste code here..."},
        ],
    },
    "caption-generator": {
        "title": "Social Caption Generator",
        "description": "Create social media captions with hashtags.",
        "button_text": "Generate Captions",
        "fields": [
            {"name": "topic", "label": "Topic", "type": "text", "placeholder": "e.g., New product launch"},
            {"name": "platform", "label": "Platform", "type": "text", "placeholder": "e.g., Instagram"},
            {"name": "tone", "label": "Tone", "type": "text", "placeholder": "e.g., Energetic"},
        ],
    },
    "habit-coach": {
        "title": "Habit Coach",
        "description": "Build a practical 21-day habit plan.",
        "button_text": "Create Habit Plan",
        "fields": [
            {"name": "habit", "label": "Habit", "type": "text", "placeholder": "e.g., Morning reading"},
            {"name": "time_slot", "label": "Preferred Time", "type": "text", "placeholder": "e.g., 7:00 AM"},
            {"name": "obstacle", "label": "Main Obstacle", "type": "text", "placeholder": "e.g., Phone distractions"},
        ],
    },
    "swot-analyzer": {
        "title": "SWOT Analyzer",
        "description": "Generate strengths, weaknesses, opportunities, and threats for your idea.",
        "button_text": "Analyze SWOT",
        "fields": [
            {"name": "business", "label": "Business/Idea", "type": "text", "placeholder": "e.g., Online bakery"},
            {"name": "market", "label": "Target Market", "type": "text", "placeholder": "e.g., College students in Pune"},
            {"name": "goal", "label": "Main Goal", "type": "text", "placeholder": "e.g., Reach 500 monthly orders"},
        ],
    },
    "proposal-writer": {
        "title": "Client Proposal Writer",
        "description": "Create a structured proposal draft with scope, timeline, and pricing.",
        "button_text": "Generate Proposal",
        "fields": [
            {"name": "client", "label": "Client Name", "type": "text", "placeholder": "e.g., Acme Pvt Ltd"},
            {"name": "service", "label": "Service Offered", "type": "text", "placeholder": "e.g., SEO and content strategy"},
            {"name": "budget", "label": "Budget Range", "type": "text", "placeholder": "e.g., 60,000-80,000 INR"},
        ],
    },
    "interview-coach": {
        "title": "Interview Coach",
        "description": "Get role-specific interview questions and strong answer frameworks.",
        "button_text": "Build Interview Prep",
        "fields": [
            {"name": "role", "label": "Role", "type": "text", "placeholder": "e.g., Python Developer"},
            {"name": "experience", "label": "Experience", "type": "text", "placeholder": "e.g., 2 years"},
            {"name": "company_type", "label": "Company Type", "type": "text", "placeholder": "e.g., Product startup"},
        ],
    },
    "weekly-content-plan": {
        "title": "Weekly Content Planner",
        "description": "Generate a 7-day content calendar with hooks and post ideas.",
        "button_text": "Create Content Plan",
        "fields": [
            {"name": "niche", "label": "Niche", "type": "text", "placeholder": "e.g., Fitness coaching"},
            {"name": "platform", "label": "Platform", "type": "text", "placeholder": "e.g., Instagram"},
            {"name": "goal", "label": "Goal", "type": "text", "placeholder": "e.g., Lead generation"},
        ],
    },
}


def generate_generic_tool_result(tool_key, form_data, mode="advanced"):
    config = AI_TOOL_CONFIG.get(tool_key)
    if config:
        llm_system = (
            "You are a practical assistant. Return concise, high-value output as short bullet points. "
            "Avoid hype, do not promise guaranteed outcomes, and include actionable steps."
        )
        llm_user = (
            f"Create a {mode} quality response for this tool request.\n"
            f"{tool_prompt_from_form(config, form_data)}\n"
            "Return 8-12 bullet points."
        )
        llm_text = call_llm(llm_system, llm_user)
        if llm_text:
            parsed = llm_to_list(llm_text)
            if parsed:
                return parsed

    get = lambda key: form_data.get(key, "").strip()
    if tool_key == "resume-bullets":
        role = get("role")
        task = get("task")
        impact = get("impact")
        return [
            f"Developed and executed {task.lower()} strategies in role as {role}.",
            f"Collaborated cross-functionally to streamline processes related to {task.lower()}.",
            f"Drove measurable business value: {impact}.",
        ]
    if tool_key == "study-planner":
        subjects = [s.strip() for s in get("subjects").split(",") if s.strip()]
        hours = get("hours") or "2"
        exam_date = get("exam_date") or "Not provided"
        base = [f"Exam Date: {exam_date}", f"Daily Study Hours: {hours}"]
        for idx, sub in enumerate(subjects[:5], start=1):
            base.append(f"Day {idx}: {sub} - concept revision + 20 practice questions")
        return base
    if tool_key == "budget-planner":
        income = get("income")
        rent = get("rent")
        goal = get("goal")
        return [
            f"Income (monthly): {income}",
            f"Fixed costs: {rent}",
            f"Savings target: {goal}",
            "Suggested split: Needs 50%, Wants 30%, Savings/Investments 20%.",
            "Track expenses weekly and reduce non-essential costs by 10%.",
        ]
    if tool_key == "meal-planner":
        return [
            f"Goal: {get('goal')}",
            f"Diet: {get('diet')}",
            f"Restrictions: {get('restrictions') or 'None'}",
            "Breakfast: Oats + fruits + protein source",
            "Lunch: Balanced plate (protein, whole grains, vegetables)",
            "Dinner: Light meal with lean protein and fiber",
        ]
    if tool_key == "workout-builder":
        days = get("days") or "4"
        return [
            f"Goal: {get('goal')}",
            f"Level: {get('level')}",
            f"Days/Week: {days}",
            "Plan: Push, Pull, Legs, Core + Cardio",
            "Progression: Increase load or reps every week.",
        ]
    if tool_key == "trip-planner":
        destination = get("destination")
        days = get("days") or "3"
        budget = get("budget")
        return [
            f"Destination: {destination}",
            f"Trip length: {days} days",
            f"Budget style: {budget}",
            "Day 1: Local city tour + food market",
            "Day 2: Landmark visits + cultural activity",
            "Day 3: Shopping + relaxed departure plan",
        ]
    if tool_key == "meeting-notes":
        notes = get("notes")
        short = notes[:220]
        return [
            "Summary: Team discussed priorities, blockers, and upcoming deadlines.",
            f"Key context captured: {short}",
            "Action Items: Assign owners, define due dates, and share status update in next sync.",
        ]
    if tool_key == "code-explainer":
        return [
            f"Language: {get('language')}",
            "High-level: The code takes input, processes it step-by-step, and returns output.",
            "Key logic: Conditions/loops/functions coordinate to solve the target problem.",
            "Next step: Add comments and unit tests for maintainability.",
        ]
    if tool_key == "caption-generator":
        topic = get("topic")
        platform = get("platform")
        tone = get("tone")
        return [
            f"{topic} is here. Big results start today. #{platform.replace(' ', '')} #Growth",
            f"Built with care and launched with {tone.lower()} energy. Ready to try it? #NewLaunch",
            f"Small changes, massive outcomes. {topic} for people who want progress. #LevelUp",
        ]
    if tool_key == "habit-coach":
        habit = get("habit")
        time_slot = get("time_slot")
        obstacle = get("obstacle")
        return [
            f"Habit: {habit}",
            f"Daily slot: {time_slot}",
            f"Obstacle plan: If {obstacle.lower()}, then do a 5-minute minimum version.",
            "Week 1: Build consistency, Week 2: Increase duration, Week 3: Track streak and reward progress.",
        ]
    if tool_key == "swot-analyzer":
        business = get("business")
        market = get("market")
        goal = get("goal")
        return [
            f"Business/Idea: {business}",
            f"Target market: {market}",
            f"Goal: {goal}",
            f"Strength: {business} can differentiate with faster delivery and personalized experience.",
            "Weakness: Limited initial trust and lower brand recall vs established players.",
            f"Opportunity: Rising demand in {market} and underserved micro-segments.",
            "Threat: Price competition and copycat offerings from larger incumbents.",
            "Action: Build one clear positioning message and test 3 acquisition channels for 2 weeks.",
        ]
    if tool_key == "proposal-writer":
        client = get("client")
        service = get("service")
        budget = get("budget")
        return [
            f"Client: {client}",
            f"Service scope: {service}",
            f"Estimated budget: {budget}",
            "Objective: Improve measurable outcomes with a phased execution plan.",
            "Phase 1 (Week 1-2): Audit current setup, goals, and baseline metrics.",
            "Phase 2 (Week 3-6): Implement high-impact improvements and quick wins.",
            "Phase 3 (Week 7-8): Optimize based on performance data and handoff playbooks.",
            "Deliverables: Weekly report, KPI dashboard, and action backlog with priorities.",
        ]
    if tool_key == "interview-coach":
        role = get("role")
        experience = get("experience")
        company_type = get("company_type")
        return [
            f"Role target: {role}",
            f"Experience level: {experience}",
            f"Company type: {company_type}",
            "Question 1: Tell me about a project where you solved a difficult problem.",
            "Answer frame: Situation -> Task -> Action -> Result with one metric.",
            "Question 2: How do you prioritize when deadlines conflict?",
            "Answer frame: Clarify impact, estimate effort, align stakeholders, then execute.",
            "Mock practice: Run 20-minute timed rounds and refine weak answers.",
        ]
    if tool_key == "weekly-content-plan":
        niche = get("niche")
        platform = get("platform")
        goal = get("goal")
        return [
            f"Niche: {niche}",
            f"Platform: {platform}",
            f"Goal: {goal}",
            "Monday: Problem post - one painful mistake your audience makes.",
            "Tuesday: Tutorial carousel - 5-step actionable framework.",
            "Wednesday: Case study - before/after with result metric.",
            "Thursday: Myth-buster - challenge one common belief.",
            "Friday: Offer post - clear CTA and deadline-based hook.",
            "Weekend: Community Q&A and repurpose best-performing post.",
        ]
    return []

# Create database table
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                password TEXT,
                google_id TEXT
            )
        """)
        cursor.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cursor.fetchall()]
        if "google_id" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
        conn.commit()

init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/live")
def live_status():
    return "Website Live 🚀"

@app.route("/get-started")
def get_started():
    return render_template("get_started.html", logged_in=("user_id" in session))

@app.route("/index.html")
def home_alias():
    return redirect(url_for("home"))

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/features.html")
def features_alias():
    return redirect(url_for("features"))

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/pricing.html")
def pricing_alias():
    return redirect(url_for("pricing"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/about.html")
def about_alias():
    return redirect(url_for("about"))

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/contact.html")
def contact_alias():
    return redirect(url_for("contact"))

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/signup.html")
def signup_alias():
    return redirect(url_for("signup"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template(
            "login.html",
            error=request.args.get("error", ""),
            success=request.args.get("success", ""),
        )

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return redirect(url_for("login", error="Email and password are required."))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email FROM users WHERE email = ? AND password = ?",
            (email, password),
        )
        user = cursor.fetchone()

    if not user:
        return redirect(url_for("login", error="Invalid email or password."))

    session["user_id"] = user[0]
    session["user_name"] = user[1]
    session["user_email"] = user[2]
    return redirect(url_for("dashboard"))

@app.route("/login.html")
def login_alias():
    return redirect(url_for("login"))


@app.route("/auth/google/start")
def google_start():
    cfg = get_google_oauth_config()
    if not is_google_oauth_configured():
        return redirect(url_for("google_setup", error="Please add Google OAuth Client ID and Secret first."))

    state = secrets.token_urlsafe(24)
    session["google_oauth_state"] = state
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@app.route("/auth/google/callback")
def google_callback():
    if request.args.get("error"):
        return redirect(url_for("login", error="Google login was canceled or failed."))

    expected_state = session.pop("google_oauth_state", "")
    received_state = request.args.get("state", "")
    if not expected_state or expected_state != received_state:
        return redirect(url_for("login", error="Invalid Google login state. Please try again."))

    code = request.args.get("code", "").strip()
    if not code:
        return redirect(url_for("login", error="Missing Google authorization code."))

    token_data = urlencode(
        {
            "code": code,
            "client_id": get_google_oauth_config()["client_id"],
            "client_secret": get_google_oauth_config()["client_secret"],
            "redirect_uri": google_redirect_uri(),
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    try:
        token_req = Request(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(token_req, timeout=15) as resp:
            token_json = json.loads(resp.read().decode("utf-8"))
        access_token = token_json.get("access_token", "")
        if not access_token:
            return redirect(url_for("login", error="Google token exchange failed."))

        profile_req = Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        with urlopen(profile_req, timeout=15) as resp:
            profile = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return redirect(url_for("login", error="Could not complete Google login."))

    google_id = (profile.get("sub") or "").strip()
    email = (profile.get("email") or "").strip()
    name = (profile.get("name") or "Google User").strip()
    if not email:
        return redirect(url_for("login", error="Google account email was not provided."))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email FROM users WHERE google_id = ? OR email = ? LIMIT 1",
            (google_id, email),
        )
        user = cursor.fetchone()

        if user:
            user_id = user[0]
            cursor.execute(
                "UPDATE users SET name = ?, email = ?, google_id = ? WHERE id = ?",
                (name, email, google_id, user_id),
            )
            conn.commit()
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password, google_id) VALUES (?, ?, ?, ?)",
                (name, email, "", google_id),
            )
            conn.commit()
            user_id = cursor.lastrowid

    session["user_id"] = user_id
    session["user_name"] = name
    session["user_email"] = email
    return redirect(url_for("dashboard"))


@app.route("/auth/google/setup", methods=["GET", "POST"])
def google_setup():
    if request.method == "POST":
        client_id = request.form.get("client_id", "").strip()
        client_secret = request.form.get("client_secret", "").strip()
        if not client_id or not client_secret:
            return redirect(url_for("google_setup", error="Both fields are required."))
        session["google_client_id"] = client_id
        session["google_client_secret"] = client_secret
        return redirect(url_for("google_start"))

    return render_template(
        "google_setup.html",
        error=request.args.get("error", ""),
        suggested_redirect=google_redirect_uri(),
    )

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        user_name=session.get("user_name", "User"),
        user_email=session.get("user_email", ""),
    )


@app.route("/ai/ad-copy", methods=["GET", "POST"])
@login_required
def ai_ad_copy():
    result = None
    if request.method == "POST":
        product = request.form.get("product", "").strip()
        audience = request.form.get("audience", "").strip()
        tone = request.form.get("tone", "Professional").strip()

        if product and audience:
            result = {
                "headline": f"{tone} Growth for {audience} with {product}",
                "body": (
                    f"Use {product} to remove manual work, improve decisions, and scale faster for {audience}. "
                    f"Built for teams that want clear ROI and consistent performance."
                ),
                "cta": "Book a 15-minute AI strategy demo",
            }

    return render_template("ai_ad_copy.html", result=result)


@app.route("/ai/email-writer", methods=["GET", "POST"])
@login_required
def ai_email_writer():
    result = None
    if request.method == "POST":
        goal = request.form.get("goal", "").strip()
        audience = request.form.get("audience", "").strip()
        offer = request.form.get("offer", "").strip()

        if goal and audience and offer:
            result = {
                "subject": f"{offer} for {audience} - quick win inside",
                "body": (
                    f"Hi {audience},\n\n"
                    f"We created this to help you {goal} without adding more manual steps.\n"
                    f"Offer: {offer}.\n\n"
                    "If you'd like, I can share a short plan tailored to your workflow.\n\n"
                    "Best,\nNextGen AI"
                ),
            }

    return render_template("ai_email_writer.html", result=result)


@app.route("/ai/keyword-ideas", methods=["GET", "POST"])
@login_required
def ai_keyword_ideas():
    result = []
    if request.method == "POST":
        niche = request.form.get("niche", "").strip()
        location = request.form.get("location", "").strip()

        if niche:
            suffix = f" in {location}" if location else ""
            result = [
                f"best {niche} tools{suffix}",
                f"{niche} pricing comparison{suffix}",
                f"affordable {niche} services{suffix}",
                f"{niche} automation for small business{suffix}",
                f"top-rated {niche} platform{suffix}",
                f"how to choose {niche} software{suffix}",
            ]

    return render_template("ai_keyword_ideas.html", result=result)


@app.route("/ai/support-reply", methods=["GET", "POST"])
@login_required
def ai_support_reply():
    result = None
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip() or "there"
        issue = request.form.get("issue", "").strip()

        if issue:
            result = (
                f"Hi {customer_name},\n\n"
                "Thank you for sharing this. I understand how frustrating it can be.\n"
                f"Regarding: \"{issue}\", our team is already checking the root cause.\n"
                "As a next step, please share your order ID or account email so we can fix this quickly.\n\n"
                "We appreciate your patience,\nSupport Team"
            )

    return render_template("ai_support_reply.html", result=result)


@app.route("/ai/exam-prep", methods=["GET", "POST"])
@login_required
def ai_exam_prep():
    result = None
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        exam_date = request.form.get("exam_date", "").strip()
        syllabus = request.form.get("syllabus", "").strip()

        if subject and syllabus:
            raw_topics = [
                item.strip(" -\t")
                for line in syllabus.splitlines()
                for item in line.split(",")
                if item.strip()
            ]
            topics = raw_topics[:12]

            high_priority = topics[:6] if len(topics) >= 6 else topics
            practice_questions = [
                f"Explain the core concept of {topic} with one real-world example."
                for topic in high_priority
            ]
            practice_questions += [
                f"Compare {high_priority[0]} and {high_priority[1]} with key differences."
            ] if len(high_priority) >= 2 else []
            practice_questions += [
                f"Write a short note on {high_priority[-1]} and common exam mistakes."
            ] if high_priority else []

            days_left_note = (
                f"Target exam date: {exam_date}. Prioritize revision and timed practice."
                if exam_date
                else "Add exam date to get a tighter revision timeline."
            )

            result = {
                "subject": subject,
                "days_left_note": days_left_note,
                "important_topics": high_priority,
                "practice_questions": practice_questions[:10],
                "mini_mock": [
                    "Section A: 5 short-answer questions (2 marks each).",
                    "Section B: 3 medium questions (5 marks each).",
                    "Section C: 1 long-answer question (10 marks).",
                ],
                "note": "These are high-probability practice areas based on your syllabus, not guaranteed exam questions.",
            }

    return render_template("ai_exam_prep.html", result=result)


@app.route("/ai/tool/<tool_key>", methods=["GET", "POST"])
@login_required
def ai_generic_tool(tool_key):
    config = AI_TOOL_CONFIG.get(tool_key)
    if not config:
        return redirect(url_for("dashboard"))

    result = None
    mode = "advanced"
    if request.method == "POST":
        mode = request.form.get("mode", "advanced").strip() or "advanced"
        result = generate_generic_tool_result(tool_key, request.form, mode=mode)

    return render_template(
        "ai_generic_tool.html",
        tool_key=tool_key,
        config=config,
        result=result,
        mode=mode,
        llm_enabled=bool(os.getenv("OPENAI_API_KEY", "").strip()),
    )


@app.route("/ai/chat", methods=["GET", "POST"])
@login_required
def ai_chat():
    history = session.get("ai_chat_history", [])
    llm_enabled = bool(os.getenv("OPENAI_API_KEY", "").strip())

    if request.method == "POST":
        if request.form.get("action") == "clear":
            session["ai_chat_history"] = []
            return redirect(url_for("ai_chat"))

        message = request.form.get("message", "").strip()
        if message:
            history.append({"role": "user", "content": message})
            history = history[-16:]

            system_prompt = (
                "You are an advanced AI assistant focused on accurate reasoning and practical execution. "
                "Solve logic questions step-by-step, explain clearly, and verify assumptions. "
                "If information is missing, ask one concise clarifying question. "
                "For coding: provide correct, runnable solutions and briefly explain why they work. "
                "Do not hallucinate facts; when uncertain, clearly say what is unknown."
            )
            messages = [{"role": "system", "content": system_prompt}]
            for item in history[-12:]:
                role = item.get("role", "user")
                if role not in ("user", "assistant"):
                    role = "user"
                messages.append({"role": role, "content": item.get("content", "")})

            llm_reply = call_llm_chat(messages)
            reply = llm_reply or fallback_chat_reply(message)
            history.append({"role": "assistant", "content": reply})
            history = history[-16:]
            session["ai_chat_history"] = history

    return render_template("ai_chat.html", history=history, llm_enabled=llm_enabled)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login", success="You have been logged out."))

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        return "All fields are required.", 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password),
            )
            conn.commit()
    except sqlite3.Error as exc:
        return f"Database error: {exc}", 500

    return redirect(url_for("login", success="Account created. Please login."))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
