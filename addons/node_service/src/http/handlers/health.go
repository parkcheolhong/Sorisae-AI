package handlers

import (
	"encoding/json"
	"net/http"
	"generated/service/internal/service"
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
