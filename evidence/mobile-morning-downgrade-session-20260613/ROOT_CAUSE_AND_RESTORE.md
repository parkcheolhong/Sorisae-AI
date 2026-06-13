# 2026-06-13 모바일 APK 혼선 사고 — 해명 및 복원 기록

## 1. 혼선의 근본 원인

### 원인 A: 잘못된 작업 방향 (다운그레이드를 업그레이드로 보고)
- 사용자 요청: **기능 개선·업그레이드**
- 실제 수행: `App.tsx` **8,420줄 삭제** (채팅·친구·WebView·OCR 등 제거)
- `translate.ts`에서 `translateImage`·`region_hint` 삭제
- versionCode만 27→31로 연속 증가 → **겉으로는 버전이 올라가지만 기능은 줄어듦**

### 원인 B: 검증 없이 연속 빌드·설치
- typecheck 실패 상태에서도 Gradle만 성공하면 APK 생성됨
- build27~31을 **2시간 내 5회** 연속 빌드, 단말기에 build30/31 설치
- **기능 번들 문자열 검증 없음** (translateImage 등 삭제 감지 안 됨)

### 원인 C: 복구 과정에서 이중 혼선
- 오후: build32로 App.tsx HEAD 복구
- 이후: build33에 **미검증 wiring** (`useVoipIncomingCalls` 등) 추가
- 사용자 체감: "복구했다는데도 안 됨" — **검증된 build26이 아닌 새 조합을 또 올림**

### 원인 D: Git 기준선과 실제 빌드 기준선 불일치
- Git HEAD: `1.0.23` / versionCode 24
- 검증 완료 빌드: `1.0.25` / versionCode **26** (로컬 미커밋 상태에서 빌드)
- 에이전트가 HEAD/스테이징/워킹트리/build31/build33을 **섞어서** 작업

---

## 2. 타임라인

| 시각 | 빌드 | APK 크기 | JS번들 | 상태 |
|------|------|----------|--------|------|
| 06-12 06:37 | **build26** | 37.37MB | 1,545KB | ✅ 정식 검증 완료 |
| 06-13 02:06~02:47 | build27~31 | 37.24MB | 1,278KB | ❌ 기능 삭제 |
| 06-13 14:33 | build32 | 37.36MB | 1,524KB | App.tsx 복구 |
| 06-13 15:02 | build33 | 37.36MB | 1,524KB | wiring 추가 (미검증) |

---

## 3. 이 폴더 보관물

| 파일 | 설명 |
|------|------|
| `nadotongryoksa-v1.0.25-build26-baseline-good.apk` | **정상 기준선** (복원 대상) |
| `nadotongryoksa-v1.0.25-build31-morning-downgrade.apk` | 아침 다운그레이드 산출물 |
| `App.tsx.morning-gutted-summary.md` | 아침 App.tsx 삭제 내역 (소스 유실, APK로만 증명) |
| `translate.ts.morning-regressed.ts` | 아침 translate.ts 퇴행 상태 기록 |
| `translate.ts.good-baseline.ts` | 정상 translate.ts |
| `App.tsx-afternoon-build33-wiring.diff` | 오후 build33에서 추가한 diff |
| `app.json-changes.diff` | app.json 변경 이력 |

---

## 4. 복원 조치 (2026-06-13)

1. 소스: `App.tsx` → Git HEAD (build26과 동일 기능), `app.json` → 1.0.25 / versionCode **34**
   - 단말기에 build33이 설치되어 versionCode 26 APK는 downgrade 불가 → **build26 동일 소스로 build34 재빌드**
2. 마켓플레이스: `nadotongryoksa-v1.0.25-build34-current.apk` 게시 (build26 기능 동일, 번들 검증 완료)
3. 단말기 2대: build34 APK 재설치
4. build27~33은 이 폴더에만 보관, 배포 경로에서 제외

### build34 vs build26 번들 검증

| 기능 | build26 | build34 |
|------|---------|---------|
| translateImage | ✅ | ✅ |
| ChatRoomListScreen | ✅ | ✅ |
| FriendMapDiscoveryScreen | ✅ | ✅ |
| WebView | ✅ | ✅ |
| useVoipIncomingCalls | ❌ | ❌ |

---

## 5. 재발 방지 (권장)

- `publish_worldlinco_apk.ps1`에 번들 필수 문자열 게이트 추가
- App.tsx 줄 수 급감(>500줄) 시 빌드 중단
- versionCode 증가 시 이전 APK 대비 번들 크기·기능 diff 리포트 필수
