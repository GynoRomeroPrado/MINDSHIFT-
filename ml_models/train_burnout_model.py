"""
Burnout Model Training Script
Trains the burnout prediction model using historical employee data
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

from burnout_ml.predictor import BurnoutPredictor


def generate_synthetic_training_data(n_samples=1000):
    """
    Generate synthetic training data for initial model training

    In production, replace this with real anonymized employee data
    """
    np.random.seed(42)

    data = []
    labels = []

    for i in range(n_samples):
        # Randomly determine if employee is burned out (30% burnout rate)
        is_burned_out = np.random.random() < 0.3

        if is_burned_out:
            # High burnout features
            features = {
                # Communication (high volume, after hours)
                'email_count_7d': np.random.randint(150, 300),
                'email_count_30d': np.random.randint(600, 1200),
                'after_hours_email_ratio': np.random.uniform(0.3, 0.6),
                'weekend_email_ratio': np.random.uniform(0.2, 0.5),
                'avg_email_response_time': np.random.uniform(4, 12),
                'msg_count_7d': np.random.randint(200, 400),
                'msg_response_time': np.random.uniform(20, 60),
                'msg_sentiment_avg': np.random.uniform(-0.5, -0.1),
                'negative_msg_ratio': np.random.uniform(0.3, 0.6),
                'meeting_hours_weekly': np.random.uniform(20, 35),
                'back_to_back_meetings_ratio': np.random.uniform(0.5, 0.8),
                'meeting_overlap_count': np.random.randint(2, 8),

                # Work behavior (long hours, no breaks)
                'avg_login_hour': np.random.uniform(7, 9),
                'avg_logout_hour': np.random.uniform(19, 23),
                'work_hours_daily_avg': np.random.uniform(10, 14),
                'work_hours_variance': np.random.uniform(2, 4),
                'weekend_work_hours': np.random.uniform(4, 10),
                'late_night_sessions': np.random.randint(3, 10),
                'vacation_days_taken': np.random.randint(0, 5),
                'days_since_vacation': np.random.randint(120, 365),
                'sick_days_30d': np.random.randint(1, 5),
                'task_completion_rate': np.random.uniform(0.5, 0.8),
                'deadline_miss_rate': np.random.uniform(0.15, 0.4),
                'project_count': np.random.randint(4, 8),
                'avg_focus_time_daily': np.random.uniform(1, 3),
                'context_switches_daily': np.random.randint(25, 50),

                # Self-report (low mood, high stress)
                'mood_avg_7d': np.random.uniform(2, 4),
                'mood_variance_7d': np.random.uniform(1, 3),
                'energy_avg_7d': np.random.uniform(2, 4),
                'stress_avg_7d': np.random.uniform(7, 10),
                'sleep_avg_7d': np.random.uniform(2, 5),
                'workload_avg_7d': np.random.uniform(8, 10),
                'mood_avg_30d': np.random.uniform(2, 4),
                'stress_avg_30d': np.random.uniform(7, 10),
                'mood_trend': np.random.uniform(-1, -0.3),
                'coach_sessions_30d': np.random.randint(3, 10),
                'crisis_keywords_30d': np.random.randint(1, 5),
                'avg_conversation_sentiment': np.random.uniform(-0.5, -0.1),

                # Temporal
                'tenure_days': np.random.randint(180, 2000),
                'tenure_months': np.random.randint(6, 66),
                'days_since_role_change': np.random.randint(30, 365),
                'is_q4': np.random.choice([0, 1]),
                'is_january': np.random.choice([0, 1]),

                # Social (poor support)
                'team_size': np.random.randint(3, 15),
                '1on1_frequency': np.random.randint(0, 2),
                'peer_interactions_weekly': np.random.randint(5, 15),
                'manager_response_time': np.random.uniform(24, 72),
                'manager_tenure_months': np.random.randint(1, 12),
                'peer_feedback_score': np.random.uniform(3, 6)
            }
        else:
            # Low burnout features (healthy)
            features = {
                # Communication (normal volume, work hours)
                'email_count_7d': np.random.randint(50, 150),
                'email_count_30d': np.random.randint(200, 600),
                'after_hours_email_ratio': np.random.uniform(0, 0.15),
                'weekend_email_ratio': np.random.uniform(0, 0.1),
                'avg_email_response_time': np.random.uniform(1, 4),
                'msg_count_7d': np.random.randint(80, 200),
                'msg_response_time': np.random.uniform(5, 20),
                'msg_sentiment_avg': np.random.uniform(0.1, 0.5),
                'negative_msg_ratio': np.random.uniform(0, 0.2),
                'meeting_hours_weekly': np.random.uniform(8, 20),
                'back_to_back_meetings_ratio': np.random.uniform(0.1, 0.4),
                'meeting_overlap_count': np.random.randint(0, 2),

                # Work behavior (normal hours, regular breaks)
                'avg_login_hour': np.random.uniform(8, 10),
                'avg_logout_hour': np.random.uniform(16, 18),
                'work_hours_daily_avg': np.random.uniform(7, 9),
                'work_hours_variance': np.random.uniform(0.5, 1.5),
                'weekend_work_hours': np.random.uniform(0, 2),
                'late_night_sessions': np.random.randint(0, 2),
                'vacation_days_taken': np.random.randint(10, 20),
                'days_since_vacation': np.random.randint(10, 90),
                'sick_days_30d': np.random.randint(0, 1),
                'task_completion_rate': np.random.uniform(0.85, 0.98),
                'deadline_miss_rate': np.random.uniform(0, 0.1),
                'project_count': np.random.randint(1, 4),
                'avg_focus_time_daily': np.random.uniform(4, 7),
                'context_switches_daily': np.random.randint(8, 20),

                # Self-report (good mood, low stress)
                'mood_avg_7d': np.random.uniform(6, 9),
                'mood_variance_7d': np.random.uniform(0.5, 1.5),
                'energy_avg_7d': np.random.uniform(6, 9),
                'stress_avg_7d': np.random.uniform(2, 5),
                'sleep_avg_7d': np.random.uniform(6, 9),
                'workload_avg_7d': np.random.uniform(3, 6),
                'mood_avg_30d': np.random.uniform(6, 9),
                'stress_avg_30d': np.random.uniform(2, 5),
                'mood_trend': np.random.uniform(-0.2, 0.5),
                'coach_sessions_30d': np.random.randint(0, 3),
                'crisis_keywords_30d': 0,
                'avg_conversation_sentiment': np.random.uniform(0.2, 0.6),

                # Temporal
                'tenure_days': np.random.randint(180, 2000),
                'tenure_months': np.random.randint(6, 66),
                'days_since_role_change': np.random.randint(30, 365),
                'is_q4': np.random.choice([0, 1]),
                'is_january': np.random.choice([0, 1]),

                # Social (good support)
                'team_size': np.random.randint(4, 12),
                '1on1_frequency': np.random.randint(2, 5),
                'peer_interactions_weekly': np.random.randint(15, 30),
                'manager_response_time': np.random.uniform(4, 24),
                'manager_tenure_months': np.random.randint(12, 48),
                'peer_feedback_score': np.random.uniform(7, 10)
            }

        data.append(features)
        labels.append(1 if is_burned_out else 0)

    return pd.DataFrame(data), np.array(labels)


def train_model(output_path='burnout_model.pkl'):
    """Train the burnout prediction model"""
    print("=" * 70)
    print("MINDSHIFT BURNOUT PREDICTION MODEL TRAINING")
    print("=" * 70)

    # Generate training data
    print("\n1. Generating training data...")
    print("   Note: In production, use real anonymized employee data")
    X, y = generate_synthetic_training_data(n_samples=2000)

    print(f"   - Generated {len(X)} samples")
    print(f"   - Burnout rate: {(y.sum() / len(y) * 100):.1f}%")
    print(f"   - Features: {X.shape[1]}")

    # Split data
    print("\n2. Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   - Training samples: {len(X_train)}")
    print(f"   - Test samples: {len(X_test)}")

    # Train model
    print("\n3. Training model...")
    predictor = BurnoutPredictor()
    predictor.train(X_train, y_train)
    print("   ✓ Random Forest trained")
    print("   ✓ Isolation Forest trained")

    # Evaluate on training set
    print("\n4. Evaluating model on training set...")
    train_predictions = []
    for idx, row in X_train.iterrows():
        user_data = {
            'hire_date': datetime.now(),
            'communication': {},
            'work_behavior': {},
            'self_report': {'checkins_7d': [], 'checkins_30d': []},
            'social': {}
        }
        # Create minimal user data for prediction
        prediction = predictor.predict(user_data)
        train_predictions.append(1 if prediction['score'] >= 50 else 0)

    # Evaluate on test set
    print("\n5. Evaluating model on test set...")
    test_predictions = []
    test_scores = []

    for idx, row in X_test.iterrows():
        # Convert row to user data format
        features = row.to_dict()

        # Create minimal user data
        user_data = {
            'hire_date': datetime.now(),
            'communication': {
                'email': {
                    'count_7d': features['email_count_7d'],
                    'count_30d': features['email_count_30d'],
                    'after_hours_ratio': features['after_hours_email_ratio'],
                    'weekend_ratio': features['weekend_email_ratio'],
                    'avg_response_time_hours': features['avg_email_response_time']
                },
                'messaging': {
                    'count_7d': features['msg_count_7d'],
                    'avg_response_time_minutes': features['msg_response_time'],
                    'avg_sentiment': features['msg_sentiment_avg'],
                    'negative_ratio': features['negative_msg_ratio']
                },
                'meetings': {
                    'hours_per_week': features['meeting_hours_weekly'],
                    'back_to_back_ratio': features['back_to_back_meetings_ratio'],
                    'overlaps_per_week': features['meeting_overlap_count']
                }
            },
            'work_behavior': {
                'avg_login_hour': features['avg_login_hour'],
                'avg_logout_hour': features['avg_logout_hour'],
                'avg_work_hours': features['work_hours_daily_avg'],
                'work_hours_variance': features['work_hours_variance'],
                'weekend_hours_avg': features['weekend_work_hours'],
                'sessions_after_10pm': features['late_night_sessions'],
                'vacation_days_ytd': features['vacation_days_taken'],
                'days_since_last_vacation': features['days_since_vacation'],
                'sick_days_last_30d': features['sick_days_30d'],
                'task_completion_rate': features['task_completion_rate'],
                'deadline_miss_rate': features['deadline_miss_rate'],
                'active_projects': features['project_count'],
                'avg_focus_time_hours': features['avg_focus_time_daily'],
                'avg_context_switches': features['context_switches_daily']
            },
            'self_report': {
                'checkins_7d': [
                    {
                        'mood': features['mood_avg_7d'],
                        'energy': features['energy_avg_7d'],
                        'stress': features['stress_avg_7d'],
                        'sleep': features['sleep_avg_7d'],
                        'workload': features['workload_avg_7d']
                    }
                ],
                'checkins_30d': [
                    {
                        'mood': features['mood_avg_30d'],
                        'stress': features['stress_avg_30d']
                    }
                ],
                'coach_sessions_count': features['coach_sessions_30d'],
                'crisis_keywords_count': features['crisis_keywords_30d'],
                'avg_sentiment': features['avg_conversation_sentiment']
            },
            'social': {
                'team_size': features['team_size'],
                'manager_1on1_per_month': features['1on1_frequency'],
                'peer_interactions_weekly': features['peer_interactions_weekly'],
                'manager_response_time_hours': features['manager_response_time'],
                'manager_tenure_months': features['manager_tenure_months'],
                'peer_feedback_score': features['peer_feedback_score']
            },
            'days_since_role_change': features['days_since_role_change']
        }

        prediction = predictor.predict(user_data)
        test_scores.append(prediction['score'])
        test_predictions.append(1 if prediction['score'] >= 50 else 0)

    # Calculate metrics
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    accuracy = accuracy_score(y_test, test_predictions)
    precision = precision_score(y_test, test_predictions)
    recall = recall_score(y_test, test_predictions)
    f1 = f1_score(y_test, test_predictions)

    print("\n" + "=" * 70)
    print("MODEL PERFORMANCE METRICS")
    print("=" * 70)
    print(f"Accuracy:  {accuracy:.3f} ({accuracy*100:.1f}%)")
    print(f"Precision: {precision:.3f} ({precision*100:.1f}%)")
    print(f"Recall:    {recall:.3f} ({recall*100:.1f}%)")
    print(f"F1 Score:  {f1:.3f}")

    # Confusion matrix
    cm = confusion_matrix(y_test, test_predictions)
    print("\nConfusion Matrix:")
    print(f"                Predicted No Burnout  Predicted Burnout")
    print(f"Actual No Burnout        {cm[0][0]:>5}              {cm[0][1]:>5}")
    print(f"Actual Burnout           {cm[1][0]:>5}              {cm[1][1]:>5}")

    # Feature importance
    print("\n" + "=" * 70)
    print("TOP 10 MOST IMPORTANT FEATURES")
    print("=" * 70)
    sorted_features = sorted(
        predictor.feature_importance.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    for i, (feature, importance) in enumerate(sorted_features, 1):
        print(f"{i:2d}. {feature:30s} {importance:.4f}")

    # Save model
    print(f"\n6. Saving model to {output_path}...")
    predictor.save_model(output_path)
    print("   ✓ Model saved successfully")

    # Save metadata
    metadata = {
        'training_date': datetime.now().isoformat(),
        'n_samples': len(X),
        'n_features': X.shape[1],
        'burnout_rate': float(y.sum() / len(y)),
        'test_accuracy': float(accuracy),
        'test_precision': float(precision),
        'test_recall': float(recall),
        'test_f1': float(f1),
        'feature_importance': {k: float(v) for k, v in sorted_features}
    }

    metadata_path = output_path.replace('.pkl', '_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   ✓ Metadata saved to {metadata_path}")

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE!")
    print("=" * 70)
    print(f"\nModel files:")
    print(f"  - {output_path}")
    print(f"  - {metadata_path}")
    print(f"\nTo use this model in production:")
    print(f"  1. Copy {output_path} to backend/ml_models/")
    print(f"  2. Update BURNOUT_MODEL_PATH in .env")
    print(f"  3. Restart the backend service")

    return predictor, metadata


if __name__ == "__main__":
    # Train model
    predictor, metadata = train_model()

    print("\n✓ Training pipeline completed successfully!")
