package handlers

import (
	"encoding/json"
	"net/http"
	"generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/service"
)

type HealthHandler struct {
	service service.InventoryService
}

func NewHealthHandler(service service.InventoryService) HealthHandler {
	return HealthHandler{service: service}
}

func (handler HealthHandler) ServeHTTP(writer http.ResponseWriter, _ *http.Request) {
	writer.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(writer).Encode(handler.service.HealthPayload())
}
