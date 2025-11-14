from fastapi import FastAPI
from app.routers.metrics import router as metrics_router
from app.routers.report import router as report_router
from app.routers.llm import router as llm_router

def create_app() -> FastAPI:
    app = FastAPI(title="Oathkeeper Metrics Analyzer (Modular)")
    app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
    app.include_router(report_router,  prefix="/metrics", tags=["report"])
    app.include_router(llm_router,     prefix="/metrics", tags=["llm"])
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
