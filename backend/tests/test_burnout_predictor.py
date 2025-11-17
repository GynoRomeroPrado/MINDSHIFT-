"""
Tests for Burnout Prediction ML System
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from burnout_ml.predictor import BurnoutPredictor


@pytest.fixture
def predictor():
    """Create BurnoutPredictor instance"""
    return BurnoutPredictor()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        'hire_date': datetime.now() - timedelta(days=365),
        'days_since_role_change': 90,
        'communication': {
            'email': {
                'count_7d': 150,
                'count_30d': 600,
                'after_hours_ratio': 0.3,
                'weekend_ratio': 0.2,
                'avg_response_time_hours': 4
            },
            'messaging': {
                'count_7d': 200,
                'avg_response_time_minutes': 15,
                'avg_sentiment': -0.1,
                'negative_ratio': 0.3
            },
            'meetings': {
                'hours_per_week': 20,
                'back_to_back_ratio': 0.6,
                'overlaps_per_week': 3
            }
        },
        'work_behavior': {
            'avg_login_hour': 8,
            'avg_logout_hour': 19,
            'avg_work_hours': 10,
            'work_hours_variance': 2,
            'weekend_hours_avg': 4,
            'sessions_after_10pm': 3,
            'vacation_days_ytd': 5,
            'days_since_last_vacation': 120,
            'sick_days_last_30d': 2,
            'task_completion_rate': 0.75,
            'deadline_miss_rate': 0.15,
            'active_projects': 5,
            'avg_focus_time_hours': 3,
            'avg_context_switches': 25
        },
        'self_report': {
            'checkins_7d': [
                {'mood': 4, 'energy': 4, 'stress': 8, 'sleep': 5, 'workload': 9},
                {'mood': 5, 'energy': 5, 'stress': 7, 'sleep': 5, 'workload': 8},
                {'mood': 4, 'energy': 4, 'stress': 8, 'sleep': 4, 'workload': 9}
            ],
            'checkins_30d': [
                {'mood': 5, 'energy': 5, 'stress': 7, 'sleep': 6, 'workload': 7}
            ] * 10,
            'coach_sessions_count': 3,
            'crisis_keywords_count': 1,
            'avg_sentiment': -0.2
        },
        'social': {
            'team_size': 8,
            'manager_1on1_per_month': 1,
            'peer_interactions_weekly': 15,
            'manager_response_time_hours': 48,
            'manager_tenure_months': 6,
            'peer_feedback_score': 6
        }
    }


@pytest.fixture
def low_risk_user_data():
    """Data for a low-risk user"""
    return {
        'hire_date': datetime.now() - timedelta(days=365),
        'days_since_role_change': 90,
        'communication': {
            'email': {
                'count_7d': 80,
                'count_30d': 320,
                'after_hours_ratio': 0.05,
                'weekend_ratio': 0.02,
                'avg_response_time_hours': 2
            },
            'messaging': {
                'count_7d': 100,
                'avg_response_time_minutes': 10,
                'avg_sentiment': 0.3,
                'negative_ratio': 0.1
            },
            'meetings': {
                'hours_per_week': 10,
                'back_to_back_ratio': 0.2,
                'overlaps_per_week': 0
            }
        },
        'work_behavior': {
            'avg_login_hour': 9,
            'avg_logout_hour': 17,
            'avg_work_hours': 8,
            'work_hours_variance': 0.5,
            'weekend_hours_avg': 0,
            'sessions_after_10pm': 0,
            'vacation_days_ytd': 15,
            'days_since_last_vacation': 30,
            'sick_days_last_30d': 0,
            'task_completion_rate': 0.95,
            'deadline_miss_rate': 0.02,
            'active_projects': 2,
            'avg_focus_time_hours': 6,
            'avg_context_switches': 10
        },
        'self_report': {
            'checkins_7d': [
                {'mood': 8, 'energy': 8, 'stress': 3, 'sleep': 8, 'workload': 5}
            ] * 7,
            'checkins_30d': [
                {'mood': 8, 'energy': 8, 'stress': 3, 'sleep': 8, 'workload': 5}
            ] * 30,
            'coach_sessions_count': 1,
            'crisis_keywords_count': 0,
            'avg_sentiment': 0.5
        },
        'social': {
            'team_size': 6,
            'manager_1on1_per_month': 4,
            'peer_interactions_weekly': 20,
            'manager_response_time_hours': 12,
            'manager_tenure_months': 24,
            'peer_feedback_score': 9
        }
    }


class TestFeatureExtraction:
    """Test feature extraction from user data"""

    def test_extract_all_features(self, predictor, sample_user_data):
        """Test that all features are extracted"""
        features = predictor.extract_features(sample_user_data)

        assert len(features) > 40  # Should have 40+ features
        assert 'email_count_7d' in features
        assert 'mood_avg_7d' in features
        assert 'work_hours_daily_avg' in features

    def test_communication_features(self, predictor, sample_user_data):
        """Test communication feature extraction"""
        features = predictor.extract_features(sample_user_data)

        assert features['email_count_7d'] == 150
        assert features['after_hours_email_ratio'] == 0.3
        assert features['meeting_hours_weekly'] == 20

    def test_work_behavior_features(self, predictor, sample_user_data):
        """Test work behavior feature extraction"""
        features = predictor.extract_features(sample_user_data)

        assert features['avg_work_hours'] == 10
        assert features['weekend_work_hours'] == 4
        assert features['days_since_vacation'] == 120

    def test_self_report_features(self, predictor, sample_user_data):
        """Test self-report feature extraction"""
        features = predictor.extract_features(sample_user_data)

        assert 'mood_avg_7d' in features
        assert 'stress_avg_7d' in features
        assert features['mood_avg_7d'] < 5  # Should be low

    def test_missing_data_handling(self, predictor):
        """Test handling of missing data"""
        minimal_data = {
            'hire_date': datetime.now() - timedelta(days=365),
            'communication': {},
            'work_behavior': {},
            'self_report': {'checkins_7d': [], 'checkins_30d': []},
            'social': {}
        }

        features = predictor.extract_features(minimal_data)

        # Should have default values
        assert features['email_count_7d'] == 0
        assert features['mood_avg_7d'] == 5  # Default neutral


class TestPrediction:
    """Test burnout prediction"""

    def test_high_risk_prediction(self, predictor, sample_user_data):
        """Test prediction for high-risk user"""
        prediction = predictor.predict(sample_user_data)

        assert 'score' in prediction
        assert 'risk_level' in prediction
        assert 'confidence' in prediction
        assert 'trajectory' in prediction
        assert 'contributing_factors' in prediction

        # High risk indicators should result in higher score
        assert prediction['score'] >= 50

    def test_low_risk_prediction(self, predictor, low_risk_user_data):
        """Test prediction for low-risk user"""
        prediction = predictor.predict(low_risk_user_data)

        # Low risk indicators should result in lower score
        assert prediction['score'] <= 50
        assert prediction['risk_level'] in ['low', 'moderate']

    def test_prediction_score_range(self, predictor, sample_user_data):
        """Test that prediction score is within valid range"""
        prediction = predictor.predict(sample_user_data)

        assert 0 <= prediction['score'] <= 100

    def test_confidence_range(self, predictor, sample_user_data):
        """Test that confidence is within valid range"""
        prediction = predictor.predict(sample_user_data)

        assert 0 <= prediction['confidence'] <= 1


class TestRiskLevels:
    """Test risk level classification"""

    def test_low_risk_threshold(self, predictor):
        """Test low risk classification"""
        risk_level = predictor._score_to_risk_level(30)
        assert risk_level == "low"

    def test_moderate_risk_threshold(self, predictor):
        """Test moderate risk classification"""
        risk_level = predictor._score_to_risk_level(50)
        assert risk_level == "moderate"

    def test_high_risk_threshold(self, predictor):
        """Test high risk classification"""
        risk_level = predictor._score_to_risk_level(70)
        assert risk_level == "high"

    def test_critical_risk_threshold(self, predictor):
        """Test critical risk classification"""
        risk_level = predictor._score_to_risk_level(90)
        assert risk_level == "critical"


class TestTrajectoryCalculation:
    """Test trajectory calculation"""

    def test_improving_trajectory(self, predictor):
        """Test detection of improving trajectory"""
        features = {
            'mood_trend': 0.5,  # Positive trend
            'stress_avg_7d': 4,
            'stress_avg_30d': 6
        }

        trajectory = predictor._calculate_trajectory(features)
        assert trajectory == "improving"

    def test_worsening_trajectory(self, predictor):
        """Test detection of worsening trajectory"""
        features = {
            'mood_trend': -0.5,  # Negative trend
            'stress_avg_7d': 8,
            'stress_avg_30d': 6
        }

        trajectory = predictor._calculate_trajectory(features)
        assert trajectory == "worsening"

    def test_stable_trajectory(self, predictor):
        """Test detection of stable trajectory"""
        features = {
            'mood_trend': 0.1,  # Minimal trend
            'stress_avg_7d': 6,
            'stress_avg_30d': 6
        }

        trajectory = predictor._calculate_trajectory(features)
        assert trajectory == "stable"


class TestContributingFactors:
    """Test contributing factors identification"""

    def test_high_stress_factor(self, predictor):
        """Test identification of high stress as factor"""
        features = {
            'stress_avg_7d': 9,
            'workload_avg_7d': 5,
            'mood_avg_7d': 7,
            'sleep_avg_7d': 7,
            'energy_avg_7d': 7,
            'work_hours_daily_avg': 8,
            'weekend_work_hours': 2,
            'days_since_vacation': 90,
            'meeting_hours_weekly': 15,
            'back_to_back_meetings_ratio': 0.3,
            'deadline_miss_rate': 0.1,
            'avg_conversation_sentiment': 0.2
        }

        factors = predictor._identify_contributing_factors(features)

        # Should identify high stress
        factor_descriptions = [f['factor'] for f in factors]
        assert any('stress' in desc.lower() for desc in factor_descriptions)

    def test_work_life_balance_factor(self, predictor):
        """Test identification of work-life balance issues"""
        features = {
            'stress_avg_7d': 5,
            'workload_avg_7d': 5,
            'mood_avg_7d': 7,
            'sleep_avg_7d': 7,
            'energy_avg_7d': 7,
            'work_hours_daily_avg': 12,  # Long hours
            'weekend_work_hours': 6,     # Working weekends
            'days_since_vacation': 200,  # No vacation
            'meeting_hours_weekly': 15,
            'back_to_back_meetings_ratio': 0.3,
            'deadline_miss_rate': 0.1,
            'avg_conversation_sentiment': 0.2
        }

        factors = predictor._identify_contributing_factors(features)

        # Should identify work-life balance issues
        categories = [f['category'] for f in factors]
        assert 'work_life_balance' in categories

    def test_top_5_factors(self, predictor, sample_user_data):
        """Test that only top 5 factors are returned"""
        features = predictor.extract_features(sample_user_data)
        factors = predictor._identify_contributing_factors(features)

        assert len(factors) <= 5


class TestModelTraining:
    """Test model training functionality"""

    def test_model_training(self, predictor):
        """Test basic model training"""
        # Create synthetic training data
        np.random.seed(42)
        n_samples = 100

        training_data = pd.DataFrame({
            'feature1': np.random.rand(n_samples),
            'feature2': np.random.rand(n_samples),
            'feature3': np.random.rand(n_samples)
        })

        labels = np.random.randint(0, 2, n_samples)

        # Train model
        predictor.train(training_data, labels)

        # Model should be trained
        assert predictor.rf_model is not None
        assert predictor.isolation_forest is not None

    def test_feature_importance(self, predictor):
        """Test feature importance calculation"""
        # Create synthetic data
        np.random.seed(42)
        training_data = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100)
        })
        labels = np.random.randint(0, 2, 100)

        predictor.train(training_data, labels)

        # Feature importance should be calculated
        assert len(predictor.feature_importance) > 0


class TestRuleBasedScoring:
    """Test rule-based scoring fallback"""

    def test_rule_based_high_risk(self, predictor):
        """Test rule-based scoring for high risk"""
        features = {
            'stress_avg_7d': 9,
            'workload_avg_7d': 9,
            'mood_avg_7d': 2,
            'weekend_work_hours': 8,
            'work_hours_daily_avg': 12,
            'days_since_vacation': 250,
            'sleep_avg_7d': 3,
            'energy_avg_7d': 2,
            'mood_trend': -0.8,
            'meeting_hours_weekly': 25,
            'back_to_back_meetings_ratio': 0.7
        }

        score = predictor._rule_based_score(features)

        # Should be high risk
        assert score >= 70

    def test_rule_based_low_risk(self, predictor):
        """Test rule-based scoring for low risk"""
        features = {
            'stress_avg_7d': 3,
            'workload_avg_7d': 4,
            'mood_avg_7d': 8,
            'weekend_work_hours': 0,
            'work_hours_daily_avg': 8,
            'days_since_vacation': 30,
            'sleep_avg_7d': 8,
            'energy_avg_7d': 8,
            'mood_trend': 0.3,
            'meeting_hours_weekly': 10,
            'back_to_back_meetings_ratio': 0.2
        }

        score = predictor._rule_based_score(features)

        # Should be low risk
        assert score <= 50
