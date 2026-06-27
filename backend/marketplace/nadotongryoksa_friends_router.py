from __future__ import annotations

from datetime import datetime, timedelta

from backend.time_utils import utcnow
from math import asin, cos, radians, sin, sqrt
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.marketplace import models


router = APIRouter(tags=["nadotongryoksa-friends"])

DISCOVERY_TTL = timedelta(minutes=10)
REQUEST_TTL = timedelta(days=7)
PROXIMITY_AUTO_FRIEND_M = 800.0
MAP_DISCOVERY_USERS: dict[int, dict] = {}


class FriendCreateRequest(BaseModel):
    targetEmail: EmailStr
    phoneNumber: Optional[str] = None
    displayName: Optional[str] = None


class FriendInviteRequestCode(BaseModel):
    targetEmail: EmailStr
    phoneNumber: Optional[str] = None
    displayName: Optional[str] = None
    verificationChannel: str = "email"


class FriendInviteConfirmRequest(BaseModel):
    inviteSessionToken: str
    verificationCode: str


class DiscoveryLocationUpsertRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    countryCode: Optional[str] = None
    gender: Optional[str] = None
    nickname: Optional[str] = None
    shareOnMap: bool = True


class FriendRequestCreateRequest(BaseModel):
    receiverUserId: int


def _utcnow() -> datetime:
    return utcnow()


def _normalize_country_code(country_code: Optional[str]) -> str:
    return (country_code or "").strip().upper()[:2]


def _normalize_gender(gender: Optional[str]) -> str:
    normalized = (gender or "unknown").strip().lower()
    return (
        normalized
        if normalized in {"male", "female", "other"}
        else "unknown"
    )


def _country_flag(country_code: str) -> str:
    if len(country_code) != 2 or not country_code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in country_code.upper())


def _haversine_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    earth_radius_m = 6371000.0
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return earth_radius_m * c


def _build_google_maps_url(
    latitude: float, longitude: float, label: str
) -> str:
    query = f"{latitude:.6f},{longitude:.6f}"
    if label.strip():
        query = f"{query}({label.strip()})"
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def _cleanup_discovery_state() -> None:
    _cleanup_discovery_state_db(None)


def _cleanup_discovery_state_db(db: Optional[Session]) -> None:
    now = _utcnow()
    for user_id, payload in list(MAP_DISCOVERY_USERS.items()):
        updated_at = payload.get("updated_at")
        if (
            not isinstance(updated_at, datetime)
            or now - updated_at > DISCOVERY_TTL
        ):
            MAP_DISCOVERY_USERS.pop(user_id, None)
    if db is not None:
        cutoff = now - DISCOVERY_TTL
        (
            db.query(models.FriendDiscoveryLocation)
            .filter(models.FriendDiscoveryLocation.updated_at < cutoff)
            .delete(synchronize_session=False)
        )
        request_cutoff = now - REQUEST_TTL
        (
            db.query(models.FriendRequest)
            .filter(
                models.FriendRequest.status == "pending",
                models.FriendRequest.created_at < request_cutoff,
            )
            .delete(synchronize_session=False)
        )
        db.commit()


def _build_voice_id(user_id: int) -> str:
    return f"nado-{user_id:06d}"


def _discovery_record_to_payload(
    record: models.FriendDiscoveryLocation,
) -> dict:
    return {
        "user_id": record.user_id,
        "username": (
            getattr(record.user, "username", None)
            if getattr(record, "user", None) is not None
            else None
        ),
        "nickname": record.nickname,
        "gender": _normalize_gender(record.gender),
        "country_code": _normalize_country_code(record.country_code),
        "latitude": record.latitude,
        "longitude": record.longitude,
        "accuracy": record.accuracy,
        "voice_id": _build_voice_id(record.user_id),
        "share_on_map": record.share_on_map,
        "updated_at": record.updated_at,
    }


def _get_active_discovery_payload(user_id: int, db: Session) -> Optional[dict]:
    cutoff = _utcnow() - DISCOVERY_TTL
    record = (
        db.query(models.FriendDiscoveryLocation)
        .filter(
            models.FriendDiscoveryLocation.user_id == user_id,
            models.FriendDiscoveryLocation.updated_at >= cutoff,
        )
        .first()
    )
    return _discovery_record_to_payload(record) if record is not None else None


def _friend_status(
    current_user_id: int, target_user_id: int, db: Session
) -> str:
    if (
        db.query(models.Friend)
        .filter(
            models.Friend.user_id == current_user_id,
            models.Friend.friend_user_id == target_user_id,
        )
        .first()
    ):
        return "friend"
    if (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.sender_user_id == current_user_id,
            models.FriendRequest.receiver_user_id == target_user_id,
            models.FriendRequest.status == "pending",
        )
        .first()
    ):
        return "outgoing_pending"
    if (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.sender_user_id == target_user_id,
            models.FriendRequest.receiver_user_id == current_user_id,
            models.FriendRequest.status == "pending",
        )
        .first()
    ):
        return "incoming_pending"
    return "available"


def _try_proximity_auto_accept_friend_request(
    friend_request: models.FriendRequest,
    sender_user: models.User,
    receiver_user: models.User,
    db: Session,
) -> bool:
    sender_discovery = _get_active_discovery_payload(int(sender_user.id), db) or {}
    receiver_discovery = _get_active_discovery_payload(int(receiver_user.id), db) or {}
    if not sender_discovery or not receiver_discovery:
        return False
    if not sender_discovery.get("share_on_map", True):
        return False
    if not receiver_discovery.get("share_on_map", True):
        return False
    distance_m = _haversine_meters(
        float(sender_discovery["latitude"]),
        float(sender_discovery["longitude"]),
        float(receiver_discovery["latitude"]),
        float(receiver_discovery["longitude"]),
    )
    if distance_m > PROXIMITY_AUTO_FRIEND_M:
        return False
    _ensure_friend_link(sender_user, receiver_user, db)
    _ensure_friend_link(receiver_user, sender_user, db)
    friend_request.status = "accepted"
    friend_request.responded_at = _utcnow()
    return True


def _ensure_friend_link(
    owner: models.User, target: models.User, db: Session
) -> None:
    if (
        existing := (
            db.query(models.Friend)
            .filter(
                models.Friend.user_id == owner.id,
                models.Friend.friend_email == target.email,
            )
            .first()
        )
    ):
        existing.friend_user_id = target.id
        existing.friend_username = target.username
        return
    db.add(
        models.Friend(
            user_id=owner.id,
            friend_user_id=target.id,
            friend_email=target.email,
            friend_username=target.username,
            friend_phone=None,
        )
    )


def _map_user_payload(payload: dict, distance_m: float, status: str) -> dict:
    country_code = _normalize_country_code(payload.get("country_code"))
    nickname = (
        str(payload.get("nickname") or payload.get("username") or "사용자")
        .strip()
        or "사용자"
    )
    return {
        "userId": payload["user_id"],
        "nickname": nickname,
        "gender": payload.get("gender") or "unknown",
        "countryCode": country_code,
        "countryFlag": _country_flag(country_code),
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "accuracy": payload.get("accuracy"),
        "distanceM": round(distance_m, 1),
        "voiceId": payload.get("voice_id"),
        "friendshipStatus": status,
        "googleMapsUrl": _build_google_maps_url(
            payload["latitude"], payload["longitude"], nickname
        ),
        "updatedAt": (
            payload["updated_at"].isoformat()
            if payload.get("updated_at")
            else ""
        ),
    }


def _request_payload(request: models.FriendRequest) -> dict:
    country_code = _normalize_country_code(request.sender_country_code)
    return {
        "requestId": request.request_id,
        "senderUserId": request.sender_user_id,
        "senderNickname": request.sender_nickname or "사용자",
        "senderGender": request.sender_gender or "unknown",
        "senderCountryCode": country_code,
        "senderCountryFlag": _country_flag(country_code),
        "senderVoiceId": request.sender_voice_id,
        "createdAt": request.created_at.isoformat() if request.created_at else "",
        "status": request.status or "pending",
    }


def _outgoing_request_payload(
    request: models.FriendRequest, db: Session
) -> dict:
    receiver_user_id = int(request.receiver_user_id)
    receiver_user = (
        db.query(models.User)
        .filter(models.User.id == receiver_user_id)
        .first()
    )
    receiver_discovery = (
        _get_active_discovery_payload(receiver_user_id, db) or {}
    )
    country_code = _normalize_country_code(
        receiver_discovery.get("country_code")
    )
    return {
        "requestId": request.request_id,
        "receiverUserId": receiver_user_id,
        "receiverNickname": receiver_discovery.get("nickname")
        or getattr(receiver_user, "username", None)
        or getattr(receiver_user, "email", "사용자").split("@")[0],
        "receiverGender": receiver_discovery.get("gender") or "unknown",
        "receiverCountryCode": country_code,
        "receiverCountryFlag": _country_flag(country_code),
        "receiverVoiceId": receiver_discovery.get("voice_id")
        or _build_voice_id(receiver_user_id),
        "createdAt": request.created_at.isoformat() if request.created_at else "",
        "status": request.status or "pending",
    }


def _friend_payload(
    friend: models.Friend, db: Optional[Session] = None
) -> dict:
    friend_user_id = friend.friend_user_id
    friend_voice_id = (
        _build_voice_id(friend_user_id)
        if friend_user_id is not None
        else None
    )
    discovery_payload = (
        _get_active_discovery_payload(friend_user_id, db)
        if friend_user_id is not None and db is not None
        else None
    )
    country_code = (
        _normalize_country_code(discovery_payload.get("country_code"))
        if discovery_payload
        else ""
    )
    gender = (
        _normalize_gender(discovery_payload.get("gender"))
        if discovery_payload
        else None
    )
    preferred_language = None
    if friend_user_id is not None and friend.friend_user is not None:
        preferred_language = getattr(
            friend.friend_user, "preferred_language", None
        )
    return {
        "id": friend.id,
        "userId": friend.user_id,
        "friendUserId": friend_user_id,
        "friendVoiceId": friend_voice_id,
        "friendUsername": (
            friend.friend_username or friend.friend_email.split("@")[0]
        ),
        "friendEmail": friend.friend_email,
        "friendPhone": friend.friend_phone,
        "friendCountryCode": country_code or None,
        "friendCountryFlag": _country_flag(country_code) or None,
        "friendGender": gender,
        "friendPreferredLanguage": preferred_language,
        "addedAt": friend.added_at.isoformat() if friend.added_at else "",
    }


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if phone is None:
        return None
    cleaned = phone.strip()
    return cleaned or None


def _normalize_display_name(display_name: Optional[str]) -> Optional[str]:
    if display_name is None:
        return None
    cleaned = display_name.strip()
    if len(cleaned) > 120:
        cleaned = cleaned[:120]
    return cleaned or None


def _resolve_friend_username(
    *,
    target_user: Optional[models.User],
    target_email: str,
    display_name: Optional[str],
) -> str:
    if target_user is not None:
        return str(target_user.username or display_name or target_email.split("@")[0])
    return str(display_name or target_email.split("@")[0])


@router.get("/users/{user_id}/friends")
def list_friends(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    current_user_id = int(current_user.id)
    if (
        current_user_id != user_id
        and not getattr(current_user, "is_admin", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 친구 목록은 조회할 수 없습니다",
        )

    friends = (
        db.query(models.Friend)
        .filter(models.Friend.user_id == user_id)
        .order_by(models.Friend.added_at.desc(), models.Friend.id.desc())
        .all()
    )
    return {
        "friends": [_friend_payload(friend, db) for friend in friends],
        "total": len(friends),
    }


@router.post("/friends/invites/request-code")
def request_friend_invite_verification_code(
    request: FriendInviteRequestCode,
    current_user=Depends(get_current_user),
) -> dict:
    from backend.marketplace.friend_invite_service import request_friend_invite_code

    try:
        return request_friend_invite_code(
            sender_user=current_user,
            target_email=str(request.targetEmail),
            phone_number=_normalize_phone(request.phoneNumber),
            display_name=_normalize_display_name(request.displayName),
            verification_channel=request.verificationChannel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/friends/invites/confirm")
def confirm_friend_invite_verification(
    request: FriendInviteConfirmRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from backend.marketplace.friend_invite_service import consume_verified_friend_invite

    try:
        verified = consume_verified_friend_invite(
            request.inviteSessionToken,
            request.verificationCode,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if int(verified.get("senderUserId") or 0) != int(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="인증 세션 사용자가 일치하지 않습니다",
        )

    target_email = str(verified.get("targetEmail") or "").strip().lower()
    phone_number = _normalize_phone(verified.get("phoneNumber"))
    display_name = _normalize_display_name(verified.get("displayName"))
    target_user = (
        db.query(models.User).filter(models.User.email == target_email).first()
    )
    if target_user is None and not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="앱 미가입 연락처는 전화번호와 함께 인증해야 저장할 수 있습니다",
        )

    if (
        existing := (
            db.query(models.Friend)
            .filter(
                models.Friend.user_id == current_user.id,
                models.Friend.friend_email == target_email,
            )
            .first()
        )
    ):
        existing.friend_user_id = target_user.id if target_user else existing.friend_user_id
        existing.friend_username = _resolve_friend_username(
            target_user=target_user,
            target_email=target_email,
            display_name=display_name or existing.friend_username,
        )
        existing.friend_phone = phone_number or existing.friend_phone
        db.commit()
        db.refresh(existing)
        return _friend_payload(existing, db)

    friend = models.Friend(
        user_id=current_user.id,
        friend_user_id=target_user.id if target_user else None,
        friend_email=target_email,
        friend_username=_resolve_friend_username(
            target_user=target_user,
            target_email=target_email,
            display_name=display_name,
        ),
        friend_phone=phone_number,
    )
    db.add(friend)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 친구입니다",
        )
    db.refresh(friend)
    return _friend_payload(friend, db)


@router.post("/friends")
def add_friend(
    request: FriendCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from backend.services.contact_verification import allow_unverified_friend_add

    if not allow_unverified_friend_add():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="친구 추가는 이메일/전화 OTP 인증이 필요합니다. /api/friends/invites/request-code → /confirm 경로를 사용하세요.",
        )
    target_email = str(request.targetEmail).strip().lower()
    phone_number = _normalize_phone(request.phoneNumber)
    display_name = _normalize_display_name(request.displayName)
    current_email = str(getattr(current_user, "email", "") or "")
    current_email = current_email.strip().lower()

    if target_email == current_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신은 친구로 추가할 수 없습니다",
        )

    target_user = (
        db.query(models.User)
        .filter(models.User.email == target_email)
        .first()
    )
    if target_user is None and not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="앱 미가입 연락처는 전화번호를 함께 입력해야 친구 연락처로 저장할 수 있습니다",
        )

    if (
        existing := (
            db.query(models.Friend)
            .filter(
                models.Friend.user_id == current_user.id,
                models.Friend.friend_email == target_email,
            )
            .first()
        )
    ):
        existing.friend_user_id = (
            target_user.id if target_user else existing.friend_user_id
        )
        existing.friend_username = _resolve_friend_username(
            target_user=target_user,
            target_email=target_email,
            display_name=display_name or existing.friend_username,
        )
        existing.friend_phone = phone_number or existing.friend_phone
        db.commit()
        db.refresh(existing)
        return _friend_payload(existing, db)

    friend = models.Friend(
        user_id=current_user.id,
        friend_user_id=target_user.id if target_user else None,
        friend_email=target_email,
        friend_username=_resolve_friend_username(
            target_user=target_user,
            target_email=target_email,
            display_name=display_name,
        ),
        friend_phone=phone_number,
    )
    db.add(friend)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 친구입니다",
        )
    db.refresh(friend)
    return _friend_payload(friend, db)


@router.delete("/friends/{friend_id}")
def remove_friend(
    friend_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    friend = (
        db.query(models.Friend)
        .filter(models.Friend.id == friend_id)
        .first()
    )
    if friend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="친구를 찾을 수 없습니다",
        )
    if (
        friend.user_id != int(current_user.id)
        and not getattr(current_user, "is_admin", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 친구 항목을 삭제할 권한이 없습니다",
        )

    db.delete(friend)
    db.commit()
    return {"status": "ok", "friendId": friend_id}


@router.post("/friends/discovery/location")
def upsert_discovery_location(
    request: DiscoveryLocationUpsertRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    user_id = int(current_user.id)
    nickname = (
        (request.nickname or getattr(current_user, "username", None) or "")
        .strip()
        or getattr(current_user, "email", "사용자").split("@")[0]
    )
    record = (
        db.query(models.FriendDiscoveryLocation)
        .filter(models.FriendDiscoveryLocation.user_id == user_id)
        .first()
    )
    if record is None:
        record = models.FriendDiscoveryLocation(user_id=user_id)
        db.add(record)

    record.nickname = nickname
    record.gender = _normalize_gender(request.gender)
    record.country_code = _normalize_country_code(request.countryCode)
    record.latitude = request.latitude
    record.longitude = request.longitude
    record.accuracy = request.accuracy
    record.share_on_map = request.shareOnMap
    record.updated_at = _utcnow()
    db.commit()
    return {
        "status": "ok",
        "userId": user_id,
        "voiceId": _build_voice_id(user_id),
    }


@router.get("/friends/discovery/nearby")
def list_nearby_discovery_users(
    lat: float,
    lon: float,
    radius_m: Optional[float] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    current_user_id = int(current_user.id)
    nearby_users = []
    apply_radius_filter = radius_m is not None and radius_m > 0
    cutoff = _utcnow() - DISCOVERY_TTL
    discovery_records = (
        db.query(models.FriendDiscoveryLocation)
        .filter(models.FriendDiscoveryLocation.updated_at >= cutoff)
        .all()
    )
    for record in discovery_records:
        payload = _discovery_record_to_payload(record)
        if (
            int(payload["user_id"]) == current_user_id
            or not payload.get("share_on_map", True)
        ):
            continue
        distance_m = _haversine_meters(
            lat, lon, payload["latitude"], payload["longitude"]
        )
        if apply_radius_filter and distance_m > radius_m:
            continue
        nearby_users.append(
            _map_user_payload(
                payload,
                distance_m,
                _friend_status(current_user_id, int(payload["user_id"]), db),
            )
        )
    nearby_users.sort(key=lambda item: item["distanceM"])
    return {
        "status": "ok",
        "users": nearby_users,
        "total": len(nearby_users),
        "viewerLatitude": lat,
        "viewerLongitude": lon,
        "radiusM": radius_m if apply_radius_filter else None,
    }


@router.post("/friends/requests")
def create_friend_request(
    request: FriendRequestCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    sender_user_id = int(current_user.id)
    receiver_user_id = int(request.receiverUserId)
    if sender_user_id == receiver_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신에게 친구 요청을 보낼 수 없습니다",
        )

    receiver_user = (
        db.query(models.User)
        .filter(models.User.id == receiver_user_id)
        .first()
    )
    if receiver_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="친구 요청 대상 사용자를 찾을 수 없습니다",
        )
    if _friend_status(sender_user_id, receiver_user_id, db) == "friend":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 친구로 등록된 사용자입니다",
        )
    if (
        _friend_status(sender_user_id, receiver_user_id, db)
        == "outgoing_pending"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 보낸 친구 요청이 있습니다",
        )

    sender_discovery = _get_active_discovery_payload(sender_user_id, db) or {}
    friend_request = models.FriendRequest(
        request_id=uuid4().hex,
        sender_user_id=sender_user_id,
        receiver_user_id=receiver_user_id,
        sender_nickname=(
            sender_discovery.get("nickname")
            or getattr(current_user, "username", None)
            or getattr(current_user, "email", "사용자").split("@")[0]
        ),
        sender_gender=sender_discovery.get("gender") or "unknown",
        sender_country_code=sender_discovery.get("country_code") or "",
        sender_voice_id=(
            sender_discovery.get("voice_id") or _build_voice_id(sender_user_id)
        ),
        status="pending",
        created_at=_utcnow(),
    )
    db.add(friend_request)
    auto_accepted = _try_proximity_auto_accept_friend_request(
        friend_request,
        current_user,
        receiver_user,
        db,
    )
    db.commit()
    db.refresh(friend_request)
    return {
        "status": "ok",
        "request": _request_payload(friend_request),
        "autoAccepted": auto_accepted,
    }


@router.get("/friends/requests/incoming")
def list_incoming_friend_requests(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    current_user_id = int(current_user.id)
    requests = [
        _request_payload(friend_request)
        for friend_request in (
            db.query(models.FriendRequest)
            .filter(
                models.FriendRequest.receiver_user_id == current_user_id,
                models.FriendRequest.status == "pending",
            )
            .order_by(
                models.FriendRequest.created_at.desc(),
                models.FriendRequest.id.desc(),
            )
            .all()
        )
    ]
    requests.sort(key=lambda item: item["createdAt"], reverse=True)
    return {"requests": requests, "total": len(requests)}


@router.get("/friends/requests/outgoing")
def list_outgoing_friend_requests(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    current_user_id = int(current_user.id)
    requests = [
        _outgoing_request_payload(friend_request, db)
        for friend_request in (
            db.query(models.FriendRequest)
            .filter(
                models.FriendRequest.sender_user_id == current_user_id,
                models.FriendRequest.status == "pending",
            )
            .order_by(
                models.FriendRequest.created_at.desc(),
                models.FriendRequest.id.desc(),
            )
            .all()
        )
    ]
    requests.sort(key=lambda item: item["createdAt"], reverse=True)
    return {"requests": requests, "total": len(requests)}


@router.post("/friends/requests/{request_id}/accept")
def accept_friend_request(
    request_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    friend_request = (
        db.query(models.FriendRequest)
        .filter(models.FriendRequest.request_id == request_id)
        .first()
    )
    if friend_request is None or friend_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대기 중인 친구 요청을 찾을 수 없습니다",
        )
    if int(friend_request.receiver_user_id) != int(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 친구 요청을 수락할 권한이 없습니다",
        )

    sender_user = (
        db.query(models.User)
        .filter(models.User.id == int(friend_request.sender_user_id))
        .first()
    )
    receiver_user = (
        db.query(models.User)
        .filter(models.User.id == int(friend_request.receiver_user_id))
        .first()
    )
    if sender_user is None or receiver_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="친구 요청 대상 사용자를 찾을 수 없습니다",
        )

    _ensure_friend_link(sender_user, receiver_user, db)
    _ensure_friend_link(receiver_user, sender_user, db)
    friend_request.status = "accepted"
    friend_request.responded_at = _utcnow()
    db.commit()
    receiver_friend = (
        db.query(models.Friend)
        .filter(
            models.Friend.user_id == receiver_user.id,
            models.Friend.friend_user_id == sender_user.id,
        )
        .first()
    )
    return {
        "status": "ok",
        "requestId": request_id,
        "friend": _friend_payload(receiver_friend, db)
        if receiver_friend is not None
        else {
            "userId": sender_user.id,
            "friendUserId": sender_user.id,
            "friendVoiceId": _build_voice_id(sender_user.id),
            "friendUsername": sender_user.username,
            "friendEmail": sender_user.email,
            "friendPhone": None,
            "friendCountryCode": None,
            "friendCountryFlag": None,
            "friendGender": None,
            "friendPreferredLanguage": getattr(
                sender_user, "preferred_language", None
            ),
            "addedAt": _utcnow().isoformat(),
            "id": 0,
        },
    }


@router.post("/friends/requests/{request_id}/reject")
def reject_friend_request(
    request_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _cleanup_discovery_state_db(db)
    friend_request = (
        db.query(models.FriendRequest)
        .filter(models.FriendRequest.request_id == request_id)
        .first()
    )
    if friend_request is None or friend_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대기 중인 친구 요청을 찾을 수 없습니다",
        )
    if int(friend_request.receiver_user_id) != int(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 친구 요청을 거절할 권한이 없습니다",
        )
    friend_request.status = "rejected"
    friend_request.responded_at = _utcnow()
    db.commit()
    return {"status": "ok", "requestId": request_id}
