# boardly/api/projects_routes.py
"""POST /projects with a Decimal budget — the safe version."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing_extensions import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from fastapi.encoders import jsonable_encoder


# 1. The request model — rejects floats at the boundary
class ProjectCreate(BaseModel):
    name: str
    budget: Annotated[Decimal, Field(max_digits=12, decimal_places=2)]

    @field_validator("budget", mode="before")
    @classmethod
    def reject_float(cls, v):
        if isinstance(v, float):
            raise ValueError("budget must be a JSON string, not a number")
        return v

# 2. The response model — same fields, separate class (so we can differ later)
class ProjectOut(BaseModel):
    name: str
    budget: Decimal

# 3. The boardly app
app = FastAPI(title="boardly")

@app.post("/projects", response_model=ProjectOut)
def create_project(p: ProjectCreate) -> ProjectOut:
    """Create a project; tax-aware remaining-budget computation lives in the service."""
    return ProjectOut(name=p.name, budget=p.budget)

@app.get("/projects/{name}/remaining", response_model=ProjectOut)
def remaining(name: str, spent: Decimal = Decimal("0.00")) -> ProjectOut:
    """Compute remaining budget given a spent amount; rounds half-up to 2dp."""
    budget = Decimal("1000.00")
    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        remaining_value = (budget - spent).quantize(Decimal("0.01"))
    return ProjectOut(name=name, budget=remaining_value)

# 4. The serialisation contract — str(Decimal) round-trips
sample = ProjectOut(name="alpha", budget=Decimal("1000.00"))
print("model_dump:", sample.model_dump())          # {'name': 'alpha', 'budget': Decimal('1000.00')}
print("model_dump_json:", sample.model_dump_json())  # {"name":"alpha","budget":"1000.00"}
print("jsonable_encoder:", jsonable_encoder(sample))  # {'name': 'alpha', 'budget': '1000.00'}
print("str(Decimal):", str(Decimal("1.00")))        # 1.00

# 5. The int-cents alternative — for systems that need the speed
class ProjectCents(BaseModel):
    name: str
    budget_cents: int = Field(ge=0)   # $1.00 stored as 100

print("int-cents json:", ProjectCents(name="alpha", budget_cents=1000).model_dump_json())
# {"name":"alpha","budget_cents":1000}
