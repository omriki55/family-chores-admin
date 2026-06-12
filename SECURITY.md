# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.
Email **omrigonen5050@gmail.com** with details; you'll get a response within 72 hours.

## Scope

- Row-level security (RLS) bypasses in the Supabase schema
- Leakage of user API keys (`user_secrets`)
- XSS in the tracker/landing (user-controlled content is escaped via `esc()`)

## Out of scope

- Issues requiring the service-role key (it is never shipped to clients)
- Rate-limit abuse of the public `events` insert
