# Document Chat AI

##  Tech Stack

### Backend
- FastAPI
- FAISS (vector search)
- Sentence Transformers
- OpenAI API

### Frontend
- React (Vite)
- EventSource (streaming)

---

##  Setup Instructions

### 1. Clone repo

```bash
git clone https://github.com/your-username/p1.git
cd p1
```
2. Backend setup
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```
Create .env:
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```
Run backend:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
3. Frontend setup
```bash
cd frontend
npm install
```
Run frontend:
```bash
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```
Open:
http://localhost:5173

How to Use
Upload a PDF
Go to Chat page
Ask questions about the document
View answers + source chunks

Author
Vivall Merugu 
ivivall663@gmail.com
