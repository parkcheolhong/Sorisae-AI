package handlers

import (
	"encoding/json"
	"net/http"
	"generated/service/internal/service"
)

type InventoryHandler struct {
	service service.InventoryService
}

func NewInventoryHandler(service service.InventoryService) InventoryHandler {
	return InventoryHandler{service: service}
}

func (handler InventoryHandler) ServeHTTP(writer http.ResponseWriter, _ *http.Request) {
	writer.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(writer).Encode(handler.service.InventoryPayload())
}
