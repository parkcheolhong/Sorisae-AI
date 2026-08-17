# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4 출고 패키지

- product_ready: False
- packaging_ready: True
- feature_list: 상품 관리, 카탈로그 노출, 주문 추적, 고객 상태 확인, AI 엔진 구성, 학습 파이프라인, 추론 런타임, 평가 리포트, 전략/업무 서비스 연동
- completion_conditions: 필수 파일/구조 생성, 도메인 계약 마커 포함, semantic gate 통과, 패키징 문서/설정값 포함
- test_conditions: 도메인별 필수 테스트 파일 생성, runtime verification 통과 기준 정리, 배포/환경 변수 예시 포함, 주문문에 명시된 테스트 요구 반영
- failed_reasons: semantic gate failed | shipping zip reproduction validation failed | test coverage too small: 0 | commerce backend implementation too small: 0 | runtime scenario marker missing: catalog flow | runtime scenario marker missing: marketplace publish payload | thin implementation files detected: scripts/check.sh
- validation_reports: docs/automatic_validation_result.json, docs/automatic_validation_result.md, docs/failure_report.md, docs/root_cause_analysis.md
