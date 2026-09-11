import streamlit as st
import time
from google import genai
from google.genai import errors
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

API_KEY = st.secrets["API_KEY"]

st.title("Tutor AI - Geografi")
st.write("Tanyakan sesuatu tentang materi Geografi, tutor ini akan membantumu menjawab.")

SYSTEM_PROMPT = """
Kamu adalah asisten AI yang membantu siswa SMA kelas XI belajar materi
Geografi.

ATURAN UTAMA:
1. Jawab pertanyaan siswa secara langsung, jelas, dan lengkap.
2. Berikan penjelasan yang mudah dipahami disertai contoh konkret.
3. Jika siswa meminta data atau fakta, kamu BOLEH memberikan data
   tersebut secara langsung beserta penjelasan/kesimpulannya.
4. Jika kamu tidak memiliki data yang akurat atau terkini untuk
   menjawab permintaan siswa, katakan dengan jujur bahwa kamu
   tidak memiliki informasi tersebut, dan sarankan siswa mencari
   langsung dari sumber resmi seperti BPS, BNPB, atau jurnal terkait,
   alih-alih memberikan data yang tidak pasti kebenarannya.
5. Jangan pernah mengarang data, fakta, atau tautan yang tidak
   benar-benar ada.
6. Gunakan bahasa yang ramah dan sesuai usia siswa SMA.
"""

client = genai.Client(api_key=API_KEY)


@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(creds)
    sheet = gc.open("Log Chatbot Skripsi").sheet1
    return sheet


def simpan_log(kelompok, pengirim, pesan):
    try:
        sheet = get_sheet()
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([waktu, kelompok, pengirim, pesan])
        st.toast("Log tersimpan ke Google Sheets ✅")
    except Exception as e:
        st.error(f"GAGAL menyimpan log: {e}")


if "chat" not in st.session_state:
    st.session_state.client = client
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-3.6-flash",
        config={"system_instruction": SYSTEM_PROMPT}
    )
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

pesan_siswa = st.chat_input("Ketik pertanyaanmu di sini...")

if pesan_siswa:
    st.session_state.messages.append({"role": "user", "content": pesan_siswa})
    with st.chat_message("user"):
        st.write(pesan_siswa)
    simpan_log("Kontrol", "Siswa", pesan_siswa)

    jawaban = None
    percobaan_maksimal = 3
    for percobaan in range(percobaan_maksimal):
        try:
            response = st.session_state.chat.send_message(pesan_siswa)
            jawaban = response.text
            break
        except errors.ServerError:
            if percobaan < percobaan_maksimal - 1:
                with st.spinner(f"Server sedang sibuk, mencoba lagi... ({percobaan + 1}/{percobaan_maksimal})"):
                    time.sleep(5)
            else:
                jawaban = "Maaf, server sedang sangat sibuk. Silakan coba kirim pesanmu lagi beberapa saat lagi."

    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    with st.chat_message("assistant"):
        st.write(jawaban)
    simpan_log("Kontrol", "Chatbot", jawaban)
