from flask import Flask, render_template, request, redirect, session, Response
from db import students, companies_collection, resources_collection, questions_collection, notifications_collection, mcq_collection
import os
import PyPDF2
from werkzeug.utils import secure_filename
from PyPDF2.errors import PdfReadError
from bson import ObjectId
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from flask import send_file




app = Flask(__name__)
app.secret_key = "skillara_secret_key_123"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


def safe_float(value, default=0):
    try:
        return float(value)
    except:
        return default
def calculate_readiness(student):

    aptitude = min(safe_int(student.get("aptitude_score", 0)), 100)
    communication = min(safe_int(student.get("communication_score", 0)), 100)
    cgpa = min(safe_float(student.get("cgpa", 0)), 10)

    skills = student.get("skills", "")
    skill_count = len([s for s in skills.split(",") if s.strip()])
    skill_score = min(skill_count * 20, 100)

    readiness = (
        aptitude * 0.25 +
        communication * 0.20 +
        (cgpa * 10) * 0.30 +
        skill_score * 0.25
    )

    return round(readiness, 2)

def extract_text_from_pdf(file_path):
    text = ""

    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)

            for page in reader.pages:
                text += page.extract_text() or ""

    except PdfReadError:
        return None

    except Exception:
        return None

    return text


def extract_skills(text):
    skill_list = [
        "python", "java", "sql", "html", "css",
        "javascript", "mongodb", "machine learning",
        "excel", "power bi", "dsa", "flask"
    ]

    detected = []

    text = text.lower()

    for skill in skill_list:
        if skill in text:
            detected.append(skill.title())

    return detected

def recommend_career(student):
    target_role = student.get("target_role", "")

    if target_role:
        return target_role

    skills = student.get("skills", "").lower()

    if "python" in skills and "sql" in skills:
        return "Data Analyst"
    elif "python" in skills:
        return "Python Developer"
    elif "java" in skills:
        return "Software Developer"
    elif "html" in skills or "css" in skills or "javascript" in skills:
        return "Web Developer"

    return "General IT Career"


def get_missing_skills(student):
    role = student.get("target_role", "")

    required_skills = {
        "Data Analyst": ["Python", "SQL", "Excel", "Power BI"],
        "Web Developer": ["HTML", "CSS", "JavaScript"],
        "Software Developer": ["Java", "DSA", "SQL"],
        "AI Engineer": ["Python", "Machine Learning", "Deep Learning", "SQL"]
    }

    student_skills = [
        skill.strip().lower()
        for skill in student.get("skills", "").split(",")
    ]

    missing = []

    for skill in required_skills.get(role, []):
        if skill.lower() not in student_skills:
            missing.append(skill)

    return missing


def get_learning_resources(missing_skills):

    default_resources = {
        "Python": "https://www.w3schools.com/python/",
        "SQL": "https://www.w3schools.com/sql/",
        "Machine Learning": "https://www.coursera.org/learn/machine-learning",
        "Deep Learning": "https://www.deeplearning.ai/",
        "Power BI": "https://learn.microsoft.com/en-us/power-bi/",
        "Excel": "https://support.microsoft.com/excel",
        "HTML": "https://www.w3schools.com/html/",
        "CSS": "https://www.w3schools.com/css/",
        "JavaScript": "https://www.w3schools.com/js/",
        "Java": "https://www.w3schools.com/java/",
        "DSA": "https://takeuforward.org/"
    }

    result = {}

    for skill in missing_skills:

        resource = resources_collection.find_one({
            "skill": {
                "$regex": f"^{skill}$",
                "$options": "i"
            }
        })

        if resource:
            result[skill] = resource.get("url")

        elif skill in default_resources:
            result[skill] = default_resources[skill]

    return result

def get_mcq_progress(student):

    completed_days = 0
    day_scores = []

    for day in range(1, 8):
        score = student.get(f"day{day}_score")

        if score is not None:
            completed_days += 1

        day_scores.append({
            "day": day,
            "score": score
        })

    progress = round((completed_days / 7) * 100)

    return progress, day_scores
def generate_suggestions(student):

    suggestions = []
    missing_skills = get_missing_skills(student)

    for skill in missing_skills:
        suggestions.append(f"Learn {skill} to improve placement readiness.")

    if safe_int(student.get("aptitude_score", 0)) < 60:
        suggestions.append("Practice aptitude daily.")

    if safe_int(student.get("communication_score", 0)) < 60:
        suggestions.append("Improve communication skills.")

    if safe_float(student.get("cgpa", 0)) < 7:
        suggestions.append("Improve CGPA for better company eligibility.")

    if not suggestions:
        suggestions.append("Great progress! Continue practicing mock tests and projects.")

    return suggestions

def get_student_rank(student):

    all_students = list(students.find())

    all_students.sort(
        key=lambda x: x.get("mock_score", 0),
        reverse=True
    )

    for index, s in enumerate(all_students, start=1):
        if s.get("email") == student.get("email"):
            return index, len(all_students)

    return 0, len(all_students)


def recommend_companies(student):
    recommended = []

    cgpa = float(student.get("cgpa", 0))
    skills = student.get("skills", "").lower()

    if cgpa >= 6:
        recommended.append("TCS")

    if cgpa >= 6.5:
        recommended.append("Infosys")

    if cgpa >= 7:
        recommended.append("Cognizant")

    if cgpa >= 8 and "python" in skills:
        recommended.append("Accenture")

    if cgpa >= 8 and "java" in skills:
        recommended.append("Wipro")

    return recommended


def generate_study_plan(student):
    role = student.get("target_role", "")
    missing_skills = get_missing_skills(student)

    plan = []

    if missing_skills:
        for skill in missing_skills:
            plan.append(f"Learn basics of {skill}")
            plan.append(f"Practice 5 questions on {skill}")
    else:
        plan.append("Revise your current skills")
        plan.append("Practice mock interview questions")
        plan.append("Improve resume and communication")

    if int(student.get("aptitude_score", 0)) < 60:
        plan.append("Practice aptitude for 30 minutes daily")

    if int(student.get("communication_score", 0)) < 60:
        plan.append("Practice self-introduction and HR questions")

    return plan


def check_job_eligibility(student):

    cgpa = float(student.get("cgpa", 0))
    student_skills = student.get("skills", "").lower()

    eligible = []
    not_eligible = []

    all_companies = list(companies_collection.find())

    for company in all_companies:

        missing = []

        if cgpa < float(company.get("min_cgpa", 0)):
            missing.append(
                f"CGPA should be at least {company.get('min_cgpa')}"
            )

        for skill in company.get("skills", []):

            if skill.lower() not in student_skills:
                missing.append(
                    f"Need {skill.upper()} skill"
                )

        if missing:
            not_eligible.append({
                "name": company.get("name"),
                "reason": missing
            })

        else:
            eligible.append(company.get("name"))

    return eligible, not_eligible
def placement_prediction(student):

    readiness = calculate_readiness(student)
    mock_score = safe_float(student.get("mock_score", 0))
    resume_score = safe_float(student.get("resume_score", 70))

    chance = readiness * 0.5 + mock_score * 0.3 + resume_score * 0.2

    return round(chance, 2)
def profile_completion(student):

    fields = [
        "cgpa",
        "skills",
        "interests",
        "target_role",
        "aptitude_score",
        "communication_score"
    ]

    completed = 0

    for field in fields:

        if student.get(field):
            completed += 1

    return round((completed / len(fields)) * 100)


def generate_notifications(student):

    notifications = []

    if not student.get("resume_uploaded"):
        notifications.append(
            "Upload Resume"
        )

    if student.get("mock_score", 0) < 60:
        notifications.append(
            "Take Mock Test Again"
        )

    if float(student.get("cgpa", 0)) < 7:
        notifications.append(
            "Improve CGPA"
        )

    return notifications


def generate_roadmap(role):
    roadmaps = {
        "Data Analyst": ["Learn Python", "Learn SQL", "Learn Excel", "Learn Power BI", "Build dashboard project"],
        "Web Developer": ["Learn HTML", "Learn CSS", "Learn JavaScript", "Learn Flask", "Build portfolio website"],
        "Software Developer": ["Learn Java", "Practice DSA", "Learn SQL", "Build mini projects"],
        "AI Engineer": ["Learn Python", "Learn ML", "Learn Deep Learning", "Build AI project"]
    }
    return roadmaps.get(role, ["Learn programming basics"])
def calculate_resume_score(text, detected_skills):

    score = 30
    suggestions = []

    text = text.lower()

    if len(detected_skills) >= 3:
        score += 20
    else:
        suggestions.append("Add more technical skills.")

    if "project" in text or "projects" in text:
        score += 20
    else:
        suggestions.append("Add projects section.")

    if "education" in text:
        score += 15
    else:
        suggestions.append("Add education section.")

    if "certification" in text or "certifications" in text:
        score += 10
    else:
        suggestions.append("Add certifications.")

    if "github" in text or "linkedin" in text:
        score += 5
    else:
        suggestions.append("Add GitHub or LinkedIn links.")

    if score > 100:
        score = 100

    return int(score), suggestions

@app.route('/')
def home():
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            return "All fields are required"

        existing_user = students.find_one({"email": email})

        if existing_user:
            return "Email already registered"

        student = {
            "name": name,
            "email": email,
            "password": password
        }

        students.insert_one(student)

        return redirect('/login')

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = students.find_one({
            "email": email,
            "password": password
        })

        if user:
            session["email"] = email

            if user.get("cgpa") and user.get("skills") and user.get("target_role"):
                return redirect('/dashboard')
            else:
                return redirect('/profile')

        return render_template(
            "login.html",
            error="Invalid email or password"
        )

    return render_template("login.html")


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if "email" not in session:
        return redirect('/login')

    if request.method == 'POST':

        students.update_one(
            {"email": session["email"]},
            {"$set": {
                "cgpa": float(request.form['cgpa']),
                "skills": request.form['skills'],
                "interests": request.form['interests'],
                "target_role": request.form['target_role'],
                "aptitude_score": int(request.form['aptitude_score']),
                "communication_score": int(request.form['communication_score'])
            }}
        )

        return redirect('/dashboard')

    return render_template("profile.html")



def get_student_rank(student):

    all_students = list(students.find())

    all_students.sort(
        key=lambda x: float(x.get("mock_score", 0)),
        reverse=True
    )

    for index, s in enumerate(all_students, start=1):

        if s.get("email") == student.get("email"):
            return index, len(all_students)

    return 0, len(all_students)

@app.route('/dashboard')
def dashboard():

    if "email" not in session:
        return redirect('/login')

    student = students.find_one({"email": session["email"]})

    if not student:
        session.clear()
        return redirect('/login')

    if not student.get("skills"):
        return redirect('/profile')
    readiness = calculate_readiness(student)
    career = recommend_career(student)
    missing_skills = get_missing_skills(student)
    resources = get_learning_resources(missing_skills)
    suggestions = generate_suggestions(student)
    recommended_companies = recommend_companies(student)
    study_plan = generate_study_plan(student)
    eligible_companies, not_eligible_companies = check_job_eligibility(student)
    overall_progress = profile_completion(student)
    placement_chance = placement_prediction(student)
    roadmap = generate_roadmap(student.get("target_role", ""))
    notifications = list(
        notifications_collection.find()
        .sort("_id", -1)
        .limit(3)
    )
    mcq_progress, day_scores = get_mcq_progress(student)
    placement_progress, day_status = get_placement_progress(student)
    rank, total_rank_students = get_student_rank(student)
    rank, total_rank_students = get_student_rank(student)

    return render_template(
        "dashboard.html",
        student=student,
        readiness=readiness,
        career=career,
        missing_skills=missing_skills,
        resources=resources,
        suggestions=suggestions,
        recommended_companies=recommended_companies,
        study_plan=study_plan,
        eligible_companies=eligible_companies,
        not_eligible_companies=not_eligible_companies,
        overall_progress=overall_progress,
        placement_chance=placement_chance,
        roadmap=roadmap,
        notifications=notifications,
        mcq_progress=mcq_progress,
        day_scores=day_scores,
        placement_progress=placement_progress,
        day_status=day_status,
        rank=rank,
        total_rank_students=total_rank_students
    )
@app.route('/resume', methods=['GET', 'POST'])
def resume():

    if "email" not in session:
        return redirect('/login')

    if request.method == 'POST':

        file = request.files['resume']

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            text = extract_text_from_pdf(file_path)
            if text is None:
                return "Invalid or corrupted PDF. Please upload a proper resume PDF."
            detected_skills = extract_skills(text)

            resume_score = 40
            resume_suggestions = []

            if len(detected_skills) >= 3:
                resume_score += 20
            else:
                resume_suggestions.append("Add more technical skills.")

            if "project" in text.lower() or "projects" in text.lower():
                resume_score += 20
            else:
                resume_suggestions.append("Add a projects section.")

            if "education" in text.lower():
                resume_score += 20
            else:
                resume_suggestions.append("Add education details.")

            if resume_score > 100:
                resume_score = 100

            students.update_one(
                {"email": session["email"]},
                {"$set": {
                    "resume_skills": detected_skills,
                    "resume_uploaded": True,
                    "resume_score": resume_score,
                    "resume_suggestions": resume_suggestions
                }}
            )

            return render_template(
                "resume_result.html",
                skills=detected_skills,
                resume_score=resume_score,
                suggestions=resume_suggestions
            )

    return render_template("resume.html")

@app.route('/certificate')
def certificate():

    if "email" not in session:
        return redirect('/login')

    student = students.find_one({"email": session["email"]})

    if not student.get("resume_uploaded") or "mock_score" not in student:
        return "Complete resume upload and mock test before downloading certificate."

    filename = f"Skillara_Certificate_{student['name']}.pdf"
    filepath = os.path.join("uploads", filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # Background
    c.setFillColorRGB(0.94, 0.97, 1)
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Borders
    c.setStrokeColorRGB(0.10, 0.25, 0.55)
    c.setLineWidth(8)
    c.rect(35, 35, width - 70, height - 70, fill=False)

    c.setStrokeColorRGB(0.20, 0.55, 0.95)
    c.setLineWidth(3)
    c.rect(55, 55, width - 110, height - 110, fill=False)

    # Logo
    c.setFillColorRGB(0.15, 0.45, 0.95)
    c.circle(100, height - 100, 28, fill=1)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(100, height - 106, "AI")

    c.setFillColorRGB(0.10, 0.25, 0.55)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(140, height - 100, "Skillara")

    c.setFont("Helvetica", 11)
    c.drawString(140, height - 120, "Smart AI Career Guidance Platform")

    # Title
    c.setFillColorRGB(0.20, 0.55, 0.95)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, height - 180, "Certificate of Achievement")

    # Subtitle
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 235, "This certificate is proudly presented to")

    # Student name
    c.setFillColorRGB(0.05, 0.35, 0.70)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2, height - 285, student.get("name", "Student"))

    # Body
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 15)
    c.drawCentredString(
        width / 2,
        height - 340,
        "for successfully completing placement readiness activities"
    )

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, height - 385, f"Target Role: {student.get('target_role', 'N/A')}")
    c.drawCentredString(width / 2, height - 415, f"Mock Test Score: {student.get('mock_score', 0)}%")
    c.drawCentredString(width / 2, height - 445, f"Resume ATS Score: {student.get('resume_score', 0)}%")

    # Footer banner
    c.setFillColorRGB(0.10, 0.25, 0.55)
    c.roundRect(90, 105, width - 180, 55, 15, fill=True, stroke=False)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(
        width / 2,
        125,
        "Smart AI Career Guidance and Placement Readiness System"
    )

    # Signature
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 12)
    c.drawString(90, 75, "Authorized by Skillara")
    c.drawRightString(width - 90, 75, "Generated Certificate")

    c.save()

    return send_file(filepath, as_attachment=True)

@app.route('/mock', methods=['GET', 'POST'])
def mock():

    if "email" not in session:
        return redirect('/login')

    student = students.find_one({
        "email": session["email"]
    })

    role = student.get("target_role", "")

    questions = list(questions_collection.find({
        "role": role
    }))

    if not questions:
        questions = list(questions_collection.find({
            "role": "General"
        }))

    if len(questions) == 0:
        return render_template(
            "mock.html",
            role=role,
            questions=[],
            no_questions=True
        )

    if request.method == 'POST':

        score = 0
        results = []

        for i, item in enumerate(questions):

            user_answer = request.form.get(
                f"answer{i}", ""
            ).lower().strip()

            correct_answer = item.get(
                "answer", ""
            ).lower().strip()

            keywords = correct_answer.split()

            matched = False

            for keyword in keywords:
                if keyword.lower() in user_answer:
                    matched = True
                    break

            if matched:
                score += 1
                status = "Correct"
            else:
                status = "Wrong"

            results.append({
                "question": item.get("question"),
                "your_answer": user_answer,
                "correct_answer": item.get("answer"),
                "status": status
            })

        percentage = round(
            (score / len(questions)) * 100,
            2
        )

        students.update_one(
            {"email": session["email"]},
            {"$set": {
                "mock_score": percentage
            }}
        )

        return render_template(
            "mock_result.html",
            score=score,
            total=len(questions),
            percentage=percentage,
            results=results
        )

    return render_template(
        "mock.html",
        role=role,
        questions=questions,
        no_questions=False
    )
@app.route('/delete-student/<id>')
def delete_student(id):

    if "admin" not in session:
        return redirect('/admin-login')

    students.delete_one({"_id": ObjectId(id)})

    return redirect('/admin-dashboard')


@app.route('/delete-question/<id>')
def delete_question(id):

    if "admin" not in session:
        return redirect('/admin-login')

    questions_collection.delete_one({"_id": ObjectId(id)})

    return redirect('/admin-add-question')


@app.route('/delete-resource/<id>')
def delete_resource(id):

    if "admin" not in session:
        return redirect('/admin-login')

    resources_collection.delete_one({"_id": ObjectId(id)})

    return redirect('/admin-add-resource')


@app.route('/delete-company/<id>')
def delete_company(id):

    if "admin" not in session:
        return redirect('/admin-login')

    companies_collection.delete_one({"_id": ObjectId(id)})

    return redirect('/admin-add-company')

@app.route('/admin-add-notification', methods=['GET', 'POST'])
def admin_add_notification():

    if "admin" not in session:
        return redirect('/admin-login')

    if request.method == 'POST':

        title = request.form['title']
        message = request.form['message']

        notifications_collection.insert_one({
            "title": title,
            "message": message
        })

        return redirect('/admin-add-notification')

    notifications = list(notifications_collection.find())

    return render_template(
        "admin_add_notification.html",
        notifications=notifications
    )

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect('/admin-dashboard')

        return "Invalid Admin Login"

    return render_template("admin_login.html")

def get_placement_progress(student):

    completed = 0
    day_status = []

    for day in range(1, 8):

        score = student.get(f"day{day}_score")

        if score is not None:
            completed += 1
            status = "Completed"
        else:
            status = "Pending"

        day_status.append({
            "day": day,
            "status": status
        })

    progress = round((completed / 7) * 100)

    return progress, day_status

@app.route('/admin-dashboard')
def admin_dashboard():

    if "admin" not in session:
        return redirect('/admin-login')

    search = request.args.get("search", "")

    if search:
        all_students = list(students.find({
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"target_role": {"$regex": search, "$options": "i"}}
            ]
        }))
    else:
        all_students = list(students.find())

    total_students = len(all_students)

    readiness_scores = []
    mock_scores = []
    roles = []
    resume_uploaded_count = 0

    for s in all_students:
        if "cgpa" in s and "aptitude_score" in s and "communication_score" in s:
            readiness_scores.append(calculate_readiness(s))

        if "mock_score" in s:
            mock_scores.append(float(s.get("mock_score", 0)))

        if "target_role" in s:
            roles.append(s["target_role"])

        if s.get("resume_uploaded"):
            resume_uploaded_count += 1

    avg_readiness = round(sum(readiness_scores) / len(readiness_scores), 2) if readiness_scores else 0
    avg_mock_score = round(sum(mock_scores) / len(mock_scores), 2) if mock_scores else 0
    common_role = max(set(roles), key=roles.count) if roles else "Not Available"
    total_questions = questions_collection.count_documents({})

    total_resources = resources_collection.count_documents({})

    total_companies = companies_collection.count_documents({})

    total_notifications = notifications_collection.count_documents({})

    resume_uploaded_percent = round((resume_uploaded_count / total_students) * 100, 2) if total_students else 0

    top_students = sorted(
        all_students,
        key=lambda x: x.get("mock_score", 0),
        reverse=True
    )[:5]

    top_resume_students = sorted(
        all_students,
        key=lambda x: x.get("resume_score", 0),
        reverse=True
    )[:5]

    return render_template(
        "admin_dashboard.html",
        students=all_students,
        total_students=total_students,
        avg_readiness=avg_readiness,
        avg_mock_score=avg_mock_score,
        common_role=common_role,
        resume_uploaded_percent=resume_uploaded_percent,
        top_students=top_students,
        top_resume_students=top_resume_students,
        total_questions=total_questions,
        total_resources=total_resources,
        total_companies=total_companies,
        total_notifications=total_notifications
    )

@app.route('/admin-add-question', methods=['GET', 'POST'])
def admin_add_question():

    if "admin" not in session:
        return redirect('/admin-login')

    if request.method == 'POST':

        role = request.form['role']
        question = request.form['question']
        answer = request.form['answer']

        questions_collection.insert_one({
            "role": role,
            "question": question,
            "answer": answer
        })

        return redirect('/admin-add-question')

    all_questions = list(questions_collection.find())

    return render_template(
        "admin_add_question.html",
        questions=all_questions
    )


@app.route('/admin-add-resource', methods=['GET', 'POST'])
def admin_add_resource():

    if "admin" not in session:
        return redirect('/admin-login')

    if request.method == 'POST':

        skill = request.form['skill']
        url = request.form['url']

        resources_collection.insert_one({
            "skill": skill,
            "url": url
        })

        return redirect('/admin-add-resource')

    all_resources = list(resources_collection.find())

    return render_template(
        "admin_add_resource.html",
        resources=all_resources
    )


@app.route('/admin-add-company', methods=['GET', 'POST'])
def admin_add_company():

    if "admin" not in session:
        return redirect('/admin-login')

    if request.method == 'POST':

        name = request.form['name']
        min_cgpa = float(request.form['min_cgpa'])
        skills = request.form['skills'].lower().split(",")

        skills = [s.strip() for s in skills]

        companies_collection.insert_one({
            "name": name,
            "min_cgpa": min_cgpa,
            "skills": skills
        })

        return redirect('/admin-add-company')

    all_companies = list(companies_collection.find())

    return render_template(
        "admin_add_company.html",
        companies=all_companies
    )


@app.route('/admin-view-student/<id>')
def admin_view_student(id):

    if "admin" not in session:
        return redirect('/admin-login')

    student = students.find_one({"_id": ObjectId(id)})

    readiness = calculate_readiness(student)

    return render_template(
        "admin_view_student.html",
        student=student,
        readiness=readiness
    )

def is_day_unlocked(student, day):

    if day == 1:
        return True

    previous_day_score = student.get(f"day{day-1}_score")

    if previous_day_score is not None:
        return True

    return False


@app.route('/placement-plan/<int:day>', methods=['GET', 'POST'])
def placement_plan(day):

    if "email" not in session:
        return redirect('/login')

    if day < 1 or day > 7:
        return redirect('/placement-plan/1')

    student = students.find_one({"email": session["email"]})

    if not is_day_unlocked(student, day):
        return render_template(
            "day_locked.html",
            day=day,
            previous_day=day-1
        )

    role = student.get("target_role", "")

    questions = list(mcq_collection.find({
        "role": role,
        "day": day
    }))

    if request.method == 'POST':

        score = 0
        results = []

        for q in questions:

            selected = request.form.get(str(q["_id"]))
            correct = q.get("answer")

            if selected == correct:
                score += 1
                status = "Correct"
            else:
                status = "Wrong"

            results.append({
                "question": q["question"],
                "selected": selected,
                "correct": correct,
                "status": status,
                "resource": q.get("resource", "")
            })

        percentage = round(
            (score / len(questions)) * 100,
            2
        ) if questions else 0

        students.update_one(
            {"email": session["email"]},
            {"$set": {
                f"day{day}_score": percentage
            }}
        )

        return render_template(
            "placement_result.html",
            score=score,
            total=len(questions),
            percentage=percentage,
            results=results,
            day=day
        )

    return render_template(
        "placement_plan.html",
        questions=questions,
        day=day,
        role=role,
        student=student
    )


@app.route('/leaderboard')
def leaderboard():

    if "email" not in session:
        return redirect('/login')

    all_students = list(students.find())

    all_students.sort(
        key=lambda x: x.get("mock_score", 0),
        reverse=True
    )

    return render_template(
        "leaderboard.html",
        students=all_students
    )

@app.route('/export-students')
def export_students():

    if "admin" not in session:
        return redirect('/admin-login')

    def generate():

        data = list(students.find())

        yield "Name,Email,CGPA,Mock Score\n"

        for s in data:

            yield f"{s.get('name','')},{s.get('email','')},{s.get('cgpa','')},{s.get('mock_score',0)}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=students.csv"
        }
    )

@app.route('/admin-logout')
def admin_logout():
    session.pop("admin", None)
    return redirect('/admin-login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)