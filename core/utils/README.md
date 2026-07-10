# Utils

Shared utility functions used across the platform. Organized by domain: datetime formatting, HTTP request helpers, and security primitives.

For validators, see [core/validators/](../validators/README.md).

## API

### formatting.py

Pure formatting/serialization of values into strings. Date, time, and number display helpers. No I/O, no side effects.

- `format_datetime(dt, format_string="%Y-%m-%d %H:%M:%S")` — format a datetime to string
- `format_date(dt, format_string="%Y-%m-%d")` — format the date portion
- `format_time(dt, format_string="%H:%M:%S")` — format the time portion

```python
from datetime import datetime
from core.utils.formatting import format_datetime, format_date, format_time

now = datetime.now()

format_datetime(now)                        # "2025-01-15 14:30:00"
format_datetime(now, "%d/%m/%Y %H:%M")     # "15/01/2025 14:30"

format_date(now)                            # "2025-01-15"
format_date(now, "%d %b %Y")               # "15 Jan 2025"

format_time(now)                            # "14:30:00"
format_time(now, "%H:%M")                   # "14:30"
```

### request.py

Extracting metadata from Django/DRF `Request` objects — client IP, normalized body, headers.

- `get_client_ip(request)` — extract the client IP address (uses `django-ipware`)
- `get_request_data(request)` — normalize request body across content types into a dict

```python
from core.utils.request import get_client_ip, get_request_data

# In a view
ip = get_client_ip(request)  # "192.168.1.100" or "" if unresolvable

# Normalize body regardless of content type (JSON, form-data, urlencoded)
data = get_request_data(request)  # {"email": "user@example.com", ...}
```

### security.py

Cryptographic and security-related operations — password validation, key/token generation, data masking.

- `validate_password_complexity(password, config=None)` — validate password against configurable rules; returns `{is_valid, errors}`
- `generate_api_key(length=32)` — generate a cryptographically secure alphanumeric key
- `mask_sensitive_data(data, visible_chars=4, mask_char="*")` — mask a string keeping first/last N characters visible

```python
from core.utils.security import (
    validate_password_complexity,
    generate_api_key,
    mask_sensitive_data,
)

# Password validation with default rules
result = validate_password_complexity("weak")
# {"is_valid": False, "errors": ["Password must be at least 8 characters long.", ...]}

# Password validation with custom config
result = validate_password_complexity("MyP@ss123", config={
    "min_length": 10,
    "forbidden_words": ["pass", "admin"],
})
# {"is_valid": False, "errors": ["Password must be at least 10 characters long.", "Password cannot contain the word 'pass'."]}

# Generate API key
key = generate_api_key()      # "aB3kF9mNpQ2xR7wL..."  (32 chars)
key = generate_api_key(64)    # 64-char key

# Mask sensitive data
mask_sensitive_data("1234567890")        # "1234**7890"
mask_sensitive_data("secret", 2, "#")    # "se##et"
```

