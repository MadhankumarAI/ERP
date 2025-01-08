from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from datetime import datetime, timedelta
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os

from flask import Flask, render_template, request, jsonify
import mysql.connector
from datetime import datetime, timedelta
import logging
from datetime import datetime


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database Connection Configuration
import os

import mysql.connector
import os

def get_db_connection():
    connection_url = 'mysql://root:buAaAdqKZqXtqnubglideseeOvNHCBFK@junction.proxy.rlwy.net:25956/railway'

    # Parsing the connection string manually
    from urllib.parse import urlparse
    result = urlparse(connection_url)

    db_config = {
        'host': result.hostname,
        'user': result.username,
        'password': result.password,
        'database': result.path[1:],  # Remove leading '/' from database name
        'port': result.port
    }

    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        raise

# Example usage:
conn = get_db_connection()



@app.route('/')
def index():
    """Render the main index page"""
    return render_template('index.html')

@app.route('/bot_entry', methods=['GET', 'POST'])
def bot_entry():
    """Handle bot entry form submissions"""
    if request.method == 'POST':
        total_amount = request.form['total_amount']
        invoice_number = request.form['invoice_number']
        # When processing the form
        invoice_date_str = request.form['invoice_date']
        invoice_date = datetime.strptime(invoice_date_str, '%d%m%Y').date()
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert data into the ERP table
            query = """
            INSERT INTO erp (total_amount, invoice_number, invoice_date) 
            VALUES (%s, %s, %s)
            """
            cursor.execute(query, (total_amount, invoice_number, invoice_date))
            
            conn.commit()
            cursor.close()
            conn.close()
            
           
        except Exception as e:
            logger.error(f"Bot entry error: {str(e)}")
            return f"An error occurred: {str(e)}"
        
    return render_template('botentry.html')


@app.route('/user_invoice_summary', methods=['GET', 'POST'])
def user_invoice_summary():
    """Handle user invoice summary requests."""
    if request.method == 'POST':
        summary_type = request.form.get('summary_type')

        # Validate input
        valid_summary_types = ['today', 'this_week', 'year']
        if not summary_type or summary_type not in valid_summary_types:
            return jsonify({'error': 'Invalid summary type'}), 400

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Prepare the query based on summary type
            if summary_type == 'today':
                query = """
                    SELECT 
                        COALESCE(SUM(total_amount), 0) as total
                    FROM erp
                    WHERE DATE(invoice_date) = CURDATE()
                """
            elif summary_type == 'this_week':
                query = """
                    SELECT 
                        COALESCE(SUM(total_amount), 0) as total
                    FROM erp
                    WHERE YEAR(invoice_date) = YEAR(CURDATE()) 
                    AND WEEK(invoice_date, 1) = WEEK(CURDATE(), 1)
                """
            elif summary_type == 'year':
                query = """
                    SELECT 
                        COALESCE(SUM(total_amount), 0) as total
                    FROM erp
                    WHERE invoice_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 1 YEAR) AND CURDATE()
                """

            # Execute the query
            cursor.execute(query)
            result = cursor.fetchone()

            # Ensure total is always a numeric value
            total = float(result['total']) if result else 0

            return jsonify({
                'total': total,
                'summary_type': summary_type
            })

        except mysql.connector.Error as db_error:
            logger.error(f"Database error: {db_error}")
            return jsonify({'error': f'Database error: {str(db_error)}'}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
        finally:
            # Ensure connection is closed even if an error occurs
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return render_template('users.html')


# Add these configurations
app.secret_key = os.urandom(24)  # For session management
smtp_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_username': 'madhan786819@gmail.com',  # Replace with your email
    'smtp_password': 'yhvc yxrm snkg jgza'      # Replace with your app password
}

def send_otp_email(email, otp):
    """Send OTP via email using SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_config['smtp_username']
        msg['To'] = email
        msg['Subject'] = 'Your Login OTP'
        
        body = f'Welcome to erp\nwe aim to prosecc invoices in lightning spped with maximum accuracy\nYour OTP for login is: {otp}\n this otp system is to keep our erp invoice/budget details safe'
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
        server.starttls()
        server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        return False

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """Handle user sign-in"""
    if request.method == 'POST':
        company_name = request.form['company_name']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Verify company credentials
            query = """
            SELECT email, password 
            FROM password_man 
            WHERE company_name = %s
            """
            cursor.execute(query, (company_name,))
            result = cursor.fetchone()
            
            if result and result['password'] == password:
                # Generate OTP
                otp = str(random.randint(100000, 999999))
                session['otp'] = otp
                session['company_name'] = company_name
                session['email'] = result['email']
                
                # Send OTP via email
                if send_otp_email(result['email'], otp):
                    return redirect(url_for('verify_otp'))
                else:
                    return "Error sending OTP email", 500
            else:
                return "Invalid credentials", 401
                
        except Exception as e:
            logger.error(f"Sign-in error: {str(e)}")
            return f"An error occurred: {str(e)}"
        finally:
            cursor.close()
            conn.close()
            
    return render_template('signin.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Handle OTP verification"""
    if 'otp' not in session:
        return redirect(url_for('signin'))
        
    if request.method == 'POST':
        user_otp = request.form['otp']
        if user_otp == session['otp']:
            # Clear sensitive session data
            session.pop('otp', None)
            session['authenticated'] = True
            return redirect(url_for('user_invoice_summary'))
        else:
            return "Invalid OTP", 401
            
    return render_template('verify_otp.html')

# Add authentication check to protected routes
def login_required(f):
    """Decorator to require login for routes"""
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

