# Contributing to TN Electoral Search

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/[your-username]/tn-electoral-search.git
   cd tn-electoral-search
   ```

3. Set up development environment:
   ```bash
   make install
   make init-db
   ```

4. Run development server:
   ```bash
   make dev
   ```

## Code Structure

- `app/` - Core application code
  - `main.py` - FastAPI application and web UI
  - `database.py` - Database operations
  - `search_service.py` - Search logic and caching
  - `pdf_service.py` - PDF import functionality
  - `extractors/` - PDF data extraction modules

- `config/` - Configuration files
- `scripts/` - Utility scripts
- `tests/` - Test files

## Coding Standards

- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes
- Keep functions focused and small
- Use type hints where appropriate
- Add tests for new functionality

## Testing

Run tests with:
```bash
make test
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages (if any)

## Security Issues

For security-related issues, please email directly rather than creating a public issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.