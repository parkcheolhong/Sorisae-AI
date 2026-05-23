import zipfile
import sys
import os

zip_path = r"D:\프로제트별모음\에이전트 모델파일\codeAI_2026_04_11.zip"
extract_path = r"C:\Users\WORK\source\repos\parkcheolhong\codeAI\tmp\codeAI_2026_04_11_extracted"

if not os.path.exists(zip_path):
    print(f"오류: {zip_path} 파일을 찾을 수 없습니다.")
    sys.exit(1)

os.makedirs(extract_path, exist_ok=True)

try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        total_files = len(file_list)
        print(f"총 {total_files}개의 파일 압축을 해제합니다...")
        print(f"대상 경로: {extract_path}\n")

        extracted_count = 0
        for file in file_list:
            file_info = zip_ref.getinfo(file)
            size_mb = file_info.file_size / (1024 * 1024)
            
            # 용량이 100MB 이상인 큰 파일은 미리 알려주기
            if size_mb > 100:
                print(f"\n[대용량 파일 해제 중...] {file} ({size_mb:.1f} MB)")
                
            zip_ref.extract(file, extract_path)
            extracted_count += 1
            
            # 진행률 출력 (1% 단위 또는 100개 단위)
            if extracted_count % max(1, total_files // 100) == 0 or extracted_count == total_files:
                percent = (extracted_count / total_files) * 100
                sys.stdout.write(f"\r진행률: [{percent:.1f}%] ({extracted_count}/{total_files} 파일 해제 완료)")
                sys.stdout.flush()

    print("\n\n압축 해제가 완료되었습니다!")
except zipfile.BadZipFile:
    print("\n오류: 압축 파일이 손상되었거나 올바른 ZIP 파일이 아닙니다.")
except Exception as e:
    print(f"\n오류 발생: {e}")
