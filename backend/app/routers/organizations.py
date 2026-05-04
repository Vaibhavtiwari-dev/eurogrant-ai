from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, database
from ..auth import get_current_user

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"]
)

@router.get("/me", response_model=schemas.OrganizationOut)
async def get_my_organization(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
