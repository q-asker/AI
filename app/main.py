from fastapi import FastAPI, status, Request
from starlette.responses import JSONResponse

from app.router.generate_router import router as generate_router
from app.util.logger import logger

app = FastAPI(docs_url="/")


app.include_router(generate_router)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.exception(exc)
    message = str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": exc.__class__.__name__,
            "detail": message,
        },
    )
