"""
GDPR Data Export Utility
Allows users to export all their personal data
"""
import json
import csv
import io
import zipfile
from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import Session

from models import (
    User, Conversation, Message, DailyCheckIn,
    BurnoutScore, Intervention, AnalyticsEvent
)


class DataExporter:
    """
    Export user data in various formats for GDPR compliance
    """

    def __init__(self, user_id: int, db: Session):
        self.user_id = user_id
        self.db = db
        self.user = db.query(User).filter(User.id == user_id).first()

        if not self.user:
            raise ValueError(f"User {user_id} not found")

    def export_all_data(self, format: str = 'json') -> bytes:
        """
        Export all user data in specified format

        Args:
            format: 'json', 'csv', or 'zip' (contains both)

        Returns:
            Bytes of exported data
        """
        data = self._gather_all_data()

        if format == 'json':
            return self._export_json(data)
        elif format == 'csv':
            return self._export_csv(data)
        elif format == 'zip':
            return self._export_zip(data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _gather_all_data(self) -> Dict:
        """Gather all user data from database"""
        return {
            'export_info': {
                'export_date': datetime.utcnow().isoformat(),
                'user_id': self.user_id,
                'format_version': '1.0'
            },
            'profile': self._get_profile_data(),
            'conversations': self._get_conversations_data(),
            'daily_checkins': self._get_checkins_data(),
            'burnout_assessments': self._get_burnout_data(),
            'interventions': self._get_interventions_data(),
            'analytics_events': self._get_analytics_data()
        }

    def _get_profile_data(self) -> Dict:
        """Export user profile data"""
        return {
            'email': self.user.email,
            'full_name': self.user.full_name,
            'role': self.user.role.value if self.user.role else None,
            'job_title': self.user.job_title,
            'hire_date': self.user.hire_date.isoformat() if self.user.hire_date else None,
            'timezone': self.user.timezone,
            'language': self.user.language,
            'preferences': self.user.preferences,
            'organization': self.user.organization.name if self.user.organization else None,
            'department': self.user.department.name if self.user.department else None,
            'consent_data_collection': self.user.consent_data_collection,
            'consent_analytics': self.user.consent_analytics,
            'created_at': self.user.created_at.isoformat() if self.user.created_at else None,
            'last_login': self.user.last_login.isoformat() if self.user.last_login else None
        }

    def _get_conversations_data(self) -> List[Dict]:
        """Export conversation and message data"""
        conversations = self.db.query(Conversation).filter(
            Conversation.user_id == self.user_id
        ).all()

        result = []
        for conv in conversations:
            messages = self.db.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.created_at).all()

            result.append({
                'conversation_id': conv.id,
                'started_at': conv.started_at.isoformat() if conv.started_at else None,
                'ended_at': conv.ended_at.isoformat() if conv.ended_at else None,
                'status': conv.status.value if conv.status else None,
                'coach_persona': conv.coach_persona,
                'message_count': conv.message_count,
                'crisis_detected': conv.crisis_detected,
                'messages': [
                    {
                        'role': msg.role,
                        'content': msg.content,
                        'sentiment': msg.sentiment,
                        'created_at': msg.created_at.isoformat() if msg.created_at else None
                    }
                    for msg in messages
                ]
            })

        return result

    def _get_checkins_data(self) -> List[Dict]:
        """Export daily check-in data"""
        checkins = self.db.query(DailyCheckIn).filter(
            DailyCheckIn.user_id == self.user_id
        ).order_by(DailyCheckIn.check_in_date).all()

        return [
            {
                'date': checkin.check_in_date.isoformat() if checkin.check_in_date else None,
                'mood_score': checkin.mood_score,
                'energy_score': checkin.energy_score,
                'stress_score': checkin.stress_score,
                'sleep_quality': checkin.sleep_quality,
                'workload_score': checkin.workload_score,
                'notes': checkin.notes
            }
            for checkin in checkins
        ]

    def _get_burnout_data(self) -> List[Dict]:
        """Export burnout assessment data"""
        assessments = self.db.query(BurnoutScore).filter(
            BurnoutScore.user_id == self.user_id
        ).order_by(BurnoutScore.prediction_date).all()

        return [
            {
                'prediction_date': assessment.prediction_date.isoformat() if assessment.prediction_date else None,
                'score': assessment.score,
                'risk_level': assessment.risk_level.value if assessment.risk_level else None,
                'confidence': assessment.confidence,
                'trajectory': assessment.trajectory,
                'contributing_factors': assessment.factors,
                'model_version': assessment.model_version
            }
            for assessment in assessments
        ]

    def _get_interventions_data(self) -> List[Dict]:
        """Export intervention data"""
        interventions = self.db.query(Intervention).filter(
            Intervention.user_id == self.user_id
        ).order_by(Intervention.triggered_at).all()

        return [
            {
                'type': intervention.type,
                'trigger': intervention.trigger,
                'trigger_value': intervention.trigger_value,
                'title': intervention.title,
                'description': intervention.description,
                'completed': intervention.completed,
                'effectiveness_rating': intervention.effectiveness_rating,
                'user_feedback': intervention.user_feedback,
                'triggered_at': intervention.triggered_at.isoformat() if intervention.triggered_at else None,
                'completed_at': intervention.completed_at.isoformat() if intervention.completed_at else None
            }
            for intervention in interventions
        ]

    def _get_analytics_data(self) -> List[Dict]:
        """Export analytics events (anonymized)"""
        events = self.db.query(AnalyticsEvent).filter(
            AnalyticsEvent.user_id == self.user_id
        ).order_by(AnalyticsEvent.event_timestamp).all()

        return [
            {
                'event_type': event.event_type,
                'event_timestamp': event.event_timestamp.isoformat() if event.event_timestamp else None,
                # Note: event_data may contain sensitive info, consider filtering
                'event_data': event.event_data if event.event_data else {}
            }
            for event in events
        ]

    def _export_json(self, data: Dict) -> bytes:
        """Export data as JSON"""
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        return json_str.encode('utf-8')

    def _export_csv(self, data: Dict) -> bytes:
        """Export data as CSV (flattened structure)"""
        output = io.StringIO()

        # Profile CSV
        writer = csv.DictWriter(output, fieldnames=data['profile'].keys())
        writer.writeheader()
        writer.writerow(data['profile'])
        output.write('\n\n')

        # Check-ins CSV
        if data['daily_checkins']:
            output.write('=== DAILY CHECK-INS ===\n')
            writer = csv.DictWriter(output, fieldnames=data['daily_checkins'][0].keys())
            writer.writeheader()
            writer.writerows(data['daily_checkins'])
            output.write('\n\n')

        # Burnout assessments CSV
        if data['burnout_assessments']:
            output.write('=== BURNOUT ASSESSMENTS ===\n')
            fields = ['prediction_date', 'score', 'risk_level', 'confidence', 'trajectory']
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for assessment in data['burnout_assessments']:
                writer.writerow({k: assessment[k] for k in fields})
            output.write('\n\n')

        return output.getvalue().encode('utf-8')

    def _export_zip(self, data: Dict) -> bytes:
        """Export data as ZIP containing both JSON and CSV"""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add JSON file
            json_data = self._export_json(data)
            zip_file.writestr('user_data.json', json_data)

            # Add CSV file
            csv_data = self._export_csv(data)
            zip_file.writestr('user_data.csv', csv_data)

            # Add conversations as separate files
            for i, conv in enumerate(data['conversations']):
                conv_json = json.dumps(conv, indent=2)
                zip_file.writestr(f'conversations/conversation_{i+1}.json', conv_json)

            # Add README
            readme = f"""
MindShift Data Export
=====================

Export Date: {data['export_info']['export_date']}
User ID: {data['export_info']['user_id']}

This archive contains all your personal data from MindShift in compliance with GDPR.

Files included:
- user_data.json: Complete data export in JSON format
- user_data.csv: Flattened data in CSV format
- conversations/: Individual conversation transcripts

For questions or to request data deletion, contact: privacy@mindshift.ai
            """
            zip_file.writestr('README.txt', readme)

        return zip_buffer.getvalue()


class DataDeletion:
    """
    Handle permanent data deletion (GDPR Right to be Forgotten)
    """

    def __init__(self, user_id: int, db: Session):
        self.user_id = user_id
        self.db = db

    def delete_all_user_data(self) -> Dict:
        """
        Permanently delete all user data

        Returns:
            Summary of deleted data
        """
        summary = {
            'user_id': self.user_id,
            'deleted_at': datetime.utcnow().isoformat(),
            'items_deleted': {}
        }

        # Delete messages
        messages_deleted = self.db.query(Message).filter(
            Message.conversation_id.in_(
                self.db.query(Conversation.id).filter(
                    Conversation.user_id == self.user_id
                )
            )
        ).delete(synchronize_session=False)
        summary['items_deleted']['messages'] = messages_deleted

        # Delete conversations
        conversations_deleted = self.db.query(Conversation).filter(
            Conversation.user_id == self.user_id
        ).delete()
        summary['items_deleted']['conversations'] = conversations_deleted

        # Delete check-ins
        checkins_deleted = self.db.query(DailyCheckIn).filter(
            DailyCheckIn.user_id == self.user_id
        ).delete()
        summary['items_deleted']['daily_checkins'] = checkins_deleted

        # Delete burnout scores
        burnout_deleted = self.db.query(BurnoutScore).filter(
            BurnoutScore.user_id == self.user_id
        ).delete()
        summary['items_deleted']['burnout_scores'] = burnout_deleted

        # Delete interventions
        interventions_deleted = self.db.query(Intervention).filter(
            Intervention.user_id == self.user_id
        ).delete()
        summary['items_deleted']['interventions'] = interventions_deleted

        # Anonymize analytics events (don't delete for aggregated analytics)
        analytics_anonymized = self.db.query(AnalyticsEvent).filter(
            AnalyticsEvent.user_id == self.user_id
        ).update({
            'user_id': None,
            'anonymized': True
        })
        summary['items_deleted']['analytics_events'] = analytics_anonymized

        # Delete user account
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if user:
            email = user.email
            self.db.delete(user)
            summary['email'] = email

        self.db.commit()

        return summary


class DataPortability:
    """
    Handle data portability requests (export to other services)
    """

    @staticmethod
    def export_for_external_service(data: Dict, service: str) -> Dict:
        """
        Format data for export to external services

        Args:
            data: User data from DataExporter
            service: Target service ('apple_health', 'google_fit', etc.)

        Returns:
            Formatted data for target service
        """
        if service == 'apple_health':
            return DataPortability._format_for_apple_health(data)
        elif service == 'google_fit':
            return DataPortability._format_for_google_fit(data)
        else:
            # Default: return as-is
            return data

    @staticmethod
    def _format_for_apple_health(data: Dict) -> Dict:
        """Format data for Apple Health export"""
        # Apple Health XML format
        return {
            'format': 'apple_health_xml',
            'data': {
                'mood_entries': [
                    {
                        'type': 'HKCategoryTypeIdentifierMindfulSession',
                        'value': checkin['mood_score'],
                        'startDate': checkin['date'],
                        'endDate': checkin['date']
                    }
                    for checkin in data.get('daily_checkins', [])
                ]
            }
        }

    @staticmethod
    def _format_for_google_fit(data: Dict) -> Dict:
        """Format data for Google Fit export"""
        return {
            'format': 'google_fit_json',
            'data': {
                'mood_data': [
                    {
                        'dataTypeName': 'com.google.activity.segment',
                        'startTimeNanos': checkin['date'],
                        'endTimeNanos': checkin['date'],
                        'value': checkin['mood_score']
                    }
                    for checkin in data.get('daily_checkins', [])
                ]
            }
        }
