import os
import smtplib
import csv
import io
from flask import Flask, render_template, request, flash, redirect, url_for
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = os.urandom(24) # Generates a secure secret key

# SMTP server details
SMTP_CONFIG = {
    'gmail':    {'server': 'smtp.gmail.com', 'port': 587},
    'icloud':   {'server': 'smtp.mail.me.com', 'port': 587},
    'outlook':  {'server': 'smtp.office365.com', 'port': 587},
    'yahoo':    {'server': 'smtp.mail.yahoo.com', 'port': 587}
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send():
    try:
        # --- 1. Get Form Data ---
        server_choice = request.form['smtp_server']
        sender_name = request.form['sender_name']
        subject = request.form['subject']
        body = request.form['body']
        
        smtp_file = request.files.get('smtp_credentials')
        customers_file = request.files.get('customers_file')
        attachments = request.files.getlist('attachment') # Use getlist for multiple files

        # --- 2. Process SMTP Credentials File (INSECURE) ---
        if not smtp_file:
            flash('Error: SMTP credentials file is missing.', 'danger')
            return redirect(url_for('index'))

        # Read the file in memory without saving it
        stream = io.StringIO(smtp_file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        try:
            sender_email, sender_password = next(csv_reader)
        except (StopIteration, ValueError):
            flash('Error: SMTP credentials CSV is empty or malformed. Format should be: email,password', 'danger')
            return redirect(url_for('index'))

        # --- 3. Process Customer List File ---
        if not customers_file:
            flash('Error: Customer list file is missing.', 'danger')
            return redirect(url_for('index'))
            
        stream = io.StringIO(customers_file.stream.read().decode("UTF8"), newline=None)
        customer_emails = [line[0] for line in csv.reader(stream) if line and line[0].strip()]

        if not customer_emails:
            flash('Error: No valid email addresses found in the customer list file.', 'danger')
            return redirect(url_for('index'))

        # --- 4. Connect to SMTP Server ---
        config = SMTP_CONFIG[server_choice]
        server = smtplib.SMTP(config['server'], config['port'])
        server.starttls()
        server.login(sender_email, sender_password)

        # --- 5. Loop Through Customers and Send Emails ---
        sent_count = 0
        for email in customer_emails:
            msg = MIMEMultipart()
            msg['From'] = f"{sender_name} <{sender_email}>"
            msg['To'] = email
            msg['Subject'] = subject

            # Attach body
            msg.attach(MIMEText(body, 'html'))

            # Attach files
            for f in attachments:
                if f and f.filename:
                    f.seek(0) # Reset file pointer to the beginning
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={f.filename}')
                    msg.attach(part)
            
            server.send_message(msg)
            sent_count += 1
        
        server.quit()
        flash(f'Success! Sent {sent_count} emails using your {server_choice.capitalize()} account.', 'success')

    except smtplib.SMTPAuthenticationError:
        flash('SMTP Authentication Error. Please check the email and app password in your credentials file.', 'danger')
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'danger')

    return redirect(url_for('index'))

if __name__ == '__main__':
    # For local testing only. Render will use gunicorn.
    app.run(debug=True, port=5001)
