from flask import Flask, render_template, request, redirect, session,url_for
import mysql.connector
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cloudinary
import cloudinary.uploader
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as SACredentials
from datetime import timedelta
import json
import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = "heavy-secret"
app.permanent_session_lifetime = timedelta(days=60)

cloudinary.config(
    cloud_name="dajnnvznf",
    api_key="949949375829316",
    api_secret="BQ1CJTtlscFnilZ1OnU-MBgZ6vA"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

clint_secret=json.loads(os.getenv("clint_secret"))
ABCD = json.loads(os.getenv("ABCD"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(ABCD, SCOPES)
client = gspread.authorize(creds)



# ----------send email for password --------------
def send_verification_email(to_email, code):
    try:
        message = Mail(
            from_email='heavydeals07@gmail.com',
            to_emails=to_email,
            subject='Heavy Deals | Password Reset Code',
            html_content=f'''
                <h3>Heavy Deals – Password Reset</h3>
                <p>Your verification code is:</p>
                <h2>{code}</h2>
                <p>If you did not request this, ignore this email.</p>
            '''
        )

        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)

        print("Email sent:", response.status_code)

    except Exception as e:
        print("SENDGRID ERROR:", str(e))
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

    # 🔹 Customer already logged in?
    if session.get('Cust num'):
        return redirect('/Customer_Portal/Dashboard')

    # 🔹 Mediator already logged in?
    if session.get('Med Username'):
        return redirect('/Mediator_Portal/Dashboard')

    # 🔹 Otherwise show home page
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
        upi = request.form['upi']
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ShopKaro_Customers WHERE Number=%s", (num,))
        if cur.fetchone():
            msg = "This mobile number is already registered"
        else:
            cur.execute(
                "INSERT INTO ShopKaro_Customers (Name, Number, passw, email,upi) VALUES (%s,%s,%s,%s,%s)",
                (name, num, passw, email,upi)
            )
            conn.commit()
            cur.close()
            conn.close()

            CustomerSheet=client.open("ShopKaro").sheet2
            data = {"Name":name,"Whatsapp":num,"Email":email,"UPI ID":upi}
            safe_append(CustomerSheet, data)

            session.permanent = True
            session['Cust name'] = name
            session['Cust num'] = num
            session['Cust passw'] = passw
            session['Cust email'] = email
            session['Cust upi']=upi
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
        cur.execute("SELECT * FROM ShopKaro_Customers WHERE Number=%s", (num,))
        row = cur.fetchone()
        if row is None:
            msg = "Mobile number not registered"
        elif row[3] != passw:
            msg = "Incorrect password"
        else:
            cur.close()
            conn.close()
            session.permanent = True
            session['Cust name'] = row[1]
            session['Cust num'] = row[2]
            session['Cust passw'] = row[3]
            session['Cust email'] = row[4]
            session['Cust upi']=row[5]
            return redirect('/Customer_Portal/Dashboard')
        cur.close()
        conn.close()
    return render_template("Customer_Login.html", msg=msg)

# ---------- Logout ----------
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
        cur.execute("SELECT * FROM ShopKaro_Customers WHERE email=%s", (email,))
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
                "UPDATE ShopKaro_Customers SET passw=%s WHERE email=%s",
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
    elif session.get('Med num') != None :
        return redirect("/Mediator_Portal/Dashboard")

    sheet = client.open("ShopKaro").sheet1
    all_values = sheet.get_all_values()
    headers = all_values[0]
    data_rows = all_values[1:]
    mobile_index = headers.index("Whatsapp")
    order_id_index = headers.index("Order ID")
    order_date_index = headers.index("Order Date")
    order_status_index = headers.index("Status")
    order_brand_index = headers.index("Brand Name")
    order_refundAmount_index = headers.index("Refund Amount")
    order_reviewer_index = headers.index("Profile Name")
    user_orders = []


    TO = 0
    for row in data_rows:
        if str(row[mobile_index]) == str(num):
            TO+=1
            user_orders.append((row[order_id_index], row[order_date_index], row[order_status_index], row[order_brand_index], row[order_refundAmount_index],row[order_reviewer_index]))
    
    RO = 0
    Payout=0
    for i in user_orders:
        if i[2]=="Done":
            Payout+=int(i[4])
            RO+=1
    
    
    return render_template("Customer_Dashboard.html",orders=user_orders, name=name, num=num, passw=passw, email=email,TO=TO,PO=TO-RO,CO=RO,R=Payout)

# ---------- MEDIATOR LOGIN ----------
@app.route('/Mediator_Login',methods=['GET','POST'])
def Mediator_Login():
    msg=""
    if request.method == 'POST':
        MUN=request.form['MUN']
        MP=request.form['MP']

        conn = db()
        cur=conn.cursor()

        cur.execute("SELECT * FROM ShopKaro_mediator WHERE username=%s", (MUN,))
        row = cur.fetchone()

        if row is None:
            msg = "Username not found"
        elif row[4] != MP:
            msg = "Incorrect password"
        else:
            cur.close()
            conn.close()
            session.permanent = True
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
        cur.execute("SELECT * FROM ShopKaro_mediator WHERE email=%s", (email,))
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
@app.route('/Med_Reset_Password/', methods=['GET', 'POST'])
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
                "UPDATE ShopKaro_mediator SET password=%s WHERE email=%s",
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
    Nmsg = request.args.get("Nmsg")
    Pmsg = request.args.get("Pmsg")
    MUN = session.get('Med Username')
    MN = session.get('Med name')
    MNUM = session.get('Med num')

    if MUN == None:
        return redirect('/')
    
    sheet = client.open("ShopKaro").sheet1
    sheeturl=sheet.url
    all_values = sheet.get_all_values()
    headers = all_values[0]
    data_rows = all_values[1:]
    order_status_index = headers.index("Status")
    order_refundAmount_index = headers.index("Refund Amount")
    user_orders = []

    TO=0
    for row in data_rows:
        TO+=1
        user_orders.append((row[order_status_index],row[order_refundAmount_index]))

    
    CO=0
    Payout=0
    for i in user_orders:
        if i[0]=="Done":
            Payout+=int(i[1])
            CO+=1
    
    return render_template('Mediator_Dashboard.html',Nmsg=Nmsg,Pmsg=Pmsg, MUN=MUN, MN=MN, MNUM=MNUM, TO=TO, CO=CO,PF=(TO-CO), TP=Payout, url=sheeturl)



@app.route("/add_deal_code", methods=["POST"])
def add_deal_code():
    Nmsg=""
    pmsg=""
    MUN = session.get('Med Username')
    MN = session.get('Med name')
    MNUM = session.get('Med num')
    if request.method=='POST':
        seller = request.form["deal_code"]
        conn = db()
        cur=conn.cursor()
        cur.execute("SELECT * FROM ShopKaro_Sellers WHERE Seller=%s", (seller,))
        if cur.fetchone():
            Nmsg = "This Brand is already exist"
            cur.close()
            conn.close()
            return redirect(f'/Mediator_Portal/Dashboard?Nmsg={Nmsg}')
            
        else:
            
            cur.close()
            conn.close()
            session['Brand'] = seller
            return redirect('/login')
        
    return redirect('/Mediator_Portal/Dashboard')
@app.route("/login")
def login():

    username = session.get("Med Username")

    if not username:
        return redirect("/Mediator_Login")

    # -------- Check Token in DB --------
    conn = db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT token FROM ShopKaro_mediator
        WHERE username=%s
    """, (username,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    # If token exists → skip Google login
    if row and row["token"]:
        return redirect("/create-sheet")

    # -------- Else Google OAuth --------
    flow = Flow.from_client_secrets_file(
        clint_secret,
        scopes=SCOPES,
        redirect_uri=url_for("callback", _external=True)
    )

    auth_url, state = flow.authorization_url(prompt="consent")
    session["state"] = state

    return redirect(auth_url)
# ---------------- CALLBACK ----------------
@app.route("/callback")
def callback():

    flow = Flow.from_client_secrets_file(
        clint_secret,
        scopes=SCOPES,
        state=session["state"],
        redirect_uri=url_for("callback", _external=True)
    )

    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials

    # Save token
    token_json = creds.to_json()

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE ShopKaro_mediator SET token=%s WHERE username=%s", (token_json,session["Med Username"]))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/create-sheet")
from google.oauth2.credentials import Credentials
import json
def get_mediator_creds(username):
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT token FROM ShopKaro_mediator
        WHERE username=%s
    """, (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not row["token"]:
        return None
    
    token_data = json.loads(row["token"])
    creds = Credentials.from_authorized_user_info(token_data)
    return creds
from google.auth.transport.requests import Request
def refresh_if_needed(creds, username):
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save updated token
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE ShopKaro_mediator
            SET token=%s
            WHERE username=%s
        """, (
            creds.to_json(),
            username
        ))
        conn.commit()
        cur.close()
        conn.close()
    return creds
# ---------------- CREATE SHEET ----------------
from google.auth.transport.requests import Request
@app.route("/create-sheet")
def create_sheet():

    username = session["Med Username"]

    creds = get_mediator_creds(username)

    if not creds:
        return redirect("/login")

    creds = refresh_if_needed(creds, username)

    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    # Continue sheet creation...

    # -------- Create Sheet --------
    Brand=session.get('Brand')
    spreadsheet = {
        "properties": {
            "title": Brand
        }
    }

    sheet = sheets_service.spreadsheets().create(
        body=spreadsheet,
        fields="spreadsheetId,spreadsheetUrl"
    ).execute()

    

    sheet_id = sheet["spreadsheetId"]
    sheet_url = sheet["spreadsheetUrl"]

    # -------- Add Header Row --------
    headers = [[
        "Brand Name",
        "Order Date",
        "Product Name",
        "Order ID",
        "Profile Name",
        "Order Amount",
        "Order SS",
        "Delivered SS",
        "Review SS",
        "Review Link",
        "Status"
    ]]

    body = {
        "values": headers
    }

    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="A1",
        valueInputOption="RAW",
        body=body
    ).execute()

    # -------- Share Sheet --------
    permission = {
        "type": "user",
        "role": "writer",
        "emailAddress": "hd-839@last-488313.iam.gserviceaccount.com"   # 👈 Change this
    }

    drive_service.permissions().create(
        fileId=sheet_id,
        body=permission
    ).execute()

    
# -------- Format Header Like Screenshot --------

    requests = [

        # Header Style
        {
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 1,
                            "green": 0.8,
                            "blue": 0.2
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "fontSize": 18,
                            "bold": True,
                            "foregroundColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0
                            }
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        },

        # Freeze Header Row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": 0,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        },

        # Set Row Height Bigger
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 45
                },
                "fields": "pixelSize"
            }
        }
    ]

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": requests}
    ).execute()

    Pmsg=f"Added :- {Brand}"
    conn = db()
    cur=conn.cursor()
    cur.execute("INSERT INTO ShopKaro_Sellers (Seller) VALUES (%s)",(Brand,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(f'/Mediator_Portal/Dashboard?Pmsg={Pmsg}')


@app.route("/Brands")
def Brands():

    MUN = session.get('Med Username')
    MN = session.get('Med name')
    MNUM = session.get('Med num')

    brands = []

    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT Seller FROM ShopKaro_Sellers")
    db_brands = cursor.fetchall()
    cursor.close()
    conn.close()

    for b in db_brands:
        brandSheet = client.open(b[0]).sheet1
        url=brandSheet.url
        data = brandSheet.get_all_values()
        row = data[1:]
        brands.append((b[0], len(row),url))

    return render_template("Brands.html", MUN=MUN, MN=MN, MNUM=MNUM, brands=brands)
   

@app.route("/delete-brand/<brand>")
def delete_brand(brand):

    username = session.get("Med Username")

    if not username:
        return redirect("/")

    creds = get_mediator_creds(username)
    creds = refresh_if_needed(creds, username)

    drive_service = build("drive", "v3", credentials=creds)

    try:
        spreadsheet = client.open(brand)
        sheet_id = spreadsheet.id

        # 🔥 Delete using mediator (Owner)
        drive_service.files().delete(fileId=sheet_id).execute()

    except Exception as e:
        print("Delete Error:", e)

    # 🔹 Remove brand from MySQL
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ShopKaro_Sellers WHERE Seller=%s", (brand,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/Mediator_Portal/Dashboard")


def safe_append(sheet, data_dict):
    headers = sheet.row_values(1)  # First row = header
    row = []
    for header in headers:
        row.append(data_dict.get(header, ""))  # Missing column = blank
    sheet.append_row(row)
@app.route("/orderform", methods=["GET", "POST"])
def orderform():
    name = session.get('Cust name')
    num = session.get('Cust num')
    passw = session.get('Cust passw')
    email = session.get('Cust email')
    upi = session.get("Cust upi")
    if request.method == "POST":

        brand = request.form.get("brand")
        order_id = request.form.get("order_id").replace(" ", "")
        date_input = request.form.get("order_date")
        order_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%d-%m-%Y")
        reviewer_name = request.form.get("reviewer_name")
        Product_name = request.form.get("PN")
        Oamount = int(request.form.get("amount"))
        Ramount = int(request.form.get("refund_amount"))
        upi = request.form.get("upi")

        OSheet = client.open("ShopKaro").sheet1
        BrandSheet = client.open(brand).sheet1

        now = datetime.now().replace(microsecond=0)

        url = ""   # 🔥 important fix (avoid undefined error)

        Order_SS = request.files.get("screenshot")
        if Order_SS:
            result = cloudinary.uploader.upload(Order_SS)
            url = result['secure_url']

        # 🔥 Header-based mapping
        data = {
            "TimeStamp": str(now),
            "Brand Name": brand,
            "Profile Name": reviewer_name,
            "Order Date": order_date,
            "Product Name": Product_name,
            "Order SS": url,
            "Order Amount": Oamount,
            "Order ID": order_id,
            "Email": email,
            "Whatsapp": int(num),
            "Status": "Pending",
            "UPI ID": upi,
            "Refund Amount": Ramount,
            "Mediator name": 'ShopKaro'
        }

        safe_append(OSheet, data)
        safe_append(BrandSheet, data)

        return render_template("order_success.html")

    # -------- GET REQUEST PART --------
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT Seller FROM ShopKaro_Sellers")
    brands = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "Customer_Order_Form.html",
        upi = upi,
        name=name,
        num=num,
        passw=passw,
        email=email,
        brands=brands
    )


@app.route("/refundform", methods=["GET", "POST"])
def refundform():
    msg=""
    id = request.args.get("id")
    DC = request.args.get("DealCode")
    RN = request.args.get("ProfileName")
    name=session.get('Cust name')
    num=session.get('Cust num')
    passw=session.get('Cust passw')
    email=session.get('Cust email')
    if request.method == "POST":
        
        
        OrderSheet = client.open("ShopKaro").sheet1
        
        if DC :
            deal_code=DC
        else:
            deal_code   = request.form.get("deal_code")
        
        if id :
            order_id=id.replace(" ","")
        else:
            order_id       = request.form.get("order_id_p").replace(" ","")

        
        reviewer_name  = request.form.get("reviewer_name")
        link           = request.form.get("link")

        all_values = OrderSheet.get_all_values()
        headers = all_values[0]
        data_rows = all_values[1:]
        order_id_index = headers.index("Order ID")
        order_mobile_index = headers.index("Whatsapp")
        status_col   = headers.index("Status")
        Dss_col      = headers.index("Delivered SS")
        Rss_col      = headers.index("Review SS")
        RL_col       = headers.index("Review Link")


        flag = 0
        for row in data_rows:
            if row[order_id_index] == order_id and row[order_mobile_index]==num:
                flag=1
                break
            
        if flag == 0:
            msg="Invalid Order-ID"
            if id != 'undefined' :
                return render_template("Customer_Refund_Form.html",RN=RN,DC=DC,msg=msg,id=id, name=name, num=num, passw=passw, email=email)
            else :
                return render_template("Customer_Refund_Form.html",RN=RN,DC=DC,msg=msg, name=name, num=num, passw=passw, email=email)

        else:
            Review_SS = request.files.get("Review-screenshot")
            if Review_SS:
                result = cloudinary.uploader.upload(Review_SS)
                Review_url = result['secure_url']

            D_SS = request.files.get("D-screenshot")
            if D_SS:
                result = cloudinary.uploader.upload(D_SS)
                D_url = result['secure_url']


            for i, row in enumerate(data_rows, start=2):
                if row[order_id_index] == order_id:
                    OrderSheet.update_cell(i, status_col + 1, "Done")
                    OrderSheet.update_cell(i, Dss_col + 1, D_url)
                    OrderSheet.update_cell(i, Rss_col + 1, Review_url)
                    OrderSheet.update_cell(i, RL_col + 1, link)
                    break

            
            BrandSheet= client.open(deal_code).sheet1
            Call_values = BrandSheet.get_all_values()
            Cheaders = Call_values[0]
            Cdata_rows = Call_values[1:]
            Corder_id_index = Cheaders.index("Order ID")
            Cstatus_col   = Cheaders.index("Status")
            CDss_col      = Cheaders.index("Delivered SS")
            CRss_col      = Cheaders.index("Review SS")
            CRL_col       = Cheaders.index("Review Link")
            for i, row in enumerate(Cdata_rows, start=2):
                if row[Corder_id_index] == order_id:
                    BrandSheet.update_cell(i, Cstatus_col + 1, "Done")
                    BrandSheet.update_cell(i, CDss_col + 1, D_url)
                    BrandSheet.update_cell(i, CRss_col + 1, Review_url)
                    BrandSheet.update_cell(i, CRL_col + 1, link)
                    break

            return render_template("order_success.html")
    
    if id != 'undefined' :
        return render_template("Customer_Refund_Form.html",RN=RN,DC=DC,id=id,msg=msg, name=name, num=num, passw=passw, email=email)
    else :
        return render_template("Customer_Refund_Form.html",RN=RN,DC=DC, name=name,msg=msg, num=num, passw=passw, email=email)

@app.route("/open-sheet/<Name>")
def open_sheet(Name):

    spreadsheet = client.open(Name)   # existing sheet open
    sheet_url = spreadsheet.url        # get link

    return redirect(sheet_url)



# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)







