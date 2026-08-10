"""FastAPI application scaffold with no operational engineering behaviour."""

from fastapi import FastAPI


app = FastAPI(
    title="OT Graduate Demonstrator",
    version="0.1.0",
    description="Fictional local engineering demonstrator — I1 scaffold",
)
