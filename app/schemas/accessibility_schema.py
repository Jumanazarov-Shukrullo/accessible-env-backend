from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CriterionSchema:
    class Create(BaseModel):
        criterion_name: str
        code: Optional[str] = None
        description: Optional[str] = None
        max_score: int
        unit: Optional[str] = None
        model_config = ConfigDict(from_attributes=True)

    class Out(Create):
        criterion_id: int


class AssessmentSetSchema:
    class Create(BaseModel):
        set_name: str
        description: Optional[str] = None
        version: int = 1
        is_active: bool = True
        model_config = ConfigDict(from_attributes=True)

    class Out(Create):
        set_id: int


class SetCriterionSchema:
    class Add(BaseModel):
        set_id: int
        criterion_id: int
        sequence: int
        model_config = ConfigDict(from_attributes=True)

    class Out(BaseModel):
        set_id: int
        criterion_id: int
        sequence: int
        model_config = ConfigDict(from_attributes=True)
