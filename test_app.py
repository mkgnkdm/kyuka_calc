"""
kyuka_calc テストスイート
実行: venv\\Scripts\\python.exe -m pytest test_app.py -v

このアプリはDBなし・保存なしの純計算ツールのため、テストは
(1) 計算エンジン leave.py の境界ケース (2) 法定テーブルの構造 (3) 画面のスモーク
（歩き通しシナリオA〜Cの機械検証）の3層で構成する。
法定テーブルの「値の正しさ」の最終確認は労務専門家（ユーザー本人）が行う——
本テストの期待値は実装者が条文から起こした下書きであり、rules.json と独立に手書きしてある
（テーブルをそのまま照合する同義反復テストにしないため）。
"""
from datetime import date

import pytest

import leave
from app import app

RULES = leave.load_rules()


# ==========================================================
# 法定テーブルの構造検証（値の検証は人間が行う。ここでは壊れ方を検出する）
# ==========================================================

class TestRulesStructure:
    def test_all_categories_have_seven_steps(self):
        """全区分が勤続7段階（6か月〜6年6か月以上）を持つ"""
        for key, cat in RULES["categories"].items():
            assert len(cat["days_by_service"]) == 7, key

    def test_days_non_decreasing(self):
        """付与日数は勤続とともに減らない"""
        for key, cat in RULES["categories"].items():
            days = cat["days_by_service"]
            assert days == sorted(days), key

    def test_proportional_less_than_full(self):
        """比例付与はフルタイムより常に少ない"""
        full = RULES["categories"]["full"]["days_by_service"]
        for key, cat in RULES["categories"].items():
            if cat["proportional"]:
                assert all(p < f for p, f in zip(cat["days_by_service"], full)), key

    def test_source_and_status_present(self):
        """出典と確認ステータスが必ず存在する（画面の根拠表示の前提）"""
        assert RULES["source"]
        assert RULES["status"] in ("draft", "verified")


# ==========================================================
# 期待値テスト（実装者が条文から手書きした下書き。ユーザー確認で確定する）
# ==========================================================

class TestStatutoryValues:
    @pytest.mark.parametrize("step, expected", [(0, 10), (1, 11), (2, 12), (3, 14), (4, 16), (5, 18), (6, 20)])
    def test_full_time_days(self, step, expected):
        """通常付与: 10,11,12,14,16,18,20"""
        assert RULES["categories"]["full"]["days_by_service"][step] == expected

    @pytest.mark.parametrize("category, step, expected", [
        ("week4", 0, 7), ("week4", 6, 15),
        ("week3", 0, 5), ("week3", 6, 11),
        ("week2", 0, 3), ("week2", 6, 7),
        ("week1", 0, 1), ("week1", 6, 3),
    ])
    def test_proportional_days_endpoints(self, category, step, expected):
        """比例付与の始点・終点（全マスの最終確認は人間が行う）"""
        assert RULES["categories"][category]["days_by_service"][step] == expected


# ==========================================================
# 計算エンジン（境界ケース）
# ==========================================================

class TestEngine:
    def test_first_grant_six_months_after_hire(self):
        grants = leave.calc_grants(date(2024, 10, 1), "full", RULES)
        assert grants[0]["grant_date"] == date(2025, 4, 1)
        assert grants[0]["days"] == 10
        assert grants[0]["service_label"] == "6か月"

    def test_grants_yearly_after_first(self):
        grants = leave.calc_grants(date(2024, 10, 1), "full", RULES)
        assert grants[1]["grant_date"] == date(2026, 4, 1)
        assert grants[2]["grant_date"] == date(2027, 4, 1)
        assert grants[2]["days"] == 12  # 勤続2年6か月

    def test_month_end_hire_clamps(self):
        """8/31入社の6か月後は2/28（月末丸め）"""
        grants = leave.calc_grants(date(2025, 8, 31), "full", RULES)
        assert grants[0]["grant_date"] == date(2026, 2, 28)

    def test_month_end_hire_leap_year(self):
        """8/31入社でうるう年に当たる場合は2/29"""
        grants = leave.calc_grants(date(2023, 8, 31), "full", RULES)
        assert grants[0]["grant_date"] == date(2024, 2, 29)

    def test_final_step_capped(self):
        """勤続6年6か月以降は上限で頭打ち（フルタイム20日）"""
        grants = leave.calc_grants(date(2018, 4, 1), "full", RULES)
        assert grants[-1]["days"] == 20
        assert grants[-1]["is_final_step"] is True

    def test_proportional_week1(self):
        grants = leave.calc_grants(date(2024, 10, 1), "week1", RULES)
        assert grants[0]["days"] == 1

    def test_next_grant_picks_future(self):
        grants = leave.calc_grants(date(2024, 10, 1), "full", RULES)
        nxt = leave.next_grant(grants, today=date(2026, 7, 13))
        assert nxt["grant_date"] == date(2027, 4, 1)
        assert nxt["days"] == 12

    def test_next_grant_beyond_table(self):
        """勤続が表示範囲を超えた古参でも「次回の付与」が合成される（毎年同日数）"""
        grants = leave.calc_grants(date(2000, 4, 1), "full", RULES)
        nxt = leave.next_grant(grants, today=date(2026, 7, 13))
        assert nxt["grant_date"] == date(2026, 10, 1)
        assert nxt["days"] == 20


# ==========================================================
# 基準日方式（一斉付与・§9-2）
# ==========================================================

class TestBaseDateEngine:
    def test_scenario_d_values(self):
        """歩き通しシナリオD: 入社2024-06-01・週5日以上・基準日4/1"""
        grants = leave.calc_grants_base_date(date(2024, 6, 1), "full", 4, 1, RULES)
        assert grants[0]["grant_date"] == date(2024, 12, 1)
        assert grants[0]["days"] == 10
        assert grants[1]["grant_date"] == date(2025, 4, 1)
        assert grants[1]["days"] == 11
        assert grants[1]["legal_date"] == date(2025, 12, 1)  # 前倒し表示の元になる法定日
        assert grants[2]["grant_date"] == date(2026, 4, 1)
        assert grants[2]["days"] == 12

    def test_matching_hire_date_equals_legal(self):
        """入社日と基準日が一致するケース: 法定原則と全行同一になる（テスト2）"""
        legal = leave.calc_grants(date(2024, 10, 1), "full", RULES)
        company = leave.calc_grants_base_date(date(2024, 10, 1), "full", 4, 1, RULES)
        for l, c in zip(legal, company):
            assert l["grant_date"] == c["grant_date"]
            assert l["days"] == c["days"]

    @pytest.mark.parametrize("hire", [
        date(2020, 1, 15), date(2021, 5, 31), date(2022, 8, 31),
        date(2023, 2, 28), date(2024, 11, 20),
        date(2026, 8, 28),  # 初回付与が非うるう年の2/28になる要注意パターン（2/29問題の実証入社日）
    ])
    @pytest.mark.parametrize("category", ["full", "week3"])
    @pytest.mark.parametrize("base_month, base_day", [(4, 1), (1, 1), (10, 15), (2, 28)])
    def test_invariant_company_never_later_than_legal(self, hire, category, base_month, base_day):
        """不変条件（テスト3・適法性の担保）: company の各付与日 <= 法定の各付与日"""
        legal = leave.calc_grants(hire, category, RULES)
        company = leave.calc_grants_base_date(hire, category, base_month, base_day, RULES)
        for l, c in zip(legal, company):
            assert c["grant_date"] <= l["grant_date"]

    def test_feb29_base_date_can_violate_invariant_hence_blocked_at_ui(self):
        """基準日2/29はエンジン上、法定より1日遅い付与を生みうる（実証ケース）。
        このため画面側で入力を禁止している（TestScreens::test_feb29_base_date_rejected）。"""
        legal = leave.calc_grants(date(2026, 8, 28), "full", RULES)
        company = leave.calc_grants_base_date(date(2026, 8, 28), "full", 2, 29, RULES)
        violations = [1 for l, c in zip(legal, company) if c["grant_date"] > l["grant_date"]]
        assert violations  # 違反が実在することの記録（だからUIで2/29を弾く）

    def test_base_date_feb29_clamps_to_feb28_in_common_year(self):
        """基準日2/29 → 非うるう年は2/28に丸める（テスト4）"""
        grants = leave.calc_grants_base_date(date(2024, 6, 1), "full", 2, 29, RULES)
        # 2025年は非うるう年 → 2/28、2028年はうるう年 → 2/29 のままになる行を確認する
        non_leap = [g for g in grants if g["grant_date"].year == 2025]
        assert non_leap and non_leap[0]["grant_date"] == date(2025, 2, 28)
        leap = [g for g in grants if g["grant_date"].year == 2028]
        assert leap and leap[0]["grant_date"] == date(2028, 2, 29)

    def test_next_grant_works_with_base_date(self):
        """next_grant が基準日方式の一覧でも正しく動く"""
        grants = leave.calc_grants_base_date(date(2024, 6, 1), "full", 4, 1, RULES)
        nxt = leave.next_grant(grants, today=date(2025, 5, 1))
        assert nxt["grant_date"] == date(2026, 4, 1)
        assert nxt["days"] == 12


# ==========================================================
# 画面スモーク（歩き通しシナリオA〜Cの機械検証）
# ==========================================================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestScreens:
    def test_scenario_a_landing_is_minimal(self, client):
        """シナリオA-1: 初期表示は入力フォームのみ（結果表・エラーが出ていない）"""
        text = client.get("/").get_data(as_text=True)
        assert "入社日" in text and "週の所定労働日数" in text and "計算する" in text
        assert "次回の付与" not in text

    def test_scenario_a_calculation(self, client):
        """シナリオA-2〜3: フルタイム計算で履歴表と次回付与が出る"""
        text = client.get("/?hire_date=2024-10-01&category=full").get_data(as_text=True)
        assert "次回の付与" in text
        assert "2025-04-01" in text and "10日" in text
        assert "2027-04-01" in text and "12日" in text
        assert "出勤率8割" in text  # 注記
        assert "計算の根拠" in text  # 根拠の折りたたみ

    def test_scenario_b_proportional(self, client):
        """シナリオB: 週3日で比例付与の説明と日数が出る"""
        text = client.get("/?hire_date=2024-10-01&category=week3").get_data(as_text=True)
        assert "比例付与" in text
        assert "5日" in text  # 勤続6か月

    def test_scenario_c_invalid_input(self, client):
        """シナリオC: 不正入力は同じ画面で優しくエラー（結果は出ない）"""
        text = client.get("/?hire_date=&category=full").get_data(as_text=True)
        assert "入社日を入力してください" in text
        assert "次回の付与" not in text

    def test_scenario_c_unrealistic_year(self, client):
        text = client.get("/?hire_date=1900-01-01&category=full").get_data(as_text=True)
        assert "現実的な範囲" in text

    def test_feb29_base_date_rejected(self, client):
        """基準日2/29は入力段階で禁止（適法でない結果を表示しうるため。検品 2026-07-13）"""
        text = client.get(
            "/?hire_date=2026-08-28&category=full&method=base_date&base_month=2&base_day=29"
        ).get_data(as_text=True)
        assert "2月29日は基準日に指定できません" in text
        assert "次回の付与" not in text

    def test_draft_warning_shown_until_verified(self, client):
        """法定表が未確認（draft）の間は警告が出る（確認後に消える仕組みの検証）"""
        text = client.get("/").get_data(as_text=True)
        if RULES["status"] != "verified":
            assert "下書き" in text
        else:
            assert "下書き（専門家の確認前）" not in text

    def test_security_headers(self, client):
        resp = client.get("/")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_scenario_d_base_date_fields_appear_and_shown(self, client):
        """シナリオD-1: 基準日方式を選ぶと基準日欄が現れる（選択保持・値の反映を確認）"""
        text = client.get("/?method=base_date").get_data(as_text=True)
        assert "基準日（月）" in text and "基準日（日）" in text
        assert 'id="base-date-fields" style="display:block;"' in text

    def test_scenario_d_calculation_shows_front_load_and_explanation(self, client):
        """シナリオD-2〜3: 前倒し表示・方式の説明文が出る"""
        text = client.get(
            "/?hire_date=2024-06-01&category=full&method=base_date&base_month=4&base_day=1"
        ).get_data(as_text=True)
        assert "2024-12-01" in text and "2025-04-01" in text and "2026-04-01" in text
        assert "法定 2025-12-01 を前倒し" in text
        assert "初回のみ法定" in text  # 方式の説明文

    def test_base_date_invalid_input_shows_friendly_error(self, client):
        """テスト5: 月日として不正な基準日は優しいエラー（画面遷移しない）"""
        text = client.get(
            "/?hire_date=2024-06-01&category=full&method=base_date&base_month=13&base_day=1"
        ).get_data(as_text=True)
        assert "基準日が正しくありません" in text
        assert "次回の付与" not in text
