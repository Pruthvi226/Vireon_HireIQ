# AI Interview Coach - Smart Virtual Interview Platform

Production-ready monorepo with:
- `database/` MySQL schema
- `backend/` Spring Boot API + JWT + JPA + WebSocket
- `ai-service/` FastAPI AI microservice (Gemini + prompt pipelines)
- `frontend/` React + Vite + Tailwind + Framer Motion

## 1) SQL Schema
Run `database/schema.sql` against MySQL 8+

## 2) Backend (Spring Boot)

### Env
**Default run** uses in-memory H2 (profile `dev`); MySQL env vars apply only when profile **`mysql`** is active.

For MySQL:
- `SPRING_PROFILES_ACTIVE=mysql`
- `DB_URL`, `DB_USERNAME`, `DB_PASSWORD` (default password `password` matches `docker-compose.yml`)
- `JWT_SECRET` (set secure 32+ chars)
- `AI_SERVICE_BASE_URL` (default: `http://localhost:8000`)
- `CORS_ALLOWED_ORIGINS` (default: `http://localhost:5173`)

See `backend/.env.example`. Copy to `backend/.env` (gitignored). A startup hook loads `.env` from the current working directory before the datasource is created.

### MySQL `Access denied` (1045)

The backend uses `root` + `DB_PASSWORD`. If you see `Access denied for user 'root'@'localhost'`:

1. **Using Docker MySQL** (recommended): from repo root run `docker compose up -d mysql`, wait until healthy, then start the backend with profile `mysql` (root password is `password` per compose).
2. **Using a local MySQL install**: activate profile `mysql` and set the real password, e.g. PowerShell:
   ```powershell
   $env:SPRING_PROFILES_ACTIVE="mysql"
   $env:DB_PASSWORD="YourActualRootPassword"
   cd backend
   mvn spring-boot:run
   ```
   Or put `SPRING_PROFILES_ACTIVE=mysql` and `DB_PASSWORD=...` in `backend/.env`.
3. Ensure schema exists: apply `database/schema.sql` (Docker applies it on first init; local MySQL may need manual import).

If you see **Unable to determine Dialect without JDBC metadata**, that usually follows a failed DB connection; the app now sets `hibernate.dialect` for MySQL so Hibernate still configures correctly once credentials are fixed.

### Run (default — H2, no MySQL)

`spring-boot-maven-plugin` activates profile **`dev`** for `mvn spring-boot:run`, so you get H2 even if Windows has a user-wide `SPRING_PROFILES_ACTIVE` (e.g. `mysql`) set. To use MySQL from Maven, pass `-Dspring-boot.run.profiles=mysql` explicitly.

If you still see MySQL errors on `mvn spring-boot:run`, clear the variable for that session:

```powershell
Remove-Item Env:SPRING_PROFILES_ACTIVE -ErrorAction SilentlyContinue
```

```bash
cd backend
mvn spring-boot:run
```

### Run with MySQL

After `docker compose up -d mysql` (or with a local MySQL matching `DB_*`):

```bash
cd backend
mvn spring-boot:run -Dspring-boot.run.profiles=mysql
```

If port **8080** is already in use, stop the other process or set `SERVER_PORT=8081` (or `server.port` in config).

## 3) AI Service (FastAPI)

### Env
- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (optional, default `gemini-1.5-flash`)
- `ALLOWED_ORIGINS` (optional)

### Run
```bash
cd ai-service
python -m venv .venv
# windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 4) Frontend (React)

### Env
Copy `frontend/.env.example` to `.env` and adjust values if needed.

### Run
```bash
cd frontend
npm install
npm run dev
```

## 5) Docker MySQL (optional)
```bash
docker compose up -d mysql
```

## API Endpoints

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`

### Interview
- `POST /api/interview/start`
- `POST /api/interview/{id}/question`
- `POST /api/interview/{id}/answer`
- `GET /api/interview/{id}/feedback`
- `POST /api/interview/{id}/finish`

### Dashboard
- `GET /api/user/interviews?page=0&size=10`
- `GET /api/user/progress`

### AI Service
- `POST /generate-question`
- `POST /analyze-answer`
- `POST /generate-feedback`
- `POST /resume-analysis`

## Notes
- Interview stream updates are published over STOMP topic `/topic/interview.{id}` via `/ws/interview`.
- Resume extraction currently decodes plain text from bytes; replace with OCR/PDF parser in production.
- Add Flyway migrations and object-storage integration before deployment.
