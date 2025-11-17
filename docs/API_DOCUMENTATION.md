# MindShift API Documentation

## Base URL
```
Development: http://localhost:8000
Production: https://api.mindshift.ai
```

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

### Register New User

**POST** `/api/auth/register`

Create a new user account and organization.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "organization_name": "Acme Corp",
  "organization_domain": "acme.com"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "employee",
    "organization_id": 1
  }
}
```

### Login

**POST** `/api/auth/login`

Authenticate and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "employee",
    "organization_id": 1
  }
}
```

### Get Current User

**GET** `/api/auth/me`

Get authenticated user information.

**Headers:**
```http
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "employee",
  "organization_id": 1
}
```

---

## AI Coach

### Send Message

**POST** `/api/coach/chat`

Send a message to the AI coach and receive a response.

**Headers:**
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "I'm feeling overwhelmed with work lately.",
  "conversation_id": 123,  // Optional: omit to start new conversation
  "persona": "coach"       // Optional: "coach", "friend", or "expert"
}
```

**Response (200 OK):**
```json
{
  "response": "I hear you. Feeling overwhelmed is a common experience, especially when work demands are high. Let's explore what's contributing to this feeling...",
  "conversation_id": 123,
  "metadata": {
    "crisis_level": "none",
    "crisis_keywords": [],
    "sentiment": -0.3,
    "intervention": null,
    "topics": ["work_stress", "anxiety"],
    "persona": "coach",
    "model_used": "gpt-4-turbo-preview"
  }
}
```

### Get Conversations

**GET** `/api/coach/conversations`

Get user's conversation history.

**Headers:**
```http
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (optional): Number of conversations to return (default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response (200 OK):**
```json
[
  {
    "id": 123,
    "title": null,
    "status": "active",
    "message_count": 8,
    "started_at": "2025-01-15T10:30:00Z",
    "coach_persona": "coach"
  },
  {
    "id": 122,
    "title": null,
    "status": "completed",
    "message_count": 12,
    "started_at": "2025-01-14T15:20:00Z",
    "coach_persona": "friend"
  }
]
```

### Get Conversation Messages

**GET** `/api/coach/conversations/{conversation_id}/messages`

Get all messages from a specific conversation.

**Headers:**
```http
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "role": "user",
    "content": "I'm feeling overwhelmed with work.",
    "created_at": "2025-01-15T10:30:00Z",
    "sentiment": -0.3
  },
  {
    "id": 2,
    "role": "assistant",
    "content": "I hear you. Let's explore what's contributing to this...",
    "created_at": "2025-01-15T10:30:15Z",
    "sentiment": null
  }
]
```

### Get Intervention Details

**GET** `/api/coach/interventions/{intervention_type}`

Get detailed information about a specific intervention/exercise.

**Headers:**
```http
Authorization: Bearer <token>
```

**Path Parameters:**
- `intervention_type`: breathing | grounding | mindfulness | cognitive_reframe | journaling | progressive_relaxation

**Response (200 OK):**
```json
{
  "type": "breathing",
  "title": "4-7-8 Breathing Exercise",
  "description": "A calming breathing technique to reduce anxiety and stress",
  "steps": [
    "Find a comfortable seated position",
    "Breathe in through your nose for 4 counts",
    "Hold your breath for 7 counts",
    "Exhale completely through your mouth for 8 counts",
    "Repeat 3-4 times"
  ],
  "duration": "2-3 minutes",
  "benefits": [
    "Reduces anxiety",
    "Lowers heart rate",
    "Promotes relaxation"
  ]
}
```

### Delete Conversation

**DELETE** `/api/coach/conversations/{conversation_id}`

Delete a conversation and all its messages (GDPR right to deletion).

**Headers:**
```http
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "status": "deleted",
  "conversation_id": 123
}
```

---

## Burnout Detection

### Predict Burnout Risk

**POST** `/api/burnout/predict`

Generate a burnout risk prediction for the current user.

**Headers:**
```http
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "score": 65.5,
  "risk_level": "moderate",
  "confidence": 0.82,
  "trajectory": "stable",
  "contributing_factors": [
    {
      "factor": "High stress levels",
      "value": 8.2,
      "importance": 0.9,
      "category": "wellbeing"
    },
    {
      "factor": "Heavy workload",
      "value": 8.5,
      "importance": 0.8,
      "category": "work_life_balance"
    }
  ],
  "prediction_date": "2025-01-15T10:30:00Z"
}
```

**Risk Levels:**
- `low`: Score 0-40
- `moderate`: Score 40-60
- `high`: Score 60-80
- `critical`: Score 80-100

### Get Burnout History

**GET** `/api/burnout/history`

Get user's burnout prediction history.

**Headers:**
```http
Authorization: Bearer <token>
```

**Query Parameters:**
- `days` (optional): Number of days of history to return (default: 90)

**Response (200 OK):**
```json
{
  "predictions": [
    {
      "score": 65.5,
      "risk_level": "moderate",
      "confidence": 0.82,
      "trajectory": "stable",
      "contributing_factors": [...],
      "prediction_date": "2025-01-15T10:30:00Z"
    },
    {
      "score": 58.2,
      "risk_level": "moderate",
      "confidence": 0.79,
      "trajectory": "improving",
      "contributing_factors": [...],
      "prediction_date": "2025-01-08T10:30:00Z"
    }
  ],
  "average_score": 61.8,
  "trend": "stable"
}
```

### Submit Daily Check-In

**POST** `/api/burnout/check-in`

Submit daily wellbeing check-in.

**Headers:**
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "mood": 6,         // 1-10 scale
  "energy": 5,       // 1-10 scale
  "stress": 7,       // 1-10 scale
  "sleep": 6,        // 1-10 scale
  "workload": 8,     // 1-10 scale
  "notes": "Had a tough meeting this morning but feeling better now."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Check-in recorded",
  "check_in_date": "2025-01-15T10:30:00Z"
}
```

### Get Team Analytics (HR/Manager only)

**GET** `/api/burnout/analytics/team`

Get aggregated burnout analytics for a team or organization.

**Headers:**
```http
Authorization: Bearer <token>
```

**Query Parameters:**
- `department_id` (optional): Filter by department

**Response (200 OK):**
```json
{
  "total_employees": 50,
  "average_score": 55.3,
  "risk_distribution": {
    "low": 15,
    "moderate": 25,
    "high": 8,
    "critical": 2
  },
  "top_contributing_factors": [
    {
      "category": "work_life_balance",
      "count": 32
    },
    {
      "category": "wellbeing",
      "count": 28
    }
  ],
  "high_risk_count": 10,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Privacy Note:** Only returns aggregated data for groups of 5+ employees.

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Validation error message",
  "status_code": 400
}
```

### 401 Unauthorized
```json
{
  "error": "Could not validate credentials",
  "status_code": 401
}
```

### 403 Forbidden
```json
{
  "error": "Insufficient permissions",
  "status_code": 403
}
```

### 404 Not Found
```json
{
  "error": "Resource not found",
  "status_code": 404
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "status_code": 429
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "status_code": 500
}
```

---

## Rate Limiting

API requests are rate-limited to **60 requests per minute** per user.

When rate limit is exceeded, the API returns a `429 Too Many Requests` error.

Response headers include:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642255200
```

---

## Webhooks (Enterprise Only)

Enterprise customers can configure webhooks to receive real-time notifications.

### Available Events

- `burnout.high_risk` - Triggered when user reaches high/critical burnout risk
- `crisis.detected` - Triggered when crisis keywords detected
- `check_in.completed` - Triggered when user completes daily check-in
- `intervention.triggered` - Triggered when system recommends intervention

### Webhook Payload Example

```json
{
  "event": "burnout.high_risk",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "user_id": 123,
    "score": 78,
    "risk_level": "high",
    "department_id": 5
  }
}
```

### Webhook Security

All webhook requests include a signature in the `X-MindShift-Signature` header:

```python
# Verify webhook signature
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## SDKs

### Python SDK

```bash
pip install mindshift-sdk
```

```python
from mindshift import MindShift

client = MindShift(api_key="your_api_key")

# Send message to AI coach
response = client.coach.chat(
    message="I'm feeling stressed",
    persona="coach"
)

# Get burnout prediction
prediction = client.burnout.predict()
print(f"Burnout score: {prediction.score}")

# Submit check-in
client.burnout.check_in(
    mood=6,
    energy=5,
    stress=7,
    sleep=6,
    workload=8
)
```

### JavaScript SDK

```bash
npm install @mindshift/sdk
```

```javascript
import MindShift from '@mindshift/sdk';

const client = new MindShift({ apiKey: 'your_api_key' });

// Send message to AI coach
const response = await client.coach.chat({
  message: "I'm feeling stressed",
  persona: "coach"
});

// Get burnout prediction
const prediction = await client.burnout.predict();
console.log(`Burnout score: ${prediction.score}`);

// Submit check-in
await client.burnout.checkIn({
  mood: 6,
  energy: 5,
  stress: 7,
  sleep: 6,
  workload: 8
});
```

---

## API Versioning

The API uses URL versioning. Current version is **v1**.

All endpoints are prefixed with `/api/` which implicitly refers to v1.

Future versions will use `/api/v2/`, etc.

---

## Support

For API support:
- Email: api-support@mindshift.ai
- Documentation: https://docs.mindshift.ai
- Status: https://status.mindshift.ai

**Document Version**: 1.0
**Last Updated**: January 2025
