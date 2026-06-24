# Rocket Bootstrap Plan

Rocket bootstrap is an idempotent OpenCode runtime verification step.

## Responsibilities

- Ensure `C:\Users\Aarush\.config\opencode` exists.
- Sync powers from `C:\Users\Aarush\shokunin-opencode-powers`.
- Merge missing MCP/plugin config without overwriting user customization.
- Migrate real-looking MCP env secrets into RocketVault.
- Create the configured workspace directory.
- Store readiness results in Rocket memory.

## Not Responsibilities

- Starting OpenWork.
- Installing global tooling during every backend launch.
- Storing raw credentials in mobile app preferences.
- Overwriting user-managed OpenCode config values.

## Runtime Contract

```text
rocket_bootstrap()
  -> OpenCodeRuntimeManager.ensure_ready()
  -> RuntimeReadinessReport
```

The backend may start even if runtime readiness is incomplete, but task execution fails closed with a readable terminal message.
