# Validators

Reusable validation logic for the enterprise platform. Organized by where they plug in.

## Structure

```
core/validators/
├── fields.py        # Django model field validators (deconstructible classes)
├── functions.py     # Standalone validation utility functions
└── serializers.py   # DRF serializer-level validators (Meta.validators)
```

## API

### fields.py

Deconstructible validator classes for use on Django model fields.

- `UsernameValidator` — alphanumeric + underscores, 3-30 chars
- `PhoneNumberValidator` — 10-15 digits after stripping formatting
- `EmailDomainValidator(allowed_domains)` — restrict email to a whitelist of domains

```python
from core.validators import UsernameValidator, PhoneNumberValidator, EmailDomainValidator

# On a model field
username = models.CharField(max_length=30, validators=[UsernameValidator()])

# Direct usage
validate_phone = PhoneNumberValidator()
validate_phone("+1 (555) 123-4567")  # OK

validate_domain = EmailDomainValidator(["company.com", "corp.io"])
validate_domain("user@company.com")  # OK
validate_domain("user@gmail.com")    # raises ValidationError
```

### functions.py

Standalone validation utility functions called manually in views, serializers, or services.

- `validate_email_uniqueness(email, model_class, exclude_id=None)` — case-insensitive uniqueness check
- `validate_unique_slug(value, model_class, field_name="slug", exclude_id=None)` — slug uniqueness check
- `validate_file_size(file, max_size_mb=10)` — file size limit check
- `validate_date_range(start_date, end_date, max_days=365)` — date range validation; returns `{is_valid, errors}`
- `validate_json_field(value, schema=None)` — JSON parsing + optional JSON Schema validation; returns `{is_valid, errors, data}`

```python
from core.validators import validate_email_uniqueness, validate_file_size

is_unique = validate_email_uniqueness("admin@company.com", User)
is_valid = validate_file_size(uploaded_file, max_size_mb=5)
```

### serializers.py

DRF serializer-level validators that plug into `Meta.validators`.

- `UniqueTogetherContextValidator` — validates uniqueness using field values and serializer context values

```python
from core.validators import UniqueTogetherContextValidator

class MembershipCreateSerializer(serializers.Serializer):
    user_id = ...
    role_id = ...

    class Meta:
        model = TenantMembership
        validators = [
            UniqueTogetherContextValidator(
                fields={"user_id": "user_id"},
                message="User is already a member of this tenant.",
            ),
        ]
```

Parameters:
- `fields` — mapping of queryset lookup keys to serializer field names
- `context_fields` — mapping of queryset lookup keys to serializer context keys (defaults to `{"tenant_id": "tenant_id"}`)
- `queryset` — explicit queryset; if not provided, inferred from `serializer.Meta.model`
- `message` — error message on violation
