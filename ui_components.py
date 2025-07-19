import streamlit as st
import pandas as pd
import datetime
from supabase import Client

def manage_trips_and_guests(all_hotels: list):
    """Renders the UI for managing trips and guests, with detailed flight inputs per trip."""
    if 'family_members' not in st.session_state:
        st.session_state.family_members = []
    if 'trips' not in st.session_state:
        # Add 'airline' to the default trip
        st.session_state.trips = [{
            'country': 'France', 'arrival_date': datetime.date.today(), 'departure_date': datetime.date.today() + datetime.timedelta(days=7),
            'airline': 'Travaky Airlines', 'pnr': 'ABCDEF', 'flight_no': 'TVK-123', 'ticket_no': '180-1234567890',
            'dep_time': '10:30', 'arr_time': '18:45'
        }]

    def add_trip():
        # Add 'airline' to newly added trips
        st.session_state.trips.append({
            'country': '', 'arrival_date': datetime.date.today(), 'departure_date': datetime.date.today() + datetime.timedelta(days=7),
            'airline': 'Travaky Airlines', 'pnr': '', 'flight_no': '', 'ticket_no': '', 'dep_time': '', 'arr_time': ''
        })
    def remove_trip(i):
        st.session_state.trips.pop(i)
    def add_family():
        st.session_state.family_members.append({'name': '', 'age': 0, 'gender': 'Other'})
    def remove_family(i):
        st.session_state.family_members.pop(i)

    with st.expander("Manage Trips & Guests", expanded=True):
        st.subheader("Travel Plan & Flight Details")
        st.button("Add Trip", on_click=add_trip)
        
        for i, trip in enumerate(st.session_state.trips):
            st.markdown(f"---")
            st.markdown(f"**Trip {i+1}**")
            
            # --- Trip Destination and Dates ---
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            trip['country'] = c1.text_input("Country/City", trip.get('country', ''), key=f"country_{i}")
            trip['arrival_date'] = c2.date_input("Arrival Date", trip.get('arrival_date'), key=f"arr_{i}")
            trip['departure_date'] = c3.date_input("Departure Date", trip.get('departure_date'), key=f"dep_{i}")
            c4.button("❌", key=f"rem_trip_{i}", on_click=remove_trip, args=(i,), help="Remove trip")

            # --- Manual Flight Information Inputs Per Trip ---
            st.markdown("###### Flight Details for this Leg")
            
            # <<< NEW: Added Airline Name input field >>>
            c1, c2, c3 = st.columns(3)
            trip['airline'] = c1.text_input("Airline Name", trip.get('airline', 'Travaky Airlines'), key=f"airline_{i}")
            trip['pnr'] = c2.text_input("PNR", trip.get('pnr', ''), key=f"pnr_{i}")
            trip['flight_no'] = c3.text_input("Flight Number", trip.get('flight_no', ''), key=f"flight_no_{i}")
            
            c1, c2, c3 = st.columns(3)
            trip['dep_time'] = c1.text_input("Departure Time (e.g., 10:30)", trip.get('dep_time', ''), key=f"dep_time_{i}")
            trip['arr_time'] = c2.text_input("Arrival Time (e.g., 18:45)", trip.get('arr_time', ''), key=f"arr_time_{i}")
            trip['ticket_no'] = c3.text_input("E-Ticket Number", trip.get('ticket_no', ''), key=f"ticket_no_{i}")

            # --- Hotel Selection Logic ---
            location_lower = trip['country'].lower() if trip.get('country') else ''
            options_for_this_trip = [h for h in all_hotels if (h.get('City') and h.get('City').lower() == location_lower) or (h.get('Country') and h.get('Country').lower() == location_lower)]
            if options_for_this_trip:
                def format_hotel_option(hotel): return f"{hotel['Hotel Name']} ({hotel['City']}) - EUR {hotel['Rate']}/night"
                st.selectbox(f"Select Hotel for {trip.get('country', f'Trip {i+1}')}", options=[None] + options_for_this_trip, format_func=lambda h: "No Selection" if h is None else format_hotel_option(h), key=f"hotel_selection_{i}")
        
        st.markdown("---")
        st.subheader("Accompanying Guests")
        st.button("Add Guest", on_click=add_family)
        for i, member in enumerate(st.session_state.family_members):
            # <<< CHANGE HERE: Added a column for the Gender selectbox >>>
            c1, c2, c3, c4 = st.columns([4, 1, 2, 1]) 
            member['name'] = c1.text_input(f"Guest {i+1}", member.get('name', ''), key=f"fam_name_{i}")
            member['age'] = c2.number_input("Age", 0, 120, member.get('age', 0), key=f"fam_age_{i}")
            # Add the gender selectbox and store its value
            member['gender'] = c3.selectbox("Gender", ["Male", "Female", "Other"], key=f"fam_gender_{i}")
            c4.button("❌", key=f"rem_fam_{i}", on_click=remove_family, args=(i,), help="Remove guest")

def display_past_records(supabase: Client):
    # This function remains unchanged
    st.markdown("---")
    st.header("Previously Generated Records")
    try:
        response = supabase.table("travel_records").select("*").order("created_at", desc=True).limit(10).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            def format_trips(trip_list):
                if not isinstance(trip_list, list) or not trip_list: return "N/A"
                # This could be improved to show more trip details from the JSON if needed
                countries = [t.get('country', 'N/A') for t in trip_list]
                return ", ".join(countries)
            df['trips'] = df['trips'].apply(format_trips)
            
            url_cols = {col: st.column_config.LinkColumn(display_text="🔗 Link") for col in df.columns if col.endswith('_url')}
            
            st.data_editor(df, column_config=url_cols, use_container_width=True, hide_index=True, disabled=True,
                           column_order=("created_at", "passenger_name", "trips", "selected_hotel", "flight_ticket_url", "hotel_booking_url", "itinerary_url", "cover_letter_url"))
        else:
            st.info("No records found yet.")
    except Exception as e:
        st.error(f"Could not fetch past records: {e}")