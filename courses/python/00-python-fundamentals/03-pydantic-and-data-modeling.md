# 03 – Pydantic and Data Modeling

Pydantic is a data validation library that uses type hints to define schemas. Think of it as Zod but integrated into the type system — you define a class with type annotations, and Pydantic automatically validates input, coerces types, serializes output, and generates JSON Schema.

---

## 1. What Pydantic Actually Is

```python
from pydantic import BaseModel, Field, field_validator

class User(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., gt=0)
    email: str

    @field_validator("email")
    @classmethod
    def must_be_valid_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email")
        return v.lower()

# Validation happens at instantiation
user = User(name="Alice", age=30, email="ALICE@EXAMPLE.COM")
user.email  # "alice@example.com" — validator lowercased it

# Invalid data raises ValidationError
User(name="", age=-1, email="bad")
# ValidationError: 3 errors — name too short, age too low, invalid email

# Serialization
user.model_dump()       # {"name": "Alice", "age": 30, "email": "alice@example.com"}
user.model_dump_json()  # JSON string

# Schema generation (drives OpenAPI docs in FastAPI)
User.model_json_schema()
```

---

## 2. Why Frameworks Use Pydantic Everywhere

In Express, you parse the body, validate with Zod/Joi, and type-cast manually. In FastAPI, all of that is automatic — driven by Pydantic type hints:

```python
# FastAPI reads the type hint and:
# 1. Parses the request body as JSON
# 2. Validates it against UserCreate's schema
# 3. Returns 422 with detailed errors if validation fails
# 4. Passes the validated, typed object to your function
@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    # user is already validated — no manual checks needed
    ...
```

---

## 3. Model Inheritance

Pydantic models use inheritance to share fields and avoid repetition:

```python
# Base — shared fields
class ItemBase(BaseModel):
    name: str
    price: float

# Create — what clients send (no id, no timestamps)
class ItemCreate(ItemBase):
    pass

# Update — all fields optional
class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

# Response — what clients receive (includes server-generated fields)
class ItemResponse(ItemBase):
    id: int
    created_at: datetime
```

This `Base → Create / Update / Response` pattern is used extensively in API development.

---

## 4. Field Validation

### Built-in Constraints

```python
class Product(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0, le=10_000)
    sku: str = Field(..., pattern=r"^[A-Z]{2}-\d{4}$")
    tags: list[str] = Field(default_factory=list)
```

### Custom Validators

```python
from pydantic import field_validator, model_validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str
    password_confirm: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("must be alphanumeric")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        return self
```

---

## 5. Configuration

```python
from pydantic import ConfigDict

class StrictUser(BaseModel):
    model_config = ConfigDict(
        strict=True,           # no type coercion (int stays int, not "42" -> 42)
        frozen=True,           # immutable after creation
        extra="forbid",        # reject unexpected fields
    )

    name: str
    age: int
```

---

## 6. Computed Fields

```python
from pydantic import computed_field

class Order(BaseModel):
    items: list[float]
    tax_rate: float = 0.08

    @computed_field
    @property
    def total(self) -> float:
        subtotal = sum(self.items)
        return round(subtotal * (1 + self.tax_rate), 2)

order = Order(items=[10.0, 20.0, 30.0])
order.total       # 64.8
order.model_dump()  # includes "total": 64.8
```

---

## 7. Dataclasses vs Pydantic

| Feature | `dataclass` | `Pydantic BaseModel` |
|---------|------------|---------------------|
| Purpose | Data containers | Data validation + serialization |
| Validation | None (just stores values) | Full runtime validation |
| Performance | Faster (no validation) | Slower but Pydantic v2 is Rust-based |
| Serialization | Manual | Built-in `.model_dump()`, `.model_dump_json()` |
| Immutability | `frozen=True` | `model_config = ConfigDict(frozen=True)` |
| Use case | Internal data structures | API boundaries, config, external data |

**Rule of thumb**: Use Pydantic at the edges (API input/output, config, external data). Use dataclasses for internal data structures where validation overhead is unnecessary.

---

## Key Takeaways

- Pydantic validates data at instantiation — invalid input raises `ValidationError`.
- `Field(...)` marks required fields; `Field(None)` or `Field(default=...)` for optional.
- `@field_validator` validates individual fields; `@model_validator` validates across fields.
- `model_dump()` and `model_dump_json()` handle serialization.
- The `Base → Create / Update / Response` pattern avoids field repetition.
- Use Pydantic at system boundaries; use dataclasses for internal data.
