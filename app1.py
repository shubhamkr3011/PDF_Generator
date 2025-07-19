import streamlit as st
import datetime
import uuid
import json 
import services
import pdf_generator
import html_generator # Import the new HTML generator
import ui_components

# --- PAGE CONFIGURATION & CLIENT INITIALIZATION ---
st.set_page_config(page_title="Travaky Document Generator", layout="wide")
supabase = services.init_supabase_connection()
llm_client = services.init_groq_client()

st.title("Travaky Document Generator")

# Fetch all hotels once and pass the list to the UI component.
all_hotels = services.get_all_hotels(supabase)
ui_components.manage_trips_and_guests(all_hotels)
st.markdown("---")

# --- MAIN FORM FOR DOCUMENT GENERATION ---
with st.form("travel_form"):
    st.header("Applicant Information")
    c1, c2, c3, c4 = st.columns(4)
    passenger_name = c1.text_input("Full Name*", placeholder="John Doe")
    hometown = c2.text_input("Hometown*", placeholder="New York")
    age = c3.number_input("Age*", min_value=1, step=1)
    gender = c4.selectbox("Gender", ["Male", "Female", "Other"])

    st.subheader("Employment & Passport Details (for Cover Letter)")
    c1, c2 = st.columns(2)
    job_title = c1.text_input("Job Title")
    company_name = c2.text_input("Company Name")
    
    # <<< CHANGE HERE: Added Phone Number input >>>
    c1, c2, c3 = st.columns(3)
    joining_date = c1.date_input("Joining Date", datetime.date(2020, 1, 1))
    passport_number = c2.text_input("Passport Number")
    phone_number = c3.text_input("Contact Phone Number") # New Field
    
    st.subheader("Overall Flight Cost")
    flight_cost = st.number_input(
        "Total Flight Cost (per person, in USD)", 
        min_value=0.0, 
        step=50.0, 
        value=1200.0, 
        help="This cost will be shown in the 'Fare Breakup' section of the flight ticket."
    )

    # --- Document Selection ---
    st.header("Select Documents to Generate")
    st.markdown("##### PDF Format")
    c1, c2, c3, c4 = st.columns(4)
    wants_pdf_flight = c1.checkbox("PDF Flight Ticket", True)
    wants_pdf_hotel = c2.checkbox("PDF Hotel Booking", True)
    wants_pdf_itinerary = c3.checkbox("PDF Itinerary", True)
    wants_pdf_cover = c4.checkbox("PDF Cover Letter", True)
    
    st.markdown("##### HTML Format (Ocean Blue Theme)")
    c1, c2, c3, c4 = st.columns(4)
    wants_html_flight = c1.checkbox("HTML Flight Ticket")
    wants_html_hotel = c2.checkbox("HTML Hotel Booking")
    wants_html_itinerary = c3.checkbox("HTML Itinerary")
    wants_html_cover = c4.checkbox("HTML Cover Letter")

    submitted = st.form_submit_button("Generate & Store Documents", type="primary")

# --- FORM SUBMISSION LOGIC ---
if submitted:
    if not passenger_name or not age or not hometown:
        st.error("Please fill in all required (*) fields: Name, Hometown, and Age.")
    elif not any(t.get('country') for t in st.session_state.trips):
        st.error("Please add at least one trip.")
    else:
        # --- GATHER ALL DATA FOR PROCESSING ---
        selected_hotels_per_trip = []
        for i, trip in enumerate(st.session_state.trips):
            selection_key = f"hotel_selection_{i}"
            if selection_key in st.session_state and st.session_state[selection_key] is not None:
                selected_hotels_per_trip.append({
                    "trip_data": trip,
                    "hotel_data": st.session_state[selection_key]
                })

        record_uuid = str(uuid.uuid4())
        full_trips_data = st.session_state.trips
        family_data = [m for m in st.session_state.family_members if m.get('name')]
        selected_hotel_names = ", ".join([stay['hotel_data']['Hotel Name'] for stay in selected_hotels_per_trip]) if selected_hotels_per_trip else None

        form_data = {
            "uuid": record_uuid, "passenger_name": passenger_name, "age": age, "gender": gender,
            "hometown": hometown, "flight_cost": flight_cost,
            "trips": full_trips_data, "family_members": family_data, "job_title": job_title,
            "company_name": company_name, "joining_date": str(joining_date), "passport_number": passport_number,
            "phone_number": phone_number, # <-- ADD THIS LINE
            "selected_hotels_per_trip": selected_hotels_per_trip, "selected_hotel": selected_hotel_names
        }
        
        document_urls = {}
        with st.spinner("Generating and uploading documents..."):
            # --- PDF GENERATION ---
            if wants_pdf_flight:
                pdf_bytes = pdf_generator.create_flight_ticket_pdf(form_data)
                url = services.upload_and_get_url(supabase, pdf_bytes, "travel-documents", f"{record_uuid}/flight.pdf", "application/pdf")
                if url: document_urls['pdf_flight_ticket_url'] = url
            
            if wants_pdf_hotel and selected_hotels_per_trip:
                pdf_bytes = pdf_generator.create_hotel_booking_pdf(form_data)
                url = services.upload_and_get_url(supabase, pdf_bytes, "travel-documents", f"{record_uuid}/hotel.pdf", "application/pdf")
                if url: document_urls['pdf_hotel_booking_url'] = url

            if wants_pdf_itinerary:
                pdf_bytes = pdf_generator.create_itinerary_pdf(form_data)
                url = services.upload_and_get_url(supabase, pdf_bytes, "travel-documents", f"{record_uuid}/itinerary.pdf", "application/pdf")
                if url: document_urls['pdf_itinerary_url'] = url

            if wants_pdf_cover:
                text = services.generate_cover_letter_text(llm_client, form_data)
                pdf_bytes = pdf_generator.create_cover_letter_pdf(text)
                url = services.upload_and_get_url(supabase, pdf_bytes, "travel-documents", f"{record_uuid}/cover_letter.pdf", "application/pdf")
                if url: document_urls['pdf_cover_letter_url'] = url

            # --- HTML GENERATION ---
            if wants_html_flight:
                html_content = html_generator.create_flight_ticket_html(form_data).encode('utf-8')
                url = services.upload_and_get_url(supabase, html_content, "travel-documents", f"{record_uuid}/flight.html", "text/html")
                if url: document_urls['html_flight_url'] = url
            
            if wants_html_hotel and selected_hotels_per_trip:
                html_content = html_generator.create_hotel_booking_html(form_data).encode('utf-8')
                url = services.upload_and_get_url(supabase, html_content, "travel-documents", f"{record_uuid}/hotel.html", "text/html")
                if url: document_urls['html_hotel_url'] = url

            if wants_html_itinerary:
                html_content = html_generator.create_itinerary_html(form_data).encode('utf-8')
                url = services.upload_and_get_url(supabase, html_content, "travel-documents", f"{record_uuid}/itinerary.html", "text/html")
                if url: document_urls['html_itinerary_url'] = url

            if wants_html_cover:
                text = services.generate_cover_letter_text(llm_client, form_data)
                html_content = html_generator.create_cover_letter_html(text).encode('utf-8')
                url = services.upload_and_get_url(supabase, html_content, "travel-documents", f"{record_uuid}/cover_letter.html", "text/html")
                if url: document_urls['html_cover_letter_url'] = url

        if document_urls:
            st.success("✅ Documents generated and uploaded!")
            
            # --- PREPARE RECORD FOR DATABASE ---
            db_record = form_data.copy()
            del db_record['selected_hotels_per_trip']
            
            serializable_trips = []
            for trip in db_record['trips']:
                trip_copy = trip.copy()
                trip_copy['arrival_date'] = str(trip['arrival_date'])
                trip_copy['departure_date'] = str(trip['departure_date'])
                serializable_trips.append(trip_copy)
            
            db_record['trips'] = serializable_trips
            db_record.update(document_urls)

            try:
                supabase.table("travel_records").insert(db_record).execute()
                st.subheader("Your Permanent Document Links:")
                for name, url in document_urls.items():
                    st.markdown(f"📄 **{name.replace('_', ' ').title()}:** [View/Download Here]({url})")
            except Exception as e:
                st.error(f"Database error: {e}")
        else:
            st.warning("No documents were selected or generated.")

# --- DISPLAY PAST RECORDS FROM MODULE ---
ui_components.display_past_records(supabase)