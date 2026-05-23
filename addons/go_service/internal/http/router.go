package httpapi

import (
	"net/http"
	"generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/http/handlers"
	"generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/repository"
	"generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/service"
)

func NewRouter() http.Handler {
	repo := repository.NewInventoryRepository()
	serviceLayer := service.NewInventoryService(repo)
	mux := http.NewServeMux()
	mux.Handle("/health", handlers.NewHealthHandler(serviceLayer))
	mux.Handle("/inventory", handlers.NewInventoryHandler(serviceLayer))
	return mux
}
