import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.company_name = os.getenv("COMPANY_NAME", "Premium Real Estate")
    
    def send_appointment_confirmation(self, appointment_data: dict) -> bool:
        """
        Send appointment confirmation email to the caller.
        Returns True if email was sent successfully, False otherwise.
        """
        if not self.smtp_user or not self.smtp_password:
            print("Email not configured - SMTP credentials missing")
            return False
        
        try:
            to_email = appointment_data.get("email")
            name = appointment_data.get("name", "Valued Customer")
            location = appointment_data.get("location", "To be confirmed")
            property_type = appointment_data.get("property_type", "Property")
            appointment_date = appointment_data.get("appointment_date", "To be confirmed")
            appointment_time = appointment_data.get("appointment_time", "To be confirmed")
            budget = appointment_data.get("budget", "Not specified")
            notes = appointment_data.get("notes", "")
            
            subject = f"🏠 Your Property Viewing Appointment - {self.company_name}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%); color: white; padding: 30px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .content {{ padding: 30px; }}
                    .greeting {{ font-size: 18px; color: #2d3748; margin-bottom: 20px; }}
                    .details-box {{ background: #f7fafc; border-left: 4px solid #3182ce; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
                    .detail-row {{ display: flex; margin: 10px 0; }}
                    .detail-label {{ font-weight: 600; color: #4a5568; width: 140px; }}
                    .detail-value {{ color: #2d3748; }}
                    .cta-button {{ display: inline-block; background: #3182ce; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-top: 20px; }}
                    .footer {{ background: #2d3748; color: #a0aec0; padding: 20px; text-align: center; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏠 {self.company_name}</h1>
                        <p>Appointment Confirmation</p>
                    </div>
                    <div class="content">
                        <p class="greeting">Dear {name},</p>
                        <p>Thank you for scheduling a property viewing with us! We're excited to help you find your perfect property.</p>
                        
                        <div class="details-box">
                            <h3 style="margin-top: 0; color: #2c5282;">📋 Appointment Details</h3>
                            <div class="detail-row">
                                <span class="detail-label">📅 Date:</span>
                                <span class="detail-value"><strong>{appointment_date}</strong></span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">⏰ Time:</span>
                                <span class="detail-value"><strong>{appointment_time}</strong></span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">📍 Location:</span>
                                <span class="detail-value">{location}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">🏡 Property Type:</span>
                                <span class="detail-value">{property_type}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">💰 Budget:</span>
                                <span class="detail-value">{budget}</span>
                            </div>
                            {f'<div class="detail-row"><span class="detail-label">📝 Notes:</span><span class="detail-value">{notes}</span></div>' if notes else ''}
                        </div>
                        
                        <p>One of our property specialists will contact you shortly to confirm the exact meeting point.</p>
                        <p>If you need to reschedule, please reply to this email or call us.</p>
                        
                        <p style="margin-top: 30px;">Best regards,<br><strong>The {self.company_name} Team</strong></p>
                    </div>
                    <div class="footer">
                        <p>© 2024 {self.company_name}. All rights reserved.</p>
                        <p>This is an automated confirmation email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.company_name} <{self.from_email}>"
            msg["To"] = to_email
            
            # Plain text fallback
            text_body = f"""
            Appointment Confirmation - {self.company_name}
            
            Dear {name},
            
            Your property viewing appointment has been confirmed!
            
            Details:
            - Date: {appointment_date}
            - Time: {appointment_time}
            - Location: {location}
            - Property Type: {property_type}
            - Budget: {budget}
            
            One of our specialists will contact you shortly.
            
            Best regards,
            The {self.company_name} Team
            """
            
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            print(f"✅ Appointment confirmation email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False


# Singleton instance
email_service = EmailService()

def send_appointment_email(appointment_data: dict) -> bool:
    """Convenience function to send appointment confirmation."""
    return email_service.send_appointment_confirmation(appointment_data)
