package repository

import "generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/domain"

type InventoryRepository struct{}

func NewInventoryRepository() InventoryRepository {
	return InventoryRepository{}
}

func (InventoryRepository) List() []domain.InventoryItem {
	return []domain.InventoryItem{{ID: "item-1", Name: "Starter", Quantity: 3}}
}
