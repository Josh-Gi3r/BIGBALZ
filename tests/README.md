# BIGBALZ Bot Test Suite

Comprehensive test coverage for the BIGBALZ Bot application.

## Structure

- `unit/` - Unit tests for individual components
  - `api/` - API client and external service tests
  - `bot/` - Telegram bot handler and button tests
  - `classification/` - BALZ reasoning engine tests
  - `monitoring/` - Background monitoring tests
  - `utils/` - Utility function tests
- `integration/` - End-to-end integration tests
- `fixtures/` - Test data and mock responses

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/unit/api/
pytest tests/integration/

# Run with coverage
pytest tests/ --cov=src/
```

## Test Guidelines

- Use descriptive test names
- Mock external dependencies
- Include both positive and negative test cases
- Maintain test isolation
