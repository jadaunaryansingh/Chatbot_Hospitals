import sys
sys.path.append(r"C:\Users\coder\OneDrive\Documents\Python Libraries")
import requests
from bs4 import BeautifulSoup
import time
import google.generativeai as genai
import os
import textwrap
import gradio as gr
from concurrent.futures import ThreadPoolExecutor
import datetime 
os.environ["GOOGLE_API_KEY"] = "AIzaSyDB-abo6SyU9xyKfiV6yPejb0piDJYX8Dc"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
HOSPITAL_URLS = {
    "All hospitals":"https://m.edarabia.com/hospitals-clinics/india/?",
    "SDMH Hospital Jaipur":"https://sdmh.in/",
    "CK Birla Hospitals, Jaipur": "https://ckbirlahospitals.com/rbh",
    "Jaipur Hospital": "https://jaipurhospital.in/",
    "Rungta Hospital Jaipur": "https://rungtahospital.com/",
    "MG Hospital & Research Centre Jaipur": "https://mgmch.org/",
    "Shalby Hospital Jaipur": "https://shalby.org/hospitals/jaipur-shalby/",
    "Rajasthan Hospital Jaipur": "https://rajasthanhospital.in/",
    "Manipal Hospital Jaipur": "https://www.manipalhospitals.com/jaipur/",
    "Bhagwan Mahaveer Cancer Hospital & Research Centre Jaipur": "https://bmchrc.org/",
    "Eternal Hospital Jaipur": "https://ehcc.org/",
    "Goyal Hospital & Research Centre Jaipur": "https://www.goyalhospital.org/",
    "Yashaman Hospital Jaipur": "https://www.yashamanhospital.com/",
    "ASG Eye Hospital Jaipur": "https://www.asgeyehospital.com/",
    "Manidhari Hospital Jaipur": "https://manidharihospital.com/",
    "Daukiya Hospital Jaipur": "https://www.daukiyahospital.com/"
}
SCRAPED_HOSPITAL_DATA = {}
MANUAL_DOCTOR_DATA = {
    "SDMH Hospital Jaipur": [
        {"name": "Dr. Rahul Verma", "specialty": "Cardiologist", "info": "Senior Cardiologist, specializes in interventional cardiology."},
        {"name": "Dr. Smita Singh", "specialty": "Cardiologist", "info": "Cardiologist, expert in heart failure management."},
        {"name": "Dr. Alok Kumar", "specialty": "Neurologist", "info": "Consultant Neurologist, expert in epilepsy."}
    ],
    "CK Birla Hospitals, Jaipur": [
        {"name": "Dr. Priya Sharma", "specialty": "Cardiologist", "info": "Known for non-invasive cardiology procedures."},
        {"name": "Dr. Vivek Jain", "specialty": "Orthopedic Surgeon", "info": "Specializes in joint replacement and sports injuries."}
    ],
    "Manipal Hospital Jaipur": [
        {"name": "Dr. Seema Gupta", "specialty": "Pediatrician", "info": "Experienced in child health and vaccinations."},
        {"name": "Dr. Ritesh Modi", "specialty": "General Surgeon", "info": "Specializes in laparoscopic surgeries."}
    ]
    
}


# --- Web Scraping Function ---
def scrape_hospital_data(url_tuple):
    name, url = url_tuple
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        print(f"Scraping {name} (Threaded)...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        main_content_tags = ['p', 'h1', 'h2', 'h3', 'li', 'span', 'div']
        relevant_text = []
        
        filter_keywords = [
            'privacy', 'terms', 'copyright', 'menu', 'subscribe', 'button', 
            'search', 'home', 'footer', 'header', 'navigation', 'login', 
            'sign up', 'cookie policy', 'site map', 'contact us', 'all rights reserved'
        ]

        for tag_name in main_content_tags:
            for tag in soup.find_all(tag_name):
                text = tag.get_text(separator=' ', strip=True)
                if len(text) > 20 and not any(keyword in text.lower() for keyword in filter_keywords):
                    relevant_text.append(text)

        full_text = " ".join(relevant_text)
        return name, ' '.join(full_text.split())[:5000]
    
    except requests.exceptions.RequestException as e:
        print(f"Network or request error scraping {name} ({url}): {e}")
        return name, "Information not available due to a network or access issue."
    except Exception as e:
        print(f"General error scraping {name} ({url}): {e}")
        return name, "Information could not be retrieved from this website."

# --- Gemini-based Response Generation Function ---
def generate_response(query, hospital_data, conversation_history):
    context_data = ""
    for hospital, data in hospital_data.items():
        if "Information not available" not in data:
            context_data += f"\n--- Hospital: {hospital} ---\n{data}\n"
        
        # Add manual doctor data to the context
        if hospital in MANUAL_DOCTOR_DATA:
            context_data += f"\n--- Doctors at {hospital} ---\n"
            for doc in MANUAL_DOCTOR_DATA[hospital]:
                context_data += f"- {doc['name']} ({doc['specialty']}): {doc['info']}\n"
    
    if not context_data.strip():
        context_data = "No specific hospital or doctor information was successfully scraped or provided. I can provide general assistance."

    # --- Updated Prompt for Appointment and Prescription ---
    prompt = textwrap.dedent(f"""
    You are a helpful chatbot providing information about hospitals and doctors in Jaipur.
    Your responses must be based ONLY on the following provided data.
    If you are asked a question that cannot be answered from this data, state that you do not have that specific information.
    Do NOT make up information.
    
    Here is the available hospital and doctor data:
    {context_data}

    If a user asks to book an appointment, follow these steps for a simulated booking:
    1. First, ask for the preferred hospital name and the patient's full name.
    2. Next, ask for the reason for their visit (e.g., general check-up, specific medical issue, specialist consultation).
    3. Then, ask if they have a preferred doctor. If they mention a doctor, check if that doctor is in your provided data for that hospital. If not, do not state that you don't have information on that specific doctor but you can proceed with general appointment by stating that i dont have information regarding the specified doctor but if he is available in the hospital .
    4. After that, ask for their preferred date and time for the appointment.
    5. When all necessary details (hospital name, patient name, reason, preferred doctor (or "any available"), date, and time) have been successfully collected, you MUST do the following in ONE SINGLE RESPONSE:
        a. State: "Appointment booked successfully!"
        b. Summarize the complete booking details clearly.
        c. Immediately following the summary, generate a simulated pdf , empty prescription paper in the EXACT MARKDOWN FORMAT provided below. Fill in the placeholders [ ] with the gathered information. If a doctor was not specified, use "Any available doctor". For the date on the prescription, use the appointment date you collected and at top mention th hospital name in bold and at top corner write booking with medibot.

    ```
    ### Simulated Prescription Paper booked by Medibot

    **Hospital:** [Hospital Name]
    **Patient Name:** [Patient Full Name]
    **Doctor:** [Doctor Name or Any available doctor]
    **Date of Appointment:** [Appointment Date]
    **Time of Appointment:** [Appointment Time]

    ---
    **Medication / Notes:**
    __________________________________________________
    __________________________________________________
    __________________________________________________
    __________________________________________________

    **Doctor's Signature:** _________________________

    *This is a simulated prescription for demonstration purposes only. Consult a real doctor for medical advice.*
    ```
    Ensure all bracketed placeholders `[ ]` in the prescription format are accurately filled using the collected information.
    """)
    # --- End Updated Prompt ---

    chat_messages = []
    chat_messages.append({"role": "user", "parts": [{"text": prompt}]})

    # Convert Gradio's history format (list of lists) to Gemini's expected format (list of dicts)
    for m in conversation_history:
        # User message is m[0], AI message is m[1]
        if m[0] is not None: # User message exists
            chat_messages.append({"role": "user", "parts": [{"text": m[0]}]})
        if m[1] is not None: # AI message exists
            chat_messages.append({"role": "model", "parts": [{"text": m[1]}]})
    
    # Add the current user query to the messages being sent
    chat_messages.append({"role": "user", "parts": [{"text": query}]})

    print("\n--- Messages sent to Gemini API ---")
    for msg_dict in chat_messages:
        # Accessing content safely for printing
        content_preview = msg_dict.get('parts', [{}])[0].get('text', '')[:150]
        print(f"Role: {msg_dict.get('role')}, Content: \"{content_preview}...\"")
    print("-----------------------------------")

    try:
        result = model.generate_content(chat_messages)
        
        print(f"--- Gemini Raw Result: {result} ---")
        if hasattr(result, 'text') and result.text:
            print(f"--- Gemini Text Result (Preview): {result.text[:200]}... ---")
        else:
            # FIX: Corrected the unterminated string literal here
            print("--- Gemini Result has no 'text' attribute or is empty. Potential content block or empty reply. ---")
            return "Sorry, I couldn't generate a response for that. The AI might have found the query sensitive, or returned an empty reply."
        print("---------------------------------")
        
        return result.text
    
    except Exception as e:
        print(f"--- Gemini API Error ---")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_details = e.response.json()
                print(f"API Response Error Details: {error_details}")
            except ValueError:
                print(f"API Response Raw Text: {e.response.text}")
        print("------------------------")
        return "Sorry, I encountered an issue communicating with the AI. Please try again or check the console for details."

# --- Gradio Chatbot Interface Logic (now using Blocks) ---
# Global Gradio components
chatbot = gr.Chatbot(height=400, label="Conversation") # Changed height for better layout
msg = gr.Textbox(label="Your Message", placeholder="Type your message here...", lines=1)
send_btn = gr.Button("Send")
clear_btn = gr.Button("Clear")

# New component for prescription download
prescription_file = gr.File(label="Download Prescription", visible=False) # Initially hidden

# Function to handle chat submission and potentially file download
def chat_and_download(message, chat_history):
    # Ensure chat_history is a list (Gradio might pass None initially for an empty chat)
    if chat_history is None:
        chat_history = []

    # Call generate_response to get the AI's reply
    # Note: We pass chat_history directly to generate_response which expects
    # Gradio's internal list-of-lists history format.
    ai_response = generate_response(message, SCRAPED_HOSPITAL_DATA, chat_history)

    # --- Process AI Response for Prescription ---
    prescription_content = None
    chat_part = ai_response

    # Check if the AI's response contains the prescription marker
    if "### Simulated Prescription Paper" in ai_response:
        # Split the response into the conversational part and the prescription part
        parts = ai_response.split("### Simulated Prescription Paper", 1) # Split only on first occurrence
        chat_part = parts[0].strip() # The chat part before the prescription
        prescription_markdown = "### Simulated Prescription Paper" + parts[1].strip() # The full prescription part

        # Generate a unique temporary filename
        # Using a simple .txt for text-based prescription
        temp_file_name = f"simulated_prescription_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        temp_file_path = os.path.join(os.getcwd(), temp_file_name) # Save in current working directory

        # Save the prescription content to the temporary file
        try:
            with open(temp_file_path, "w") as f:
                f.write(prescription_markdown)
            prescription_content = temp_file_path # Store the file path for Gradio's File component
            print(f"Prescription saved to: {temp_file_path}")
        except Exception as e:
            print(f"Error saving prescription file: {e}")
            chat_part += "\n\n*Error generating downloadable prescription. Please copy text manually.*"
            prescription_content = None # Don't try to provide a broken download link

    # --- Update Chat History for gr.Chatbot ---
    # Add user message
    chat_history.append([message, None]) 
    # Add AI response (only the chat part)
    chat_history.append([None, chat_part]) 

    # --- Update Gradio Components ---
    # Return values for the output components:
    # 1. Clear the textbox (msg)
    # 2. Update the chatbot history
    # 3. Update the prescription_file component (its value and visibility)
    if prescription_content:
        return "", chat_history, gr.update(value=prescription_content, visible=True)
    else:
        # If no prescription, ensure the download button is hidden and cleared
        # Reset value to None to clear any previous file if one existed
        return "", chat_history, gr.update(value=None, visible=False)

# --- Build the Gradio Blocks interface ---
with gr.Blocks(theme="soft", title="🏥 Jaipur Hospital Chatbot") as demo:
    gr.Markdown(
        """
        # 🏥 Jaipur Hospital Chatbot
        #Hello! I'm your Jaipur Hospital Chatbot. 
        #I can provide information about hospitals and doctors in Jaipur based on scraped data, 
        #or help you simulate an appointment booking. 
        #When an appointment is 'booked', a simulated prescription will appear below for download!
        """
    )
    
    chatbot.render() # Display the chatbot component
    
    with gr.Row(): # Arrange textbox and send button horizontally
        msg.render()
        send_btn.render()
    
    prescription_file.render() # Display the prescription download component (initially hidden)

    # Examples for convenience
    gr.Examples(
        examples=[
            "I want to book an appointment.",
            "Who is Dr. Rahul Verma?",
            "What services does Manipal Hospital Jaipur offer?",
            "Tell me about cardiologists at SDMH Hospital."
        ],
        inputs=msg
    )

    # Define interactions: what happens when send_btn is clicked or msg is submitted
    send_btn.click(
        fn=chat_and_download, 
        inputs=[msg, chatbot], 
        outputs=[msg, chatbot, prescription_file])
    msg.submit( # Allow pressing Enter in the textbox
        fn=chat_and_download, 
        inputs=[msg, chatbot], 
        outputs=[msg, chatbot, prescription_file]
    )

    # Clear button functionality
    clear_btn.click(
        fn=lambda: ("", [], gr.update(value=None, visible=False)), # Clear textbox, chat, and hide file
        inputs=None, 
        outputs=[msg, chatbot, prescription_file]
    )

# --- Initial Data Scraping Process (runs once on script start) ---
if __name__ == "__main__":
    print("Starting initial data scraping (using threading for speed)...")
    # Using ThreadPoolExecutor to scrape URLs concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        # executor.map applies scrape_hospital_data to each (name, url) tuple
        for name, data in executor.map(scrape_hospital_data, HOSPITAL_URLS.items()):
            SCRAPED_HOSPITAL_DATA[name] = data
    print("Scraping completed. Chatbot is ready!")

    # Launch the Gradio Blocks interface
    demo.launch(share=True) # Set share=True to get a public link if desired