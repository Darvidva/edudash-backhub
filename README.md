This is the FastAPI backend for the Personalized Learning Recommendation System. It handles authentication, course registration, CGPA data storage, and other academic utilities.

🚀 Features
🔐 JWT-based authentication

📦 RESTful endpoints for courses, semesters, users

🧠 Easily extendable for ML/AI integrations

🗃️ PostgreSQL database

📄 Pydantic for validation

📁 Folder Structure
bash
Copy
Edit
/backend
├── app/
│   ├── main.py             # FastAPI entry point
│   ├── models.py           # SQLAlchemy ORM models
│   ├── schemas.py          # Pydantic request/response models
│   ├── routes/             # All routers (e.g., auth, courses, semesters)
│   ├── database.py         # DB connection setup
│   ├── token.py            # JWT token utilities
│   └── dependencies.py     # Auth and shared dependencies
├── .env                    # Secrets and DB URL
├── requirements.txt
└── venv/ (excluded from git)
🧪 Setup Instructions
bash
Copy
Edit
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Set up your .env file
cp .env.example .env
Example .env:

env
Copy
Edit
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<dbname>
SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
🖥️ Run the App
bash
Copy
Edit
uvicorn app.main:app --reload
📦 Hosting
Use Render or Railway for easy deployment.

Set the DATABASE_URL from the cloud PostgreSQL database (e.g., Supabase or Render Postgres).

Add the .env settings under "Environment Variables".

🔐 Git Best Practices
Your .gitignore should contain:

bash
Copy
Edit
# Python
venv/
__pycache__/
*.pyc
.env

# Node
node_modules/
dist/
.env
✅ Don’t commit .env or venv/

🤝 Credits
Developed by David Mbre
Final Year Project – Department of Computer Science, EKSU

