from fastapi import FastAPI
from api.routes import countries

app = FastAPI(
    title="Country Intelligence API",
    description="Multi-dimensional country data from international sources",
    version="0.1.0"
)

app.include_router(countries.router, prefix="/api")

@app.get("/")
def root():
    return {
        "name": "Country Intelligence API",
        "version": "0.1.0",
        "docs": "/docs"
    }