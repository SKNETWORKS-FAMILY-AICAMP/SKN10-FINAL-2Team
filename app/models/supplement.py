from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Supplement(BaseModel):
    __tablename__ = "supplements"

    name = Column(String(100), nullable=False)
    brand = Column(String(100))
    description = Column(Text)
    category = Column(String(50))
    target_gender = Column(String(10))
    target_age_range = Column(String(50))
    
    ingredients = relationship("SupplementIngredient", back_populates="supplement")

class Ingredient(BaseModel):
    __tablename__ = "ingredients"

    name = Column(String(100), nullable=False)
    risk_info = Column(Text)
    
    supplements = relationship("SupplementIngredient", back_populates="ingredient")
    interactions = relationship("Interaction", 
                              primaryjoin="or_(Ingredient.id==Interaction.ingredient_id_1, "
                                        "Ingredient.id==Interaction.ingredient_id_2)")

class SupplementIngredient(BaseModel):
    __tablename__ = "supplement_ingredients"

    supplement_id = Column(Integer, ForeignKey("supplements.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    amount_mg = Column(Float)
    
    supplement = relationship("Supplement", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="supplements")

class Interaction(BaseModel):
    __tablename__ = "interactions"

    ingredient_id_1 = Column(Integer, ForeignKey("ingredients.id"))
    ingredient_id_2 = Column(Integer, ForeignKey("ingredients.id"))
    interaction_type = Column(String(50))
    note = Column(Text) 