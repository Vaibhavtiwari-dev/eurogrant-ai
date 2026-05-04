from fastapi import FastAPI, Depends, HTTPException, status
from . import models, database, schemas, auth
from .database import engine, get_db
from .routers import auth as auth_router, uploads as uploads_router, organizations as organizations_router

# ... (main part stays same)

app.include_router(auth_router.router)
app.include_router(uploads_router.router)
app.include_router(organizations_router.router)


@app.get("/")
async def root():
    return {"message": "Welcome to EuroGrant AI API"}

@app.get("/users/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
