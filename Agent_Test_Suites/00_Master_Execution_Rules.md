# Master Execution Rules for Agents

1. **SSO Over Direct Login**: Always login to Core to get a JWT. Launch external modules by appending `?sso_token=<token>`.
2. **Evidence**: Every bug requires a base64 screenshot or full Request/Response pair.
3. **Exceptions**: Soft deletes (HTTP 200) and DB-stored XSS are BY DESIGN. Do not report them.

Proceed to modules 01 through 08 and execute every mapped checkbox.
