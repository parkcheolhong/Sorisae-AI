import json
import urllib.request

try:
    response = urllib.request.urlopen("http://127.0.0.1:8000/api/marketplace/projects")
    data = json.loads(response.read().decode("utf-8"))
    
    print(f"API 응답 키: {list(data.keys())}")
    print(f"projects 개수: {len(data.get('projects', []))}")
    
    # sorisae 상품 검색
    projects = data.get('projects', [])
    sorisae_items = [p for p in projects if 'sorisae' in p.get('title', '').lower()]
    
    print(f"\nsorisae 검색 결과: {len(sorisae_items)}개")
    for item in sorisae_items:
        print(f"  ID {item['id']}: {item['title']}")
    
    # ID 10 직접 검색
    id10 = [p for p in projects if p['id'] == 10]
    print(f"\nID 10: {len(id10)}개")
    if id10:
        print(f"  제목: {id10[0]['title']}")
    
    # 전체 ID 목록
    print(f"\n전체 상품 ID: {sorted([p['id'] for p in projects])}")
    
except Exception as e:
    print(f"오류: {e}")
