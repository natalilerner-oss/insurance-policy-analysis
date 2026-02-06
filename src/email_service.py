"""
Email service for sending insurance portfolio download links via SendGrid.
Supports Hebrew text with RTL formatting.

Environment Variables Required:
- SENDGRID_API_KEY: SendGrid API key for sending emails (REQUIRED)
- SENDER_EMAIL: The verified sender email address configured in SendGrid (REQUIRED)
  
Note: The sender email must be verified in your SendGrid account before sending emails.
If these environment variables are not set, emails will not be sent and a warning will be logged.
"""

import os
import logging
from typing import Optional, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)


def create_portfolio_email_html(
    family_name: str,
    download_link: str,
    total_premium: float,
    products_count: int,
    report_date: str
) -> str:
    """
    Create Hebrew HTML email template with RTL support for portfolio download.
    
    Args:
        family_name: Name of the family
        download_link: URL to download the portfolio
        total_premium: Total monthly premium amount
        products_count: Number of insurance products
        report_date: Report generation date
        
    Returns:
        HTML email content
    """
    html = f"""
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>תיק ביטוח משפחתי</title>
    <style>
        body {{
            font-family: Arial, 'Segoe UI', Tahoma, sans-serif;
            direction: rtl;
            text-align: right;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .greeting {{
            font-size: 18px;
            margin-bottom: 20px;
            color: #333;
        }}
        .summary-box {{
            background-color: #f8f9fa;
            border-right: 4px solid #4F46E5;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .summary-box h3 {{
            margin-top: 0;
            color: #4F46E5;
            font-size: 18px;
        }}
        .summary-item {{
            margin: 10px 0;
            font-size: 16px;
            color: #555;
        }}
        .summary-item strong {{
            color: #333;
        }}
        .download-button {{
            display: inline-block;
            background-color: #10B981;
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 6px;
            font-size: 18px;
            font-weight: bold;
            margin: 20px 0;
            text-align: center;
        }}
        .download-button:hover {{
            background-color: #059669;
        }}
        .notice {{
            background-color: #FEF3C7;
            border-right: 4px solid #F59E0B;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            font-size: 14px;
            color: #92400E;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 14px;
            color: #666;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 0;
                border-radius: 0;
            }}
            .content {{
                padding: 20px 15px;
            }}
            .download-button {{
                display: block;
                width: 100%;
                box-sizing: border-box;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 PolicyLens</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px;">תיק הביטוח המשפחתי שלך מוכן!</p>
        </div>
        
        <div class="content">
            <div class="greeting">
                שלום,
            </div>
            
            <p style="font-size: 16px; line-height: 1.6; color: #444;">
                תיק הביטוח המשפחתי עבור <strong>משפחת {family_name}</strong> נוצר בהצלחה ומוכן להורדה.
            </p>
            
            <div class="summary-box">
                <h3>📊 סיכום תיק הביטוח</h3>
                <div class="summary-item">
                    <strong>שם המשפחה:</strong> {family_name}
                </div>
                <div class="summary-item">
                    <strong>תאריך הדוח:</strong> {report_date}
                </div>
                <div class="summary-item">
                    <strong>מספר מוצרים:</strong> {products_count}
                </div>
                <div class="summary-item">
                    <strong>סה"כ פרמיה חודשית:</strong> ₪{total_premium:,.2f}
                </div>
            </div>
            
            <div style="text-align: center;">
                <a href="{download_link}" class="download-button">
                    📥 הורד את תיק הביטוח
                </a>
            </div>
            
            <div class="notice">
                <strong>⏰ שים לב:</strong> קישור ההורדה תקף למשך 7 ימים. לאחר מכן, יהיה צורך ליצור תיק חדש.
            </div>
            
            <p style="font-size: 14px; color: #666; margin-top: 30px;">
                הקובץ כולל סיכום מקיף של כל הפוליסות המשפחתיות, כולל פרטי כיסויים, פרמיות, והחרגות.
            </p>
        </div>
        
        <div class="footer">
            <p style="margin: 5px 0;">
                <strong>PolicyLens by DocumentInsight.ai</strong>
            </p>
            <p style="margin: 5px 0; font-size: 12px;">
                From a junkyard of information to a gallery of Knowledge
            </p>
        </div>
    </div>
</body>
</html>
"""
    return html


def send_portfolio_email(
    recipient_email: str,
    family_name: str,
    download_link: str,
    total_premium: float,
    products_count: int,
    report_date: str
) -> Dict[str, Any]:
    """
    Send insurance portfolio download link via email using SendGrid.
    
    Args:
        recipient_email: Email address to send to
        family_name: Name of the family
        download_link: URL to download the portfolio
        total_premium: Total monthly premium amount
        products_count: Number of insurance products
        report_date: Report generation date
        
    Returns:
        Dict with success status and message
        
    Example:
        result = send_portfolio_email(
            "user@example.com",
            "ישראלי",
            "https://storage.example.com/portfolio.xlsx",
            500.50,
            5,
            "2024-01-15"
        )
    """
    # Check if SendGrid is configured
    api_key = os.getenv('SENDGRID_API_KEY')
    sender_email = os.getenv('SENDER_EMAIL')
    
    if not api_key or not sender_email:
        logger.warning(
            "SendGrid not properly configured - email not sent. "
            "Please set SENDGRID_API_KEY and SENDER_EMAIL environment variables."
        )
        return {
            "success": False,
            "error": "SendGrid not configured",
            "message": "Email service is not configured. Please set SENDGRID_API_KEY and SENDER_EMAIL environment variables."
        }
    
    try:
        # Create email content
        html_content = create_portfolio_email_html(
            family_name=family_name,
            download_link=download_link,
            total_premium=total_premium,
            products_count=products_count,
            report_date=report_date
        )
        
        # Create message
        message = Mail(
            from_email=Email(sender_email, "PolicyLens"),
            to_emails=To(recipient_email),
            subject=f"תיק הביטוח של משפחת {family_name} מוכן להורדה",
            html_content=Content("text/html", html_content)
        )
        
        # Send email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        logger.info(
            f"Email sent successfully to {recipient_email} "
            f"(status: {response.status_code}, family: {family_name})"
        )
        
        return {
            "success": True,
            "message": "Email sent successfully",
            "status_code": response.status_code
        }
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send email: {str(e)}"
        }
