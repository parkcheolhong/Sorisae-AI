package service

import "generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/repository"

type InventoryService struct {
	repo repository.InventoryRepository
}

func NewInventoryService(repo repository.InventoryRepository) InventoryService {
	return InventoryService{repo: repo}
}

func (service InventoryService) HealthPayload() map[string]any {
	return map[string]any{"ok": true, "service": "go-ops-service"}
}

func (service InventoryService) InventoryPayload() map[string]any {
	return map[string]any{"items": service.repo.List(), "count": len(service.repo.List())}
}
