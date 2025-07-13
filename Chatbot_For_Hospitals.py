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

def scrape_hospital_data(url_tuple):
    name, url = url_tuple
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
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
    except:
        return name, "Information not available due to a network or access issue."

def generate_response(query, hospital_data, history):
    context_data = ""
    for hospital, data in hospital_data.items():
        if "Information not available" not in data:
            context_data += f"\n--- Hospital: {hospital} ---\n{data}\n"
        if hospital in MANUAL_DOCTOR_DATA:
            context_data += f"\n--- Doctors at {hospital} ---\n"
            for doc in MANUAL_DOCTOR_DATA[hospital]:
                context_data += f"- {doc['name']} ({doc['specialty']}): {doc['info']}\n"

    if not context_data.strip():
        context_data = "No specific hospital or doctor information was successfully scraped or provided. I can provide general assistance."

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
    """)

    chat_messages = [{"role": "user", "parts": [{"text": prompt}]}]
    for m in history:
        role = m.get("role")
        content = m.get("content")
        if role and content:
            chat_messages.append({"role": role, "parts": [{"text": content}]})
    chat_messages.append({"role": "user", "parts": [{"text": query}]})

    try:
        result = model.generate_content(chat_messages)
        return result.text if result.text else "Sorry, I couldn't generate a response."
    except:
        return "Sorry, I encountered an error with the AI service."

custom_css = """
body { background: linear-gradient(to bottom, #e0f7fa, #ffffff); font-family: 'Segoe UI', sans-serif; }
.gr-button { background-color: #0077cc !important; color: white !important; border-radius: 8px !important; font-weight: bold; }
textarea, input { border-radius: 8px; padding: 10px; font-size: 16px; }
.file-wrap { background-color: #e6f2ff; padding: 10px; border-radius: 8px; }
#component-0 { font-size: 22px; font-weight: bold; color: #004d99; text-align: center; }
.chatbot { border: 2px solid #0077cc; border-radius: 12px; }
"""

chatbot = gr.Chatbot(label="🧠 Chat History", type="messages", elem_classes="chatbot")
msg = gr.Textbox(label="💬 Your Message", placeholder="Type your message here...")
send_btn = gr.Button("📨 Send")
clear_btn = gr.Button("🗑️ Clear")
prescription_file = gr.File(label="📄 Download Prescription", visible=False)

def chat(message, chat_history):
    if chat_history is None:
        chat_history = []
    ai_response = generate_response(message, SCRAPED_HOSPITAL_DATA, chat_history)
    chat_part = ai_response
    prescription_content = None
    if "### Simulated Prescription Paper" in ai_response:
        parts = ai_response.split("### Simulated Prescription Paper", 1)
        chat_part = parts[0].strip()
        prescription_markdown = "### Simulated Prescription Paper" + parts[1].strip()
        temp_file_name = f"prescription_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(temp_file_name, "w") as f:
            f.write(prescription_markdown)
        prescription_content = temp_file_name
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": chat_part})
    return "", chat_history, gr.update(value=prescription_content, visible=bool(prescription_content))

with gr.Blocks(title="🏥 Jaipur Hospital Chatbot", css=custom_css) as demo:
    gr.Markdown("""
    # 🏥 Jaipur Hospital Chatbot
    👋 Hello! I'm your Jaipur Hospital Chatbot. Ask me about hospitals 🏨, doctors 👨‍⚕️👩‍⚕️, or book appointments!
    """)
    chatbot.render()
    with gr.Row():
        msg.render()
        send_btn.render()
    prescription_file.render()
    clear_btn.render()
    send_btn.click(chat, [msg, chatbot], [msg, chatbot, prescription_file])
    msg.submit(chat, [msg, chatbot], [msg, chatbot, prescription_file])
    clear_btn.click(lambda: ("", [], gr.update(value=None, visible=False)), None, [msg, chatbot, prescription_file])

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as executor:
        for name, data in executor.map(scrape_hospital_data, HOSPITAL_URLS.items()):
            SCRAPED_HOSPITAL_DATA[name] = data
    demo.launch(share=True)
