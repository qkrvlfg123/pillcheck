"""
엔진 회귀 테스트

실행:  python tests/test_engine.py      (추가 설치 없이 실행)
       pytest tests/                    (pytest가 있으면)

실제로 발생했던 오류가 다시 생기지 않는지 검사한다.
"""
import filecmp
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "10-review-chatbot", "app"))   # drug_advisor (+ 번들 엔진)

import drug_advisor as advisor          # noqa: E402
import drug_interaction as engine       # noqa: E402  (advisor가 경로를 추가한 뒤 import)


def rid(query):
    d = engine.resolve_drug(query)
    return d["drug_id"] if d else None


def check(names, **kw):
    return engine.check(names, **kw)


def rules(names):
    return {r["interaction_id"] for r in check(names)["axis1_interactions"]}


def level(names, **kw):
    return check(names, **kw)["overall_risk"]["level"]


# ---------------------------------------------------------------- 이름 해석

def test_partial_strings_do_not_resolve():
    """이전 버그: 부분 문자열 일치라서 빈 문자열·'제'가 와파린으로, '진통제'가 소염진통제로 해석됐다."""
    for q in ["", " ", "제", "약", "정", "피린", "처방", "진통제", "두통약", "위장약"]:
        assert rid(q) is None, q


def test_ambiguous_class_words_do_not_resolve():
    """둘 이상의 약물군에 걸리는 말은 엔진이 임의로 고르지 않는다."""
    for q in ["혈압약", "항우울제", "항생제", "수면제", "위장약"]:
        assert rid(q) is None, q


def test_brand_family_does_not_resolve_to_one_member():
    """이전 버그: '이지엔6'(5종 중 불명)가 아세트아미노펜 제품으로, '타이레놀콜드'가 일반 타이레놀로 해석됐다."""
    assert rid("이지엔6") is None
    assert rid("타이레놀콜드") is None
    assert rid("이지엔6에이스") == "PROD:이지엔6에이스"
    assert rid("이지엔6프로") == "PROD:이지엔6프로"


def test_exact_names_and_forms_resolve():
    assert rid("와파린") == rid("Warfarin") == rid("warfarin") == rid("와파린나트륨") == "RX001"
    assert rid("타이레놀") == rid("타이레놀정") == rid("타이레놀8시간이알서방정") == "PROD:타이레놀"
    assert rid("리피토정") == "PROD:리피토"
    assert rid("RX004") == "RX004"


# ---------------------------------------------------------------- 병용금기·주의

def test_product_names_trigger_pair_rules():
    """이전 버그: 제품명으로 입력한 약은 'PROD:' ID만 가져서 규칙이 하나도 걸리지 않았다."""
    assert rules(["와파린", "타이레놀"]) == rules(["와파린", "타이레놀정"]) == {"DDI002"}
    assert rules(["와파린", "리피토정"]) == {"DDI012"}
    assert rules(["디오반", "부루펜"]) == rules(["디오반", "탁센"]) == {"DDI003"}
    assert rules(["씬지로이드정", "겔포스"]) == {"DDI006"}
    assert "DDI001" in rules(["와파린", "탁센"])
    assert level(["디오반", "탁센"]) == "높음"


def test_combination_product_uses_each_ingredient():
    """복합제는 성분별로 규칙을 찾는다: 게보린(아세트아미노펜 + 카페인) + 스틸녹스 → 카페인–수면제 규칙."""
    assert "DDI016" in rules(["게보린", "스틸녹스"])
    assert "DDI002" in rules(["와파린", "판피린"])       # 종합감기약의 아세트아미노펜


def test_statin_rule_fires_on_macrolide_not_quinolone():
    """이전 버그: 근거가 마크로라이드인 규칙(DDI004)이 테트라사이클린·퀴놀론 계열에 연결돼 있었다."""
    assert "DDI004" in rules(["리피토", "클래리스로마이신"])
    assert "DDI004" in rules(["리피토", "에리트로마이신"])
    assert "DDI004" not in rules(["리피토", "크라비트"])       # 레보플록사신(퀴놀론)
    assert "DDI019" in rules(["야스민", "리팜핀"])
    assert "DDI019" not in rules(["야스민", "크라비트"])


# ---------------------------------------------------------------- 중복·개수

def test_same_drug_listed_twice_counts_once():
    """이전 버그: 같은 약의 다른 표기가 따로 세어져 '아세트아미노펜 중복'이 나왔다."""
    r = check(["타이레놀", "타이레놀정"])
    assert r["axis3_polypharmacy"]["count"] == 1 and not r["axis2_duplicates"]
    r = check(["타이레놀", "아세트아미노펜"])          # 제품명과 그 성분명
    assert r["axis3_polypharmacy"]["count"] == 1 and not r["axis2_duplicates"]


def test_real_duplicates_are_still_flagged():
    titles = [f["title"] for f in check(["타이레놀", "게보린"])["axis2_duplicates"]]
    assert any("아세트아미노펜" in t for t in titles)
    titles = [f["title"] for f in check(["타이레놀", "써스펜"])["axis2_duplicates"]]   # 서로 다른 제품
    assert any("아세트아미노펜" in t for t in titles)


# ---------------------------------------------------------------- 모르는 약

def test_unknown_drugs_are_not_reported_as_low_risk():
    """이전 버그: 모르는 약 두 개를 넣으면 '낮음'이 나왔다."""
    r = check(["듣보약", "모르는약"])
    assert r["overall_risk"]["code"] == "UNKNOWN" and r["overall_risk"]["level"] == "판단 불가"
    assert r["axis3_polypharmacy"]["count"] == 2          # 모르는 약도 복용 중인 약으로 센다
    assert level(["", ""]) == "판단 불가"                  # 빈 입력
    assert level(["타이레놀"]) == "판단 불가"              # 약 하나로는 상호작용을 말할 수 없다


def test_known_findings_survive_unknown_drug():
    r = check(["와파린", "부루펜", "듣보약"])
    assert r["overall_risk"]["level"] == "높음"
    assert any("듣보약" in reason for reason in r["overall_risk"]["reasons"])


def test_five_drugs_is_polypharmacy_even_if_unknown():
    assert check(["가나약", "다라약", "마바약", "사아약", "자차약"])["axis3_polypharmacy"]["level"] == "HIGH"


# ---------------------------------------------------------------- 근거 표시·노인주의

def test_report_never_claims_official_dur_data():
    """이전 버그: DUR API를 호출하지 않는데 키만 있으면 '식약처 DUR 공식 데이터 기준'이라고 표시했다."""
    os.environ["DUR_SERVICE_KEY"] = "dummy"
    try:
        r = check(["와파린", "부루펜"])
        report = engine.format_report(r)
    finally:
        del os.environ["DUR_SERVICE_KEY"]
    assert r["mode"] == "LOCAL_RULES"
    assert "공식 데이터 기준" not in report and "자체 구축 규칙" in report


def test_elderly_section_is_conditional_when_age_unknown():
    names = ["부루펜", "자낙스"]
    assert "[노인주의 — 65세 이상인 경우]" in engine.format_report(check(names))
    assert "[노인주의]" in engine.format_report(check(names, age=70))
    assert "노인주의" not in engine.format_report(check(names, age=40))


# ---------------------------------------------------------------- 채팅 추출

def test_chat_does_not_count_one_drug_many_times():
    """이전 버그: '타이레놀8시간이알서방정' 하나가 2~4개의 약으로 추출됐다."""
    assert advisor.extract_drug_names("타이레놀8시간이알서방정 하나") == ["타이레놀8시간이알서방정"]
    assert advisor.extract_drug_names("아스피린프로텍트") == ["아스피린프로텍트"]
    assert sorted(advisor.extract_drug_names("넥시움정 리피토정")) == ["넥시움정", "리피토정"]
    assert sorted(advisor.extract_drug_names("와파린나트륨 먹는데 부루펜")) == ["부루펜", "와파린나트륨"]


def test_chat_does_not_read_conditions_as_drugs():
    """이전 버그: '혈압이 높은데'를 혈압약 복용으로, '당뇨가 있는데'를 당뇨약 복용으로 읽었다."""
    assert advisor.extract_drug_names("혈압이 높은데 타이레놀 먹어도 되나") == ["타이레놀"]
    assert len(advisor.extract_drug_names("당뇨가 있는데 감기약 먹어도 돼?")) == 1
    assert len(advisor.extract_drug_names("혈압약이랑 타이레놀 같이 먹어도 돼?")) == 2


def test_chat_routing_keywords():
    """이전 버그: '약', '같이'가 들어가면 무조건 약물 상담으로 보냈다."""
    assert not advisor.is_drug_question("예약 변경하고 싶어요")
    assert not advisor.is_drug_question("같이 쓰기 좋은 청소기 추천")
    assert advisor.is_drug_question("타이레놀이랑 부루펜 같이 먹어도 돼?")
    assert advisor.is_drug_question("이 약 부작용이 뭐예요")


# ---------------------------------------------------------------- 배포 번들

def test_deploy_bundles_match_source():
    """apps/* 안의 엔진·데이터 복사본은 배포용 번들이다. 원본과 내용이 같아야 한다."""
    shared = os.path.join(ROOT, "packages", "shared")
    bundles = [os.path.join(ROOT, "apps", "10-review-chatbot", "shared"),
               os.path.join(ROOT, "apps", "voice-assistant", "api", "_bundle", "shared")]
    files = ["engine/drug_interaction.py", "dur_client/product_resolver.py",
             "data/drug_dictionary.json", "data/drug_drug_interactions_demo.json",
             "data/product_ingredient_map.json", "data/evidence_sources.json"]
    for b in bundles:
        for f in files:
            assert filecmp.cmp(os.path.join(shared, f), os.path.join(b, f), shallow=False), (b, f)
    assert filecmp.cmp(os.path.join(ROOT, "apps", "10-review-chatbot", "app", "drug_advisor.py"),
                       os.path.join(ROOT, "apps", "voice-assistant", "api", "_bundle", "app", "drug_advisor.py"),
                       shallow=False)


def test_every_rule_points_to_existing_drugs():
    ids = {d["drug_id"] for d in engine.DRUG_DICT}
    for r in engine.DEMO_INTERACTIONS:
        assert r["drug_a"] in ids and r["drug_b"] in ids, r["interaction_id"]


def test_dur_is_opt_in_and_default_is_local():
    """기본(use_dur 미지정)은 로컬 규칙만. 결과에 dur 키가 없고 mode는 LOCAL_RULES."""
    r = check(["타이레놀", "게보린"])
    assert r["mode"] == "LOCAL_RULES"
    assert "dur" not in r


def test_dur_augment_is_offline_safe_without_key():
    """DUR 키가 없으면 네트워크 호출 없이 available=False로만 표시하고 로컬 결과는 유지한다."""
    saved = getattr(engine.dur_api, "SERVICE_KEY", "")
    try:
        engine.dur_api.SERVICE_KEY = ""          # 키 없는 상황을 강제(네트워크 호출 안 함)
        r = engine.check(["타이레놀", "게보린"], use_dur=True)
        assert r["dur"]["available"] is False
        # 로컬 판정은 그대로 살아 있어야 한다
        assert "overall_risk" in r and "axis1_interactions" in r
        # 보고서가 깨지지 않고, 거짓으로 공식 데이터를 조회했다고 하지 않는다
        rep = engine.format_report(r)
        assert "식약처 DUR 공식 데이터 실시간 조회" not in rep
    finally:
        engine.dur_api.SERVICE_KEY = saved


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as err:
            failed += 1
            print(f"FAIL  {name}: {err}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
