package app

import (
	"fmt"
	"net/http"
	"generated/오케스트레이터_자가개선_실험_즉시_실행_원본_대상_경로_C_Use_88b347d566_go_service/internal/httpapi"
)

func Run() error {
	router := httpapi.NewRouter()
	return http.ListenAndServe(":8080", router)
}
