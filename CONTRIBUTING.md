# Contributing to Lambda Architecture Pipeline

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Keep discussions professional

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Kubernetes version, etc.)
   - Logs or error messages

### Suggesting Enhancements

1. Check if the enhancement has been suggested
2. Create a new issue with:
   - Clear description of the enhancement
   - Use case and benefits
   - Potential implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `python3 -m pytest tests/ -v`
5. Update documentation if needed
6. Commit with clear messages
7. Push to your fork
8. Create a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Trend-Analysis.git
cd Trend-Analysis

# Install dependencies
make install

# Deploy locally for testing
make deploy

# Run tests
python3 -m pytest tests/ -v
```

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use type hints where applicable
- Add docstrings to functions and classes
- Keep functions focused and small
- Write unit tests for new code

Example:
```python
def process_data(data: Dict[str, Any]) -> List[str]:
    """
    Process input data and return results.
    
    Args:
        data: Input data dictionary
        
    Returns:
        List of processed results
    """
    # Implementation
    pass
```

### YAML (Kubernetes Manifests)

- Use 2 spaces for indentation
- Add comments for complex configurations
- Follow Kubernetes best practices
- Validate with `kubectl apply --dry-run=client`

### Shell Scripts

- Use `#!/bin/bash` shebang
- Add `set -e` for error handling
- Comment complex logic
- Make scripts executable: `chmod +x script.sh`

## Testing Guidelines

### Unit Tests

- Place in `tests/` directory
- Name files `test_*.py`
- Use descriptive test names
- Test both success and failure cases
- Aim for >80% code coverage

Example:
```python
def test_schema_generation():
    """Test that schemas are generated correctly"""
    schema = DataSchemas()
    post = schema.generate_post("id1", "user1", "python")
    assert post["post_id"] == "id1"
    assert "timestamp" in post
```

### Integration Tests

- Test component interactions
- Use test fixtures for setup/teardown
- Document expected behavior
- Clean up resources after tests

## Documentation Standards

### Code Comments

- Explain "why", not "what"
- Keep comments up-to-date
- Use clear, concise language

### Documentation Files

- Use Markdown format
- Include code examples
- Add diagrams where helpful
- Keep documentation synchronized with code

## Commit Messages

Follow conventional commits:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

Example:
```
feat(kafka): add support for SSL connections

- Add SSL configuration options
- Update Kafka producer/consumer
- Add documentation for SSL setup

Closes #123
```

## Branch Naming

- `feature/feature-name`: New features
- `fix/bug-name`: Bug fixes
- `docs/doc-name`: Documentation updates
- `test/test-name`: Test additions

## Pull Request Process

1. **Create PR** with clear title and description
2. **Link related issues** using "Closes #123"
3. **Ensure tests pass** locally
4. **Update documentation** if needed
5. **Request review** from maintainers
6. **Address feedback** promptly
7. **Squash commits** if requested
8. **Wait for approval** before merging

## Review Process

Reviewers will check:
- Code quality and style
- Test coverage
- Documentation completeness
- Performance impact
- Security considerations
- Backward compatibility

## Areas for Contribution

### High Priority

- Additional Spark aggregations
- More Grafana dashboards
- Security hardening (authentication, encryption)
- Performance optimizations
- Additional test coverage

### Medium Priority

- Schema evolution with Schema Registry
- ML model integration
- Advanced analytics (sentiment analysis)
- Multi-region deployment
- S3/MinIO integration

### Low Priority

- Alternative storage backends
- Additional visualization tools
- CI/CD pipeline improvements
- Alternative streaming frameworks

## Getting Help

- **Questions**: Create a GitHub issue with "Question:" prefix
- **Discussions**: Use GitHub Discussions
- **Chat**: Join our community chat (link TBD)
- **Documentation**: Read docs in the repo

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in commit history

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🙏
