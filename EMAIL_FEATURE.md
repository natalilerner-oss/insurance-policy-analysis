# Email Delivery Feature for Insurance Portfolio

This document describes the email delivery functionality added to the Insurance Policy Analysis system.

## Overview

Users can now optionally receive insurance portfolio download links via email after generating a portfolio. This feature uses SendGrid for reliable email delivery and includes a professional Hebrew email template with RTL support.

## Features

- ✅ Optional email delivery checkbox in the UI
- ✅ Professional Hebrew email template with RTL layout
- ✅ Portfolio summary included in email (family name, premium, product count)
- ✅ Mobile-responsive email design
- ✅ 7-day download link expiration notice
- ✅ Asynchronous email sending (doesn't block portfolio generation)
- ✅ Graceful degradation if SendGrid not configured
- ✅ Comprehensive error handling and logging

## Environment Configuration

To enable email functionality, configure the following environment variables:

### Required Variables

```bash
# SendGrid API Key (obtain from https://sendgrid.com)
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx

# Verified sender email address (must be verified in SendGrid)
SENDER_EMAIL=noreply@yourdomain.com
```

### SendGrid Setup

1. Create a SendGrid account at https://sendgrid.com
2. Verify your sender email address or domain
3. Generate an API key with "Mail Send" permissions
4. Add the API key to your environment variables

## Usage

### Frontend (User Experience)

1. Navigate to Tab 3: "יצירת תיק ביטוח" (Create Insurance Portfolio)
2. Fill in family name and report date
3. Check the box "📧 שלח לינק למייל" (Send link via email)
4. Enter email address in the text field
5. Click "צור תיק ביטוח Excel" (Create Excel Portfolio)
6. Success message confirms email was sent (if configured)

### Backend (API)

The portfolio generation endpoint accepts an optional `recipient_email` field:

```json
POST /generate_insurance_portfolio
{
  "family_name": "ישראלי",
  "report_date": "2024-01-15",
  "family_members": [...],
  "insurance_products": [...],
  "recipient_email": "user@example.com"  // Optional
}
```

If `recipient_email` is provided and SendGrid is configured, an email will be sent asynchronously after the portfolio is generated.

## Email Template

The email includes:

- **Header**: PolicyLens branding with gradient background
- **Greeting**: Personalized in Hebrew
- **Summary Box**: 
  - Family name
  - Report date
  - Number of products
  - Total monthly premium
- **Download Button**: Large, prominent call-to-action
- **Expiration Notice**: 7-day validity warning
- **Footer**: Branding and tagline

### Sample Email

```
🔍 PolicyLens
תיק הביטוח המשפחתי שלך מוכן!

שלום,

תיק הביטוח המשפחתי עבור משפחת ישראלי נוצר בהצלחה ומוכן להורדה.

📊 סיכום תיק הביטוח
- שם המשפחה: ישראלי
- תאריך הדוח: 2024-01-15
- מספר מוצרים: 5
- סה"כ פרמיה חודשית: ₪1,500.50

[📥 הורד את תיק הביטוח]

⏰ שים לב: קישור ההורדה תקף למשך 7 ימים.
```

## Error Handling

### SendGrid Not Configured

If `SENDGRID_API_KEY` or `SENDER_EMAIL` are not set:
- Warning is logged
- Email is not sent
- Portfolio generation continues successfully
- No error shown to user

### Email Sending Failure

If SendGrid API fails:
- Error is logged with full details
- Portfolio generation continues successfully
- Download link still available in UI
- No error shown to user (graceful degradation)

### Invalid Email Address

Frontend validation checks:
- Email contains '@' symbol
- Email has valid domain with TLD (e.g., .com, .org)
- Email matches standard email format regex

## Implementation Details

### Files Modified

1. **src/insurance_portfolio_schema.py**: Added `recipient_email` field
2. **src/email_service.py**: New email service module
3. **src/blueprints/portfolio.py**: Integrated email sending
4. **frontend/app.py**: Added UI elements for email input
5. **requirements.txt**: Added SendGrid dependency

### Architecture

```
Frontend (Streamlit)
    ↓
    POST /generate_insurance_portfolio
    ↓
Portfolio Endpoint
    ↓
Generate Excel → Upload to Blob Storage → Get Download URL
    ↓
[If email provided]
    ↓
Spawn Background Thread → Email Service → SendGrid API
    ↓
Return Response (immediate, doesn't wait for email)
```

### Thread Safety

- Email sending uses daemon threads for simplicity
- For production with high reliability requirements, consider using a message queue (Azure Storage Queue)
- Current implementation ensures portfolio generation is never blocked or failed by email issues

## Testing

### Unit Tests

Run the email service tests:

```bash
python test_email_service.py
```

Tests cover:
- HTML email generation
- SendGrid not configured scenario
- Successful email sending (mocked)
- Email sending failures

### Integration Test

Run the full portfolio generation test:

```bash
python test_portfolio.py
```

This verifies no regressions in portfolio generation.

## Monitoring and Logging

All email operations are logged:

```python
# Success
logger.info(f"Email sent successfully to {recipient_email}")

# Configuration warning
logger.warning("SendGrid not properly configured - email not sent")

# Failure
logger.error(f"Failed to send email to {recipient_email}: {error}")
```

Check application logs to monitor email delivery status.

## Security Considerations

- ✅ Email addresses validated before sending
- ✅ No sensitive data in email body (only download link)
- ✅ Download links expire after 7 days
- ✅ SendGrid API key stored in environment variables (never in code)
- ✅ No email content logged (privacy)
- ✅ Sender email must be verified in SendGrid

## Future Enhancements

Potential improvements:
1. Email templates in multiple languages
2. Custom email templates per organization
3. Email delivery status tracking
4. Retry logic for failed emails
5. Queue-based email sending for better reliability
6. Email open/click tracking
7. Batch email sending for multiple recipients

## Support

For issues or questions:
1. Check application logs for error messages
2. Verify SendGrid configuration
3. Test with SendGrid's email validation tool
4. Review SendGrid dashboard for delivery status
