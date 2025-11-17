"""
Notification System for MindShift
Handles email, Slack, and other notification channels
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
import aiohttp
import logging
from jinja2 import Template

from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Unified notification service supporting multiple channels
    """

    def __init__(self):
        self.smtp_configured = all([
            getattr(settings, 'SMTP_HOST', None),
            getattr(settings, 'SMTP_USER', None),
            getattr(settings, 'SMTP_PASSWORD', None)
        ])

        self.slack_configured = getattr(settings, 'SLACK_WEBHOOK_URL', None) is not None

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email notification

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            html: Optional HTML email body
            cc: Optional CC recipients
            bcc: Optional BCC recipients

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.smtp_configured:
            logger.warning("SMTP not configured, skipping email")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.SMTP_FROM
            msg['To'] = ', '.join(to)

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Plain text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # HTML part
            if html:
                html_part = MIMEText(html, 'html')
                msg.attach(html_part)

            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                recipients = to + (cc or []) + (bcc or [])
                server.send_message(msg, from_addr=settings.SMTP_FROM, to_addrs=recipients)

            logger.info(f"Email sent successfully to {', '.join(to)}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_slack_message(
        self,
        message: str,
        channel: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send Slack notification via webhook

        Args:
            message: Message text
            channel: Optional channel override
            attachments: Optional Slack attachments

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.slack_configured:
            logger.warning("Slack not configured, skipping notification")
            return False

        try:
            payload = {
                'text': message
            }

            if channel:
                payload['channel'] = channel

            if attachments:
                payload['attachments'] = attachments

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info("Slack message sent successfully")
                        return True
                    else:
                        logger.error(f"Slack webhook returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

    async def notify_crisis_detected(
        self,
        user_id: int,
        user_name: str,
        user_email: str,
        keywords: List[str],
        conversation_id: int
    ):
        """
        Send crisis alert to appropriate parties

        Args:
            user_id: User ID
            user_name: User's name
            user_email: User's email
            keywords: Crisis keywords detected
            conversation_id: Conversation ID where crisis was detected
        """
        # Email to crisis team
        subject = f"🚨 URGENT: Crisis Detected - User {user_name}"

        body = f"""
URGENT: Crisis Keywords Detected

User Information:
- Name: {user_name}
- Email: {user_email}
- User ID: {user_id}

Detection Details:
- Keywords detected: {', '.join(keywords)}
- Conversation ID: {conversation_id}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Action Required:
1. Review conversation immediately
2. Contact user if appropriate
3. Escalate to professional if needed

Resources:
- National Suicide & Crisis Lifeline: 988
- Crisis Text Line: Text HELLO to 741741

View conversation: https://app.mindshift.ai/admin/conversations/{conversation_id}
"""

        html = self._get_crisis_email_html(user_name, user_email, keywords, conversation_id)

        await self.send_email(
            to=[settings.ESCALATION_EMAIL],
            subject=subject,
            body=body,
            html=html
        )

        # Slack alert
        if self.slack_configured:
            slack_message = {
                'text': '🚨 *URGENT: Crisis Detected*',
                'attachments': [
                    {
                        'color': 'danger',
                        'fields': [
                            {'title': 'User', 'value': user_name, 'short': True},
                            {'title': 'User ID', 'value': str(user_id), 'short': True},
                            {'title': 'Keywords', 'value': ', '.join(keywords), 'short': False}
                        ],
                        'actions': [
                            {
                                'type': 'button',
                                'text': 'View Conversation',
                                'url': f'https://app.mindshift.ai/admin/conversations/{conversation_id}'
                            }
                        ]
                    }
                ]
            }
            await self.send_slack_message(slack_message['text'], attachments=slack_message['attachments'])

    async def notify_high_burnout_risk(
        self,
        user_id: int,
        user_name: str,
        user_email: str,
        burnout_score: float,
        risk_level: str,
        contributing_factors: List[Dict],
        manager_email: Optional[str] = None
    ):
        """
        Notify about high burnout risk

        Args:
            user_id: User ID
            user_name: User's name
            user_email: User's email
            burnout_score: Burnout score (0-100)
            risk_level: Risk level (high, critical)
            contributing_factors: List of contributing factors
            manager_email: Optional manager email for notification
        """
        subject = f"⚠️ High Burnout Risk Alert: {user_name}"

        factors_text = '\n'.join([
            f"  - {f['factor']} (importance: {f['importance']})"
            for f in contributing_factors[:5]
        ])

        body = f"""
High Burnout Risk Detected

User Information:
- Name: {user_name}
- User ID: {user_id}

Burnout Assessment:
- Score: {burnout_score:.1f}/100
- Risk Level: {risk_level.upper()}

Top Contributing Factors:
{factors_text}

Recommended Actions:
1. Schedule 1-on-1 with manager
2. Review workload and priorities
3. Consider short-term leave or PTO
4. Connect with mental health resources

View full report: https://app.mindshift.ai/admin/users/{user_id}/burnout
"""

        html = self._get_burnout_email_html(
            user_name, burnout_score, risk_level, contributing_factors
        )

        # Notify HR
        await self.send_email(
            to=[settings.ESCALATION_EMAIL],
            subject=subject,
            body=body,
            html=html
        )

        # Notify manager if provided
        if manager_email:
            manager_subject = f"Team Member Wellbeing Alert: {user_name}"
            manager_body = f"""
As {user_name}'s manager, we wanted to alert you that they may be experiencing elevated stress or burnout risk.

Burnout Risk Score: {burnout_score:.1f}/100 ({risk_level})

Recommended Actions:
1. Schedule a 1-on-1 to check in on their wellbeing
2. Review their current workload and priorities
3. Discuss potential adjustments or support needed
4. Remind them of available mental health resources

This is a confidential alert. Please handle with care and empathy.

Need support? Contact HR or reply to this email.
"""

            await self.send_email(
                to=[manager_email],
                subject=manager_subject,
                body=manager_body
            )

        # Slack notification
        if self.slack_configured and risk_level == 'critical':
            slack_message = {
                'text': '⚠️ *Critical Burnout Risk Alert*',
                'attachments': [
                    {
                        'color': 'warning',
                        'fields': [
                            {'title': 'User', 'value': user_name, 'short': True},
                            {'title': 'Score', 'value': f'{burnout_score:.1f}/100', 'short': True},
                            {'title': 'Risk Level', 'value': risk_level.upper(), 'short': True}
                        ]
                    }
                ]
            }
            await self.send_slack_message(slack_message['text'], attachments=slack_message['attachments'])

    async def send_daily_digest(
        self,
        to: str,
        organization_name: str,
        stats: Dict
    ):
        """
        Send daily digest email with organization stats

        Args:
            to: Recipient email
            organization_name: Organization name
            stats: Dictionary of statistics
        """
        subject = f"MindShift Daily Digest - {organization_name}"

        body = f"""
Daily Wellbeing Report for {organization_name}

Employee Engagement:
- Active users today: {stats.get('active_users', 0)}
- Check-ins completed: {stats.get('checkins_completed', 0)}
- Coach conversations: {stats.get('coach_conversations', 0)}

Burnout Monitoring:
- Average burnout score: {stats.get('avg_burnout_score', 0):.1f}/100
- High risk employees: {stats.get('high_risk_count', 0)}
- Critical alerts: {stats.get('critical_alerts', 0)}

Interventions:
- Self-help resources accessed: {stats.get('self_help_accessed', 0)}
- Coach sessions initiated: {stats.get('coach_sessions', 0)}
- Manager alerts sent: {stats.get('manager_alerts', 0)}

View full dashboard: https://app.mindshift.ai/dashboard

---
MindShift - Workplace Mental Health Platform
"""

        html = self._get_daily_digest_html(organization_name, stats)

        await self.send_email(
            to=[to],
            subject=subject,
            body=body,
            html=html
        )

    def _get_crisis_email_html(
        self,
        user_name: str,
        user_email: str,
        keywords: List[str],
        conversation_id: int
    ) -> str:
        """Generate HTML for crisis alert email"""
        from datetime import datetime

        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .alert { background-color: #fee; border-left: 4px solid #c00; padding: 15px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #c00; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }
        .info { background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="color: #c00;">🚨 URGENT: Crisis Alert</h1>

        <div class="alert">
            <strong>Crisis keywords detected in user conversation</strong><br>
            Immediate review required
        </div>

        <div class="info">
            <h3>User Information:</h3>
            <p>
                <strong>Name:</strong> {{ user_name }}<br>
                <strong>Email:</strong> {{ user_email }}<br>
                <strong>Time:</strong> {{ timestamp }}
            </p>

            <h3>Detection Details:</h3>
            <p>
                <strong>Keywords:</strong> {{ keywords }}<br>
                <strong>Conversation ID:</strong> {{ conversation_id }}
            </p>
        </div>

        <h3>Required Actions:</h3>
        <ol>
            <li>Review the conversation immediately</li>
            <li>Assess the situation and severity</li>
            <li>Contact user if appropriate and safe to do so</li>
            <li>Escalate to licensed professional if needed</li>
            <li>Document all actions taken</li>
        </ol>

        <h3>Crisis Resources:</h3>
        <ul>
            <li><strong>National Suicide & Crisis Lifeline:</strong> 988</li>
            <li><strong>Crisis Text Line:</strong> Text HELLO to 741741</li>
            <li><strong>Emergency Services:</strong> 911</li>
        </ul>

        <a href="https://app.mindshift.ai/admin/conversations/{{ conversation_id }}" class="button">
            View Conversation
        </a>

        <p style="margin-top: 30px; font-size: 12px; color: #666;">
            This is an automated alert from MindShift. Handle with care and maintain confidentiality.
        </p>
    </div>
</body>
</html>
        """)

        return template.render(
            user_name=user_name,
            user_email=user_email,
            keywords=', '.join(keywords),
            conversation_id=conversation_id,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        )

    def _get_burnout_email_html(
        self,
        user_name: str,
        burnout_score: float,
        risk_level: str,
        contributing_factors: List[Dict]
    ) -> str:
        """Generate HTML for burnout alert email"""
        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .warning { background-color: #fff3cd; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0; }
        .score { font-size: 48px; font-weight: bold; color: {{ score_color }}; text-align: center; margin: 20px 0; }
        .factors { background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; }
        .factor { padding: 8px 0; border-bottom: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="color: #ff9800;">⚠️ High Burnout Risk Alert</h1>

        <div class="warning">
            <strong>Employee wellbeing alert:</strong> {{ user_name }} is showing signs of elevated burnout risk.
        </div>

        <h2>Burnout Assessment</h2>
        <div class="score">{{ burnout_score }}/100</div>
        <p style="text-align: center;"><strong>Risk Level: {{ risk_level|upper }}</strong></p>

        <div class="factors">
            <h3>Top Contributing Factors:</h3>
            {% for factor in contributing_factors[:5] %}
            <div class="factor">
                <strong>{{ factor.factor }}</strong><br>
                <small>Category: {{ factor.category }} | Importance: {{ (factor.importance * 100)|round }}%</small>
            </div>
            {% endfor %}
        </div>

        <h3>Recommended Actions:</h3>
        <ol>
            <li>Schedule a private 1-on-1 conversation</li>
            <li>Review and adjust current workload</li>
            <li>Discuss work-life balance and boundaries</li>
            <li>Encourage use of PTO or mental health days</li>
            <li>Connect with mental health resources</li>
        </ol>

        <p style="margin-top: 30px; font-size: 12px; color: #666;">
            This alert is confidential. Handle with empathy and care.
        </p>
    </div>
</body>
</html>
        """)

        score_color = '#c00' if risk_level == 'critical' else '#ff9800'

        return template.render(
            user_name=user_name,
            burnout_score=f"{burnout_score:.1f}",
            risk_level=risk_level,
            contributing_factors=contributing_factors,
            score_color=score_color
        )

    def _get_daily_digest_html(self, organization_name: str, stats: Dict) -> str:
        """Generate HTML for daily digest email"""
        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
        .stat-box { background-color: #f5f5f5; padding: 15px; border-radius: 4px; text-align: center; }
        .stat-value { font-size: 32px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MindShift Daily Digest</h1>
            <p>{{ organization_name }}</p>
        </div>

        <div style="padding: 20px; background-color: white;">
            <h2>Employee Engagement</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{{ stats.active_users }}</div>
                    <div class="stat-label">Active Users</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ stats.checkins_completed }}</div>
                    <div class="stat-label">Check-ins</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ stats.coach_conversations }}</div>
                    <div class="stat-label">Coach Sessions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ stats.avg_burnout_score }}</div>
                    <div class="stat-label">Avg Burnout Score</div>
                </div>
            </div>

            <h2>Wellbeing Alerts</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{{ stats.high_risk_count }}</div>
                    <div class="stat-label">High Risk</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ stats.critical_alerts }}</div>
                    <div class="stat-label">Critical Alerts</div>
                </div>
            </div>

            <p style="text-align: center; margin-top: 30px;">
                <a href="https://app.mindshift.ai/dashboard" style="display: inline-block; padding: 12px 24px; background-color: #667eea; color: white; text-decoration: none; border-radius: 4px;">
                    View Full Dashboard
                </a>
            </p>
        </div>

        <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
            MindShift - AI-Powered Workplace Mental Health
        </p>
    </div>
</body>
</html>
        """)

        return template.render(
            organization_name=organization_name,
            stats=stats
        )


# Global notifier instance
notifier = NotificationService()
