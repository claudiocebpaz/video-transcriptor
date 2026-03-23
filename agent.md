---
name: Video Extractor Agent
description: AI assistant especializado en el proyecto Python de transcripción de video (Docker-only).
skills:
  - docker-expert
  - python-pro
---

# Video Extractor Agent

Convención de raíz obligatoria:

- Los archivos de instrucciones para agentes IA permanecen en raíz (`AGENTS.md`, `agent.md`, equivalentes).
- Los archivos de entorno permanecen en raíz (`.env`, `.env.example`).
- El flujo operativo se ejecuta por `Makefile` y Docker.

Todas las reglas del proyecto, comandos oficiales y convenciones están centralizadas en [`AGENTS.md`](./AGENTS.md).

Usar [`AGENTS.md`](./AGENTS.md) como fuente única de verdad antes de proponer o implementar cambios.

El flujo oficial es Docker-only vía [`Makefile`](./Makefile), ejecutando imagen Docker directa (`docker build` + `docker run`) sin Docker Compose.
