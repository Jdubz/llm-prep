# 03 – Advanced HTTP Patterns

This file assumes you have read `01-handlers-routing-and-middleware.md` and `02-request-handling-and-validation.md`. It covers graceful shutdown, connection pooling, rate limiting internals, CORS, WebSockets, gRPC, reverse proxies, and interview Q&A.

---

## 1. Graceful Shutdown

This is a critical production concern. You need to stop accepting new connections while letting in-flight requests finish.

### Full Graceful Shutdown Pattern

```go
func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

    srv := &http.Server{
        Addr:         ":8080",
        Handler:      setupRoutes(logger),
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    // Channel to listen for errors from the server
    serverErrors := make(chan error, 1)

    // Start server in a goroutine
    go func() {
        logger.Info("server starting", "addr", srv.Addr)
        serverErrors <- srv.ListenAndServe()
    }()

    // Channel to listen for OS signals
    shutdown := make(chan os.Signal, 1)
    signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

    // Block until we receive a signal or server error
    select {
    case err := <-serverErrors:
        logger.Error("server error", "error", err)

    case sig := <-shutdown:
        logger.Info("shutdown signal received", "signal", sig)

        // Give outstanding requests a deadline to complete
        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()

        // Shutdown gracefully: stop accepting new connections,
        // wait for in-flight requests to complete.
        if err := srv.Shutdown(ctx); err != nil {
            logger.Error("graceful shutdown failed", "error", err)

            // Force close if graceful shutdown fails
            if err := srv.Close(); err != nil {
                logger.Error("forced close failed", "error", err)
            }
        }

        logger.Info("server stopped")
    }
}
```

### Graceful Shutdown Template (condensed)

```go
srv := &http.Server{
    Addr:         ":8080",
    Handler:      handler,
    ReadTimeout:  5 * time.Second,
    WriteTimeout: 10 * time.Second,
    IdleTimeout:  120 * time.Second,
}

go func() { serverErr <- srv.ListenAndServe() }()

quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
<-quit

ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()
srv.Shutdown(ctx)
```

### How Shutdown Works

1. `signal.Notify` registers to receive SIGINT (Ctrl+C) and SIGTERM (Docker/K8s stop).
2. `srv.Shutdown(ctx)` does three things:
   - Closes all listeners (stops accepting new connections).
   - Closes idle connections immediately.
   - Waits for active connections to finish (up to context deadline).
3. If the context times out, `Shutdown` returns an error. You can then call `Close()` to force-kill remaining connections.

### Connection Draining with Health Checks

In Kubernetes, you need to signal readiness before the pod terminates:

```go
type healthChecker struct {
    mu    sync.RWMutex
    ready bool
}

func (h *healthChecker) SetReady(ready bool) {
    h.mu.Lock()
    defer h.mu.Unlock()
    h.ready = ready
}

func (h *healthChecker) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
    h.mu.RLock()
    defer h.mu.RUnlock()

    if !h.ready {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte(`{"status":"not_ready"}`))
        return
    }
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ready"}`))
}

// In main():
// 1. Set ready=true after all initialization completes
// 2. Set ready=false BEFORE calling srv.Shutdown()
// 3. Sleep briefly to let load balancer detect the change
```

### The Server Package (Production Pattern)

```go
// internal/server/server.go
package server

type Server struct {
    httpServer *http.Server
    logger     *slog.Logger
}

type Config struct {
    Host            string
    Port            int
    ReadTimeout     time.Duration
    WriteTimeout    time.Duration
    IdleTimeout     time.Duration
    ShutdownTimeout time.Duration
}

func New(cfg Config, handler http.Handler, logger *slog.Logger) *Server {
    return &Server{
        httpServer: &http.Server{
            Addr:         fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
            Handler:      handler,
            ReadTimeout:  cfg.ReadTimeout,
            WriteTimeout: cfg.WriteTimeout,
            IdleTimeout:  cfg.IdleTimeout,
            ErrorLog:     slog.NewLogLogger(logger.Handler(), slog.LevelError),
        },
        logger: logger,
    }
}

// Run starts the server and blocks until shutdown is complete.
func (s *Server) Run() error {
    serverErrors := make(chan error, 1)

    go func() {
        s.logger.Info("server starting", "addr", s.httpServer.Addr)
        serverErrors <- s.httpServer.ListenAndServe()
    }()

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

    select {
    case err := <-serverErrors:
        if err != http.ErrServerClosed {
            return fmt.Errorf("server error: %w", err)
        }

    case sig := <-quit:
        s.logger.Info("shutdown signal received", "signal", sig)

        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()

        s.logger.Info("draining connections")

        if err := s.httpServer.Shutdown(ctx); err != nil {
            s.logger.Error("graceful shutdown failed, forcing close", "error", err)
            _ = s.httpServer.Close()
            return fmt.Errorf("shutdown: %w", err)
        }
    }

    s.logger.Info("server stopped cleanly")
    return nil
}
```

---

## 2. Connection Pooling

### HTTP Client Connection Pooling

The default `http.Client` uses a global transport with connection pooling, but you should configure it explicitly:

```go
func newHTTPClient() *http.Client {
    transport := &http.Transport{
        MaxIdleConns:        100,              // Total idle connections
        MaxIdleConnsPerHost: 10,               // Per-host idle connections
        MaxConnsPerHost:     100,              // Total per-host connections
        IdleConnTimeout:     90 * time.Second, // How long idle connections live
        TLSHandshakeTimeout: 10 * time.Second,
        DialContext: (&net.Dialer{
            Timeout:   30 * time.Second,
            KeepAlive: 30 * time.Second,
        }).DialContext,
    }

    return &http.Client{
        Transport: transport,
        Timeout:   30 * time.Second, // Overall request timeout
    }
}
```

**Critical rule**: Never use the zero-value `http.Client{}` in production — it has no timeout, meaning requests can hang forever.

---

## 3. CORS

```go
func corsMiddleware(allowedOrigins []string) func(http.Handler) http.Handler {
    allowed := make(map[string]bool)
    for _, o := range allowedOrigins {
        allowed[o] = true
    }

    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            origin := r.Header.Get("Origin")
            if allowed[origin] || allowed["*"] {
                w.Header().Set("Access-Control-Allow-Origin", origin)
                w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
                w.Header().Set("Access-Control-Max-Age", "86400")
            }

            // Handle preflight
            if r.Method == http.MethodOptions {
                w.WriteHeader(http.StatusNoContent)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}
```

---

## 4. WebSockets

```go
var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
    CheckOrigin: func(r *http.Request) bool {
        origin := r.Header.Get("Origin")
        return origin == "https://example.com"
    },
}

type Hub struct {
    clients    map[*Client]bool
    broadcast  chan []byte
    register   chan *Client
    unregister chan *Client
    mu         sync.RWMutex
}

type Client struct {
    hub  *Hub
    conn *websocket.Conn
    send chan []byte
}

func (h *Hub) Run() {
    for {
        select {
        case client := <-h.register:
            h.mu.Lock()
            h.clients[client] = true
            h.mu.Unlock()

        case client := <-h.unregister:
            h.mu.Lock()
            if _, ok := h.clients[client]; ok {
                delete(h.clients, client)
                close(client.send)
            }
            h.mu.Unlock()

        case message := <-h.broadcast:
            h.mu.RLock()
            for client := range h.clients {
                select {
                case client.send <- message:
                default:
                    close(client.send)
                    delete(h.clients, client)
                }
            }
            h.mu.RUnlock()
        }
    }
}

func serveWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        slog.Error("websocket upgrade failed", "error", err)
        return
    }

    client := &Client{hub: hub, conn: conn, send: make(chan []byte, 256)}
    hub.register <- client

    // Start read/write pumps in separate goroutines
    go client.writePump()
    go client.readPump()
}
```

---

## 5. gRPC Services in Go

### Why gRPC?

If you've used tRPC in TypeScript, gRPC fills a similar niche — typed RPC with code generation. But gRPC uses Protocol Buffers (protobuf) for serialization and HTTP/2 for transport, making it language-agnostic and very fast.

### Protocol Buffer Definition

```protobuf
// proto/user/v1/user.proto
syntax = "proto3";

package user.v1;

option go_package = "myservice/gen/user/v1;userv1";

message User {
    int64 id = 1;
    string email = 2;
    string name = 3;
    google.protobuf.Timestamp created_at = 4;
}

message GetUserRequest {
    int64 id = 1;
}

message ListUsersRequest {
    int32 page_size = 1;
    string page_token = 2;
}

message ListUsersResponse {
    repeated User users = 1;
    string next_page_token = 2;
}

service UserService {
    rpc GetUser(GetUserRequest) returns (User);
    rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
    rpc WatchUser(GetUserRequest) returns (stream User); // Server streaming
}
```

### Code Generation

```bash
# Install tools
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Generate Go code
protoc --go_out=. --go-grpc_out=. proto/user/v1/user.proto
```

### Implementing the Server

```go
type userServer struct {
    userv1.UnimplementedUserServiceServer // Embed for forward compatibility
    repo UserRepository
}

func (s *userServer) GetUser(ctx context.Context, req *userv1.GetUserRequest) (*userv1.User, error) {
    user, err := s.repo.GetByID(ctx, req.Id)
    if err != nil {
        if errors.Is(err, ErrNotFound) {
            return nil, status.Error(codes.NotFound, "user not found")
        }
        return nil, status.Error(codes.Internal, "internal error")
    }
    return toProto(user), nil
}

// Server streaming
func (s *userServer) WatchUser(req *userv1.GetUserRequest, stream userv1.UserService_WatchUserServer) error {
    for {
        select {
        case <-stream.Context().Done():
            return nil
        case update := <-s.watchChan(req.Id):
            if err := stream.Send(toProto(update)); err != nil {
                return err
            }
        }
    }
}

func main() {
    lis, _ := net.Listen("tcp", ":9090")
    grpcServer := grpc.NewServer(
        grpc.UnaryInterceptor(loggingInterceptor),
    )
    userv1.RegisterUserServiceServer(grpcServer, &userServer{})
    grpcServer.Serve(lis)
}
```

### gRPC Interceptors (Middleware)

```go
// Unary interceptor — equivalent to HTTP middleware
func loggingInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    start := time.Now()
    resp, err := handler(ctx, req)
    slog.Info("grpc call",
        "method", info.FullMethod,
        "duration", time.Since(start),
        "error", err,
    )
    return resp, err
}
```

---

## 6. Reverse Proxy Patterns

Go's `httputil.ReverseProxy` is production-quality and used in major infrastructure projects.

```go
func newAPIGateway(backends map[string]*url.URL) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Route based on path prefix
        var target *url.URL
        switch {
        case strings.HasPrefix(r.URL.Path, "/api/users"):
            target = backends["users"]
        case strings.HasPrefix(r.URL.Path, "/api/orders"):
            target = backends["orders"]
        default:
            http.NotFound(w, r)
            return
        }

        proxy := &httputil.ReverseProxy{
            Director: func(req *http.Request) {
                req.URL.Scheme = target.Scheme
                req.URL.Host = target.Host
                req.Host = target.Host
            },
            ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
                slog.Error("proxy error", "error", err, "target", target)
                http.Error(w, "service unavailable", http.StatusBadGateway)
            },
            ModifyResponse: func(resp *http.Response) error {
                resp.Header.Set("X-Proxy", "api-gateway")
                return nil
            },
        }

        proxy.ServeHTTP(w, r)
    })
}
```

---

## 7. OpenAPI Generation with swaggo

```go
// Install: go install github.com/swaggo/swag/cmd/swag@latest

// Add annotations to handlers
// @Summary      Get user by ID
// @Description  Retrieve a user by their unique identifier
// @Tags         users
// @Accept       json
// @Produce      json
// @Param        id   path      int  true  "User ID"
// @Success      200  {object}  model.User
// @Failure      404  {object}  APIError
// @Router       /api/users/{id} [get]
func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    // ...
}

// Generate: swag init -g cmd/api/main.go
// Serve:    mux.Handle("/swagger/", httpSwagger.WrapHandler)
```

---

## 8. Interview Questions

### Conceptual

1. **Explain the `http.Handler` interface and why it's the foundation of Go's HTTP ecosystem.**
   A single-method interface (`ServeHTTP(ResponseWriter, *Request)`) that every handler and middleware implements. Its simplicity enables universal composability — any middleware from any library works with any handler. The `HandlerFunc` adapter allows plain functions to satisfy the interface.

2. **How does Go's middleware pattern differ from Express middleware?**
   Express uses `(req, res, next)` where `next()` is called explicitly. Go uses `func(http.Handler) http.Handler` — a wrapper function that receives the next handler and returns a new handler. There's no `next()` function; you call `next.ServeHTTP(w, r)`. If you don't call it, the chain stops. This is more explicit and less error-prone (no forgotten `next()` calls).

3. **What happens if you write to `ResponseWriter` after calling `WriteHeader`?**
   The status code is already sent. Calling `WriteHeader` again is a no-op (logged as a superfluous call). Calling `Write` without `WriteHeader` first implicitly sends 200. Headers set after `Write` or `WriteHeader` are ignored because they've already been flushed to the network.

4. **How does `http.Server.Shutdown` achieve graceful shutdown?**
   It closes all listeners (stops new connections), closes idle connections immediately, then waits for active requests to complete. If the provided context expires before all requests finish, it returns `context.DeadlineExceeded`. It does NOT forcibly close active connections — you need `Close()` for that.

5. **When would you choose Chi over the Go 1.22+ stdlib router?**
   When you need route groups (applying middleware to a subset of routes), a rich middleware library, URL generation from named routes, or mounting sub-routers. Chi maintains full `net/http` compatibility while adding these features. The stdlib is sufficient for simple services with flat route structures.

6. **Explain the `http.Transport` and why it matters for production HTTP clients.**
   Transport manages connection pooling, TLS, keep-alives, and timeouts. The default transport works but has conservative limits. In production, configure `MaxIdleConnsPerHost` to match your expected concurrency, `IdleConnTimeout` to release unused connections, and always set a `Timeout` on the client.

### Coding Challenges

7. **Write a middleware that adds a timeout to every request and logs if the timeout is exceeded.**

8. **Implement a rate limiter middleware that uses a sliding window per API key (from header) rather than per IP.**

9. **Design an error-handling middleware that catches panics, logs the stack trace, and returns a structured JSON error response.**

10. **Build a handler that accepts a multipart file upload, validates the file type (only images), resizes it, and stores it — using proper error handling throughout.**

### Architecture

11. **You're designing a REST API with 50+ endpoints across multiple resource types. How do you structure the project? How do you organize routes, handlers, and middleware?**
    Use the cmd/internal layout. Group handlers by resource in internal/handler/. Use route groups (Chi or custom) to apply shared middleware (auth) to protected routes. Keep business logic in internal/service/ — handlers should only handle HTTP concerns (parsing, validation, serialization). Use interfaces for repository layer to enable testing.

12. **How would you implement request-scoped logging where every log line includes the request ID, user ID, and trace ID?**
    Inject these values into the context via middleware. Create a helper that extracts them and returns a logger with those fields pre-set: `func LoggerFromContext(ctx context.Context) *slog.Logger`. Every service method receives `ctx` and uses this helper.

13. **Compare deploying a Go HTTP service vs a Node.js Express service. What operational differences matter?**
    Go compiles to a single static binary — no node_modules, no runtime. Docker images can use `scratch` or `distroless` (10-20 MB vs 100+ MB for Node). Go handles concurrency with goroutines (cheap, thousands per service) vs Node's single-threaded event loop. Go services typically use less memory. Go's stdlib HTTP server is production-ready; Node needs reverse proxies or process managers.

14. **When would you use gRPC instead of REST?**
    gRPC when: service-to-service communication (not browser clients), bidirectional streaming is needed, strong contract enforcement matters, payload efficiency is critical (protobuf vs JSON). REST when: browser clients, public APIs, team is unfamiliar with protobuf, simpler tooling is preferred.

---

## Related Reading

- **Concurrency for graceful shutdown** — [Module 02: Synchronization and Context](../02-concurrency/02-synchronization-and-context.md), section 4 (Graceful Shutdown) covers the `signal.NotifyContext` and context cancellation that powers the shutdown pattern in section 1
- **Data storage integration** — [Module 05: Database Drivers and ORMs](../05-data-storage/01-database-drivers-and-orms.md) covers the database drivers (pgx, sqlc) that HTTP services connect to through the patterns established in this module
- **HTTP testing** — [Module 06: Integration and HTTP Testing](../06-testing/02-integration-and-http-testing.md) covers testing the full HTTP stack from this module, including `httptest.NewServer` for integration tests with middleware
- **Deployment** — [Module 07: Deployment and Scaling](../07-production/03-deployment-and-scaling.md), section 1 (Docker Multi-Stage Builds) shows how to containerize the HTTP services built in this module
- **Rate limiting concurrency** — [Module 02: Advanced Concurrency Patterns](../02-concurrency/03-advanced-concurrency-patterns.md), section 5 (Bounded Concurrency) provides the underlying patterns for the rate limiter middleware in section 3

---

## Practice Suggestions

These exercises reinforce the HTTP service concepts from this module (Handlers, Routing, and Middleware through Advanced HTTP Patterns):

1. **Build a complete REST API** — Using only `net/http` (Go 1.22+ ServeMux), build a CRUD API with proper middleware (logging, request ID, CORS, panic recovery). Implement structured JSON error responses with error codes. Test every handler with `httptest.NewRecorder`.

2. **Middleware chain** — Implement three custom middleware functions: (a) request timing that adds `X-Response-Time` header, (b) basic auth that checks credentials from a config, (c) request body size limiter. Chain them together and write tests for each in isolation and combined.

3. **Graceful shutdown** — Build an HTTP server that accepts long-running requests (simulate with `time.Sleep`). Implement graceful shutdown that waits for in-flight requests to complete within a timeout. Test by sending a request, triggering shutdown, and verifying the request completes.

4. **WebSocket echo server** — Using `nhooyr.io/websocket`, build a WebSocket echo server with a ping/pong heartbeat. Write a test client that connects, sends messages, and verifies responses. Add a timeout that disconnects idle clients.

5. **Reverse proxy with load balancing** — Using `httputil.ReverseProxy`, build a simple load balancer that distributes requests across multiple backend servers. Use `httptest.NewServer` to create test backends. Implement health checking and automatic backend removal.

6. **Rate limiter middleware** — Implement a per-IP rate limiter using a token bucket algorithm. Store buckets in a `sync.Map` with periodic cleanup of stale entries. Write a benchmark to verify performance under concurrent load.
