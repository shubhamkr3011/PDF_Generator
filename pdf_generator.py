from fpdf import FPDF
import datetime
import uuid
import random
import io
import barcode
from barcode.writer import ImageWriter

# --- BASE PDF CLASS ---

class PDF(FPDF):
    """Custom PDF class to handle headers and footers."""
    def header(self):
        if hasattr(self, 'title_text'):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, self.title_text, 0, 1, 'C')
            self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- PDF CREATION FUNCTIONS ---

def create_flight_ticket_pdf(data: dict) -> bytes:
    """Generates a flight ticket PDF using manually entered data."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', '', 12)
    pdf.add_page()

    # --- Data Setup ---
    main_passenger = data.get('passenger_name', 'N/A')
    hometown = data.get('hometown', 'Home City')
    all_passengers = [main_passenger] + [p['name'] for p in data.get('family_members', [])]
    trip_id = data.get('uuid', str(uuid.uuid4())).split('-')[0].upper()
    
    # Use the full trip data directly
    sorted_trips = sorted(data.get('trips', []), key=lambda x: x['arrival_date'])
    
    manual_cost_per_person = data.get('flight_cost', 0.0)

    def draw_line_separator(pdf_obj):
        pdf_obj.ln(4); pdf_obj.set_draw_color(220, 220, 220)
        pdf_obj.cell(0, 0, '', 'T', 1); pdf_obj.ln(4)

    # --- Header ---
    primary_airline = sorted_trips[0].get('airline', 'Travaky Airlines') if sorted_trips else 'Travaky Airlines'
    pdf.set_font('Arial', 'B', 18); pdf.cell(0, 10, f'{primary_airline} -Ticket Confirmation', 0, 1, 'L')
    pdf.set_font('Arial', '', 12); pdf.cell(0, 10, f"Trip ID: {trip_id}", 0, 1, 'L')
    
    if sorted_trips:
        origin_city, dest_city = hometown, sorted_trips[-1]['country']
        first_pnr = sorted_trips[0].get('pnr', 'N/A')
        start_date_obj = sorted_trips[0]['arrival_date']
        date_str = start_date_obj.strftime('%a, %d %b %Y')
        pdf.set_font('Arial', 'B', 16); pdf.cell(0, 10, f"{origin_city} to {dest_city}", 0, 1, 'L')
        pdf.set_font('Arial', '', 10); pdf.cell(0, 5, f"Primary PNR: {first_pnr}", 0, 1, 'L')
    draw_line_separator(pdf)

    # --- Flight Legs using Manual Data ---
    for i, trip in enumerate(sorted_trips):
        start_date_obj = trip['arrival_date']
        airline_name = trip.get('airline', 'Travaky Airlines')
        
        pdf.set_font('Arial', 'B', 12); pdf.cell(80, 8, airline_name, 0, 0, 'L')
        pdf.set_font('Arial', 'B', 10); pdf.cell(0, 8, f"PNR: {trip.get('pnr', 'N/A')}", 0, 1, 'R')
        
        pdf.set_font('Arial', '', 10); pdf.cell(0, 6, f"Flight {trip.get('flight_no', 'N/A')} | Fare type: Saver", 0, 1, 'L')
        y_before_times = pdf.get_y()
        
        pdf.set_font('Arial', 'B', 16); pdf.cell(50, 8, trip.get('dep_time', 'N/A'), 0, 0, 'L')
        pdf.cell(20, 8, "-->", 0, 0, 'C')
        pdf.set_font('Arial', 'B', 16); pdf.cell(50, 8, trip.get('arr_time', 'N/A'), 0, 1, 'L')
        
        pdf.set_y(y_before_times + 6); pdf.set_font('Arial', '', 10)
        origin = hometown if i == 0 else sorted_trips[i-1]['country']
        pdf.cell(50, 8, origin, 0, 0, 'L'); pdf.cell(20, 8, "", 0, 0, 'C'); pdf.cell(50, 8, trip['country'], 0, 1, 'L')
        
        pdf.ln(2); seats = ", ".join([f"{random.randint(10,40)}{random.choice('ABCDEF')}" for _ in all_passengers])
        pdf.multi_cell(0, 5, f"Date: {start_date_obj.strftime('%a, %d %b %Y')}\nSeats - {seats}", 0, 'L')
        if i < len(sorted_trips) - 1: draw_line_separator(pdf)

    # --- Travellers List using Manual E-Ticket ---
    draw_line_separator(pdf); pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240, 240, 240)
    pdf.cell(140, 8, "TRAVELLERS", 1, 0, 'L', fill=True); pdf.cell(50, 8, "E-TICKET NO.", 1, 1, 'C', fill=True)

    for i, name in enumerate(all_passengers):
        ticket_no = sorted_trips[0].get('ticket_no', 'N/A') if sorted_trips else 'N/A'
        
        code128 = barcode.get_barcode_class('code128'); barcode_obj = code128(ticket_no, writer=ImageWriter())
        buffer = io.BytesIO(); barcode_obj.write(buffer); buffer.seek(0)
        y_before = pdf.get_y(); pdf.set_font('Arial', '', 11)
        pdf.cell(80, 12, f"  {name.upper()}", 'L', 0, 'L'); pdf.cell(60, 12, "", 'B', 0, 'C'); pdf.cell(50, 12, ticket_no, 'R', 1, 'C')
        pdf.image(buffer, x=pdf.get_x() + 80, y=y_before + 2, h=8)
    pdf.cell(0, 0, '', 'T', 1)
    
    # --- Fare Breakup using Manual Cost ---
    draw_line_separator(pdf); pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "FARE BREAKUP", 0, 1, 'L'); pdf.set_font('Arial', '', 10)
    base_fare = manual_cost_per_person * len(all_passengers)
    taxes = base_fare * 0.18
    total = base_fare + taxes
    pdf.cell(120, 6, "Base Fare:", 0, 0, 'L'); pdf.cell(0, 6, f"$ {base_fare:,.2f}", 0, 1, 'R')
    pdf.cell(120, 6, "Taxes and Surcharges:", 0, 0, 'L'); pdf.cell(0, 6, f"$ {taxes:,.2f}", 0, 1, 'R')
    pdf.set_font('Arial', 'B', 10); pdf.cell(120, 8, "Total Fare (USD):", 'T', 0, 'L'); pdf.cell(0, 8, f"$ {total:,.2f}", 'T', 1, 'R')

    # --- Important Information ---
    draw_line_separator(pdf); pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, "IMPORTANT INFORMATION", 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    
    rules_text = (
        "- All timings are local to the respective airport. Please verify flight times with the airline 24 hours prior to departure.\n"
        "- Check-in counters close 60 minutes before departure for international flights and 45 minutes for domestic flights. Please report early to allow sufficient time for security screening.\n"
        "- A valid, government-issued photo ID is mandatory for all passengers, including infants, at check-in.\n"
        "- For international travel, ensure your passport has at least 6 months of validity from your date of travel and that you possess any required visas or transit documents for your destination and layovers.\n"
        "- Cabin baggage is limited to 1 piece weighing up to 8kg, with dimensions not exceeding 55x35x25 cm. One personal item, such as a laptop bag or handbag, is also permitted.\n"
        "- The standard checked baggage allowance is 1 piece weighing up to 23kg. Any single bag weighing over 32kg will not be accepted.\n"
        "- Excess baggage will be chargeable at prevailing airport rates. Contact Travaky Airlines for details on pre-purchasing extra baggage allowance.\n"
        "- This e-ticket is non-transferable. Any changes to your travel date or routing are subject to airline rules, may incur fees, and will require payment of any fare difference.\n"
        "- Carriage of dangerous goods like explosives, compressed gases, flammable items, corrosives, or radioactive materials is strictly prohibited in either checked or cabin baggage.\n"
        "- Travaky Airlines is not liable for any loss or damage to fragile, valuable, or perishable items (e.g., jewelry, electronics, cash, important documents) included in your checked baggage.\n"
        "- In case of flight cancellation or a major delay, you will be re-booked on the next available flight as per our Conditions of Carriage. Please contact our ground staff for assistance.\n"
        "- This booking is governed by Travaky Airlines' Conditions of Carriage, which are available on our website."
    )
    
    rules_list = rules_text.split('\n')
    pdf.ln(1)
    for rule in rules_list:
        text_to_display = rule.strip().lstrip('-').strip()
        if not text_to_display:
            continue
        pdf.cell(4, 4, '-', 0, 0, 'C')
        text_width = pdf.w - pdf.l_margin - pdf.r_margin - 4
        pdf.multi_cell(text_width, 4, text_to_display, 0, 'L')
        pdf.set_y(pdf.get_y() + 1)
        
    draw_line_separator(pdf); pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, "Manage your booking online at support.travaky.com | Helpline: +1-800-TRAVAKY", 0, 1, 'C')
    
    return bytes(pdf.output(dest='S'))

def create_hotel_booking_pdf(data: dict) -> bytes:
    """Generates a hotel booking confirmation PDF for one or more hotel stays."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.title_text = "Hotel Booking Confirmation"
    main_passenger, num_guests, trip_id = data.get('passenger_name', 'N/A'), len([data.get('passenger_name')] + [p['name'] for p in data.get('family_members', [])]), data.get('uuid', str(uuid.uuid4())).split('-')[0].upper()
    selected_stays = data.get('selected_hotels_per_trip', [])

    def draw_line_separator(pdf_obj, margin_top=4, margin_bottom=4):
        pdf_obj.ln(margin_top); pdf_obj.set_draw_color(220, 220, 220); pdf_obj.cell(0, 0, '', 'T', 1); pdf_obj.ln(margin_bottom)

    if not selected_stays:
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "No hotel stay was selected for this itinerary.", 0, 1, 'C'); return bytes(pdf.output(dest='S'))

    pdf.set_font('Arial', 'B', 16); pdf.cell(0, 10, f"Your {len(selected_stays)} Booking(s) are Confirmed!", 0, 1, 'C')
    pdf.set_font('Arial', '', 10); pdf.cell(0, 5, f"Booking Itinerary ID: {trip_id}-HTL", 0, 1, 'C'); pdf.ln(5)

    for i, stay in enumerate(selected_stays):
        hotel, trip = stay['hotel_data'], stay['trip_data']
        check_in_obj, check_out_obj = trip['arrival_date'], trip['departure_date']
        num_nights = (check_out_obj - check_in_obj).days if (check_out_obj - check_in_obj).days > 0 else 1
        draw_line_separator(pdf)
        pdf.set_font('Arial', 'B', 14); pdf.cell(0, 8, f"Stay {i+1}: {hotel['Hotel Name']}", 0, 1, 'L')
        pdf.set_font('Arial', '', 11); pdf.cell(0, 6, f"{hotel['City']}, {hotel['Country']}", 0, 1, 'L'); pdf.ln(3)
        col_width = pdf.w / 2 - pdf.l_margin - 5
        pdf.set_font('Arial', 'B', 11); pdf.cell(col_width, 7, "Check-in", 0, 0, 'L'); pdf.cell(col_width, 7, "Check-out", 0, 1, 'L')
        pdf.set_font('Arial', '', 11); pdf.cell(col_width, 7, check_in_obj.strftime('%a, %d %b %Y'), 0, 0, 'L'); pdf.cell(col_width, 7, check_out_obj.strftime('%a, %d %b %Y'), 0, 1, 'L')
        pdf.set_font('Arial', 'B', 11); pdf.cell(col_width, 7, "Total Nights", 0, 0, 'L'); pdf.cell(col_width, 7, "Guests", 0, 1, 'L')
        pdf.set_font('Arial', '', 11); pdf.cell(col_width, 7, str(num_nights), 0, 0, 'L'); pdf.cell(col_width, 7, str(num_guests), 0, 1, 'L'); pdf.ln(5)
        nightly_rate = float(hotel.get('Rate', 0)); total_cost = nightly_rate * num_nights * num_guests
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 8, "Price Summary for this Stay", 0, 1, 'L')
        pdf.set_font('Arial', '', 11); pdf.cell(130, 7, "Nightly Rate (per guest)", 0, 0, 'L'); pdf.cell(0, 7, f"EUR {nightly_rate:,.2f}", 0, 1, 'R')
        pdf.cell(130, 8, "Total Stay Cost", 'T', 0, 'L'); pdf.cell(0, 8, f"EUR {total_cost:,.2f}", 'T', 1, 'R'); pdf.ln(5)

    pdf.set_y(-30); pdf.set_font('Arial', 'I', 9); pdf.multi_cell(0, 5, "This is a dummy document generated for demonstration purposes. Manage your booking at support.streamlit.app.", 0, 'C')
    return bytes(pdf.output(dest='S'))

def create_itinerary_pdf(data: dict) -> bytes:
    """Generates an itinerary PDF using manually entered data."""
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_font('Arial', '', 12)
    pdf.add_page()
    main_passenger, hometown = data.get('passenger_name', 'N/A').upper(), data.get('hometown', 'Home City')
    sorted_trips = sorted(data.get('trips', []), key=lambda x: x['arrival_date'])
    AIRPORT_CODES = {'France': 'CDG', 'Germany': 'FRA', 'Italy': 'FCO', 'Spain': 'MAD', 'USA': 'JFK', 'Dubai': 'DXB'}

    def draw_line_separator(pdf_obj):
        pdf_obj.ln(2); pdf_obj.set_draw_color(180, 180, 180); pdf_obj.cell(0, 0, '', 'T', 1); pdf_obj.ln(2)

    if sorted_trips:
        start_date_obj, end_date_obj = sorted_trips[0]['arrival_date'], sorted_trips[-1]['departure_date']
        start_str, end_str = start_date_obj.strftime('%d %b %Y').upper(), end_date_obj.strftime('%d %b %Y').upper()
        dest_str = sorted_trips[-1]['country'].upper()
        pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(220, 220, 220); pdf.cell(80, 7, f"{start_str}   {end_str}", 1, 0, 'C', fill=True); pdf.cell(0, 7, f"TRIP TO {dest_str}", 1, 1, 'C', fill=True)
    pdf.ln(5)
    
    pnr, airline_code = (sorted_trips[0].get('pnr', 'N/A'), sorted_trips[0].get('airline', 'TVK')[:3].upper()) if sorted_trips else ('N/A', 'TVK')
    pdf.set_font('Arial', '', 9); pdf.cell(50, 5, "PREPARED FOR", 0, 1, 'L'); pdf.set_font('Arial', 'B', 12); pdf.cell(50, 6, main_passenger, 0, 1, 'L')
    pdf.ln(3); pdf.set_font('Arial', '', 9); pdf.cell(60, 5, "RESERVATION CODE", 0, 0, 'L'); pdf.cell(60, 5, "AIRLINE RESERVATION CODE", 0, 1, 'L')
    pdf.set_font('Arial', 'B', 10); pdf.cell(60, 6, pnr, 0, 0, 'L'); pdf.cell(60, 6, f"{pnr} ({airline_code})", 0, 1, 'L'); draw_line_separator(pdf)

    for i, trip in enumerate(sorted_trips):
        start_date_obj, airline_name = trip['arrival_date'], trip.get('airline', 'Travaky Airlines')
        departure_day_str, arrival_day_str = start_date_obj.strftime('%A %d %b').upper(), (start_date_obj + datetime.timedelta(days=1)).strftime('%A %d %b').upper()
        pdf.set_font('Arial', 'B', 10); pdf.cell(0, 7, f"> DEPARTURE: {departure_day_str}  >  ARRIVAL: {arrival_day_str}", 0, 1)
        pdf.set_font('Arial', '', 8); pdf.cell(0, 4, "Please verify flight times prior to departure", 0, 1); pdf.ln(2)
        y_before_leg = pdf.get_y()
        pdf.set_font('Arial', 'B', 12); pdf.cell(45, 6, airline_name, 0, 1, 'L')
        pdf.set_font('Arial', 'B', 14); pdf.cell(45, 8, trip.get('flight_no', 'N/A'), 0, 1, 'L'); pdf.set_y(pdf.get_y() + 5)
        pdf.set_font('Arial', '', 9); pdf.cell(45, 5, f"Duration:\n{random.randint(7,12)}hr(s) {random.randint(0,59)}min(s)", 0, 1, 'L')
        pdf.cell(45, 5, "Class: Economy", 0, 1, 'L'); pdf.cell(45, 5, "Status: Confirmed", 0, 1, 'L'); y_after_col1 = pdf.get_y()
        pdf.set_y(y_before_leg); pdf.set_x(55)
        origin_country = hometown if i == 0 else sorted_trips[i-1]['country']
        origin_code, dest_country, dest_code = ("XXX" if i == 0 else AIRPORT_CODES.get(origin_country, 'YYY')), trip['country'], AIRPORT_CODES.get(trip['country'], 'ZZZ')
        pdf.set_font('Arial', 'B', 16); pdf.cell(50, 8, origin_code, 0, 0, 'L'); pdf.cell(10, 8, '>', 0, 0, 'C'); pdf.cell(50, 8, dest_code, 0, 1, 'L')
        pdf.set_x(55); pdf.set_font('Arial', '', 9); pdf.cell(60, 5, origin_country, 0, 0, 'L'); pdf.cell(60, 5, dest_country, 0, 1, 'L')
        pdf.set_x(55); pdf.rect(pdf.get_x(), pdf.get_y()+2, 90, 18); pdf.ln(3)
        pdf.set_x(57); pdf.cell(45, 5, "Departing At:", 0, 0, 'L'); pdf.cell(45, 5, "Arriving At:", 0, 1, 'L')
        pdf.set_x(57); pdf.set_font('Arial', 'B', 10); pdf.cell(45, 5, trip.get('dep_time', 'N/A'), 0, 0, 'L'); pdf.cell(45, 5, trip.get('arr_time', 'N/A'), 0, 1, 'L')
        pdf.set_x(57); pdf.set_font('Arial', '', 9); pdf.cell(45, 5, f"({start_date_obj.strftime('%a, %d %b')})", 0, 0, 'L'); pdf.cell(45, 5, f"({(start_date_obj + datetime.timedelta(days=1)).strftime('%a, %d %b')})", 0, 1, 'L')
        pdf.set_y(y_before_leg); pdf.set_x(150); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, "Aircraft:", 0, 1, 'L')
        pdf.set_x(150); pdf.set_font('Arial', 'B', 9); pdf.cell(0, 5, f"BOEING {random.choice(['777-300ER', '787-9', 'A350-900'])}", 0, 1, 'L')
        pdf.set_y(max(y_after_col1, pdf.get_y() + 10)); pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', '', 9)
        pdf.cell(95, 7, f"Passenger Name:  » {main_passenger}", 'T', 0, 'L', fill=True); pdf.cell(95, 7, "Seats:  Check-In Required", 'T', 1, 'L', fill=True)
        draw_line_separator(pdf)

    return bytes(pdf.output(dest='S'))

def create_cover_letter_pdf(text: str) -> bytes:
    """Creates a PDF from the provided cover letter text."""
    pdf = PDF()
    pdf.set_font('Arial', '', 12)
    pdf.add_page()
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, safe_text)
    return bytes(pdf.output(dest='S'))