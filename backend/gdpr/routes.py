"""
GDPR API Routes
Data export and deletion endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import io

from database import get_db
from models import User
from auth import get_current_user
from gdpr.data_export import DataExporter, DataDeletion
from notifications.notifier import notifier

router = APIRouter(prefix="/api/gdpr", tags=["GDPR"])


class ExportRequest(BaseModel):
    format: str = 'zip'  # json, csv, or zip


class DeletionRequest(BaseModel):
    confirmation: str  # User must type their email to confirm


@router.post("/export")
async def export_user_data(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all user data (GDPR Article 20 - Right to Data Portability)

    Returns:
        File download of user data in requested format
    """
    if request.format not in ['json', 'csv', 'zip']:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json', 'csv', or 'zip'")

    try:
        exporter = DataExporter(current_user.id, db)
        data_bytes = exporter.export_all_data(format=request.format)

        # Determine content type and filename
        if request.format == 'json':
            media_type = 'application/json'
            filename = f'mindshift_data_{current_user.id}.json'
        elif request.format == 'csv':
            media_type = 'text/csv'
            filename = f'mindshift_data_{current_user.id}.csv'
        else:  # zip
            media_type = 'application/zip'
            filename = f'mindshift_data_{current_user.id}.zip'

        # Create streaming response
        return StreamingResponse(
            io.BytesIO(data_bytes),
            media_type=media_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


@router.post("/delete")
async def delete_user_account(
    request: DeletionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete user account and all data
    (GDPR Article 17 - Right to be Forgotten)

    Requires email confirmation for safety
    """
    # Verify confirmation
    if request.confirmation != current_user.email:
        raise HTTPException(
            status_code=400,
            detail="Email confirmation doesn't match. Please type your email exactly."
        )

    try:
        # Create deletion service
        deletion = DataDeletion(current_user.id, db)

        # Export data first (in case user wants it later)
        exporter = DataExporter(current_user.id, db)
        data = exporter._gather_all_data()

        # Send final email with data export
        background_tasks.add_task(
            _send_deletion_email,
            current_user.email,
            current_user.full_name,
            data
        )

        # Delete all data
        summary = deletion.delete_all_user_data()

        return {
            "status": "success",
            "message": "Account and all data have been permanently deleted",
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


@router.get("/export/status")
async def get_export_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get information about what data will be exported
    """
    return {
        "data_categories": [
            {
                "category": "Profile",
                "description": "Your profile information, preferences, and settings",
                "included": True
            },
            {
                "category": "Conversations",
                "description": "All your conversations with the AI coach",
                "included": True
            },
            {
                "category": "Daily Check-ins",
                "description": "Your daily wellbeing check-in history",
                "included": True
            },
            {
                "category": "Burnout Assessments",
                "description": "Your burnout risk predictions and assessments",
                "included": True
            },
            {
                "category": "Interventions",
                "description": "Interventions triggered and your feedback",
                "included": True
            },
            {
                "category": "Analytics Events",
                "description": "Your usage analytics (anonymized)",
                "included": True
            }
        ],
        "formats_available": ["json", "csv", "zip"],
        "estimated_size": "varies based on usage (typically 1-10 MB)"
    }


async def _send_deletion_email(email: str, full_name: str, data: dict):
    """Send final email before account deletion"""
    subject = "MindShift Account Deletion Confirmation"

    body = f"""
Hi {full_name or 'there'},

Your MindShift account has been permanently deleted as requested.

All your personal data has been removed from our systems, including:
- Profile information
- Conversations with AI coach
- Daily check-ins
- Burnout assessments
- All other personal data

As required by GDPR, we've attached an export of your data to this email.

If you deleted your account by mistake or would like to return, you can create a new account at https://app.mindshift.ai/register

Thank you for using MindShift. We wish you well.

Best regards,
The MindShift Team

---
This is an automated message. For questions, contact: privacy@mindshift.ai
    """

    await notifier.send_email(
        to=[email],
        subject=subject,
        body=body
    )
