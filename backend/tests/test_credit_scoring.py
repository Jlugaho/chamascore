import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scoring.heuristic_model import HeuristicCreditScorer, engineer_features_from_raw


@pytest.fixture
def scorer():
    return HeuristicCreditScorer()

@pytest.fixture
def excellent_raw():
    return {'group_age_days':1095,'avg_contribution':2000,'stddev_contribution':50,'total_contributions':750000,'active_members':20,'total_ever_members':21,'contribution_amount':2000,'repaid_loans_count':60,'defaulted_loans_count':0,'total_savings':500000,'active_loans_total':80000,'meetings_held_30d':4,'actual_attendance_30d':76,'loans_disbursed_90d':10,'defaults_90d':0}

@pytest.fixture
def poor_raw():
    return {'group_age_days':30,'avg_contribution':500,'stddev_contribution':400,'total_contributions':2000,'active_members':3,'total_ever_members':10,'contribution_amount':1000,'repaid_loans_count':1,'defaulted_loans_count':4,'total_savings':2000,'active_loans_total':30000,'meetings_held_30d':1,'actual_attendance_30d':1,'loans_disbursed_90d':3,'defaults_90d':2}

@pytest.fixture
def zero_raw():
    return {k: 0 for k in ['group_age_days','avg_contribution','stddev_contribution','total_contributions','active_members','total_ever_members','contribution_amount','repaid_loans_count','defaulted_loans_count','total_savings','active_loans_total','meetings_held_30d','actual_attendance_30d','loans_disbursed_90d','defaults_90d']}


class TestScoreRange:
    def test_excellent_group_in_range(self, scorer, excellent_raw):
        score, _ = scorer.calculate_score(engineer_features_from_raw(excellent_raw))
        assert 300 <= score <= 850

    def test_poor_group_in_range(self, scorer, poor_raw):
        score, _ = scorer.calculate_score(engineer_features_from_raw(poor_raw))
        assert 300 <= score <= 850

    def test_empty_features_in_range(self, scorer):
        score, _ = scorer.calculate_score({})
        assert 300 <= score <= 850

    def test_zero_group_in_range(self, scorer, zero_raw):
        score, _ = scorer.calculate_score(engineer_features_from_raw(zero_raw))
        assert 300 <= score <= 850


class TestScoreLogic:
    def test_excellent_beats_poor(self, scorer, excellent_raw, poor_raw):
        e_score, _ = scorer.calculate_score(engineer_features_from_raw(excellent_raw))
        p_score, _ = scorer.calculate_score(engineer_features_from_raw(poor_raw))
        assert e_score > p_score

    def test_excellent_group_above_700(self, scorer, excellent_raw):
        score, _ = scorer.calculate_score(engineer_features_from_raw(excellent_raw))
        assert score >= 700

    def test_poor_group_below_600(self, scorer, poor_raw):
        score, _ = scorer.calculate_score(engineer_features_from_raw(poor_raw))
        assert score < 600

    def test_better_repayment_improves_score(self, scorer, poor_raw):
        base_score, _ = scorer.calculate_score(engineer_features_from_raw(poor_raw))
        better = dict(poor_raw)
        better['repaid_loans_count'] = 50
        better['defaulted_loans_count'] = 0
        better_score, _ = scorer.calculate_score(engineer_features_from_raw(better))
        assert better_score > base_score

    def test_score_is_integer(self, scorer, excellent_raw):
        score, _ = scorer.calculate_score(engineer_features_from_raw(excellent_raw))
        assert isinstance(score, int)

    def test_deterministic(self, scorer, excellent_raw):
        features = engineer_features_from_raw(excellent_raw)
        scores = [scorer.calculate_score(features)[0] for _ in range(5)]
        assert len(set(scores)) == 1


class TestWeights:
    def test_weights_sum_to_100(self, scorer):
        assert sum(scorer.WEIGHTS.values()) == 100

    def test_all_features_have_ranges(self, scorer):
        for feature in scorer.WEIGHTS:
            assert feature in scorer.NORMALIZATION_RANGES

    def test_breakdown_has_all_features(self, scorer, excellent_raw):
        _, breakdown = scorer.calculate_score(engineer_features_from_raw(excellent_raw))
        for feature in scorer.WEIGHTS:
            assert feature in breakdown


class TestScoreBands:
    def test_poor_band(self, scorer):
        assert scorer.get_score_band(300) == "Poor"
        assert scorer.get_score_band(499) == "Poor"

    def test_fair_band(self, scorer):
        assert scorer.get_score_band(500) == "Fair"
        assert scorer.get_score_band(599) == "Fair"

    def test_good_band(self, scorer):
        assert scorer.get_score_band(600) == "Good"
        assert scorer.get_score_band(659) == "Good"

    def test_very_good_band(self, scorer):
        assert scorer.get_score_band(660) == "Very Good"
        assert scorer.get_score_band(749) == "Very Good"

    def test_excellent_band(self, scorer):
        assert scorer.get_score_band(750) == "Excellent"
        assert scorer.get_score_band(850) == "Excellent"


class TestFeatureEngineering:
    def test_all_features_returned(self):
        raw = {k: 0 for k in ['group_age_days','avg_contribution','stddev_contribution','total_contributions','active_members','total_ever_members','contribution_amount','repaid_loans_count','defaulted_loans_count','total_savings','active_loans_total','meetings_held_30d','actual_attendance_30d','loans_disbursed_90d','defaults_90d']}
        features = engineer_features_from_raw(raw)
        expected = {'group_longevity_months','contribution_cv','contribution_reliability','repayment_rate','liquidity_ratio','member_stability','attendance_rate','recent_default_rate'}
        assert expected == set(features.keys())

    def test_zero_loans_perfect_repayment(self):
        raw = {k: 0 for k in ['group_age_days','avg_contribution','stddev_contribution','total_contributions','active_members','total_ever_members','contribution_amount','repaid_loans_count','defaulted_loans_count','total_savings','active_loans_total','meetings_held_30d','actual_attendance_30d','loans_disbursed_90d','defaults_90d']}
        features = engineer_features_from_raw(raw)
        assert features['repayment_rate'] == 1.0
        assert features['recent_default_rate'] == 0.0

    def test_no_active_loans_max_liquidity(self):
        raw = {k: 0 for k in ['group_age_days','avg_contribution','stddev_contribution','total_contributions','active_members','total_ever_members','contribution_amount','repaid_loans_count','defaulted_loans_count','total_savings','active_loans_total','meetings_held_30d','actual_attendance_30d','loans_disbursed_90d','defaults_90d']}
        features = engineer_features_from_raw(raw)
        assert features['liquidity_ratio'] == 10.0

    def test_longevity_in_months(self):
        raw = {k: 0 for k in ['group_age_days','avg_contribution','stddev_contribution','total_contributions','active_members','total_ever_members','contribution_amount','repaid_loans_count','defaulted_loans_count','total_savings','active_loans_total','meetings_held_30d','actual_attendance_30d','loans_disbursed_90d','defaults_90d']}
        raw['group_age_days'] = 365
        features = engineer_features_from_raw(raw)
        assert abs(features['group_longevity_months'] - 12.17) < 0.5


class TestRecommendations:
    def test_poor_group_gets_recommendations(self, scorer, poor_raw):
        _, breakdown = scorer.calculate_score(engineer_features_from_raw(poor_raw))
        recs = scorer.generate_recommendations(breakdown)
        assert len(recs) > 0
        assert all(isinstance(r, str) for r in recs)

    def test_excellent_group_positive_message(self, scorer, excellent_raw):
        _, breakdown = scorer.calculate_score(engineer_features_from_raw(excellent_raw))
        recs = scorer.generate_recommendations(breakdown)
        assert len(recs) > 0

    def test_calculation_log_is_string(self, scorer, excellent_raw):
        features = engineer_features_from_raw(excellent_raw)
        score, breakdown = scorer.calculate_score(features)
        log = scorer.generate_calculation_log(features, breakdown, score)
        assert isinstance(log, str)
        assert 'CHAMASCORE' in log
        assert str(score) in log