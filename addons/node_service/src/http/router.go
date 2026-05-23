package httpapi

import (
	"net/http"
	"generated/service/internal/http/handlers"
	"generated/service/internal/repository"
	"generated/service/internal/service"
)

func NewRouter() http.Handler {
	repo := repository.NewInventoryRepository()
	serviceLayer := service.NewInventoryService(repo)
	mux := http.NewServeMux()
	mux.Handle("/health", handlers.NewHealthHandler(serviceLayer))
	mux.Handle("/inventory", handlers.NewInventoryHandler(serviceLayer))
	return mux
}
