from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdminProgramRegistryStatus(BaseModel):
    """프로그램 레지스트리 상태값의 공통 enum-like contract."""

    build_status: str = Field(default="pending", description="빌드 상태")
    deploy_status: str = Field(default="pending", description="배포 상태")
    verification_status: str = Field(default="pending", description="검증 상태")


class AdminProgramRegistrySummaryResponse(BaseModel):
    """목록 조회용 summary 응답."""

    program_id: str = Field(..., description="프로그램 식별자")
    program_key: str = Field(..., description="내부 프로그램 키")
    program_name: str = Field(..., description="프로그램 이름")
    program_type: str = Field(default="app", description="프로그램 타입")
    build_status: str = Field(default="pending", description="빌드 상태")
    deploy_status: str = Field(default="pending", description="배포 상태")
    verification_status: str = Field(default="pending", description="검증 상태")
    latest_version: str = Field(default="0.0.0", description="최신 버전")
    latest_build_id: Optional[str] = Field(default=None, description="최신 빌드 ID")
    latest_release_channel: str = Field(default="stable", description="릴리스 채널")
    owner_team: Optional[str] = Field(default=None, description="책임 팀")
    primary_domain: Optional[str] = Field(default=None, description="기본 도메인")
    admin_domain: Optional[str] = Field(default=None, description="관리 도메인")
    updated_at: Optional[str] = Field(default=None, description="갱신 시각")


class AdminProgramRegistryArtifactResponse(BaseModel):
    """산출물 정보 응답."""

    artifact_id: str = Field(..., description="산출물 ID")
    program_id: str = Field(..., description="프로그램 ID")
    artifact_name: str = Field(..., description="산출물 이름")
    artifact_type: str = Field(default="binary", description="산출물 타입")
    artifact_path: Optional[str] = Field(default=None, description="산출물 경로")
    created_at: Optional[str] = Field(default=None, description="생성 시각")
    size_bytes: Optional[int] = Field(default=None, description="크기")
    checksum: Optional[str] = Field(default=None, description="체크섬")


class AdminProgramRegistryCheckResponse(BaseModel):
    """검증 기록 응답."""

    check_id: str = Field(..., description="검증 ID")
    program_id: str = Field(..., description="프로그램 ID")
    check_name: str = Field(..., description="검증 이름")
    check_type: str = Field(default="runtime", description="검증 타입")
    check_status: str = Field(default="pending", description="검증 상태")
    started_at: Optional[str] = Field(default=None, description="시작 시각")
    finished_at: Optional[str] = Field(default=None, description="종료 시각")
    result_summary: Optional[str] = Field(default=None, description="결과 요약")
    detail_url: Optional[str] = Field(default=None, description="상세 URL")


class AdminProgramRegistryDetailResponse(BaseModel):
    """단일 프로그램 상세 응답."""

    program_id: str = Field(..., description="프로그램 식별자")
    program_key: str = Field(..., description="내부 프로그램 키")
    program_name: str = Field(..., description="프로그램 이름")
    program_type: str = Field(default="app", description="프로그램 타입")
    primary_domain: Optional[str] = Field(default=None, description="기본 도메인")
    admin_domain: Optional[str] = Field(default=None, description="관리 도메인")
    api_base_url: Optional[str] = Field(default=None, description="API base URL")
    target_platform: Optional[str] = Field(default=None, description="대상 플랫폼")
    build_status: str = Field(default="pending", description="빌드 상태")
    deploy_status: str = Field(default="pending", description="배포 상태")
    verification_status: str = Field(default="pending", description="검증 상태")
    latest_version: str = Field(default="0.0.0", description="최신 버전")
    latest_build_id: Optional[str] = Field(default=None, description="최신 빌드 ID")
    latest_release_channel: str = Field(default="stable", description="릴리스 채널")
    owner_team: Optional[str] = Field(default=None, description="책임 팀")
    operator_notes: Optional[str] = Field(default=None, description="운영 메모")
    docs_links: List[Dict[str, str]] = Field(default_factory=list, description="문서 링크들")
    builds: List[Dict[str, Any]] = Field(default_factory=list, description="빌드 히스토리")
    deployments: List[Dict[str, Any]] = Field(default_factory=list, description="배포 히스토리")
    checks: List[Dict[str, Any]] = Field(default_factory=list, description="검증 기록")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="산출물 목록")
    updated_at: Optional[str] = Field(default=None, description="마지막 갱신 시각")


class AdminProgramRegistryStateResponse(BaseModel):
    """목록 페이지 전체 응답."""

    items: List[AdminProgramRegistrySummaryResponse] = Field(default_factory=list, description="프로그램 목록")
    total_count: int = Field(default=0, description="총 프로그램 수")
    active_filter: str = Field(default="all", description="현재 필터")
    summary: Dict[str, int] = Field(default_factory=dict, description="상태 요약")
    updated_at: Optional[str] = Field(default=None, description="갱신 시각")


class AdminProgramRegistryStatusUpdateRequest(BaseModel):
    """프로그램 상태/메타 업데이트 요청."""

    program_name: Optional[str] = Field(default=None, description="프로그램 이름")
    program_type: Optional[str] = Field(default=None, description="프로그램 타입")
    primary_domain: Optional[str] = Field(default=None, description="기본 도메인")
    admin_domain: Optional[str] = Field(default=None, description="관리 도메인")
    api_base_url: Optional[str] = Field(default=None, description="API base URL")
    target_platform: Optional[str] = Field(default=None, description="대상 플랫폼")
    build_status: Optional[str] = Field(default=None, description="빌드 상태")
    deploy_status: Optional[str] = Field(default=None, description="배포 상태")
    verification_status: Optional[str] = Field(default=None, description="검증 상태")
    latest_version: Optional[str] = Field(default=None, description="최신 버전")
    latest_build_id: Optional[str] = Field(default=None, description="최신 빌드 ID")
    latest_release_channel: Optional[str] = Field(default=None, description="릴리스 채널")
    owner_team: Optional[str] = Field(default=None, description="책임 팀")
    operator_notes: Optional[str] = Field(default=None, description="운영 메모")


class AdminProgramRegistryCheckRunRequest(BaseModel):
    """수동 검증 실행 요청."""

    check_name: str = Field(..., description="실행할 검증 이름")
    check_type: str = Field(default="runtime", description="검증 타입")
    trigger_reason: Optional[str] = Field(default=None, description="수동 실행 사유")
    target_environment: Optional[str] = Field(default="staging", description="검증 대상 환경")


class AdminProgramRegistryRollbackRequest(BaseModel):
    """롤백 요청."""

    target_version: str = Field(..., description="롤백 대상 버전")
    reason: Optional[str] = Field(default=None, description="롤백 사유")
    confirm: bool = Field(default=False, description="사용자 확인")


class AdminProgramRegistryApproveRequest(BaseModel):
    """승인 요청."""

    approved_version: str = Field(..., description="승인할 버전")
    approval_note: Optional[str] = Field(default=None, description="승인 코멘트")
    approved_by: Optional[str] = Field(default=None, description="승인자")


__all__ = [
    "AdminProgramRegistryStatus",
    "AdminProgramRegistrySummaryResponse",
    "AdminProgramRegistryArtifactResponse",
    "AdminProgramRegistryCheckResponse",
    "AdminProgramRegistryDetailResponse",
    "AdminProgramRegistryStateResponse",
    "AdminProgramRegistryStatusUpdateRequest",
    "AdminProgramRegistryCheckRunRequest",
    "AdminProgramRegistryRollbackRequest",
    "AdminProgramRegistryApproveRequest",
]
