from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.supplement import Supplement, Ingredient, Interaction
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/supplements", tags=["supplements"])

class SupplementBase(BaseModel):
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_gender: Optional[str] = None
    target_age_range: Optional[str] = None

class SupplementCreate(SupplementBase):
    pass

class SupplementResponse(SupplementBase):
    id: int

    class Config:
        from_attributes = True

class IngredientBase(BaseModel):
    name: str
    risk_info: Optional[str] = None

class IngredientCreate(IngredientBase):
    pass

class IngredientResponse(IngredientBase):
    id: int

    class Config:
        from_attributes = True

@router.post("/", response_model=SupplementResponse)
def create_supplement(supplement: SupplementCreate, db: Session = Depends(get_db)):
    db_supplement = Supplement(**supplement.dict())
    db.add(db_supplement)
    db.commit()
    db.refresh(db_supplement)
    return db_supplement

@router.get("/", response_model=List[SupplementResponse])
def get_supplements(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Supplement)
    if category:
        query = query.filter(Supplement.category == category)
    return query.offset(skip).limit(limit).all()

@router.get("/{supplement_id}", response_model=SupplementResponse)
def get_supplement(supplement_id: int, db: Session = Depends(get_db)):
    supplement = db.query(Supplement).filter(Supplement.id == supplement_id).first()
    if supplement is None:
        raise HTTPException(status_code=404, detail="Supplement not found")
    return supplement

@router.post("/ingredients/", response_model=IngredientResponse)
def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    db_ingredient = Ingredient(**ingredient.dict())
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient

@router.get("/ingredients/", response_model=List[IngredientResponse])
def get_ingredients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Ingredient).offset(skip).limit(limit).all() 