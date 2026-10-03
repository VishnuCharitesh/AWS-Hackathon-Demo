# OpenSearch Assignment Evaluation Portal

A simple, modern, and complete web application built using **Python Flask, SQLite, SQLAlchemy, HTML, CSS, and Bootstrap 5** for managing OpenSearch assignments, student submissions, and evaluator grading.

---

## 🌟 Key Features

### 👨‍🎓 Student Role
* **Register & Login**: Simple authentication system with password hashing.
* **OpenSearch Assignments**: Browse all active OpenSearch assignments by topic (e.g., Indexing, Query DSL, Aggregations).
* **Read Instructions**: View detailed requirements, problem statements, total marks, and deadlines.
* **Submit Answers**: Enter and update OpenSearch JSON queries, mapping definitions, or explanations.
* **View Results & Feedback**: See scores, automatically calculated percentage score (`score / total_marks * 100`), evaluator comments, and answer preview.

### 👩‍🏫 Evaluator Role
* **Assignment Management**: Create, edit, and delete OpenSearch assignments with topics, instructions, total marks, and deadlines.
* **Submissions Overview**: Track incoming submissions from students across all assignments.
* **Grade & Feedback**: Assign scores (validated to not exceed total marks), write detailed feedback, and automatically compute percentages.

### 🛡️ Admin Role
* **Dashboard & Metrics**: View high-level metrics (Total Users, Students, Evaluators, Assignments, Submissions, Evaluated count).
* **User Directory**: View all registered users and their roles.
* **Global Oversight**: Inspect all assignments and submissions platform-wide.

---

## 📁 Project Folder Structure

```text
AWS-Hackthon/
├── app.py                      # Core Flask application, SQLAlchemy models, auth, & routes
├── requirements.txt            # Python dependencies (Flask, Flask-SQLAlchemy, Werkzeug)
├── README.md                   # Setup guide and application documentation
├── static/
│   └── css/
│       └── style.css           # Custom Bootstrap 5 extension styling & theme
└── templates/
    ├── base.html               # Base layout with navbar, alerts, footer
    ├── login.html              # Login page with demo account quick-fill
    ├── register.html           # User registration form
    ├── student/
    │   ├── dashboard.html      # Student overview & recent assignments
    │   ├── assignments.html    # List of available OpenSearch assignments
    │   ├── submit.html         # Assignment submission page
    │   └── results.html        # Evaluation results & feedback page
    ├── evaluator/
    │   ├── dashboard.html      # Evaluator metrics & pending reviews
    │   ├── assignments.html    # List & manage evaluator's assignments
    │   ├── create_assignment.html # Create new assignment form
    │   ├── edit_assignment.html   # Edit assignment parameters
    │   ├── submissions.html    # List of student submissions
    │   └── evaluate.html       # Grading form with live percentage calculation
    └── admin/
        ├── dashboard.html      # Admin portal statistics & user list
        ├── users.html          # User directory
        ├── assignments.html    # All system assignments
        └── submissions.html    # All system submissions
```

---

## 🗄️ Database Schema

The SQLite database (`instance/opensearch_portal.db`) is managed via SQLAlchemy with the following tables and relationships:

* **`users`**: `id`, `username`, `email`, `password_hash`, `role` (`student`, `evaluator`, `admin`), `created_at`
* **`assignments`**: `id`, `title`, `description`, `topic`, `instructions`, `total_marks`, `deadline`, `created_by_id` (FK -> `users.id`)
* **`submissions`**: `id`, `assignment_id` (FK -> `assignments.id`), `student_id` (FK -> `users.id`), `answer_text`, `submitted_at`, `status` (`Submitted`, `Evaluated`)
* **`evaluations`**: `id`, `submission_id` (FK -> `submissions.id`, Unique), `evaluator_id` (FK -> `users.id`), `score`, `feedback`, `percentage`, `evaluated_at`

---

## 🔑 Pre-seeded Demo Credentials

When the application runs for the first time, sample data and ready-to-use demo accounts are automatically initialized:

| Role | Username | Password | Email |
| :--- | :--- | :--- | :--- |
| **Student** | `student1` | `stud123` | `student1@example.com` |
| **Student** | `student2` | `stud123` | `student2@example.com` |
| **Evaluator** | `evaluator1` | `eval123` | `evaluator1@opensearch.org` |
| **Evaluator** | `prof_smith` | `eval123` | `smith@university.edu` |
| **Admin** | `admin` | `admin123` | `admin@opensearch.org` |

---

## 🚀 How to Run the Application

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Flask App
```bash
python app.py
```

### 3. Open in Browser
Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 🔄 Complete Workflow Test Scenario

1. **Evaluator Login**: Log in as `evaluator1` / `eval123`.
2. **Create Assignment**: Go to **Manage Assignments** &rarr; **Create Assignment**. Fill in details for a new OpenSearch topic (e.g., *Match Query vs Term Query*), specify instructions and total marks (e.g. 50), and save.
3. **Student Submission**: Log out and log in as `student1` / `stud123`. Click **Assignments**, open the newly created assignment, enter the OpenSearch JSON query solution, and submit.
4. **Evaluator Grading**: Log out and log back in as `evaluator1`. Go to **Submissions**, click **Evaluate** on `student1`'s answer. Enter a score (e.g., 45) and feedback. Observe the live percentage calculation (`90%`). Submit the evaluation.
5. **Student View Result**: Log out and log back in as `student1`. Go to **My Results** to view score (`45 / 50`), percentage (`90%`), and feedback from the evaluator.
6. **Admin Overview**: Log in as `admin` / `admin123` to view global statistics and user activity.
