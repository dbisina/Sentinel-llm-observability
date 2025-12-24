# Contributing

Thanks for considering a contribution! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/dbisina/sentinel-llm-observability.git
cd sentinel-llm-observability
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

- Use docstrings for all public functions and classes
- Keep functions focused and under 50 lines
- Run tests before submitting PRs

## Submitting Changes

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a PR with clear description
