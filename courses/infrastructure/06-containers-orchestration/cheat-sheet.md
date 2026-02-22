# Module 06 Cheat Sheet: Containers & Orchestration

---

## Dockerfile Best Practices

- [ ] Multi-stage builds (separate build/runtime)
- [ ] Pin base image versions (`node:20.11-alpine`, not `latest`)
- [ ] Order: least to most frequently changing layers
- [ ] `npm ci` not `npm install`; `--mount=type=cache` for caches
- [ ] Non-root user (`USER appuser`)
- [ ] Distroless or alpine for production
- [ ] Never `COPY` secrets; use `--mount=type=secret`
- [ ] Scan with Trivy/Snyk in CI; fail on CRITICAL

---

## kubectl Essential Commands

```bash
# Viewing
kubectl get pods -n production -o wide
kubectl get events --sort-by=.lastTimestamp
kubectl top pods -n production

# Inspecting
kubectl describe pod <name>
kubectl logs <pod> -c <container> --previous
kubectl get pod <name> -o yaml

# Debugging
kubectl exec -it <pod> -- /bin/sh
kubectl debug -it <pod> --image=busybox
kubectl port-forward svc/api-server 8080:80
kubectl run tmp --image=busybox --rm -it -- sh

# Rollouts
kubectl rollout status deployment/api-server
kubectl rollout undo deployment/api-server
kubectl rollout undo deployment/api-server --to-revision=3
kubectl rollout restart deployment/api-server
```

---

## K8s Resource Templates

### Deployment (minimal production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
spec:
  replicas: 3
  selector:
    matchLabels: { app: api-server }
  strategy:
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  template:
    metadata:
      labels: { app: api-server }
    spec:
      containers:
        - name: api
          image: myregistry/api-server:v1.0.0
          ports: [{ containerPort: 8080 }]
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { memory: 512Mi }
          readinessProbe:
            httpGet: { path: /readyz, port: 8080 }
          livenessProbe:
            httpGet: { path: /healthz, port: 8080 }
```

### Service + Ingress + HPA

```yaml
# Service
apiVersion: v1
kind: Service
spec:
  type: ClusterIP
  selector: { app: api-server }
  ports: [{ port: 80, targetPort: 8080 }]
---
# Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
spec:
  ingressClassName: nginx
  tls: [{ hosts: [api.example.com], secretName: api-tls }]
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: api-server, port: { number: 80 } }
---
# HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api-server }
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

---

## Helm Commands

```bash
helm install my-release ./mychart -f values-prod.yaml
helm upgrade --install my-release ./mychart -f values-prod.yaml
helm template my-release ./mychart -f values.yaml   # Dry-run render
helm rollback my-release 2
helm list -A
```

---

## Resource Sizing Guide

| Workload | CPU Request | Mem Request | Mem Limit |
|---|---|---|---|
| Light API (Node/Go) | 100-250m | 128-256Mi | 512Mi |
| Heavy API (Java) | 500-1000m | 512Mi-1Gi | 2Gi |
| Worker | 250-500m | 256-512Mi | 1Gi |
| Database | 1-4 cores | 2-8Gi | 8-16Gi |
| Cache (Redis) | 250-500m | 1-4Gi | = request |

**Process:** Deploy generous -> load test -> VPA recommend mode (3-7 days) -> set requests=P95, memory limit=2x request -> consider no CPU limit -> iterate.

---

## Debugging Checklist

**Pod not starting:**
`describe pod` -> ImagePullBackOff (wrong image)? Pending (no capacity)? ConfigError (missing Secret)?

**Pod crashing:**
`logs --previous` -> OOMKilled (increase limit)? Probe too aggressive? Missing dependency?

**Service unreachable:**
`get endpoints` -> no endpoints (label mismatch)? Pod not ready (probe failing)? NetworkPolicy blocking? Port mismatch (`targetPort` != `containerPort`)?

**Performance:**
`top pods` -> CPU throttled? OOMKilled? Slow DNS (check CoreDNS, `ndots`)? HPA not scaling (check metrics-server)?
