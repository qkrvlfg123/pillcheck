# CLAUDE.md — 11 맞춤 맛집 지도

## 이 앱의 목표
주변 맛집을 검색하고, 사용자 질환·복용약 기준으로 필터링·경고하는 위치 서비스.

## 스택
- 카카오 로컬 API (맛집 검색) + 카카오맵 JS SDK (지도)
- 필터링: ../../packages/shared/data 의 질환-음식 규칙
- (선택) 약물 충돌: ../../packages/shared/engine/drug_interaction.py

## 핵심 규칙
- 식당 카테고리 → 질환-음식 규칙 매핑이 이 모듈의 핵심.
- 톤은 "먹지 마세요"가 아니라 "참고하세요". 진단·처방 아님.
- 카테고리만으로 실제 메뉴를 단정하지 말 것("이런 경향" 수준 참고).
- 카카오맵 출처·로고 표기 규정 준수.
- API 키(REST/JS)는 .env, git 금지. JS 키는 도메인 제한.

## 데이터 참고
- 질환-음식 규칙: disease_food_rules.json(고령자) + office_disease_food_rules.json(직장인)
- 약물: drug_dictionary.json, drug_drug_interactions.json
