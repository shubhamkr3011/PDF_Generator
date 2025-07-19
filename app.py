# app.py

import streamlit as st
import pandas as pd
from supabase import create_client
from fpdf import FPDF
from groq import Groq
import io
import qrcode
import barcode
from barcode.writer import ImageWriter
import datetime
import uuid
import random

# --- PAGE CONFIGURATION & CONNECTIONS ---
st.set_page_config(page_title="Travel Document Generator", layout="wide")

@st.cache_resource
def init_supabase_connection(): return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
@st.cache_resource
def init_groq_client(): return Groq(api_key=st.secrets["groq"]["api_key"])

supabase = init_supabase_connection()
llm_client = init_groq_client()

# --- HELPER & PDF FUNCTIONS ---
def upload_and_get_url(file_bytes, bucket_name, file_path):
    try:
        supabase.storage.from_(bucket_name).upload(file=file_bytes, path=file_path, file_options={"content-type": "application/pdf"})
        return supabase.storage.from_(bucket_name).get_public_url(file_path)
    except Exception as e:
        if "Duplicate" in str(e):
            st.warning(f"File {file_path} already exists. Reusing.")
            return supabase.storage.from_(bucket_name).get_public_url(file_path)
        else:
            st.error(f"Upload Error for {file_path}: {e}"); return None

class PDF(FPDF):
    def header(self):
        if hasattr(self, 'title_text'): self.set_font('Arial', 'B', 14); self.cell(0, 10, self.title_text, 0, 1, 'C'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_flight_ticket_pdf(data):
    """Generates a highly detailed, realistic dummy flight ticket PDF."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', '', 12)
    pdf.add_page()
    main_passenger = data.get('passenger_name', 'N/A')
    all_passengers = [main_passenger] + [p['name'] for p in data.get('family_members', [])]
    trip_id = data.get('uuid', str(uuid.uuid4())).split('-')[0].upper()
    sorted_trips = sorted(data.get('trips', []), key=lambda x: x['arrival_date'])
    
    def draw_line_separator(pdf_obj):
        pdf_obj.ln(4); pdf_obj.set_draw_color(220, 220, 220)
        pdf_obj.cell(0, 0, '', 'T', 1); pdf_obj.ln(4)

    pdf.set_font('Arial', 'B', 18); pdf.cell(40, 10, 'ticket', 0, 0, 'L')
    pdf.set_font('Arial', '', 12); pdf.cell(0, 10, f"Trip ID : {trip_id}", 0, 1, 'L')
    
    if sorted_trips:
        origin_city, dest_city = "Home", sorted_trips[-1]['country']
        start_date_obj = datetime.datetime.strptime(sorted_trips[0]['arrival_date'], '%Y-%m-%d')
        date_str = start_date_obj.strftime('%a, %d %b %Y')
        pdf.set_font('Arial', 'B', 16); pdf.cell(0, 10, f"{origin_city} to {dest_city}", 0, 1, 'L')
        pdf.set_font('Arial', '', 10); pdf.cell(0, 5, date_str, 0, 1, 'L')
    draw_line_separator(pdf)

    for i, trip in enumerate(sorted_trips):
        start_date_obj = datetime.datetime.strptime(trip['arrival_date'], '%Y-%m-%d')
        date_str = start_date_obj.strftime('%a, %d %b %Y')
        pdf.set_font('Arial', 'B', 12); pdf.cell(40, 8, "Streamlit Air", 0, 0, 'L')
        pdf.set_font('Arial', '', 10); pdf.cell(0, 8, f"Flight ST-{random.randint(4000, 6000)} | Fare type: Saver", 0, 1, 'L')
        y_before_times = pdf.get_y()
        pdf.set_font('Arial', 'B', 16); pdf.cell(50, 8, f"{random.randint(6,9):02d}:{random.randint(0,59):02d}", 0, 0, 'L')
        pdf.set_font('Arial', '', 10); pdf.cell(20, 8, f"{random.randint(1,3)}h {random.randint(0,59)}m", 0, 0, 'C')
        pdf.set_font('Arial', 'B', 16); pdf.cell(50, 8, f"{random.randint(10,14):02d}:{random.randint(0,59):02d}", 0, 1, 'L')
        pdf.set_y(y_before_times + 6); pdf.set_font('Arial', '', 10)
        origin = "Home City (XXX)" if i == 0 else f"{sorted_trips[i-1]['country']}"
        pdf.cell(50, 8, f"{origin}", 0, 0, 'L'); pdf.cell(20, 8, "", 0, 0, 'C'); pdf.cell(50, 8, f"{trip['country']}", 0, 1, 'L')
        pdf.ln(2); seats = ", ".join([f"{random.randint(10,40)}{random.choice('ABCDEF')}" for _ in all_passengers])
        pdf.multi_cell(0, 5, f"Baggage (per Adult/Child) - Check-in: 15kg(1 piece), Cabin: 7kg\nSeats - {seats}", 0, 'L')
        if i < len(sorted_trips) - 1: draw_line_separator(pdf)

    draw_line_separator(pdf); pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240, 240, 240)
    pdf.cell(140, 8, "TRAVELLERS", 1, 0, 'L', fill=True); pdf.cell(50, 8, "TICKET NO.", 1, 1, 'C', fill=True)

    for i, name in enumerate(all_passengers):
        ticket_no = f"ST{random.randint(1000,9999)}{chr(65+i)}"
        code128 = barcode.get_barcode_class('code128'); barcode_obj = code128(ticket_no, writer=ImageWriter())
        buffer = io.BytesIO(); barcode_obj.write(buffer); buffer.seek(0)
        y_before = pdf.get_y(); pdf.set_font('Arial', '', 11)
        pdf.cell(80, 12, f"  {name}", 'L', 0, 'L'); pdf.cell(60, 12, "", 'B', 0, 'C'); pdf.cell(50, 12, ticket_no, 'R', 1, 'C')
        pdf.image(buffer, x=pdf.get_x() + 80, y=y_before + 2, h=8)
    pdf.cell(0, 0, '', 'T', 1)
    
    draw_line_separator(pdf); pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "ABOUT THIS TRIP", 0, 1, 'L')
    pdf.set_font('Arial', '', 9); pdf.multi_cell(0, 5, "Please carry photo identification for check-in.\n This is a dummy document for visa and demonstration purposes only.", 0, 'L')
    
    draw_line_separator(pdf); pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "FARE BREAKUP", 0, 1, 'L'); pdf.set_font('Arial', '', 10)
    base_fare = random.randint(1000, 2000) * len(all_passengers); taxes = base_fare * 0.18; total = base_fare + taxes
    pdf.cell(120, 6, "Base Fare:", 0, 0, 'L'); pdf.cell(0, 6, f"Rs. {base_fare:,.2f}", 0, 1, 'R')
    pdf.cell(120, 6, "Taxes and Surcharges:", 0, 0, 'L'); pdf.cell(0, 6, f"Rs. {taxes:,.2f}", 0, 1, 'R')
    pdf.set_font('Arial', 'B', 10); pdf.cell(120, 8, "Total Fare:", 'T', 0, 'L'); pdf.cell(0, 8, f"Rs. {total:,.2f}", 'T', 1, 'R')

    draw_line_separator(pdf); pdf.set_font('Arial', '', 10); pdf.cell(0, 8, "Manage bookings online at support.streamlit.app | Helpline: +01 234 567 890", 0, 1, 'C')
    
    return pdf.output(dest='S')

def create_hotel_booking_pdf(data):
    pdf = PDF(); pdf.set_font('Arial', '', 12); pdf.title_text = 'Dummy Hotel Confirmation'; pdf.add_page(); all_guests = [data['passenger_name']] + [p['name'] for p in data.get('family_members', [])]
    pdf.cell(0, 10, f"Primary Guest: {data['passenger_name']}", 0, 1); pdf.cell(0, 10, f"Additional Guests: {len(all_guests) - 1}", 0, 1)
    if data.get('trips'):
        sorted_trips = sorted(data['trips'], key=lambda x: x['arrival_date']); pdf.cell(0, 10, f"Check-in: {sorted_trips[0]['arrival_date']}", 0, 1); pdf.cell(0, 10, f"Check-out: {sorted_trips[-1]['departure_date']}", 0, 1)
    return pdf.output(dest='S')

# This is the new function. You will use it to replace the old create_itinerary_pdf.
# This is the corrected function. Replace the old one with this.

def create_itinerary_pdf(data):
    """Generates a highly detailed, Emirates-style dummy itinerary PDF."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_font('Arial', '', 12)
    pdf.add_page()

    # --- Data Preparation ---
    main_passenger = data.get('passenger_name', 'N/A').upper()
    pnr = data.get('pnr_value', 'N/A').upper() or f"ST{random.randint(1000,9999)}"
    sorted_trips = sorted(data.get('trips', []), key=lambda x: x['arrival_date'])
    AIRPORT_CODES = {'France': 'CDG', 'Germany': 'FRA', 'Italy': 'FCO', 'Spain': 'MAD', 'USA': 'JFK', 'Dubai': 'DXB'}

    def draw_line_separator(pdf_obj):
        pdf_obj.ln(2)
        pdf_obj.set_draw_color(180, 180, 180)
        pdf_obj.cell(0, 0, '', 'T', 1)
        pdf_obj.ln(2)

    # --- 1. Top Header ---
    if sorted_trips:
        start_date_obj = datetime.datetime.strptime(sorted_trips[0]['arrival_date'], '%Y-%m-%d')
        end_date_obj = datetime.datetime.strptime(sorted_trips[-1]['departure_date'], '%Y-%m-%d')
        start_str = start_date_obj.strftime('%d %b %Y').upper()
        end_str = end_date_obj.strftime('%d %b %Y').upper()
        dest_str = sorted_trips[-1]['country'].upper()

        pdf.set_font('Arial', 'B', 11)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(80, 7, f"{start_str}   {end_str}", 1, 0, 'C', fill=True)
        pdf.cell(0, 7, f"TRIP TO {dest_str}", 1, 1, 'C', fill=True)
    pdf.ln(5)

    # --- 2. Prepared For & Reservation Codes ---
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, "PREPARED FOR", 0, 1, 'L')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 6, main_passenger, 0, 1, 'L')
    pdf.ln(3)
    pdf.set_font('Arial', '', 9)
    pdf.cell(60, 5, "RESERVATION CODE", 0, 0, 'L')
    pdf.cell(60, 5, "AIRLINE RESERVATION CODE", 0, 1, 'L')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, pnr, 0, 0, 'L')
    pdf.cell(60, 6, f"ST{random.randint(10000,99999)} (ST)", 0, 1, 'L')
    draw_line_separator(pdf)

    # --- 3. Flight Legs Section ---
    for i, trip in enumerate(sorted_trips):
        start_date_obj = datetime.datetime.strptime(trip['arrival_date'], '%Y-%m-%d')
        
        # --- Leg Header ---
        pdf.set_font('Arial', 'B', 10)
        departure_day_str = start_date_obj.strftime('%A %d %b').upper()
        arrival_day_str = (start_date_obj + datetime.timedelta(days=1)).strftime('%A %d %b').upper()
        
        # === THE FIX IS HERE ===
        # Replaced the unsupported "▸" character with ">"
        pdf.cell(0, 7, f"> DEPARTURE: {departure_day_str}  >  ARRIVAL: {arrival_day_str}", 0, 1)

        pdf.set_font('Arial', '', 8)
        pdf.cell(0, 4, "Please verify flight times prior to departure", 0, 1)
        pdf.ln(2)

        # --- Leg Details Table ---
        y_before_leg = pdf.get_y()
        # Col 1: Airline & Flight Info
        pdf.set_font('Arial', 'B', 12); pdf.cell(45, 6, "Streamlit Air", 0, 1, 'L')
        pdf.set_font('Arial', 'B', 14); pdf.cell(45, 8, f"ST {random.randint(100, 999)}", 0, 1, 'L')
        pdf.set_y(pdf.get_y() + 5)
        pdf.set_font('Arial', '', 9)
        pdf.cell(45, 5, f"Duration:\n{random.randint(5,9)}hr(s) {random.randint(0,59)}min(s)", 0, 1, 'L')
        pdf.cell(45, 5, "Class: Economy", 0, 1, 'L')
        pdf.cell(45, 5, "Status: Confirmed", 0, 1, 'L')
        y_after_col1 = pdf.get_y()

        # Col 2: Main Route Details
        pdf.set_y(y_before_leg)
        pdf.set_x(55)
        origin_country = "Home City" if i == 0 else sorted_trips[i-1]['country']
        origin_code = "XXX" if i == 0 else AIRPORT_CODES.get(origin_country, 'YYY')
        dest_country = trip['country']
        dest_code = AIRPORT_CODES.get(dest_country, 'ZZZ')
        
        # === AND THE FIX IS HERE TOO ===
        pdf.set_font('Arial', 'B', 16); pdf.cell(50, 8, origin_code, 0, 0, 'L')
        pdf.cell(10, 8, '>', 0, 0, 'C') # Replaced the unsupported "▸" character
        pdf.cell(50, 8, dest_code, 0, 1, 'L')
        
        pdf.set_x(55); pdf.set_font('Arial', '', 9); pdf.cell(60, 5, origin_country, 0, 0, 'L'); pdf.cell(60, 5, dest_country, 0, 1, 'L')
        
        pdf.set_x(55); pdf.rect(pdf.get_x(), pdf.get_y()+2, 90, 18); pdf.ln(3)
        pdf.set_x(57); pdf.cell(45, 5, "Departing At:", 0, 0, 'L'); pdf.cell(45, 5, "Arriving At:", 0, 1, 'L')
        pdf.set_x(57); pdf.set_font('Arial', 'B', 10); pdf.cell(45, 5, f"{random.randint(20,23)}:{random.randint(0,59):02d}pm", 0, 0, 'L')
        pdf.cell(45, 5, f"{random.randint(4,7)}:{random.randint(0,59):02d}am", 0, 1, 'L')
        pdf.set_x(57); pdf.set_font('Arial', '', 9); pdf.cell(45, 5, f"({start_date_obj.strftime('%a, %d %b')})", 0, 0, 'L')
        pdf.cell(45, 5, f"({(start_date_obj + datetime.timedelta(days=1)).strftime('%a, %d %b')})", 0, 1, 'L')
        pdf.set_y(pdf.get_y() + 3)

        # Col 3: Aircraft Details
        pdf.set_y(y_before_leg)
        pdf.set_x(150)
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, "Aircraft:", 0, 1, 'L')
        pdf.set_x(150); pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, f"BOEING {random.choice(['777-300ER', '787-9', 'A350-900'])}", 0, 1, 'L')
        pdf.set_x(150); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, "Stop(s): 0", 0, 1, 'L')
        pdf.set_x(150); pdf.cell(0, 5, "Meals: Meals", 0, 1, 'L')
        
        # --- Passenger Bar for this leg ---
        pdf.set_y(max(y_after_col1, pdf.get_y()) + 5) 
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font('Arial', '', 9)
        pdf.cell(95, 7, f"Passenger Name:  » {main_passenger}", 'T', 0, 'L', fill=True)
        pdf.cell(95, 7, "Seats:  Check-In Required", 'T', 1, 'L', fill=True)
        draw_line_separator(pdf)

    return pdf.output(dest='S')

def generate_cover_letter_text(data):
    st.info("🤖 Generating a professional cover letter with AI...")
    today_date, full_name = datetime.date.today().strftime("%d/%m/%Y"), data.get('passenger_name', '[Your Full Name]')
    main_country, start_date_str, end_date_str = "your destination", "", ""
    if data.get('trips'):
        sorted_trips = sorted(data['trips'], key=lambda x: x['arrival_date']); main_country, start_date_str, end_date_str = sorted_trips[0]['country'], sorted_trips[0]['arrival_date'], sorted_trips[-1]['departure_date']
    job_title, company_name, joining_date, passport_no = data.get('job_title', '[Your Job Title]'), data.get('company_name', '[Company Name]'), data.get('joining_date', '[Joining Date]'), data.get('passport_number', '[XXXXXXXXX]')
    prompt = f"""Generate a visa cover letter *exactly* in the following format, filling placeholders with the provided data. Do not add any extra conversation.
    Data: Full Name: {full_name}, Main Destination: {main_country}, Start Date: {start_date_str}, End Date: {end_date_str}, Job: {job_title}, Company: {company_name}, Joining Date: {joining_date}, Passport: {passport_no}.
    --- TEMPLATE START ---
    Date: {today_date}\n\nTo,\nThe Visa Officer\nEmbassy of {main_country}\n[Embassy Address]\n[City, Country]\n\nSubject: Tourist Visa Application – {full_name}\n\nDear Sir/Madam,\n\nI am writing to submit my application for a short-term tourist visa to visit {main_country} from {start_date_str} to {end_date_str}.\n\nThis trip is purely for tourism purposes. I plan to explore major cities and cultural landmarks. My aim is to learn more about the country's history and culture, while taking a short break from my professional routine.\n\nI am currently working as a {job_title} with {company_name} and have been employed here since {joining_date}. My leave for this trip has been approved, and I am financially prepared to support all expenses. My travel insurance, flight bookings, and hotel reservations are included.\n\nI understand and will fully comply with all visa regulations. I have strong professional and personal ties to my home country and will be returning as scheduled.\n\nPlease find below the list of documents enclosed:\n\nCompleted visa application form\nPassport with required validity\nFlight and hotel bookings\nProof of travel insurance\nLeave approval from employer\nBank statements and ITRs\nDay-wise travel itinerary\nThis covering letter\n\nI hope you find everything in order and remain available for any further clarification.\n\nThank you for considering my request.\n\nSincerely,\n{full_name}\nPassport No.: {passport_no}
    --- TEMPLATE END ---"""
    chat_completion = llm_client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama3-8b-8192")
    return chat_completion.choices[0].message.content

def create_cover_letter_pdf(text):
    pdf = PDF(); pdf.set_font('Arial', '', 12); pdf.title_text = 'Visa Application Cover Letter'; pdf.add_page()
    safe_text = text.encode('latin-1', 'replace').decode('latin-1'); pdf.multi_cell(0, 7, safe_text)
    return pdf.output(dest='S')

# --- STREAMLIT APP UI & LOGIC ---
st.title("Travel Document Generator")
if 'family_members' not in st.session_state: st.session_state.family_members = []
if 'trips' not in st.session_state: st.session_state.trips = [{'country': 'France', 'arrival_date': datetime.date.today(), 'departure_date': datetime.date.today() + datetime.timedelta(days=7)}]
def add_trip(): st.session_state.trips.append({'country': '', 'arrival_date': datetime.date.today(), 'departure_date': datetime.date.today() + datetime.timedelta(days=7)})
def remove_trip(i): st.session_state.trips.pop(i)
def add_family(): st.session_state.family_members.append({'name': '', 'age': 0})
def remove_family(i): st.session_state.family_members.pop(i)
with st.expander("Manage Trips & Guests", expanded=True):
    st.subheader("Travel Plan"); st.button("Add Trip", on_click=add_trip)
    for i, trip in enumerate(st.session_state.trips):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1]); st.session_state.trips[i]['country'] = c1.text_input("Country/City", trip.get('country', ''), key=f"country_{i}")
        st.session_state.trips[i]['arrival_date'] = c2.date_input("Arrival Date", trip.get('arrival_date'), key=f"arr_{i}"); st.session_state.trips[i]['departure_date'] = c3.date_input("Departure Date", trip.get('departure_date'), key=f"dep_{i}")
        c4.button("❌", key=f"rem_trip_{i}", on_click=remove_trip, args=(i,), help="Remove trip")
    st.subheader("Accompanying Guests"); st.button("Add Guest", on_click=add_family)
    for i, member in enumerate(st.session_state.family_members):
        c1, c2, c3 = st.columns([4, 1, 1]); st.session_state.family_members[i]['name'] = c1.text_input(f"Guest {i+1}", member.get('name', ''), key=f"fam_name_{i}")
        st.session_state.family_members[i]['age'] = c2.number_input("Age", 0, 120, member.get('age', 0), key=f"fam_age_{i}"); c3.button("❌", key=f"rem_fam_{i}", on_click=remove_family, args=(i,), help="Remove guest")
st.markdown("---")
with st.form("travel_form"):
    st.header("Applicant Information"); c1, c2, c3 = st.columns(3); passenger_name = c1.text_input("Full Name*", placeholder="John Doe"); age = c2.number_input("Age*", min_value=1, step=1); gender = c3.selectbox("Gender", ["Male", "Female", "Other"])
    st.subheader("Employment & Passport Details (for Cover Letter)"); c1, c2 = st.columns(2); job_title = c1.text_input("Job Title"); company_name = c2.text_input("Company Name")
    c1, c2 = st.columns(2); joining_date = c1.date_input("Joining Date", datetime.date(2020, 1, 1)); passport_number = c2.text_input("Passport Number")
    pnr_value = st.text_input("Main Flight PNR (Optional)", placeholder="ABCXYZ")
    st.header("Select Documents to Generate"); c1, c2, c3, c4 = st.columns(4); wants_flight = c1.checkbox("Flight Ticket", True); wants_hotel = c2.checkbox("Hotel Booking", True); wants_itinerary = c3.checkbox("Itinerary", True); wants_cover = c4.checkbox("Cover Letter (AI)", True)
    submitted = st.form_submit_button("Generate & Store Documents", type="primary")
if submitted:
    if not passenger_name or not age: st.error("Please fill in the applicant's Name and Age.")
    elif not any(t.get('country') for t in st.session_state.trips): st.error("Please add at least one trip with a country name.")
    else:
        record_uuid = str(uuid.uuid4()); trips_data = [{"country": t['country'], "arrival_date": str(t['arrival_date']), "departure_date": str(t['departure_date'])} for t in st.session_state.trips if t.get('country')]
        family_data = [m for m in st.session_state.family_members if m.get('name')]; form_data = {"uuid": record_uuid, "passenger_name": passenger_name, "age": age, "gender": gender, "pnr_value": pnr_value, "trips": trips_data, "family_members": family_data, "job_title": job_title, "company_name": company_name, "joining_date": str(joining_date), "passport_number": passport_number}
        document_urls = {};
        with st.spinner("Generating and uploading documents..."):
            if wants_flight:
                pdf_data = create_flight_ticket_pdf(form_data); url = upload_and_get_url(bytes(pdf_data), "travel-documents", f"{record_uuid}/flight.pdf");
                if url: document_urls['flight_ticket_url'] = url
            if wants_hotel:
                pdf_data = create_hotel_booking_pdf(form_data); url = upload_and_get_url(bytes(pdf_data), "travel-documents", f"{record_uuid}/hotel.pdf");
                if url: document_urls['hotel_booking_url'] = url
            if wants_itinerary:
                pdf_data = create_itinerary_pdf(form_data); url = upload_and_get_url(bytes(pdf_data), "travel-documents", f"{record_uuid}/itinerary.pdf");
                if url: document_urls['itinerary_url'] = url
            if wants_cover:
                text = generate_cover_letter_text(form_data); pdf_data = create_cover_letter_pdf(text); url = upload_and_get_url(bytes(pdf_data), "travel-documents", f"{record_uuid}/cover_letter.pdf");
                if url: document_urls['cover_letter_url'] = url
        if document_urls:
            st.success("✅ Documents generated and uploaded!"); db_record = {**form_data, **document_urls}
            try:
                supabase.table("travel_records").insert(db_record).execute()
                st.subheader("Your Permanent Document Links:")
                for name, url in document_urls.items(): st.markdown(f"📄 **{name.replace('_', ' ').title()}:** [Download Here]({url})")
            except Exception as e: st.error(f"Database error: {e}")
        else: st.warning("No documents were selected or generated.")
st.markdown("---"); st.header("Previously Generated Records")
try:
    response = supabase.table("travel_records").select("*").order("created_at", desc=True).limit(10).execute()
    if response.data:
        df = pd.DataFrame(response.data)
        def format_trips(trip_list):
            if not isinstance(trip_list, list) or not trip_list: return "N/A"
            return ", ".join([f"{t.get('country', 'N/A')}" for t in trip_list])
        df['trips'] = df['trips'].apply(format_trips)
        url_cols = {col: st.column_config.LinkColumn(display_text="🔗 Link") for col in df.columns if col.endswith('_url')}
        st.data_editor(df, column_config=url_cols, use_container_width=True, hide_index=True, disabled=True,
                       column_order=("created_at", "passenger_name", "trips", "flight_ticket_url", "hotel_booking_url", "itinerary_url", "cover_letter_url"))
    else: st.info("No records found yet.")
except Exception as e: st.error(f"Could not fetch past records: {e}")