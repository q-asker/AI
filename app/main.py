from fastapi import FastAPI

from app.router.generate_router import router as generate_router

app = FastAPI(docs_url="/")


app.include_router(generate_router)
