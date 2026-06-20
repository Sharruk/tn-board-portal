# TN State Board Learning Platform — API Reference

Base URL (local): `http://localhost:5000/api/v1`  
Interactive docs: `http://localhost:5000/docs`

---

## Public Endpoints

### Classes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/classes` | List all 4 classes (9–12) with subject counts |
| GET | `/classes/{class_id}` | Get a single class |
| GET | `/classes/{class_id}/subjects` | List all subjects for a class |

### Subjects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/subjects/{subject_id}` | Get subject details |
| GET | `/subjects/{subject_id}/papers` | List papers (filter: exam_type, paper_type, year) |

### Papers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/papers/{paper_id}` | Get paper details |
| GET | `/exam-types` | List all valid exam type strings |

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search?q=<query>` | Full-text search (also filter: class_id, exam_type, paper_type, year) |

---

## Admin Endpoints (JWT required)

### Auth
| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | `{username, password}` | Returns JWT token |

### Paper Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/papers` | List all papers (including hidden) |
| POST | `/admin/papers` | Upload a paper (multipart form) |
| PUT | `/admin/papers/{id}` | Update paper metadata |
| DELETE | `/admin/papers/{id}` | Delete paper + file |

### Admin Upload Form Fields
```
subject_id  : int      (required)
exam_type   : string   (required) e.g. "Unit Test 1"
year        : int      (required) e.g. 2024
title       : string   (required)
paper_type  : string   (required) "question" | "answer_key"
youtube_url : string   (optional)
file        : PDF file (optional)
```

---

## Authentication
All admin endpoints require:
```
Authorization: Bearer <access_token>
```
Token is returned from `POST /auth/login`.

---

## Paper Types
- `question` — Question paper PDF
- `answer_key` — Answer key PDF

## Exam Types
- Unit Test 1, Unit Test 2, Unit Test 3
- Quarterly Exam
- Half Yearly Exam
- Annual Exam
- Public Exam
- Practical Exam
- Model Exam
