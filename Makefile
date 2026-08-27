.PHONY: help phase-a compose-config phase-b-check phase-check up up-core up-ai down logs logs-core ps eeg-config eeg-up eeg-down eeg-logs

COMPOSE_FILE=infra/compose/docker-compose.dev.yml
EEG_COMPOSE_FILE=infra/compose/docker-compose.jetson-eeg-bridge.yml
CORE_SERVICES=postgres redis minio identity-service consultation-service gateway-service consultation operations-console

help:
	@echo "Available targets:"
	@echo "  compose-config  Validate docker compose configuration"
	@echo "  phase-check     Run repository checks"
	@echo "  up-core         Start the current active product chain"
	@echo "  up              Start the collaboration baseline stack"
	@echo "  up-ai           Start the collaboration baseline stack with optional ai-service"
	@echo "  down            Stop containers"
	@echo "  logs            Tail all compose logs"
	@echo "  logs-core       Tail core-chain logs"
	@echo "  ps              Show compose status"
	@echo "  eeg-config      Validate Linux EEG compose configuration"
	@echo "  eeg-up          Build and start Linux EEG bridge and multimodal service"
	@echo "  eeg-down        Stop the stack including Linux EEG bridge"
	@echo "  eeg-logs        Tail Linux EEG bridge and multimodal logs"

phase-a:
	@bash infra/scripts/bootstrap_phase_a.sh

compose-config:
	@docker compose -f $(COMPOSE_FILE) config

phase-b-check:
	@bash infra/scripts/check_phase_b.sh

phase-check: phase-b-check
	@echo "phase-check complete"

up-core:
	@docker compose -f $(COMPOSE_FILE) up -d $(CORE_SERVICES)

up:
	@docker compose -f $(COMPOSE_FILE) up -d

up-ai:
	@docker compose -f $(COMPOSE_FILE) --profile optional-ai up -d

down:
	@docker compose -f $(COMPOSE_FILE) down

logs:
	@docker compose -f $(COMPOSE_FILE) logs -f

logs-core:
	@docker compose -f $(COMPOSE_FILE) logs -f $(CORE_SERVICES)

ps:
	@docker compose -f $(COMPOSE_FILE) ps

eeg-config:
	@docker compose -f $(COMPOSE_FILE) -f $(EEG_COMPOSE_FILE) config

eeg-up:
	@docker compose -f $(COMPOSE_FILE) -f $(EEG_COMPOSE_FILE) up -d --build eeg-bridge multimodal-service

eeg-down:
	@docker compose -f $(COMPOSE_FILE) -f $(EEG_COMPOSE_FILE) down

eeg-logs:
	@docker compose -f $(COMPOSE_FILE) -f $(EEG_COMPOSE_FILE) logs -f eeg-bridge multimodal-service
