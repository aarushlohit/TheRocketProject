---
name: web-security
description: 'Apply web security best practices — OWASP Top 10, input validation, authentication, CSRF, XSS prevention, CSP headers, secure dependencies. Use when: security, web security, OWASP, XSS, CSRF, SQL injection, authentication, authorization, security audit, secure code.'
---

# Web Security

Security is not a feature — it's a property of the entire system. Apply these standards to all web code.

## OWASP Top 10 (Quick Reference)

1. **Broken Access Control** — check authorization on every request, not just authentication.
2. **Cryptographic Failures** — never roll your own crypto. Use standard libraries (bcrypt, Argon2).
3. **Injection** — never concatenate user input into SQL, shell commands, or HTML. Use parameterized queries.
4. **Insecure Design** — threat model before building. Rate limiting, request throttling.
5. **Security Misconfiguration** — disable debug endpoints in production. Remove default credentials.
6. **Vulnerable Components** — keep dependencies updated. Use `npm audit`, `pip-audit`, Dependabot.
7. **Auth Failures** — MFA, account lockout, secure password reset.
8. **Data Integrity Failures** — verify signatures, use Subresource Integrity (SRI) for CDN assets.
9. **Logging & Monitoring** — log auth events, access anomalies, and errors. Alert on suspicious patterns.
10. **SSRF** — validate and restrict URLs the server fetches. Block internal IP ranges.

## Input Validation

- Validate + sanitize every user input on the server side.
- Whitelist over blacklist — define what's allowed, not what's blocked.
- Use parameterized queries for databases (prevents SQL injection).
- Escape all output (prevents XSS).

## Headers

```
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

## Secrets Management

- Never hardcode secrets, API keys, or credentials in code.
- Use environment variables or a secrets manager (HashiCorp Vault, AWS Secrets Manager).
- Add `.env` files to `.gitignore`.
- Rotate keys regularly.
