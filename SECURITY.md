# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please follow these steps:

### Do NOT

- Open a public GitHub issue for security vulnerabilities
- Disclose the vulnerability publicly before it has been addressed

### Do

1. **Email the maintainer** at security@example.com with:
   - A description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact
   - Any suggested fixes (optional)

2. **Wait for acknowledgment** - We aim to respond within 48 hours

3. **Coordinate disclosure** - We will work with you to understand and address the issue

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Status Updates**: Regular updates on the progress
- **Resolution**: Depends on severity and complexity
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

### For Contributors

- Never commit sensitive data (API keys, passwords, tokens, OAuth credentials)
- Use environment variables for configuration (see `.env.example`)
- Follow secure coding practices
- Keep dependencies up to date
- Run security audits regularly:
  ```bash
  pip install safety
  safety check
  pip-audit
  ```
- Use type hints for type safety
- Validate and sanitize all inputs
- Never hardcode credentials in code
- Keep token files in `.gitignore`

### For Users

- Keep the application updated to the latest version
- Use strong, unique passwords for all accounts
- Protect your API keys and credentials
- Review environment variable configurations
- Run the script in a secure environment
- Limit file permissions appropriately
- Monitor API quota usage
- Review code before running in production

## Known Security Considerations

### YouTube Data API v3

This project integrates with YouTube Data API v3:

**API Key Management:**
- Never share or commit API keys to version control
- Store in `.env` files (listed in `.gitignore`)
- Use separate keys for development and production
- Rotate keys periodically
- Restrict key usage by IP address when possible
- Monitor API quota usage
- Use API key best practices from Google Console
- Consider implementing API key rotation schedules

**OAuth 2.0 Implementation:**
- Client ID and Client Secret must NOT be hardcoded in code
- Store credentials in `.env` files or secure credential management systems
- Use separate credentials for development and production environments
- Implement refresh token rotation
- Handle token expiration gracefully
- Clear tokens on logout or script completion
- Never store tokens in plaintext files
- Use secure storage for token files (restricted file permissions)
- Implement token lifecycle management

**Token File Security:**
- Token cache files (e.g., `token.json`) should have restricted permissions (mode 600 on Unix/Linux)
- Never commit token files to version control
- Ensure `.gitignore` includes `token*.json`, `credentials*.json`
- Implement automatic token rotation mechanisms
- Implement proper error handling for token refresh failures
- Consider encrypting token files for additional security

### Python Environment Security

**Virtual Environment:**
- Always use virtual environments (`venv`, `virtualenv`, or `conda`)
- Isolate dependencies per project
- Document Python version requirements (e.g., Python 3.8+)
- Use `requirements.txt` for dependency pinning
- Test in virtual environment before deployment

**Dependency Management:**
- Pin specific versions in `requirements.txt`:
  ```
  google-auth==2.x.x
  google-auth-httplib2==0.x.x
  google-auth-oauthlib==1.x.x
  google-api-python-client==1.x.x
  ```
- Run security audits regularly:
  ```bash
  safety check
  pip-audit
  ```
- Keep dependencies up to date
- Monitor security advisories from PyPI
- Review dependency sources and maintainers
- Avoid installing packages from untrusted sources

### OAuth 2.0 Authorization Code Flow Security

**Authorization Code Flow:**
- Use state parameter to prevent CSRF attacks
- Validate state parameter on callback
- Handle errors gracefully during authorization
- Implement timeout for authorization requests
- Validate OAuth redirect URIs strictly
- Store authorization state securely

**Token Storage and Management:**
- Never store tokens in version control
- Use environment variables for sensitive tokens when necessary
- Implement file-based token storage with restricted permissions:
  ```python
  import os
  os.chmod('token.json', 0o600)  # Read/write by owner only
  ```
- Encrypt tokens at rest if storing sensitive data locally
- Implement token refresh mechanisms
- Clear tokens when no longer needed
- Implement token expiration handling

### Environment Variables

Critical security-sensitive variables:

```
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8080/  # Or your callback URL

# Playlist Configuration
PLAYLIST_NAME=Latest Uploads from Subscribed Channels
PLAYLIST_DESCRIPTION=Auto-generated playlist of latest Shorts

# API Configuration
MAX_RESULTS=50
DRY_RUN=false

# Logging
LOG_LEVEL=INFO  # Use INFO or higher in production
DEBUG=False
ENABLE_FILE_LOGGING=False
```

**Important:**
- Never commit `.env` files to git
- Use `.env.example` to document required variables
- Generate strong secrets for any API credentials
- Rotate secrets regularly
- Use different secrets for each environment
- Implement secrets management for production deployments
- Consider using environment-specific configuration files

### File and Directory Permissions

**Script Files (Unix/Linux/macOS):**
```bash
# Make script executable (owner only)
chmod 700 scripts/main.py
chmod 700 setup.sh

# Token file (restrictive permissions)
chmod 600 token.json

# .env file (restrictive permissions)
chmod 600 .env
```

**Configuration Files:**
```bash
# Restrict .env file access
chmod 600 .env

# Make setup scripts executable
chmod 755 setup.sh
chmod 755 setup.ps1
```

### Script Execution Security

- Run scripts in isolated environments
- Limit script permissions to necessary operations
- Implement comprehensive logging for audit trails
- Use proper error handling and recovery mechanisms
- Don't run scripts with elevated privileges (root/administrator) unless absolutely necessary
- Validate all API responses before processing
- Implement rate limiting to avoid API quota issues
- Handle authentication failures gracefully
- Implement timeouts for long-running operations
- Clean up temporary files after execution

### API Request Security

**Input Validation:**
- Validate channel IDs and video IDs before API requests
- Sanitize user input before using in queries
- Implement request size limits
- Validate playlist metadata before processing
- Check video duration before adding to shorts playlist

**Rate Limiting and Quotas:**
- Respect YouTube API quotas and rate limits
- Implement backoff strategies for rate limiting
- Monitor API response codes
- Handle 403 (quota exceeded) errors gracefully
- Track and log API usage
- Implement request throttling if needed

**Error Handling:**
- Don't expose API error details to users
- Log errors securely with appropriate filtering
- Implement retry logic with exponential backoff
- Use generic error messages for end users
- Implement circuit breaker pattern for API failures

### Data Security

- Don't store user credentials (Google handles this through OAuth)
- Don't hardcode any secrets or sensitive data
- Encrypt sensitive data at rest if storing locally
- Implement proper data retention policies
- Clear temporary files after processing
- Use secure temp directories for operations
- Don't log sensitive data (API responses, tokens, credentials)

### Network Security

- Use HTTPS/TLS for all API communications (enforced by `google-api-python-client`)
- Validate SSL certificates in production
- Use timeout values for API requests
- Implement connection pooling
- Consider using VPN for sensitive operations
- Disable verbose logging in production

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed. Users will be notified through:

- GitHub Security Advisories
- Release notes with security badges
- Email notifications (for critical issues)

## Responsible Disclosure

We practice responsible disclosure:
- Vulnerabilities are fixed before public disclosure
- We provide credit to security researchers
- We coordinate with affected parties
- We release security advisories when appropriate

## Contact

For security concerns, please contact:
- Email: security@example.com
- GitHub: @charg

For general questions, please use GitHub issues instead.

---

Thank you for helping keep this project secure!
