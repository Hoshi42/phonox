# Contributing to Phonox

Thank you for your interest in contributing to Phonox! We welcome contributions of all kinds.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork
3. **Create** a feature branch
4. **Make** your changes
5. **Submit** a pull request

## Development Setup

Use the CLI for easy setup:

```bash
git clone https://github.com/your-username/phonox.git
cd phonox
./phonox-cli install --up
```

Or manual setup:
```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d --build
```

For troubleshooting, see [Database & Retry Configuration](database-retry.md).

## Code Style

### Python
- Use `black` for formatting
- Use `mypy` for type checking
- Use `ruff` for linting
- Write docstrings for functions and classes

### TypeScript/React
- Use ESLint (configured in project)
- Use Prettier for formatting
- Write JSDoc comments for components
- Use TypeScript for type safety

## Testing

Before submitting a PR:

```bash
# Backend tests
docker-compose exec backend python -m pytest tests/ -v
docker-compose exec backend mypy backend/

# Frontend tests
docker-compose exec frontend npm run test:e2e
```

## Pull Request Process

1. **Update** CHANGELOG.md with your changes
2. **Write** clear commit messages
3. **Test** locally before pushing
4. **Reference** any related issues (#123)
5. **Describe** what your PR changes

PR template:
```markdown
## Description
Brief description of changes.

## Type
- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Performance
- [ ] Refactoring

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Tested locally

## Checklist
- [ ] Code follows style guidelines
- [ ] Docstrings added
- [ ] CHANGELOG updated
```

## Reporting Issues

**Found a bug?** Open an issue with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Screenshots (if applicable)
- Environment (OS, Python version, etc.)

**Feature request?** Tell us:
- Use case
- Why it's needed
- Suggested implementation (optional)

## License Agreement

By contributing to Phonox, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Report violations to maintainers

## Questions?

- Check [Documentation](../index.md)
- Search [GitHub Issues](https://github.com/your-username/phonox/issues)
- Ask in [GitHub Discussions](https://github.com/your-username/phonox/discussions)

---

Thank you for contributing! 🎉
