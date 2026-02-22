# Module 05 Deep Dive: Beyond REST

This deep dive covers the patterns you'll encounter when REST alone isn't enough — GraphQL,
gRPC, message queues, event-driven architecture, and real-time communication trade-offs.

---

## 1. GraphQL with Strawberry

Strawberry is Python's modern, type-first GraphQL library. If you've used TypeGraphQL or Nexus,
Strawberry will feel familiar — it uses dataclasses and type hints instead of SDL.

### FastAPI Integration

```python
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class UserType:
    id: int
    name: str
    email: str

@strawberry.type
class Query:
    @strawberry.field
    async def users(self, limit: int = 10) -> list[UserType]:
        async with get_session() as db:
            result = await db.execute(select(User).limit(limit))
            return [UserType(id=u.id, name=u.name, email=u.email)
                    for u in result.scalars()]

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> UserType:
        async with get_session() as db:
            user = User(name=name, email=email)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return UserType(id=user.id, name=user.name, email=user.email)

schema = strawberry.Schema(query=Query, mutation=Mutation)
app.include_router(GraphQLRouter(schema), prefix="/graphql")
```

### DataLoader for N+1 Prevention

Same concept as the DataLoader pattern in Node.js GraphQL servers.

```python
from strawberry.dataloader import DataLoader

async def load_users_by_ids(ids: list[int]) -> list[UserType]:
    async with get_session() as db:
        result = await db.execute(select(User).where(User.id.in_(ids)))
        user_map = {u.id: u for u in result.scalars()}
        return [UserType(id=user_map[i].id, name=user_map[i].name,
                         email=user_map[i].email) for i in ids]

@strawberry.type
class PostType:
    id: int
    title: str
    author_id: int

    @strawberry.field
    async def author(self, info: strawberry.types.Info) -> UserType | None:
        return await info.context["user_loader"].load(self.author_id)

async def get_context():
    return {"user_loader": DataLoader(load_fn=load_users_by_ids)}

graphql_app = GraphQLRouter(schema, context_getter=get_context)
```

---

## 2. gRPC with Python

gRPC is the go-to for internal service communication when you need performance and strong
contracts. Define services in proto files, generate Python stubs.

### Proto Definition

```protobuf
syntax = "proto3";
package users;

service UserService {
  rpc GetUser (GetUserRequest) returns (UserResponse);
  rpc ListUsers (ListUsersRequest) returns (stream UserResponse);
}

message GetUserRequest { int32 id = 1; }
message ListUsersRequest { int32 limit = 1; }
message UserResponse { int32 id = 1; string name = 2; string email = 3; }
```

### Server and Client

```python
import grpc
from grpc import aio

class UserServicer(user_service_pb2_grpc.UserServiceServicer):
    async def GetUser(self, request, context):
        user = await get_user_from_db(request.id)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return user_service_pb2.UserResponse()
        return user_service_pb2.UserResponse(
            id=user.id, name=user.name, email=user.email)

    async def ListUsers(self, request, context):
        async for user in stream_users_from_db(request.limit):
            yield user_service_pb2.UserResponse(
                id=user.id, name=user.name, email=user.email)

# Client
async def get_user(user_id: int):
    async with aio.insecure_channel("localhost:50051") as channel:
        stub = user_service_pb2_grpc.UserServiceStub(channel)
        return await stub.GetUser(user_service_pb2.GetUserRequest(id=user_id))
```

---

## 3. Message Queue Integration

### RabbitMQ with aio-pika

```python
import aio_pika, json
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    app.state.mq_connection = connection
    channel = await connection.channel()
    exchange = await channel.declare_exchange("events", aio_pika.ExchangeType.TOPIC)
    queue = await channel.declare_queue("order_events", durable=True)
    await queue.bind(exchange, routing_key="order.*")
    await queue.consume(handle_order_event)
    yield
    await connection.close()

async def handle_order_event(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        await process_order_event(body)

@app.post("/orders/")
async def create_order(order: OrderCreate, request: Request):
    channel = await request.app.state.mq_connection.channel()
    exchange = await channel.get_exchange("events")
    await exchange.publish(
        aio_pika.Message(body=json.dumps({"order_id": "123"}).encode(),
                         delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key="order.created",
    )
    return {"status": "created"}
```

### Kafka with aiokafka

```python
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

producer = AIOKafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode(),
)

async def consume_events():
    consumer = AIOKafkaConsumer(
        "user-events", bootstrap_servers="localhost:9092",
        group_id="api-service",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await process_event(msg.value)
    finally:
        await consumer.stop()

@app.post("/users/")
async def create_user(user: UserCreate):
    new_user = await save_user(user)
    await producer.send("user-events",
                        value={"type": "user.created", "user_id": new_user.id},
                        key=str(new_user.id).encode())
    return new_user
```

---

## 4. CQRS Implementation

Separate your read and write models for different optimization strategies.

```python
# Write side — normalized, validates constraints
@dataclass
class CreateOrderCommand:
    user_id: int
    items: list[dict]

class OrderCommandHandler:
    def __init__(self, db: AsyncSession, event_bus: EventBus):
        self.db, self.event_bus = db, event_bus

    async def handle_create(self, cmd: CreateOrderCommand) -> int:
        order = Order(user_id=cmd.user_id, status="pending")
        self.db.add(order)
        for item in cmd.items:
            self.db.add(OrderItem(order=order, **item))
        await self.db.commit()
        await self.event_bus.publish(OrderCreatedEvent(
            order_id=order.id, user_id=cmd.user_id,
            total=sum(i["price"] * i["quantity"] for i in cmd.items)))
        return order.id

# Read side — denormalized, optimized for queries
class OrderQueryService:
    def __init__(self, read_db: AsyncSession):
        self.db = read_db

    async def get_order_summary(self, order_id: int) -> OrderSummary:
        result = await self.db.execute(
            select(OrderSummaryView).where(OrderSummaryView.order_id == order_id))
        return result.scalar_one()

# Projection — listens to events, updates read model
class OrderProjection:
    async def handle_order_created(self, event: OrderCreatedEvent):
        async with get_write_session() as db:
            db.add(OrderSummaryView(
                order_id=event.order_id, user_id=event.user_id,
                total=event.total, status="pending"))
            await db.commit()
```

---

## 5. API Gateway Patterns

### Reverse Proxy with Aggregation

```python
SERVICE_MAP = {
    "users": "http://user-service:8001",
    "orders": "http://order-service:8002",
}

@app.api_route("/api/{service}/{path:path}",
               methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(service: str, path: str, request: Request):
    base_url = SERVICE_MAP.get(service)
    if not base_url:
        raise HTTPException(404, f"Unknown service: {service}")
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method, url=f"{base_url}/{path}",
            content=await request.body(), params=request.query_params)
    return StreamingResponse(content=response.aiter_bytes(),
                             status_code=response.status_code)

@app.get("/dashboard/{user_id}")
async def user_dashboard(user_id: int):
    async with httpx.AsyncClient() as client:
        user_resp, orders_resp = await asyncio.gather(
            client.get(f"{SERVICE_MAP['users']}/users/{user_id}"),
            client.get(f"{SERVICE_MAP['orders']}/orders?user_id={user_id}&limit=5}"),
        )
    return {"user": user_resp.json(), "recent_orders": orders_resp.json()}
```

---

## 6. Webhook Delivery

Production-grade webhooks require retry logic, payload signing, and idempotency.

```python
import hashlib, hmac, json
from uuid import uuid4

WEBHOOK_SECRET = "whsec_your_secret_key"

class WebhookDelivery:
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    def sign_payload(self, payload: str, timestamp: str) -> str:
        message = f"{timestamp}.{payload}"
        return hmac.new(WEBHOOK_SECRET.encode(), message.encode(),
                        hashlib.sha256).hexdigest()

    async def deliver(self, url: str, event_type: str, data: dict) -> bool:
        delivery_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()
        payload = json.dumps({"event": event_type, "data": data})
        signature = self.sign_payload(payload, timestamp)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-ID": delivery_id,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": f"sha256={signature}",
        }
        for attempt in range(5):
            try:
                resp = await self.client.post(url, content=payload,
                                              headers=headers, timeout=10)
                if resp.status_code < 300:
                    return True
                if resp.status_code < 500:
                    return False  # Client error, don't retry
            except (httpx.TimeoutException, httpx.HTTPStatusError):
                await asyncio.sleep((2 ** attempt) + random.random() * 0.5)
        return False
```

### Verifying Webhooks (Receiver Side)

```python
async def verify_webhook_signature(
    request: Request,
    x_webhook_signature: str = Header(...),
    x_webhook_timestamp: str = Header(...),
):
    body = await request.body()
    expected = hmac.new(WEBHOOK_SECRET.encode(),
                        f"{x_webhook_timestamp}.{body.decode()}".encode(),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", x_webhook_signature):
        raise HTTPException(401, "Invalid webhook signature")
```

---

## 7. Real-Time Patterns Comparison

| Feature | WebSocket | SSE | Long Polling | Short Polling |
|---|---|---|---|---|
| **Direction** | Bidirectional | Server to client | Server to client | Client to server |
| **Protocol** | ws:// / wss:// | HTTP | HTTP | HTTP |
| **Reconnection** | Manual | Automatic | Manual | N/A |
| **Binary data** | Yes | No (text only) | Yes | Yes |
| **HTTP/2 compat** | No (separate conn) | Yes | Yes | Yes |
| **Sticky sessions** | Required | Standard | Standard | Standard |
| **Latency** | Lowest | Low | Medium | High |
| **Complexity** | Highest | Low | Medium | Lowest |

### Decision Framework

```
Need bidirectional communication?
  YES -> WebSocket
  NO  -> Need real-time (<1s latency)?
           YES -> SSE (text only) or WebSocket (binary)
           NO  -> Acceptable latency > 5s?
                    YES -> Short polling
                    NO  -> Long polling
```

### Production Considerations

1. **Scaling WebSockets:** Need sticky sessions or a pub/sub layer (Redis) for multi-instance.
   Each connection holds state in memory.

2. **Scaling SSE:** Easier than WebSocket — no bidirectional state. But each open connection
   still consumes a server resource. Use HTTP/2 for multiplexing.

3. **Hybrid approach:** Many production systems use SSE for real-time with polling fallback.
   WebSocket only for truly interactive features (collaborative editing, gaming, chat).
