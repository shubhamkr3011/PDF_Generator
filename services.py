import streamlit as st
from supabase import create_client, Client
from groq import Groq
import datetime

# --- CLIENT INITIALIZATION ---

@st.cache_resource
def init_supabase_connection() -> Client:
    """Initializes and returns the Supabase client."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

@st.cache_resource
def init_groq_client() -> Groq:
    """Initializes and returns the Groq LLM client."""
    return Groq(api_key=st.secrets["groq"]["api_key"])

# --- HELPER FUNCTIONS ---

def upload_and_get_url(supabase: Client, file_bytes: bytes, bucket_name: str, file_path: str, content_type: str) -> str | None:
    """Uploads a file to a Supabase bucket with a specific content type and returns its public URL."""
    try:
        supabase.storage.from_(bucket_name).upload(
            file=file_bytes,
            path=file_path,
            # This line now uses the 5th argument correctly
            file_options={"content-type": content_type} 
        )
        return supabase.storage.from_(bucket_name).get_public_url(file_path)
    except Exception as e:
        if "Duplicate" in str(e):
            st.warning(f"File {file_path} already exists. Reusing.")
            return supabase.storage.from_(bucket_name).get_public_url(file_path)
        else:
            st.error(f"Upload Error for {file_path}: {e}")
            return None


# In services.py, replace the existing function with this one.

def generate_cover_letter_text(llm_client: Groq, data: dict) -> str:
    """Generates a professional visa cover letter using a strict, user-provided template."""
    
    # --- Prepare Data ---
    today_date = datetime.date.today().strftime("%d/%m/%Y")
    full_name = data.get('passenger_name', '[Your Full Name]')
    
    main_country, start_date_str, end_date_str = "your destination", "[Start Date]", "[End Date]"
    if data.get('trips'):
        sorted_trips = sorted(data['trips'], key=lambda x: x['arrival_date'])
        main_country = sorted_trips[0]['country']
        start_date_obj = sorted_trips[0]['arrival_date']
        end_date_obj = sorted_trips[-1]['departure_date']
        start_date_str = start_date_obj.strftime('%d %B %Y')
        end_date_str = end_date_obj.strftime('%d %B %Y')

    job_title = data.get('job_title', '[Your Job Title]')
    company_name = data.get('company_name', '[Company Name]')
    joining_date_str = str(data.get('joining_date', '[Joining Date]'))
    
    # Use the new phone number field
    contact_no = data.get('phone_number', '[XXXXXXXXX]')

    # --- THIS IS THE NEW, STRICT PROMPT ---
    # It explicitly forbids any extra text, comments, or descriptions.
    prompt = f"""You are a silent text-replacement tool. Your ONLY job is to fill the placeholders in the provided template with the provided data.
    DO NOT add any conversational text like "Here is the letter...".
    DO NOT add any descriptions of formatting like "[Front page]" or "[Ocean blue background]".
    DO NOT add any extra placeholders like "[Signature]".
    Produce ONLY the raw, filled-in letter text and nothing else.

    Data to use:
    - [DD/MM/YYYY]: {today_date}
    - [Country Name]: {main_country}
    - [Your Full Name]: {full_name}
    - [Start Date]: {start_date_str}
    - [End Date]: {end_date_str}
    - [Your Job Title]: {job_title}
    - [Company Name]: {company_name}
    - [Joining Date]: {joining_date_str}
    - [XXXXXXXXX]: {contact_no}

    --- TEMPLATE ---
    Date: {today_date}

    To,
    The Visa Officer
    Embassy of {main_country}

    Subject: Tourist Visa Application

    Dear Sir/Madam,

    I am writing to submit my application for a short-term tourist visa to visit {main_country} from {start_date_str} to {end_date_str}.

    This trip is purely for tourism purposes. I plan to explore a few major cities and cultural landmarks during this time. My aim is to learn more about the country's history, architecture, and way of life, while taking a short break from my professional routine in India.

    I am currently working as a {job_title} with {company_name} and have been employed here since {joining_date_str}. My leave for this trip has already been approved, and I am financially prepared to support all travel-related expenses on my own. My travel insurance, round-trip flight bookings, hotel reservations, and detailed travel plan are included in the application.

    I understand the importance of following visa regulations and assure you that I will fully comply with the terms of the visa. I have strong ties to India, both professionally and personally, and I will be returning after my visit as scheduled.

    Please find below the list of documents enclosed with this application:

    -Completed visa application form
    -Passport with required validity
    -Flight and hotel bookings
    -Proof of travel insurance
    -Leave approval from employer
    -Bank statements and ITRs
    -Day-wise travel itinerary
    -This covering letter

    I hope you find everything in order, and I remain available for any further clarification if needed.

    Thank you for considering my request.

    Sincerely,
    {full_name}
    Contact No.: {contact_no}
    """
    
    chat_completion = llm_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192"
    )
    
    # Return only the raw message content, which should now be clean.
    return chat_completion.choices[0].message.content
# Replace the get_hotel_options function with this one.
# The other functions in the file remain unchanged.

def get_all_hotels(supabase: Client) -> list:
    """Fetches ALL hotel records from the Supabase table."""
    try:
        # We fetch everything and will filter it in the main app.
        response = supabase.table("hotel_attraction_list").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Fatal Error: Could not fetch hotel database. {e}")
        return []