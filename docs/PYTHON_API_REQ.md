# Python AI 서버 신규 API 요청 명세서 (v2)

- **요청일:** 2025-11-25
- **작성자:** Oath Spring 서버 개발팀
- **목적:** 그룹(채팅방) 단위의 누적 통계 및 요약 기능을 구현하기 위해 Python AI 서버에 필요한 신규 API를 요청합니다. (v1에서 일부 요구사항 변경)

---

## 1. 그룹 통합 요약 API (단일 API)

### 1.1. 변경 요약

- 기존에 제안했던 2개의 API(`.../summary`, `.../summary/text`)를 **하나의 API로 통합**하여, 한 번의 요청으로 **구조화된 통계 데이터**와 **자연어 요약 텍스트**를 모두 받을 수 있도록 변경합니다.
- Spring 서버에서는 이 API를 비동기적으로 호출하고, 그 결과를 DB에 저장하여 사용자에게 제공할 예정입니다.

### 1.2. 제안 API

- **Endpoint**: `POST /metrics/group/summary`
- **Description**: 여러 `plan_id`에 대한 `metrics` 데이터를 종합하여, 그룹 전체의 누적 통계와 LLM 기반의 자연어 요약을 함께 계산하여 반환합니다.

### 1.3. 요청 형식 (Spring → Python)

- Request Body에 분석할 `plan_id` 목록과 LLM 옵션을 함께 전달합니다.

```json
{
  "plan_ids": [1, 5, 12, 23],
  "style": "데이터 분석가처럼 객관적인 톤으로",
  "notes": "지각 빈도가 높은 경향이 있는지 분석해주세요."
}
```

### 1.4. 필요 로직 (Python 측)

1.  Request Body로부터 `plan_ids` 목록과 `style`, `notes` 등의 옵션을 받습니다.
2.  각 `plan_id`에 해당하는 `data/plan_{id}/metrics.jsonl` 파일의 모든 기록을 읽어들입니다.
3.  모든 `plan`의 `metrics` 데이터를 합산하여, 그룹 전체의 누적/평균 통계(`group_summary`)를 계산합니다.
4.  계산된 누적 통계 데이터와 `style`, `notes` 옵션을 조합하여 LLM에 전달할 프롬프트를 생성합니다.
5.  LLM으로부터 받은 자연어 텍스트(`text_summary`)를 정제합니다.
6.  `group_summary`와 `text_summary`를 **하나의 JSON 객체**에 담아 응답합니다.

### 1.5. 예상 응답 (Python → Spring)

- `data` 필드에 `group_summary`와 `text_summary`가 모두 포함된 형태를 요청합니다.

```json
{
  "success": true,
  "data": {
    "group_summary": {
      "total_plans_analyzed": 4,
      "total_records": 128,
      "total_distance_km": 258.4,
      "avg_distance_per_plan_km": 64.6,
      "total_late_minutes": 45,
      "avg_late_minutes_per_plan": 11.25
    },
    "text_summary": "분석된 4개의 약속에 따르면, 이 그룹은 약속당 평균 64.6km를 이동했으며, 평균 11.25분의 지각 시간을 기록했습니다. 전반적으로 장거리 이동이 잦고, 약속 시간을 준수하는 데 약간의 어려움이 있는 경향을 보입니다."
  }
}
```

---

## 2. 오류 처리 및 엣지 케이스 (v1과 동일)

### 2.1. 요청 `plan_ids` 중 일부에 문제가 있는 경우

- **정책**: API는 `404 Not Found`와 같은 에러를 반환하는 대신, **`200 OK`를 유지**하면서 응답 본문에 `warnings` 필드를 추가하여 해당 상황을 알려주는 것을 제안합니다.
- **사유**: 일부 데이터가 없더라도, 분석 가능한 데이터만으로 **부분적인 성공** 결과를 받을 수 있어 서비스 안정성이 높아집니다.
- **예상 응답 (일부 ID 누락 또는 데이터 없는 경우)**:

```json
{
  "success": true,
  "data": {
    "group_summary": {
      "total_plans_analyzed": 3,
      "total_distance_km": 210.1,
      ...
    },
    "text_summary": "분석된 3개의 약속에 따르면..."
  },
  "warnings": [
    "plan_id '15' was not found.",
    "plan_id '23' has no metrics data."
  ]
}
```

### 2.2. 모든 `plan_ids`에 문제가 있는 경우

- **정책**: 분석할 데이터가 전혀 없는 경우에는 `409 Conflict` 에러와 함께 명확한 에러 메시지를 반환하는 것을 제안합니다.
- **예상 응답**:

```json
{
  "success": false,
  "data": null,
  "message": "No data available for the given plan_ids."
}
```

---

위 수정된 명세에 대한 검토 및 구현 가능 여부에 대한 회신 부탁드립니다. 감사합니다.
