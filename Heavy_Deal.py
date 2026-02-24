from flask import Flask, render_template, request, redirect, session
import mysql.connector
import random
import smtplib 
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cloudinary
import cloudinary.uploader
from datetime import datetime
import json
import os

cloudinary.config(
    cloud_name="dajnnvznf",
    api_key="949949375829316",
    api_secret="BQ1CJTtlscFnilZ1OnU-MBgZ6vA"
)

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

google_creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)



app = Flask(__name__)

UPLOAD_FOLDER = 'static/deal_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = "heavy-secret"   # learning purpose

# ----------send email for password --------------
def send_verification_email(to_email, code):
    try:
        msg = MIMEText(f"""
Heavy Deals – Password Reset

Your verification code is: {code}

If you did not request this, ignore this email.
""")

        msg['Subject'] = "Heavy Deals | Password Reset Code"
        msg['From'] = "heavydeals07@gmail.com"
        msg['To'] = to_email

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login("heavydeals07@gmail.com", "tpoj rjnp ltqe fmew")
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("EMAIL ERROR:", e)

# ---------- DB CONNECTION ----------
def db():
    return mysql.connector.connect(
        host="centerbeam.proxy.rlwy.net",
        user="root",
        password="GZFvMhflsqtzEyFBvPOnNtrapaJWNqhF",
        database="railway",
        port=11620
    )

# ---------- HOME ----------
@app.route('/')
def Home():
    return render_template("Home.html")


# ---------- CUSTOMER REGISTRATION ----------
@app.route('/Customer_Ragistration', methods=['GET','POST'])
def Customer_Ragistration():
    msg = ""
    if request.method == 'POST':
        name = request.form['N']
        num = request.form['Num']
        passw = request.form['P']
        email = request.form['E']
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer WHERE Number=%s", (num,))
        if cur.fetchone():
            msg = "This mobile number is already registered"
        else:
            cur.execute(
                "INSERT INTO customer (Name, Number, passw, email) VALUES (%s,%s,%s,%s)",
                (name, num, passw, email)
            )
            conn.commit()
            cur.close()
            conn.close()
            session['Cust name'] = name
            session['Cust num'] = num
            session['Cust passw'] = passw
            session['Cust email'] = email
            return render_template("Registration_Success.html")
        cur.close()
        conn.close()
    return render_template("Customer_Ragistration.html", msg=msg)

# ---------- CUSTOMER LOGIN ----------
@app.route('/Customer_Login', methods=['GET','POST'])
def Customer_Login():
    msg = ""
    if request.method == 'POST':
        num = request.form['Num']
        passw = request.form['P']
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer WHERE Number=%s", (num,))
        row = cur.fetchone()
        if row is None:
            msg = "Mobile number not registered"
        elif row[3] != passw:
            msg = "Incorrect password"
        else:
            cur.close()
            conn.close()
            session['Cust name'] = row[1]
            session['Cust num'] = row[2]
            session['Cust passw'] = row[3]
            session['Cust email'] = row[4]
            return redirect('/Customer_Portal/Dashboard')
        cur.close()
        conn.close()
    return render_template("Customer_Login.html", msg=msg)

# ---------- Loout ----------
@app.route('/Logout')
def Logout():
    session.clear()
    return redirect('/')

    # -------------Cost Forgot password---------------

# ---------- Password reset ----------
@app.route('/Forgot_Password', methods=['GET', 'POST'])
def Forgot_Password():
    msg = ""

    if request.method == 'POST':
        email = request.form['email']

        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user is None:
            msg = "Email not registered"
        else:
            code = str(random.randint(100000, 999999))
            session['fp_email'] = email
            session['fp_code'] = code

            send_verification_email(email, code)
            return redirect('/Verify_Code')

    return render_template('Forgot_Password.html', msg=msg)
@app.route('/Verify_Code', methods=['GET', 'POST'])
def Verify_Code():
    msg = ""

    if request.method == 'POST':
        user_code = request.form['code']

        if user_code == session.get('fp_code'):
            return redirect('/Reset_Password')
        else:
            msg = "Invalid verification code"

    return render_template('Verify_Code.html', msg=msg)
@app.route('/Reset_Password', methods=['GET', 'POST'])
def Reset_Password():
    msg = ""

    if request.method == 'POST':
        p1 = request.form['p1']
        p2 = request.form['p2']

        if p1 != p2:
            msg = "Passwords do not match"
        else:
            email = session.get('fp_email')

            conn = db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE customer SET passw=%s WHERE email=%s",
                (p1, email)
            )
            conn.commit()
            cur.close()
            conn.close()

            session.pop('fp_email', None)
            session.pop('fp_code', None)

            return redirect('/Password_Reset_Success')

    return render_template('Reset_Password.html', msg=msg)
@app.route('/Password_Reset_Success')
def Password_Reset_Success():
    return render_template('Password_Reset_Success.html')


# ---------- CUSTOMER PORTAL ----------
@app.route('/Customer_Portal/Dashboard')
def Customer_Portal_Dashboard():
    name=session.get('Cust name')
    num=session.get('Cust num')
    passw=session.get('Cust passw')
    email=session.get('Cust email')
    if num == None:
        return redirect('/')

    sheet = client.open("Demo Order").sheet1
    all_values = sheet.get_all_values()
    headers = all_values[0]
    data_rows = all_values[1:]
    mobile_index = headers.index("Mobile")
    order_id_index = headers.index("Order ID")
    order_date_index = headers.index("Order date")
    order_status_index = headers.index("Status")
    user_orders = []

    TO = 0
    for row in data_rows:
        if row[mobile_index] == num:
            TO+=1
            user_orders.append((row[order_id_index], row[order_date_index], row[order_status_index]))
    
    RO = 0
    for i in user_orders:
        if i[2]=="Done":
            RO+=1
    
    
    return render_template("Customer_Dashboard.html",orders=user_orders, name=name, num=num, passw=passw, email=email,TO=TO,PO=TO-RO,CO=RO,R=RO*60)

# ---------- MEDIATOR LOGIN ----------
@app.route('/Mediator_Login',methods=['GET','POST'])
def Mediator_Login():
    msg=""
    if request.method == 'POST':
        MUN=request.form['MUN']
        MP=request.form['MP']

        conn = db()
        cur=conn.cursor()

        cur.execute("SELECT * FROM mediator WHERE username=%s", (MUN,))
        row = cur.fetchone()

        if row is None:
            msg = "Username not found"
        elif row[4] != MP:
            msg = "Incorrect password"
        else:
            cur.close()
            conn.close()
            session['Med Username'] = row[1]
            session['Med name'] = row[2]
            session['Med num'] = row[3]
            session['Med passw'] = row[4]
            return redirect('/Mediator_Portal/Dashboard')
        cur.close()
        conn.close()
    return render_template("Mediator_Login.html",msg=msg)

#------------Med Forgot passeord--------------
@app.route('/Med_Forgot_Password', methods=['GET', 'POST'])
def MForgot_Password():
    msg = ""

    if request.method == 'POST':
        email = request.form['email']

        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM mediator WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user is None:
            msg = "Email not registered"
        else:
            code = str(random.randint(100000, 999999))
            session['fp_email'] = email
            session['fp_code'] = code

            send_verification_email(email, code)
            return redirect('/Med_Verify_Code')

    return render_template('Med_Forgot_Password.html', msg=msg)
@app.route('/Med_Verify_Code', methods=['GET', 'POST'])
def MVerify_Code():
    msg = ""

    if request.method == 'POST':
        user_code = request.form['code']

        if user_code == session.get('fp_code'):
            return redirect('/Med_Reset_Password')
        else:
            msg = "Invalid verification code"

    return render_template('Med_Verify_Code.html', msg=msg)
@app.route('/Med_Reset_Password', methods=['GET', 'POST'])
def MReset_Password():
    msg = ""

    if request.method == 'POST':
        p1 = request.form['p1']
        p2 = request.form['p2']

        if p1 != p2:
            msg = "Passwords do not match"
        else:
            email = session.get('fp_email')

            conn = db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE mediator SET password=%s WHERE email=%s",
                (p1, email)
            )
            conn.commit()
            cur.close()
            conn.close()

            session.pop('fp_email', None)
            session.pop('fp_code', None)

            return redirect('/Med_Password_Reset_Success')

    return render_template('Med_Reset_Password.html', msg=msg)
@app.route('/Med_Password_Reset_Success')
def MPassword_Reset_Success():
    return render_template('Med_Password_Reset_Success.html')


# ---------- MEDIATOR PORTAL ----------
@app.route('/Mediator_Portal/Dashboard')
def Mediator_Portal_Dashboard():
    MUN = session.get('Med Username')
    MN = session.get('Med name')
    MNUM = session.get('Med num')

    if MUN == None:
        return redirect('/')
        
    TO=0
    RF=0
    
    return render_template('Mediator_Dashboard.html', MUN=MUN, MN=MN, MNUM=MNUM, TO=TO, RF=RF, TP=RF*60)



@app.route("/add_deal_code", methods=["POST"])
def add_deal_code():
    Nmsg=""
    pmsg=""
    MUN = session.get('Med Username')
    MN = session.get('Med name')
    MNUM = session.get('Med num')
    if request.method=='POST':
        deal_code = request.form["deal_code"]
        conn = db()
        cur=conn.cursor()
        cur.execute("SELECT * FROM deal_codes WHERE deal_code=%s", (deal_code,))
        if cur.fetchone():
            Nmsg = "This Deal Code is already exist"
            cur.close()
            conn.close()
            return render_template('Mediator_Dashboard.html', MUN=MUN, MN=MN, MNUM=MNUM, Nmsg=Nmsg)
        else:
            cur.execute(
                "INSERT INTO deal_codes (deal_code) VALUES (%s)",
                (deal_code,)
            )
            conn.commit()
            cur.close()
            conn.close()
            Pmsg=f"Added {deal_code}"
            return render_template('Mediator_Dashboard.html', MUN=MUN, MN=MN, MNUM=MNUM, Pmsg=Pmsg)
        
    return render_template('Mediator_Dashboard.html', MUN=MUN, MN=MN, MNUM=MNUM)


@app.route("/orderform", methods=["GET", "POST"])
def orderform():
    name=session.get('Cust name')
    num=session.get('Cust num')
    passw=session.get('Cust passw')
    email=session.get('Cust email')
    
    if request.method == "POST":
        OSheet= client.open("Demo Order").sheet1
        SellerO_sheet= client.open("Done Order Form").sheet1
        deal_code   = request.form.get("deal_code")
        order_id       = request.form.get("order_id")
        date_input     = request.form.get("order_date")
        order_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%d-%m-%Y")
        amount         = int(request.form.get("amount"))
        deal_type      = 'COD Deal'
        reviewer_name  = request.form.get("reviewer_name")
        Product_name       = request.form.get("PN")
        

        Order_SS = request.files.get("screenshot")
        if Order_SS:
            result = cloudinary.uploader.upload(Order_SS)
            url = result['secure_url']
        
        now = datetime.now().replace(microsecond=0)
        OSheet.append_row([str(now),deal_code,reviewer_name,order_date,deal_type,Product_name,url,amount,order_id,email,"Jaynil Bhalani",int(num)])
        SellerO_sheet.append_row([reviewer_name,order_date,deal_type,Product_name,url,amount,order_id,"Jaynil Bhalani","Pending"])

        conn = db()
        cur = conn.cursor()
        cur.execute("UPDATE customer SET ordercount = ordercount + 1 WHERE Number=%s", (num,))
        conn.commit()
        cur.close()
        conn.close()
        
        return render_template("order_success.html")
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT deal_code FROM deal_codes")
    deal_data = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("Customer_Order_Form.html", name=name, num=num, passw=passw, email=email,deals=deal_data)


@app.route("/refundform", methods=["GET", "POST"])
def refundform():
    id = request.args.get("id")
    name=session.get('Cust name')
    num=session.get('Cust num')
    passw=session.get('Cust passw')
    email=session.get('Cust email')
    if request.method == "POST":
        RSheet= client.open("Demo Refund").sheet1
        SellerR_sheet= client.open("Done Refund form").sheet1
        OrderSheet = client.open("Demo Order").sheet1
        deal_code   = request.form.get("deal_code")
        if id :
            order_id=id
        else:
            order_id       = request.form.get("order_id_p")
        date_input     = request.form.get("order_date")
        order_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%d-%m-%Y")
        Product_name         = request.form.get("PN")
        deal_type      = 'COD Deal'
        reviewer_name  = request.form.get("reviewer_name")
        link           = request.form.get("link")

        Review_SS = request.files.get("Review-screenshot")
        if Review_SS:
            result = cloudinary.uploader.upload(Review_SS)
            Review_url = result['secure_url']

        D_SS = request.files.get("D-screenshot")
        if D_SS:
            result = cloudinary.uploader.upload(D_SS)
            D_url = result['secure_url']

        now = datetime.now().replace(microsecond=0)
        RSheet.append_row([str(now),deal_code,reviewer_name,order_date,deal_type,Product_name,D_url,order_id,Review_url,link,"Jaynil Bhalani",int(num),email])
        SellerR_sheet.append_row([reviewer_name,order_date,deal_type,Product_name,D_url,order_id,Review_url,link,"Jaynil Bhalani"])

        all_data = OrderSheet.get_all_values()
        headers = all_data[0]
        rows = all_data[1:]
        order_id_col = headers.index("Order ID")
        status_col   = headers.index("Status")
        Dss_col      = headers.index("Delivered SS")
        Rss_col      = headers.index("Review SS")
        RL_col       = headers.index("Review Link")
        form_order_id = order_id
        for i, row in enumerate(rows, start=2):
            if row[order_id_col] == form_order_id:
                OrderSheet.update_cell(i, status_col + 1, "Done")
                OrderSheet.update_cell(i, Dss_col + 1, D_SS)
                OrderSheet.update_cell(i, Rss_col + 1, Review_url)
                OrderSheet.update_cell(i, RL_col + 1, link)
                break

        conn = db()
        cur = conn.cursor()
        cur.execute("UPDATE customer SET refundcount = refundcount + 1 WHERE Number=%s", (num,))
        conn.commit()
        cur.close()
        conn.close()


        return render_template("order_success.html")
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT deal_code FROM deal_codes")
    deal_data = cursor.fetchall()
    cursor.close()
    conn.close()
    if id != 'undefined' :
        return render_template("Customer_Refund_Form.html",id=id, name=name, num=num, passw=passw, email=email,deals=deal_data)
    else :
        return render_template("Customer_Refund_Form.html", name=name, num=num, passw=passw, email=email,deals=deal_data)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)












