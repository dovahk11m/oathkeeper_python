"""
그룹 요약 API 테스트 스크립트
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_group_summary():
    """테스트 1: 그룹 통계 요약"""
    print("=" * 60)
    print("테스트 1: POST /metrics/group/summary")
    print("=" * 60)
    
    url = f"{BASE_URL}/metrics/group/summary"
    payload = {"plan_ids": [1, 2]}
    
    print(f"요청 URL: {url}")
    print(f"요청 데이터: {json.dumps(payload, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"응답 상태: {response.status_code}")
        print(f"응답 데이터:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    
    print()

def test_group_summary_with_missing_plan():
    """테스트 2: 일부 plan_id 누락 (warnings 테스트)"""
    print("=" * 60)
    print("테스트 2: 일부 plan_id 누락 케이스")
    print("=" * 60)
    
    url = f"{BASE_URL}/metrics/group/summary"
    payload = {"plan_ids": [1, 999]}
    
    print(f"요청 URL: {url}")
    print(f"요청 데이터: {json.dumps(payload, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"응답 상태: {response.status_code}")
        print(f"응답 데이터:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    
    print()

def test_group_summary_all_missing():
    """테스트 3: 모든 plan_id 누락 (409 에러 테스트)"""
    print("=" * 60)
    print("테스트 3: 모든 plan_id 누락 케이스 (409 Conflict 예상)")
    print("=" * 60)
    
    url = f"{BASE_URL}/metrics/group/summary"
    payload = {"plan_ids": [888, 999]}
    
    print(f"요청 URL: {url}")
    print(f"요청 데이터: {json.dumps(payload, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"응답 상태: {response.status_code}")
        print(f"응답 데이터:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    
    print()

def test_group_summary_text():
    """테스트 4: 그룹 자연어 요약 (rules 모드)"""
    print("=" * 60)
    print("테스트 4: POST /metrics/group/summary/text (rules 모드)")
    print("=" * 60)
    
    url = f"{BASE_URL}/metrics/group/summary/text"
    payload = {
        "plan_ids": [1, 2],
        "mode": "rules",
        "style": "친근한 톤으로",
        "notes": "긍정적인 면을 강조해주세요"
    }
    
    print(f"요청 URL: {url}")
    print(f"요청 데이터: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"응답 상태: {response.status_code}")
        print(f"응답 데이터:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    
    print()

def test_api_docs():
    """테스트 5: API 문서 확인"""
    print("=" * 60)
    print("테스트 5: API 문서 확인")
    print("=" * 60)
    
    url = f"{BASE_URL}/docs"
    print(f"Swagger UI: {url}")
    print(f"브라우저에서 확인하세요!")
    print()

if __name__ == "__main__":
    print("\n🚀 그룹 요약 API 테스트 시작\n")
    
    test_group_summary()
    test_group_summary_with_missing_plan()
    test_group_summary_all_missing()
    test_group_summary_text()
    test_api_docs()
    
    print("=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)
