from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, auth, documents, feedback, query

app = FastAPI(
    title="LearnFlow API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi-generated.json",  # ADR-010: openapi.yaml in project root is the SoT
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(query.router)
app.include_router(documents.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
