# APILens SDKs

Official client libraries for sending telemetry data to APILens.

## Available SDKs

| Language | Status | Documentation |
|----------|--------|---------------|
| [Python](./python/) | ✅ Available | [README](./python/README.md) |
| Node.js/TypeScript | 🚧 Planned | — |
| Go | 🚧 Planned | — |

## Python SDK

```bash
pip install apilens
```

```python
from apilens import APILensClient

client = APILensClient(api_key="your-api-key", service_name="my-service")

# Metrics
client.metric("api.requests", 1, tags={"endpoint": "/users"})

# Logs
client.info("Request processed", user_id="123")

# Traces
with client.span("handle_request") as span:
    span.set_attribute("http.method", "GET")
    # ... your code ...

# Events
client.event("user", "signup", payload={"plan": "pro"})
```

See [Python SDK documentation](./python/README.md) for full details.

## Contributing

Want to build an SDK for another language? See the [contribution guide](../README.md#contributing)