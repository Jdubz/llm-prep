# 01 – Goroutines and Channels

## The Fundamental Mental Model Shift

In TypeScript/Node, concurrency is cooperative. One thread, one event loop. You write `async/await` and the runtime interleaves your I/O operations on a single thread. You cannot do two CPU-bound things at the same time.

In Go, concurrency is preemptive and parallel. Goroutines are multiplexed onto multiple OS threads. You can do two CPU-bound things at the same time. The scheduler can pause your goroutine at any point and run another.

```typescript
// TypeScript — single thread, cooperative concurrency
async function fetchBoth() {
  const [a, b] = await Promise.all([fetchA(), fetchB()]);
  return { a, b };
}
```

```go
// Go — multiple threads, preemptive concurrency
func fetchBoth(ctx context.Context) (A, B, error) {
    var a A
    var b B
    var errA, errB error

    var wg sync.WaitGroup
    wg.Add(2)

    go func() {
        defer wg.Done()
        a, errA = fetchA(ctx)
    }()

    go func() {
        defer wg.Done()
        b, errB = fetchB(ctx)
    }()

    wg.Wait()

    if errA != nil {
        return a, b, errA
    }
    return a, b, errB
}
```

---

## 1. Goroutines

### What They Are

A goroutine is a lightweight thread of execution managed by the Go runtime, not the OS. Starting a goroutine costs roughly 2-8 KB of stack memory. You can run millions of them.

```go
go doSomething()         // fire and forget
go func() {              // anonymous goroutine
    fmt.Println("hello")
}()
```

### Goroutine Lifecycle

A goroutine runs until:
1. Its function returns.
2. The program exits (`main` returns, and all goroutines are killed — no graceful shutdown by default).
3. A `runtime.Goexit()` is called (rare).

**Critical gotcha:** When `main()` returns, all goroutines are killed immediately. There is no equivalent of Node's "keep alive until the event loop is empty."

```go
func main() {
    go func() {
        time.Sleep(time.Second)
        fmt.Println("this may never print")
    }()
    // main returns immediately, goroutine is killed
}
```

### Goroutines vs Threads vs async/await

| Property | OS Thread | Goroutine | Node async |
|----------|-----------|-----------|-----------|
| Stack size | ~1 MB fixed | ~2-8 KB, grows dynamically | Shared heap |
| Creation cost | Expensive (syscall) | Cheap (~1 us) | Cheap (closure) |
| Scheduling | OS kernel | Go runtime | Event loop |
| Parallelism | Yes | Yes | No (single thread) |
| Communication | Shared memory + locks | Channels (preferred) or shared memory | Callbacks/promises |
| Count limit | ~thousands | ~millions | ~millions |

### Common Goroutine Mistakes

```go
// BUG: loop variable capture
for _, item := range items {
    go func() {
        process(item) // All goroutines see the SAME item (the last one)
    }()
}

// FIX (Go < 1.22): pass as argument
for _, item := range items {
    go func(it Item) {
        process(it)
    }(item)
}

// FIX (Go 1.22+): loop variables are per-iteration by default
for _, item := range items {
    go func() {
        process(item) // Safe in Go 1.22+
    }()
}
```

---

## 2. Channels

Channels are Go's primary mechanism for goroutine communication. The Go proverb: "Don't communicate by sharing memory; share memory by communicating."

### Unbuffered Channels

An unbuffered channel has no capacity. A send blocks until a receiver is ready. A receive blocks until a sender is ready. They synchronize goroutines.

```go
ch := make(chan string) // unbuffered

go func() {
    ch <- "hello" // blocks until someone receives
}()

msg := <-ch // blocks until someone sends
fmt.Println(msg) // "hello"
```

Think of an unbuffered channel as a handshake: both parties must be present.

### Buffered Channels

A buffered channel has capacity. Sends block only when the buffer is full. Receives block only when the buffer is empty.

```go
ch := make(chan string, 3) // buffer of 3

ch <- "a" // does not block
ch <- "b" // does not block
ch <- "c" // does not block
ch <- "d" // BLOCKS — buffer is full

msg := <-ch // "a" — FIFO order
```

Use buffered channels when:
- The producer and consumer run at different speeds.
- You want to decouple the sender from the receiver.
- You are implementing a semaphore (buffered channel as a concurrency limiter).

### Directional Channels

You can restrict a channel to send-only or receive-only:

```go
func producer(out chan<- string) { // can only send
    out <- "data"
}

func consumer(in <-chan string) { // can only receive
    msg := <-in
    fmt.Println(msg)
}
```

This is enforced at compile time. Use it in function signatures to communicate intent and prevent misuse.

### Closing Channels

Only the sender should close a channel. Closing signals "no more values."

```go
ch := make(chan int)

go func() {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch) // signal: no more values
}()

for v := range ch { // range exits when channel is closed
    fmt.Println(v)
}
```

Rules:
- Sending on a closed channel **panics**.
- Receiving from a closed channel returns the zero value immediately.
- Closing a nil channel **panics**.
- Closing an already-closed channel **panics**.
- You can check if a channel is closed: `val, ok := <-ch` — `ok` is `false` when closed and drained.

### Channel Operations Behavior Table

| Operation | nil channel | Closed channel | Open (not full/empty) | Open (full/empty) |
|-----------|-------------|----------------|----------------------|-------------------|
| **Send** `ch <- v` | Block forever | **PANIC** | Send value | Block until space |
| **Receive** `<-ch` | Block forever | Zero value, `ok=false` | Receive value | Block until value |
| **Close** `close(ch)` | **PANIC** | **PANIC** | Close (receivers get remaining then zero) | Close |
| **Len** `len(ch)` | 0 | Buffered items remaining | Buffered items | 0 |
| **Cap** `cap(ch)` | 0 | Buffer capacity | Buffer capacity | Buffer capacity |

### Nil Channel Behavior

A nil channel blocks forever on both send and receive. This is useful in select statements for dynamically enabling/disabling cases:

```go
var ch1, ch2 <-chan int
ch1 = getChannel1()
// ch2 is nil — its select case will never fire

for {
    select {
    case v := <-ch1:
        fmt.Println("from ch1:", v)
    case v := <-ch2: // never selected because ch2 is nil
        fmt.Println("from ch2:", v)
    }
}
```

---

## 3. The select Statement

`select` multiplexes channel operations. It is Go's equivalent of `Promise.race` but more powerful.

### Basic Usage

```go
select {
case msg := <-ch1:
    fmt.Println("received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("received from ch2:", msg)
case ch3 <- "hello":
    fmt.Println("sent to ch3")
}
```

If multiple cases are ready, one is chosen at random (uniformly). This prevents starvation.

### Timeout with time.After

```go
select {
case result := <-ch:
    fmt.Println("got result:", result)
case <-time.After(5 * time.Second):
    fmt.Println("timed out")
}
```

**TS equivalent:**

```typescript
const result = await Promise.race([
  fetchData(),
  new Promise((_, reject) => setTimeout(() => reject("timeout"), 5000)),
]);
```

### Default Case for Non-Blocking Operations

```go
select {
case msg := <-ch:
    fmt.Println("got:", msg)
default:
    fmt.Println("no message available, moving on")
}
```

The `default` case makes the select non-blocking. Without it, `select` blocks until a case is ready.

### Done Channel Pattern

```go
func worker(done <-chan struct{}, tasks <-chan Task) {
    for {
        select {
        case <-done:
            fmt.Println("shutting down")
            return
        case task := <-tasks:
            process(task)
        }
    }
}

// Signal shutdown by closing the done channel
done := make(chan struct{})
close(done) // all workers see this immediately
```

Closing a channel broadcasts to all receivers. This is why `chan struct{}` is used for signaling — it carries no data, only the signal.
