# Module 01 Cheat Sheet: FastAPI Foundations

## FastAPI Decorator Reference

```python
from fastapi import FastAPI, APIRouter, Depends, Query, Path, Body, Header, Cookie
from fastapi import HTTPException, status, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

# HTTP Methods
@app.get("/path")
@app.post("/path", status_code=201)
@app.put("/path")
@app.patch("/path")
@app.delete("/path", status_code=204)

# Decorator Parameters
@app.get(
    "/path/{id}",
    response_model=ResponseSchema,
    status_code=200,
    tags=["tag"],
    summary="Short description",
    dependencies=[Depends(auth)],
    responses={404: {"model": Error}},
    include_in_schema=True,
)
```

## Parameter Extraction

```python
async def handler(item_id: int = Path(..., gt=0)):           # /items/{item_id}
async def handler(skip: int = Query(0, ge=0)):               # ?skip=0
async def handler(tags: list[str] = Query(default=[])):      # ?tag=a&tag=b
async def handler(item: ItemCreate):                          # JSON body
async def handler(name: str = Body(...)):                     # body field
async def handler(x_token: str = Header(...)):                # header
async def handler(session_id: str = Cookie(None)):            # cookie
```

## Pydantic Model Template

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., gt=0)

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        return v.strip() or (_ for _ in ()).throw(ValueError("blank"))

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(None, gt=0)

class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def display_price(self) -> str:
        return f"${self.price:.2f}"
```

## Dependency Injection Patterns

```python
# Yield dependency (cleanup)
async def get_db():
    async with session_factory() as session:
        yield session

# Class dependency
class Pagination:
    def __init__(self, skip: int = Query(0, ge=0), limit: int = Query(100, le=1000)):
        self.skip = skip
        self.limit = limit

# Factory dependency
def require_role(role: str):
    async def checker(user=Depends(get_current_user)):
        if role not in user.roles: raise HTTPException(403)
        return user
    return checker

# Scopes
router = APIRouter(dependencies=[Depends(verify_api_key)])   # router-level
app = FastAPI(dependencies=[Depends(rate_limiter)])           # app-level
app.dependency_overrides[get_db] = override_get_db            # testing
```

## Common Status Codes

```python
status.HTTP_200_OK                    # GET/PUT/PATCH success
status.HTTP_201_CREATED               # POST (resource created)
status.HTTP_204_NO_CONTENT            # DELETE success
status.HTTP_400_BAD_REQUEST           # client error
status.HTTP_401_UNAUTHORIZED          # not authenticated
status.HTTP_403_FORBIDDEN             # not authorized
status.HTTP_404_NOT_FOUND             # resource missing
status.HTTP_409_CONFLICT              # duplicate
status.HTTP_422_UNPROCESSABLE_ENTITY  # validation error
status.HTTP_429_TOO_MANY_REQUESTS     # rate limited
```

## Middleware Setup

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Last added = outermost = runs first
app.add_middleware(CORSMiddleware, allow_origins=["https://example.com"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

## Lifespan + Exception Handler + Settings

```python
from contextlib import asynccontextmanager
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    yield
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"errors": exc.errors()})

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")
    database_url: str
    debug: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Express-to-FastAPI Translation

| Express | FastAPI |
|---------|---------|
| `app.use(middleware)` | `app.add_middleware(Cls)` |
| `app.get('/path', handler)` | `@app.get("/path")` |
| `express.Router()` | `APIRouter()` |
| `app.use('/prefix', router)` | `app.include_router(router, prefix="/prefix")` |
| `req.params.id` | `item_id: int` (path param) |
| `req.query.page` | `page: int = Query(1)` |
| `req.body` | `item: ItemCreate` (Pydantic model) |
| `req.headers['x-token']` | `x_token: str = Header(...)` |
| `res.status(201).json(data)` | `return data` + `status_code=201` |
| `next()` | `await call_next(request)` |
| `process.env.DB_URL` | `Settings().database_url` |
