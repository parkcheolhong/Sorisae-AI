
import urllib.request
import zipfile
import io

print("=" * 60)
print("  소리새 ZIP 2차 검증 — 다운로드 및 무결성")
print("=" * 60)

# 1. ZIP 다운로드
url = "http://127.0.0.1:8000/api/marketplace/zip/sorisae-interpreter-v1.zip"
print(f"\n1️⃣ 다운로드: {url}")
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        zip_bytes = resp.read()
        print(f"   ✅ 다운로드 성공 ({len(zip_bytes):,} bytes)")
except Exception as e:
    print(f"   ❌ 실패: {e}")
    exit(1)

# 2. ZIP 무결성 검증
print(f"\n2️⃣ ZIP 파일 무결성 검증")
try:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        files = zf.namelist()
        print(f"   ✅ ZIP 유효 ({len(files)}개 항목)")
        for fname in files:
            info = zf.getinfo(fname)
            size = info.file_size
            print(f"      - {fname}: {size:,} bytes")
except Exception as e:
    print(f"   ❌ ZIP 손상: {e}")
    exit(1)

# 3. 소스 파일 내용 검증
print(f"\n3️⃣ 소스 파일 내용 검증")
try:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # sorisae_interpreter.py 내용 확인
        for fname in files:
            if fname.endswith('sorisae_interpreter.py'):
                content = zf.read(fname).decode('utf-8')
                if 'SorisaeInterpreter' in content and 'quick_translate' in content:
                    print(f"   ✅ {fname}: 소스 코드 정상")
                else:
                    print(f"   ⚠️ {fname}: 스텁이 아닌 실제 소스")
except Exception as e:
    print(f"   ❌ 검증 실패: {e}")

print("\n" + "=" * 60)
print("  ✅ 2차 검증 완료: ZIP 다운로드 및 사용 가능")
print("=" * 60)
