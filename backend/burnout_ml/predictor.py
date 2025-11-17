"""
Burnout Prediction ML System
Multi-source data analysis for predicting employee burnout risk
"""
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle
import json


class BurnoutPredictor:
    """
    ML-based burnout prediction system using ensemble approach

    Combines multiple models:
    - Random Forest for feature-based prediction
    - Isolation Forest for anomaly detection
    - LSTM for temporal patterns (future implementation)
    """

    def __init__(self, model_path: Optional[str] = None):
        self.rf_model = None
        self.isolation_forest = None
        self.scaler = StandardScaler()
        self.feature_importance = {}

        if model_path:
            self.load_model(model_path)

    def extract_features(self, user_data: Dict) -> Dict[str, float]:
        """
        Extract features from various data sources

        Args:
            user_data: Dictionary containing all available user data

        Returns:
            Dictionary of computed features
        """
        features = {}

        # 1. Communication Pattern Features
        comm_data = user_data.get('communication', {})
        features.update(self._extract_communication_features(comm_data))

        # 2. Work Behavior Features
        work_data = user_data.get('work_behavior', {})
        features.update(self._extract_work_behavior_features(work_data))

        # 3. Self-Report Features
        self_report = user_data.get('self_report', {})
        features.update(self._extract_self_report_features(self_report))

        # 4. Temporal Features
        features.update(self._extract_temporal_features(user_data))

        # 5. Social Features
        social_data = user_data.get('social', {})
        features.update(self._extract_social_features(social_data))

        return features

    def _extract_communication_features(self, comm_data: Dict) -> Dict[str, float]:
        """Extract features from communication patterns"""
        features = {}

        # Email patterns
        email_stats = comm_data.get('email', {})
        features['email_count_7d'] = email_stats.get('count_7d', 0)
        features['email_count_30d'] = email_stats.get('count_30d', 0)
        features['after_hours_email_ratio'] = email_stats.get('after_hours_ratio', 0)
        features['weekend_email_ratio'] = email_stats.get('weekend_ratio', 0)
        features['avg_email_response_time'] = email_stats.get('avg_response_time_hours', 0)

        # Messaging patterns (Slack, Teams, etc.)
        msg_stats = comm_data.get('messaging', {})
        features['msg_count_7d'] = msg_stats.get('count_7d', 0)
        features['msg_response_time'] = msg_stats.get('avg_response_time_minutes', 0)
        features['msg_sentiment_avg'] = msg_stats.get('avg_sentiment', 0)
        features['negative_msg_ratio'] = msg_stats.get('negative_ratio', 0)

        # Meeting patterns
        meeting_stats = comm_data.get('meetings', {})
        features['meeting_hours_weekly'] = meeting_stats.get('hours_per_week', 0)
        features['back_to_back_meetings_ratio'] = meeting_stats.get('back_to_back_ratio', 0)
        features['meeting_overlap_count'] = meeting_stats.get('overlaps_per_week', 0)

        return features

    def _extract_work_behavior_features(self, work_data: Dict) -> Dict[str, float]:
        """Extract features from work behavior"""
        features = {}

        # Login patterns
        features['avg_login_hour'] = work_data.get('avg_login_hour', 9)
        features['avg_logout_hour'] = work_data.get('avg_logout_hour', 17)
        features['work_hours_daily_avg'] = work_data.get('avg_work_hours', 8)
        features['work_hours_variance'] = work_data.get('work_hours_variance', 0)

        # Weekend and after-hours work
        features['weekend_work_hours'] = work_data.get('weekend_hours_avg', 0)
        features['late_night_sessions'] = work_data.get('sessions_after_10pm', 0)

        # Vacation and time off
        features['vacation_days_taken'] = work_data.get('vacation_days_ytd', 0)
        features['days_since_vacation'] = work_data.get('days_since_last_vacation', 0)
        features['sick_days_30d'] = work_data.get('sick_days_last_30d', 0)

        # Productivity patterns
        features['task_completion_rate'] = work_data.get('task_completion_rate', 0)
        features['deadline_miss_rate'] = work_data.get('deadline_miss_rate', 0)
        features['project_count'] = work_data.get('active_projects', 0)

        # Focus time
        features['avg_focus_time_daily'] = work_data.get('avg_focus_time_hours', 0)
        features['context_switches_daily'] = work_data.get('avg_context_switches', 0)

        return features

    def _extract_self_report_features(self, self_report: Dict) -> Dict[str, float]:
        """Extract features from self-reported data"""
        features = {}

        # Daily check-ins (last 7, 30 days)
        checkins_7d = self_report.get('checkins_7d', [])
        checkins_30d = self_report.get('checkins_30d', [])

        if checkins_7d:
            features['mood_avg_7d'] = np.mean([c.get('mood', 5) for c in checkins_7d])
            features['mood_variance_7d'] = np.var([c.get('mood', 5) for c in checkins_7d])
            features['energy_avg_7d'] = np.mean([c.get('energy', 5) for c in checkins_7d])
            features['stress_avg_7d'] = np.mean([c.get('stress', 5) for c in checkins_7d])
            features['sleep_avg_7d'] = np.mean([c.get('sleep', 5) for c in checkins_7d])
            features['workload_avg_7d'] = np.mean([c.get('workload', 5) for c in checkins_7d])
        else:
            features['mood_avg_7d'] = 5
            features['mood_variance_7d'] = 0
            features['energy_avg_7d'] = 5
            features['stress_avg_7d'] = 5
            features['sleep_avg_7d'] = 5
            features['workload_avg_7d'] = 5

        if checkins_30d:
            features['mood_avg_30d'] = np.mean([c.get('mood', 5) for c in checkins_30d])
            features['stress_avg_30d'] = np.mean([c.get('stress', 5) for c in checkins_30d])

            # Trend calculation (improving/worsening)
            mood_scores = [c.get('mood', 5) for c in checkins_30d]
            if len(mood_scores) > 1:
                features['mood_trend'] = np.polyfit(range(len(mood_scores)), mood_scores, 1)[0]
            else:
                features['mood_trend'] = 0
        else:
            features['mood_avg_30d'] = 5
            features['stress_avg_30d'] = 5
            features['mood_trend'] = 0

        # Coach conversation analysis
        features['coach_sessions_30d'] = self_report.get('coach_sessions_count', 0)
        features['crisis_keywords_30d'] = self_report.get('crisis_keywords_count', 0)
        features['avg_conversation_sentiment'] = self_report.get('avg_sentiment', 0)

        return features

    def _extract_temporal_features(self, user_data: Dict) -> Dict[str, float]:
        """Extract temporal/time-based features"""
        features = {}

        # Tenure
        hire_date = user_data.get('hire_date')
        if hire_date:
            tenure_days = (datetime.now() - hire_date).days
            features['tenure_days'] = tenure_days
            features['tenure_months'] = tenure_days / 30
        else:
            features['tenure_days'] = 180
            features['tenure_months'] = 6

        # Time since last promotion/change
        features['days_since_role_change'] = user_data.get('days_since_role_change', 180)

        # Seasonality (some months have higher burnout)
        current_month = datetime.now().month
        features['is_q4'] = 1 if current_month in [10, 11, 12] else 0
        features['is_january'] = 1 if current_month == 1 else 0

        return features

    def _extract_social_features(self, social_data: Dict) -> Dict[str, float]:
        """Extract social/team interaction features"""
        features = {}

        # Team interactions
        features['team_size'] = social_data.get('team_size', 5)
        features['1on1_frequency'] = social_data.get('manager_1on1_per_month', 2)
        features['peer_interactions_weekly'] = social_data.get('peer_interactions_weekly', 10)

        # Manager relationship
        features['manager_response_time'] = social_data.get('manager_response_time_hours', 24)
        features['manager_tenure_months'] = social_data.get('manager_tenure_months', 12)

        # Peer feedback
        features['peer_feedback_score'] = social_data.get('peer_feedback_score', 7)

        return features

    def predict(self, user_data: Dict) -> Dict:
        """
        Predict burnout risk for a user

        Args:
            user_data: Dictionary containing all available user data

        Returns:
            Dictionary with prediction results
        """
        # Extract features
        features = self.extract_features(user_data)

        # Convert to numpy array in correct order
        feature_vector = self._features_to_vector(features)

        # Scale features
        scaled_features = self.scaler.transform([feature_vector])

        # Random Forest prediction
        if self.rf_model:
            rf_proba = self.rf_model.predict_proba(scaled_features)[0]
            burnout_score = rf_proba[1] * 100  # Probability of burnout class
        else:
            # Fallback: rule-based scoring
            burnout_score = self._rule_based_score(features)

        # Isolation Forest for anomaly detection
        if self.isolation_forest:
            anomaly_score = self.isolation_forest.score_samples(scaled_features)[0]
            # Normalize to 0-1, then 0-100
            anomaly_contribution = max(0, min(100, (1 - anomaly_score) * 50))

            # Combine scores (weighted average)
            final_score = burnout_score * 0.7 + anomaly_contribution * 0.3
        else:
            final_score = burnout_score

        # Determine risk level
        risk_level = self._score_to_risk_level(final_score)

        # Calculate confidence
        confidence = self._calculate_confidence(features, final_score)

        # Determine trajectory
        trajectory = self._calculate_trajectory(features)

        # Identify top contributing factors
        contributing_factors = self._identify_contributing_factors(features)

        return {
            'score': round(final_score, 2),
            'risk_level': risk_level,
            'confidence': round(confidence, 2),
            'trajectory': trajectory,
            'contributing_factors': contributing_factors,
            'features': features,
            'timestamp': datetime.now().isoformat()
        }

    def _features_to_vector(self, features: Dict) -> np.ndarray:
        """Convert features dictionary to ordered numpy array"""
        # Define expected feature order
        expected_features = [
            # Communication
            'email_count_7d', 'email_count_30d', 'after_hours_email_ratio',
            'weekend_email_ratio', 'avg_email_response_time',
            'msg_count_7d', 'msg_response_time', 'msg_sentiment_avg',
            'negative_msg_ratio', 'meeting_hours_weekly',
            'back_to_back_meetings_ratio', 'meeting_overlap_count',

            # Work behavior
            'avg_login_hour', 'avg_logout_hour', 'work_hours_daily_avg',
            'work_hours_variance', 'weekend_work_hours', 'late_night_sessions',
            'vacation_days_taken', 'days_since_vacation', 'sick_days_30d',
            'task_completion_rate', 'deadline_miss_rate', 'project_count',
            'avg_focus_time_daily', 'context_switches_daily',

            # Self-report
            'mood_avg_7d', 'mood_variance_7d', 'energy_avg_7d', 'stress_avg_7d',
            'sleep_avg_7d', 'workload_avg_7d', 'mood_avg_30d', 'stress_avg_30d',
            'mood_trend', 'coach_sessions_30d', 'crisis_keywords_30d',
            'avg_conversation_sentiment',

            # Temporal
            'tenure_days', 'tenure_months', 'days_since_role_change',
            'is_q4', 'is_january',

            # Social
            'team_size', '1on1_frequency', 'peer_interactions_weekly',
            'manager_response_time', 'manager_tenure_months', 'peer_feedback_score'
        ]

        vector = [features.get(feat, 0) for feat in expected_features]
        return np.array(vector)

    def _rule_based_score(self, features: Dict) -> float:
        """Fallback rule-based scoring when ML model not available"""
        score = 50  # Start at neutral

        # High stress indicators
        if features.get('stress_avg_7d', 5) >= 8:
            score += 15
        if features.get('workload_avg_7d', 5) >= 8:
            score += 10
        if features.get('mood_avg_7d', 5) <= 3:
            score += 15

        # Work-life balance indicators
        if features.get('weekend_work_hours', 0) > 5:
            score += 10
        if features.get('work_hours_daily_avg', 8) > 10:
            score += 10
        if features.get('days_since_vacation', 0) > 180:
            score += 5

        # Sleep and energy
        if features.get('sleep_avg_7d', 5) <= 4:
            score += 10
        if features.get('energy_avg_7d', 5) <= 3:
            score += 10

        # Negative trend
        if features.get('mood_trend', 0) < -0.5:
            score += 15

        # Meeting overload
        if features.get('meeting_hours_weekly', 0) > 20:
            score += 5
        if features.get('back_to_back_meetings_ratio', 0) > 0.5:
            score += 5

        return min(100, max(0, score))

    def _score_to_risk_level(self, score: float) -> str:
        """Convert numerical score to risk level"""
        if score < 40:
            return "low"
        elif score < 60:
            return "moderate"
        elif score < 80:
            return "high"
        else:
            return "critical"

    def _calculate_confidence(self, features: Dict, score: float) -> float:
        """Calculate confidence in prediction based on data completeness"""
        # Count how many features have non-zero values
        total_features = len(features)
        non_zero_features = sum(1 for v in features.values() if v != 0)

        data_completeness = non_zero_features / total_features if total_features > 0 else 0

        # Higher confidence if we have self-report data
        has_self_report = features.get('mood_avg_7d', 0) != 5  # Default is 5
        self_report_boost = 0.1 if has_self_report else 0

        confidence = min(0.95, data_completeness * 0.8 + self_report_boost)

        return confidence

    def _calculate_trajectory(self, features: Dict) -> str:
        """Determine if burnout risk is improving, stable, or worsening"""
        mood_trend = features.get('mood_trend', 0)

        # Compare 7d vs 30d stress
        stress_7d = features.get('stress_avg_7d', 5)
        stress_30d = features.get('stress_avg_30d', 5)

        if mood_trend > 0.3 and stress_7d < stress_30d:
            return "improving"
        elif mood_trend < -0.3 or stress_7d > stress_30d + 1:
            return "worsening"
        else:
            return "stable"

    def _identify_contributing_factors(self, features: Dict, top_n: int = 5) -> List[Dict]:
        """Identify top contributing factors to burnout risk"""
        factors = []

        # Define factor checks with weights
        factor_checks = [
            ('stress_avg_7d', 8, 'High stress levels', 0.9),
            ('workload_avg_7d', 8, 'Heavy workload', 0.8),
            ('mood_avg_7d', 4, 'Low mood', 0.9),
            ('sleep_avg_7d', 4, 'Poor sleep quality', 0.8),
            ('energy_avg_7d', 4, 'Low energy levels', 0.7),
            ('work_hours_daily_avg', 10, 'Long work hours', 0.7),
            ('weekend_work_hours', 5, 'Weekend work', 0.6),
            ('days_since_vacation', 180, 'No recent time off', 0.5),
            ('meeting_hours_weekly', 20, 'Meeting overload', 0.6),
            ('back_to_back_meetings_ratio', 0.5, 'Lack of breaks', 0.5),
            ('deadline_miss_rate', 0.2, 'Missing deadlines', 0.7),
            ('avg_conversation_sentiment', -0.3, 'Negative conversation tone', 0.6),
        ]

        for feature_name, threshold, description, importance in factor_checks:
            value = features.get(feature_name, 0)

            # Check if feature exceeds (or falls below for inverted metrics) threshold
            is_concerning = False
            if feature_name in ['mood_avg_7d', 'sleep_avg_7d', 'energy_avg_7d', 'avg_conversation_sentiment']:
                is_concerning = value < threshold
            else:
                is_concerning = value > threshold

            if is_concerning:
                factors.append({
                    'factor': description,
                    'value': round(value, 2),
                    'importance': importance,
                    'category': self._categorize_factor(feature_name)
                })

        # Sort by importance and return top N
        factors.sort(key=lambda x: x['importance'], reverse=True)
        return factors[:top_n]

    def _categorize_factor(self, feature_name: str) -> str:
        """Categorize a feature into high-level category"""
        if 'email' in feature_name or 'msg' in feature_name or 'meeting' in feature_name:
            return 'communication'
        elif 'work_hours' in feature_name or 'vacation' in feature_name or 'weekend' in feature_name:
            return 'work_life_balance'
        elif 'mood' in feature_name or 'stress' in feature_name or 'sleep' in feature_name or 'energy' in feature_name:
            return 'wellbeing'
        elif 'task' in feature_name or 'deadline' in feature_name:
            return 'productivity'
        else:
            return 'other'

    def train(self, training_data: pd.DataFrame, labels: np.ndarray):
        """
        Train the burnout prediction models

        Args:
            training_data: DataFrame with extracted features
            labels: Binary labels (0: not burned out, 1: burned out)
        """
        # Scale features
        scaled_data = self.scaler.fit_transform(training_data)

        # Train Random Forest
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.rf_model.fit(scaled_data, labels)

        # Train Isolation Forest for anomaly detection
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        self.isolation_forest.fit(scaled_data)

        # Store feature importance
        self.feature_importance = dict(zip(
            training_data.columns,
            self.rf_model.feature_importances_
        ))

    def save_model(self, path: str):
        """Save trained model to disk"""
        model_data = {
            'rf_model': self.rf_model,
            'isolation_forest': self.isolation_forest,
            'scaler': self.scaler,
            'feature_importance': self.feature_importance
        }

        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, path: str):
        """Load trained model from disk"""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)

        self.rf_model = model_data['rf_model']
        self.isolation_forest = model_data['isolation_forest']
        self.scaler = model_data['scaler']
        self.feature_importance = model_data['feature_importance']
