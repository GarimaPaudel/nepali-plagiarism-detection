# Nepali Plagiarism Detection System

A REST API for detecting plagiarism in Nepali-language assignment submissions. Each submission is checked against a static reference corpus **and** against all peer submissions within the same assignment.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (async) |
| Database | PostgreSQL + SQLModel + asyncpg |
| Task Queue | Celery + Redis |
| ML | TF-IDF, Rabin-Karp, XLM-RoBERTa (fine-tuned) |
| PDF Generation | ReportLab |
| Containerization | Docker + Docker Compose |
| Dependency Management | uv |

---

## Architecture

```
Student uploads file
        │
POST /submissions/
        │
  File saved to disk (/app/uploads/)
        │
  Submission record created in DB
        │
  Pending PlagiarismResult rows seeded
  (one per corpus file + one per peer submission)
        │
  Celery task dispatched (async)
        │
  ┌─────────────────────────────┐
  │  Plagiarism Check Worker    │
  │                             │
  │  Pass 1: vs Corpus          │
  │  Pass 2: vs Peer Submissions│
  └─────────────────────────────┘
        │
  Results saved to DB
        │
GET /submissions/{id}/status   ← poll until done
GET /submissions/{id}/report   ← download PDF
```

---

## ML Pipeline

Each submission is compared using three methods:

### 1. TF-IDF Cosine Similarity
- Text is preprocessed: tokenized, punctuation removed, Nepali stopwords filtered, then stemmed using the Snowball Nepali stemmer
- Both texts are vectorized using scikit-learn's `TfidfVectorizer`
- Cosine similarity is computed between the two vectors
- If score ≥ `PLAGIARISM_THRESHOLD` (default `0.5`) → flagged as plagiarized

### 2. Rabin-Karp Exact Sentence Matching
- Both documents are split into sentences on Nepali sentence-ending characters (`।`, `?`, `!`)
- Each sentence from the submitted text is searched inside the reference using the Rabin-Karp rolling hash algorithm
- Returns a list of matched sentences with their position (sentence index, character index)

### 3. XLM-RoBERTa Semantic Similarity
- Uses a fine-tuned multilingual XLM-RoBERTa model loaded from `/app/model/`
- Both texts are tokenized and passed through the model; embeddings are mean-pooled from the last hidden state
- Cosine similarity is computed between the two embeddings
- Gracefully skipped if the model files are not present

### Text Preprocessing Steps
1. Split into sentences on `।`, `?`, `!`
2. Extract Devanagari words using regex `[\u0900-\u097F]+`
3. Remove punctuation, digits (ASCII + Devanagari numerals), and the `।` character
4. Filter Nepali stopwords
5. Stem using the Snowball Nepali stemmer

---

## Roles

| Role | Capabilities |
|---|---|
| `teacher` | Self-registers; creates student accounts; manages assignments; views all submissions and reports; deletes submissions/users |
| `student` | Created by a teacher; submits files; views own submissions and reports |

Authentication uses **JWT Bearer tokens** (OAuth2 password flow).

---

## API Endpoints

All responses (except login and report download) follow this envelope:

```json
{
  "success": true,
  "message": "...",
  "data": { ... }
}
```

---

### Users — `/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/users/register` | Public | Register a teacher account |
| `POST` | `/users/login` | Public | Login (returns JWT token) |
| `POST` | `/users/students` | Teacher | Create a student account |
| `GET` | `/users/me` | Any | Get current logged-in user |
| `GET` | `/users/` | Teacher | List all users |
| `GET` | `/users/{user_id}` | Any | Get a user by ID |
| `DELETE` | `/users/{user_id}` | Teacher | Delete a user |

**Register teacher** `POST /users/register`
```json
{
  "username": "teacher1",
  "email": "teacher@example.com",
  "password": "secret"
}
```

**Login** `POST /users/login` (form data)
```
username=teacher@example.com&password=secret
```
Returns:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

**Create student** `POST /users/students`
```json
{
  "username": "student1",
  "email": "student@example.com",
  "password": "secret"
}
```

---

### Assignments — `/assignments`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/assignments/` | Teacher | Create an assignment |
| `GET` | `/assignments/` | Any | List all assignments |
| `GET` | `/assignments/{assignment_id}` | Any | Get assignment by ID |
| `PATCH` | `/assignments/{assignment_id}` | Teacher | Update an assignment |
| `DELETE` | `/assignments/{assignment_id}` | Teacher | Delete an assignment |

**Create assignment** `POST /assignments/`
```json
{
  "title": "Assignment 1",
  "description": "Write an essay on climate change",
  "due_date": "2026-05-01T00:00:00Z"
}
```

---

### Submissions — `/submissions`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/submissions/` | Any | Submit a file for an assignment |
| `GET` | `/submissions/{submission_id}` | Any | Get a submission by ID |
| `GET` | `/submissions/{submission_id}/status` | Any | Poll plagiarism check status |
| `GET` | `/submissions/{submission_id}/report` | Any | Download PDF plagiarism report |
| `GET` | `/submissions/by-assignment/{assignment_id}` | Any | List submissions for an assignment |
| `GET` | `/submissions/by-student/{student_id}` | Any | List submissions by a student |
| `DELETE` | `/submissions/{submission_id}` | Teacher | Delete a submission |

**Submit file** `POST /submissions/` (multipart form)
```
assignment_id=<uuid>
file=<.txt or .pdf file>
```

**Check status** `GET /submissions/{id}/status`
```json
{
  "success": true,
  "data": {
    "submission_id": "...",
    "overall_status": "done",
    "max_tfidf_similarity": 0.87,
    "results": [
      {
        "reference_filename": "reference1.txt",
        "reference_submission_id": null,
        "tfidf_similarity": 0.87,
        "xlm_similarity": 0.91,
        "is_plagiarized": true,
        "matched_sentences": [["copied sentence", 2, 14]],
        "status": "done"
      },
      {
        "reference_filename": null,
        "reference_submission_id": "<peer-submission-uuid>",
        "tfidf_similarity": 0.43,
        "xlm_similarity": 0.51,
        "is_plagiarized": false,
        "matched_sentences": [],
        "status": "done"
      }
    ]
  }
}
```

`overall_status` values: `pending` → `running` → `done` / `failed`

**Download report** `GET /submissions/{id}/report`

Returns a PDF with:
- Submitted text with matched sentences highlighted in blue
- **Corpus Comparison** section — results against each corpus file
- **Peer Submission Comparison** section — results against other students' submissions

---

## Database Models

### `submissions`
| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `assignment_id` | UUID FK | Which assignment |
| `student_id` | UUID FK | Who submitted |
| `original_filename` | string (nullable) | Uploaded filename |
| `file_path` | string (nullable) | Path to file on disk |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

### `plagiarism_results`
| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `submission_id` | UUID FK | The submission being checked |
| `reference_filename` | string (nullable) | Set for corpus comparisons |
| `reference_submission_id` | UUID FK (nullable) | Set for peer comparisons |
| `tfidf_similarity` | float | TF-IDF cosine score |
| `xlm_similarity` | float | XLM-RoBERTa cosine score |
| `is_plagiarized` | bool | Whether threshold was exceeded |
| `matched_sentences` | JSON | List of `[sentence, sent_idx, char_idx]` |
| `task_id` | string | Celery task ID |
| `status` | string | `pending` / `running` / `done` / `failed` |

---

## Running Locally

### Prerequisites
- Docker + Docker Compose
- A `.env` file (see below)
- Fine-tuned model at `model/similarity_model/` and `model/similarity_tokenizer/`
- Corpus files (`.txt` or `.pdf`) in `corpus/`
- Nepali stopwords at `resources/nepali_stopwords.txt`
- Nepali font at `resources/NotoSansDevanagari-Bold.ttf`

### `.env`
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SERVER=plagiarism_db
POSTGRES_PORT=5432
POSTGRES_DB=plagiarism
JWT_SECRET_KEY=your-secret-key
```

### Start
```bash
docker compose up --build
```

### Run migrations
```bash
docker compose exec plagiarism_api alembic upgrade head
```

### API docs
Visit `http://localhost:8000/docs`

### Monitor Celery tasks
```bash
docker compose exec plagiarism_worker celery -A src.tasks.celery_app inspect active
```

---

## Project Structure

```
src/
├── api/
│   ├── deps.py              # Auth dependencies 
│   └── endpoints/
│       ├── users.py
│       ├── assignments.py
│       └── submissions.py
├── core/
│   ├── responses.py         
│   └── exception.py         
├── database/
│   ├── main.py              
│   └── models/
│       ├── users.py
│       ├── assignment.py
│       └── submission.py    
├── ml/
│   ├── pipeline.py          
│   ├── preprocess.py        
│   ├── stemmer.py           
│   ├── embed.py             
│   └── model_loader.py      
├── schemas/                 
├── services/
│   ├── plagiarism_service.py  
│   └── report_service.py      
└── tasks/
    ├── celery_app.py        
    └── plagiarism_tasks.py  
```
