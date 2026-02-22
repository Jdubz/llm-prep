# Module 04 Deep Dive: Building Production HTTP Services

## Building a Production-Ready HTTP Service from Scratch

This is the complete example — the kind of service you'd actually deploy. Every piece from the README comes together here.

### Project Layout

```
productionapi/
├── cmd/api/main.go
├── internal/
│   ├── config/config.go
│   ├── handler/health.go
│   ├── handler/user.go
│   ├── middleware/chain.go
│   ├── middleware/logging.go
│   ├── middleware/auth.go
│   ├── middleware/recovery.go
│   ├── middleware/requestid.go
│   └── server/server.go
└── go.mod
```

### The Server Package

```go
// internal/server/server.go
package server

import (
    "context"
    "fmt"
    "log/slog"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

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

        // Mark as not ready (for K8s readiness probe)
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

### The Middleware Chain

```go
// internal/middleware/chain.go
package middleware

import "net/http"

// Stack applies middleware in the order given.
// The first middleware in the list is the outermost (runs first).
func Stack(handler http.Handler, mw ...func(http.Handler) http.Handler) http.Handler {
    for i := len(mw) - 1; i >= 0; i-- {
        handler = mw[i](handler)
    }
    return handler
}
```

### Health Check Handler

```go
// internal/handler/health.go
package handler

import (
    "encoding/json"
    "net/http"
    "sync/atomic"
    "time"
)

type HealthHandler struct {
    ready     atomic.Bool
    startTime time.Time
    version   string
}

func NewHealthHandler(version string) *HealthHandler {
    return &HealthHandler{
        startTime: time.Now(),
        version:   version,
    }
}

func (h *HealthHandler) SetReady(ready bool) {
    h.ready.Store(ready)
}

// Liveness: is the process alive?
func (h *HealthHandler) LivenessHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]any{
        "status":  "alive",
        "version": h.version,
        "uptime":  time.Since(h.startTime).String(),
    })
}

// Readiness: can the service handle traffic?
func (h *HealthHandler) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")

    if !h.ready.Load() {
        w.WriteHeader(http.StatusServiceUnavailable)
        json.NewEncoder(w).Encode(map[string]string{"status": "not_ready"})
        return
    }

    json.NewEncoder(w).Encode(map[string]string{"status": "ready"})
}
```

### Wiring It All Together

```go
// cmd/api/main.go
package main

import (
    "log/slog"
    "os"
    "time"

    "myservice/internal/handler"
    "myservice/internal/middleware"
    "myservice/internal/server"
)

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))

    health := handler.NewHealthHandler("1.0.0")

    mux := http.NewServeMux()

    // Health endpoints — no auth required
    mux.HandleFunc("GET /healthz", health.LivenessHandler)
    mux.HandleFunc("GET /readyz", health.ReadinessHandler)

    // API routes
    mux.HandleFunc("GET /api/users/{id}", userHandler.GetUser)
    mux.HandleFunc("POST /api/users", userHandler.CreateUser)

    // Build middleware stack
    app := middleware.Stack(mux,
        middleware.Recovery(logger),
        middleware.RequestID,
        middleware.Logging(logger),
        middleware.CORS([]string{"https://example.com"}),
    )

    srv := server.New(server.Config{
        Host:            "0.0.0.0",
        Port:            8080,
        ReadTimeout:     5 * time.Second,
        WriteTimeout:    10 * time.Second,
        IdleTimeout:     120 * time.Second,
        ShutdownTimeout: 30 * time.Second,
    }, app, logger)

    // Mark as ready after all initialization
    health.SetReady(true)

    if err := srv.Run(); err != nil {
        logger.Error("server failed", "error", err)
        os.Exit(1)
    }
}
```

---

## gRPC Services in Go

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

// Stream interceptor
func streamLoggingInterceptor(
    srv interface{},
    ss grpc.ServerStream,
    info *grpc.StreamServerInfo,
    handler grpc.StreamHandler,
) error {
    start := time.Now()
    err := handler(srv, ss)
    slog.Info("grpc stream",
        "method", info.FullMethod,
        "duration", time.Since(start),
        "error", err,
    )
    return err
}
```

---

## WebSocket with gorilla/websocket

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

## Reverse Proxy Patterns

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

## HTTP Client Best Practices

### Connection Pooling

The default `http.Client` uses a global transport with connection pooling, but you should configure it explicitly:

```go
func newHTTPClient() *http.Client {
    transport := &http.Transport{
        MaxIdleConns:        100,              // Total idle connections
        MaxIdleConnsPerHost: 10,               // Per-host idle connections
        MaxConnsPerHost:     100,              // Total per-host connections
        IdleConnTimeout:     90 * time.Second, // How long idle connections live
        TLSHandshakeTimeout: 10 * time.Second,
        // Use DialContext for DNS caching/custom resolution
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

### Per-Request Timeouts with Context

```go
func fetchUser(ctx context.Context, client *http.Client, id int) (*User, error) {
    // Request-specific timeout (shorter than client timeout)
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, "GET",
        fmt.Sprintf("https://api.example.com/users/%d", id), nil)
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }

    req.Header.Set("Authorization", "Bearer "+getToken())

    resp, err := client.Do(req)
    if err != nil {
        return nil, fmt.Errorf("executing request: %w", err)
    }
    defer resp.Body.Close() // ALWAYS close the body

    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
        return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, body)
    }

    var user User
    if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
        return nil, fmt.Errorf("decoding response: %w", err)
    }

    return &user, nil
}
```

### Retry with Exponential Backoff

```go
func withRetry(ctx context.Context, maxRetries int, fn func() (*http.Response, error)) (*http.Response, error) {
    var lastErr error

    for attempt := 0; attempt <= maxRetries; attempt++ {
        if attempt > 0 {
            backoff := time.Duration(1<<uint(attempt-1)) * 100 * time.Millisecond
            // Add jitter: 50-150% of backoff
            jitter := time.Duration(rand.Int63n(int64(backoff)))
            backoff = backoff/2 + jitter

            select {
            case <-ctx.Done():
                return nil, ctx.Err()
            case <-time.After(backoff):
            }
        }

        resp, err := fn()
        if err != nil {
            lastErr = err
            continue
        }

        // Only retry on 5xx or 429
        if resp.StatusCode >= 500 || resp.StatusCode == 429 {
            resp.Body.Close()
            lastErr = fmt.Errorf("status %d", resp.StatusCode)
            continue
        }

        return resp, nil
    }

    return nil, fmt.Errorf("max retries exceeded: %w", lastErr)
}
```

### OpenAPI Generation with swaggo

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

This generates an OpenAPI 2.0 (Swagger) spec from your Go code annotations. It's not as seamless as TypeScript's ts-rest or zodios, but it works well for documentation.
