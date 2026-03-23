.DEFAULT_GOAL := help

# Optional .env support (non-breaking if file does not exist)
ifneq (,$(wildcard .env))
include .env
export
endif

# Variables
IMAGE_NAME := video-extractor
IMAGE_TAG ?= dev
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
CONTAINER_NAME := video-extractor-dev
DOCKERFILE_PATH := scripts/Dockerfile
SCRIPT_PATH := scripts/transcribir_video.py
SCRIPT_MODULE := scripts.transcribir_video
DEFAULT_VIDEO_DIR := ./video_entrada
DEFAULT_OUTPUT_PREFIX := salida/transcripcion
DOCKER_BUILD_BASE := docker build -f $(DOCKERFILE_PATH) -t $(IMAGE)
DOCKER_RUN_BASE := docker run --rm -v "$(CURDIR)":/app -w /app $(IMAGE)
VIDEO ?=
WHISPER_MODEL ?= small
DEEPSEEK_MODEL ?= deepseek-chat
LANGUAGE ?= es
DEEPSEEK_APIKEY ?=
DOCKER_BUILD_EXTRA_FLAGS ?=

# Color codes
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# ================================
# Docker image lifecycle
# ================================

.PHONY: build
build: ## Build project Docker image
	@echo "$(GREEN)🔨 Construyendo imagen Docker...$(NC)"
	@$(DOCKER_BUILD_BASE) $(DOCKER_BUILD_EXTRA_FLAGS) .
	@echo "$(GREEN)✅ Imagen lista: $(IMAGE)$(NC)"

.PHONY: rebuild
rebuild: ## Build project Docker image from scratch (no cache)
	@$(MAKE) build DOCKER_BUILD_EXTRA_FLAGS="--no-cache"

.PHONY: up
up: build ## Build project Docker image

.PHONY: down
down: ## Remove project image (optional cleanup)
	@echo "$(RED)🛑 Eliminando imagen del proyecto (si existe)...$(NC)"
	@docker image rm $(IMAGE) 2>/dev/null || true

.PHONY: logs
logs: ## Show logs for a named running container (if any)
	@echo "$(YELLOW)📋 Mostrando logs de $(CONTAINER_NAME) (si existe)...$(NC)"
	@docker logs -f $(CONTAINER_NAME)

.PHONY: status
status: ## Show running containers related to this project image
	@docker ps --filter ancestor=$(IMAGE) --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"

.PHONY: shell
shell: ## Open shell in app container
	@$(DOCKER_RUN_BASE) sh

# ================================
# Setup
# ================================

.PHONY: install-dev
install-dev: ## First-time setup (Docker-only)
	@echo "$(GREEN)🔧 Preparando entorno...$(NC)"
	@$(MAKE) up
	@echo "$(GREEN)✅ Setup completo$(NC)"

# ================================
# Development commands (Docker-only)
# ================================

.PHONY: dev
dev: ## Transcribe video quickly with default config
	@echo "$(GREEN)🎙️ Transcribiendo video (modo dev)...$(NC)"
	@$(DOCKER_RUN_BASE) python -m $(SCRIPT_MODULE) $(if $(strip $(VIDEO)),"$(VIDEO)",) --output-prefix $(DEFAULT_OUTPUT_PREFIX)

.PHONY: transcribe
transcribe: ## Full transcribe command with MODEL/LANGUAGE
	@echo "$(GREEN)🎙️ Transcribiendo video con opciones...$(NC)"
	@$(DOCKER_RUN_BASE) \
		python -m $(SCRIPT_MODULE) $(if $(strip $(VIDEO)),"$(VIDEO)",) --model $(WHISPER_MODEL) --language $(LANGUAGE) --output-prefix $(DEFAULT_OUTPUT_PREFIX)

# ================================
# Quality (Docker-only)
# ================================

.PHONY: format
format: ## Run ruff format
	@echo "$(GREEN)🎨 Formateando código...$(NC)"
	@$(DOCKER_RUN_BASE) ruff format $(SCRIPT_PATH) tests/test_resolver_video_entrada.py

.PHONY: lint
lint: ## Run ruff check
	@echo "$(GREEN)✨ Ejecutando lint...$(NC)"
	@$(DOCKER_RUN_BASE) ruff check $(SCRIPT_PATH) tests/test_resolver_video_entrada.py

.PHONY: typecheck
typecheck: ## Run mypy
	@echo "$(GREEN)🔎 Ejecutando typecheck...$(NC)"
	@$(DOCKER_RUN_BASE) mypy --ignore-missing-imports $(SCRIPT_PATH)

.PHONY: test
test: check unit-tests ## Run checks + automated tests
	@echo "$(GREEN)✅ Testing OK$(NC)"

.PHONY: unit-tests
unit-tests: ## Run automated unit tests
	@echo "$(GREEN)🧪 Ejecutando unit tests...$(NC)"
	@$(DOCKER_RUN_BASE) python -m unittest discover -s tests -p "test_*.py" -v

.PHONY: check
check: lint typecheck ## Run lint + typecheck
	@echo "$(GREEN)✅ Calidad OK$(NC)"

# ================================
# Cleanup
# ================================

.PHONY: clean
clean: ## Remove stopped containers and dangling resources
	@echo "$(YELLOW)🧹 Limpiando recursos no usados...$(NC)"
	@docker container prune -f
	@docker system prune -f

# ================================
# Help
# ================================

.PHONY: help
help: ## Show available commands
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║     Video Extractor - Docker Workflow                         ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Uso:$(NC) make [target]"
	@echo "$(YELLOW)Nota:$(NC) Todos los comandos se ejecutan en contenedor (docker build + docker run)."
	@echo "$(YELLOW)Config:$(NC) Prioridad de variables = línea de comandos > entorno > .env > defaults de Makefile"
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🎯 ¿QUÉ HACE ESTE PROYECTO?$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  Transcribe videos con ffmpeg + faster-whisper y exporta TXT, SRT y JSON."
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  ⚙️ VARIABLES CLAVE$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  VIDEO=$(VIDEO)        Ruta del video (opcional). Si se omite, se autodetecta en $(DEFAULT_VIDEO_DIR)"
	@echo "  WHISPER_MODEL=$(WHISPER_MODEL)  Modelo Whisper (ej: tiny, base, small, medium, large-v3)"
	@echo "  DEEPSEEK_MODEL=$(DEEPSEEK_MODEL) Modelo DeepSeek (ej: deepseek-chat, deepseek-coder)"
	@echo "  LANGUAGE=$(LANGUAGE)  Idioma esperado (ej: es, en)"
	@echo "  DEFAULT_OUTPUT_PREFIX=$(DEFAULT_OUTPUT_PREFIX)  Prefijo de salida por defecto"
	@echo "  IMAGE_TAG=$(IMAGE_TAG)  Tag de la imagen Docker"
	@echo "  DEEPSEEK_APIKEY=$(DEEPSEEK_APIKEY)  API key opcional (cargable desde .env)"
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🚀 DESARROLLO - Preparar y ejecutar$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  $(YELLOW)make install-dev$(NC)      Primera vez: prepara entorno y construye imagen"
	@echo "  $(YELLOW)make up$(NC)               Reconstruye imagen (cuando cambian Dockerfile/dependencias)"
	@echo "  $(YELLOW)make dev VIDEO=...$(NC)    Transcripción rápida"
	@echo "  $(YELLOW)make transcribe ...$(NC)   Transcripción completa con MODEL/LANGUAGE"
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🧪 TESTING Y CALIDAD$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  $(YELLOW)make format$(NC)           Formatea el script"
	@echo "  $(YELLOW)make lint$(NC)             Lint con ruff"
	@echo "  $(YELLOW)make typecheck$(NC)        Typecheck con mypy"
	@echo "  $(YELLOW)make check$(NC)            Lint + typecheck"
	@echo "  $(YELLOW)make unit-tests$(NC)       Unit tests automáticos"
	@echo "  $(YELLOW)make test$(NC)             Check + unit-tests"
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🔧 DEBUG / INSPECCIÓN$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  $(YELLOW)make shell$(NC)            Abre shell dentro de la imagen"
	@echo "  $(YELLOW)make status$(NC)           Muestra contenedores de esta imagen"
	@echo "  $(YELLOW)make logs$(NC)             Sigue logs de contenedor nombrado"
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🧹 LIMPIEZA Y MANTENIMIENTO$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  $(YELLOW)make clean$(NC)            Limpia contenedores detenidos y caché Docker"
	@echo "  $(YELLOW)make down$(NC)             Elimina imagen local del proyecto"
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  💡 QUICK START (copiar/pegar)$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  make up"
	@echo "  make dev VIDEO=./video_entrada/sample.mp4"
	@echo "  make dev VIDEO="
	@echo "  make transcribe VIDEO=./video_entrada/entrevista.mp4 WHISPER_MODEL=medium LANGUAGE=es"
	@echo "  make transcribe VIDEO= WHISPER_MODEL=small LANGUAGE=es"
	@echo "  make check"
	@echo "  make test"
	@echo ""
	@echo "$(RED)⚠️  IMPORTANTE: no ejecutar Python en host para desarrollo del proyecto.$(NC)"
	@echo "$(YELLOW)   Usar siempre make + Docker (build/run).$(NC)"
	@echo ""
