# Utils

Shared utility functions used across the platform. Organized by domain: datetime formatting, HTTP request helpers, security primitives, and reusable validators.

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

### validators.py

Reusable validation logic — both deconstructible classes (for model fields) and standalone functions (uniqueness checks, file size, date ranges, JSON parsing).

#### Validator classes

- `UsernameValidator` — alphanumeric + underscores, 3–30 chars (deconstructible, usable on model fields)
- `PhoneNumberValidator` — 10–15 digits after stripping formatting
- `EmailDomainValidator(allowed_domains)` — restrict email to a whitelist of domains

```python
from core.utils.validators import (
    UsernameValidator,
    PhoneNumberValidator,
    EmailDomainValidator,
)

# UsernameValidator — use on model fields or call directly
validate_username = UsernameValidator()
validate_username("john_doe")    # OK
validate_username("ab")          # raises ValidationError (too short)
validate_username("no spaces!")  # raises ValidationError (invalid chars)

# PhoneNumberValidator
validate_phone = PhoneNumberValidator()
validate_phone("+1 (555) 123-4567")  # OK (stripped to 15551234567)
validate_phone("123")                # raises ValidationError (too few digits)

# EmailDomainValidator
validate_domain = EmailDomainValidator(["company.com", "corp.io"])
validate_domain("user@company.com")  # OK
validate_domain("user@gmail.com")    # raises ValidationError
```

#### Utility functions

- `validate_email_uniqueness(email, model_class, exclude_id=None)` — case-insensitive uniqueness check
- `validate_unique_slug(value, model_class, field_name="slug", exclude_id=None)` — slug uniqueness check
- `validate_file_size(file, max_size_mb=10)` — file size limit check
- `validate_date_range(start_date, end_date, max_days=365)` — date range validation; returns `{is_valid, errors}`
- `validate_json_field(value, schema=None)` — JSON parsing + optional JSON Schema validation; returns `{is_valid, errors, data}`

```python
from core.utils.validators import (
    validate_email_uniqueness,
    validate_unique_slug,
    validate_file_size,
    validate_date_range,
    validate_json_field,
)
from apps.users.models import User
from datetime import date

# Email uniqueness (case-insensitive)
is_unique = validate_email_uniqueness("Admin@Company.com", User)
# Exclude current user during update
is_unique = validate_email_uniqueness("admin@company.com", User, exclude_id=user.id)

# Slug uniqueness
validate_unique_slug("my-article", Article)                    # returns "my-article"
validate_unique_slug("my-article", Article, exclude_id=obj.id)  # skip self

# File size
validate_file_size(uploaded_file)              # True if <= 10 MB
validate_file_size(uploaded_file, max_size_mb=5)  # True if <= 5 MB

# Date range
result = validate_date_range(date(2025, 1, 1), date(2025, 3, 1))
# {"is_valid": True, "errors": []}

result = validate_date_range(date(2025, 6, 1), date(2025, 1, 1))
# {"is_valid": False, "errors": ["Start date cannot be after end date."]}

# JSON field validation
result = validate_json_field('{"name": "test"}')
# {"is_valid": True, "errors": [], "data": {"name": "test"}}

result = validate_json_field('not json')
# {"is_valid": False, "errors": ["Invalid JSON: ..."], "data": None}

# With JSON Schema
schema = {"type": "object", "required": ["name"]}
result = validate_json_field('{"age": 30}', schema=schema)
# {"is_valid": False, "errors": ["Schema validation error: 'name' is a required property"], "data": {"age": 30}}
```
